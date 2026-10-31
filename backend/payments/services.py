"""The money rules: invoices, payments, bills, instalments and profit. All amounts are whole paise.

Views stay thin and call these functions, so the tests (and other apps) can call them directly.
Every payment write happens inside one transaction that also recomputes the invoice / bill status,
so a status can never disagree with the payments behind it.
"""
import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from payments.models import Expense, Invoice, Payment, PayStatus, VendorPaymentPlan
from weddings.models import Wedding

logger = logging.getLogger(__name__)

METHODS = ("CASH", "UPI", "BANK", "CARD", "RAZORPAY")
DUPLICATE_WINDOW_DAYS = 7


class Conflict(APIException):
    status_code = 409
    default_detail = "This conflicts with what is already saved."
    default_code = "conflict"


class Overpayment(Conflict):
    default_detail = "Overpayment: this is more than the remaining balance."
    default_code = "overpayment"


class Unprocessable(APIException):
    status_code = 422
    default_detail = "This cannot be done."
    default_code = "unprocessable"


def _pk(value):
    """Accepts a model object or an id."""
    return getattr(value, "pk", value)


def derive_status(paid: int, amount: int) -> str:
    """UNPAID / PARTIAL / PAID from the money received so far."""
    if paid >= amount:
        return PayStatus.PAID
    return PayStatus.PARTIAL if paid > 0 else PayStatus.UNPAID


def _paid_sum(queryset) -> int:
    return queryset.aggregate(total=Coalesce(Sum("amount_paise"), 0))["total"]


# ---------------------------------------------------------------- status recomputing

def recompute_invoice(invoice: Invoice) -> Invoice:
    paid = _paid_sum(invoice.payments.all())
    status = derive_status(paid, invoice.amount_paise)
    if invoice.status != status:
        invoice.status = status
        invoice.save(update_fields=["status"])
    return invoice


def allocate_to_plans(plans, payments) -> dict:
    """{plan id: paise covered}. `payments` is a list of (amount, reference) for the plans' bill.

    A payment tagged `milestone:<id>` counts towards that instalment; any other payment fills the
    instalments in order (advance first).
    """
    paid = sum(amount for amount, _ in payments)
    tagged = {plan.pk: sum(a for a, ref in payments if ref == f"milestone:{plan.pk}") for plan in plans}
    loose = paid - sum(tagged.values())
    for plan in plans:
        if loose > 0 and tagged[plan.pk] < plan.amount_paise:
            extra = min(loose, plan.amount_paise - tagged[plan.pk])
            tagged[plan.pk] += extra
            loose -= extra
    return tagged


def recompute_expense(expense: Expense) -> Expense:
    """Updates the bill's status and the status of its advance / final instalments.

    A payment tagged `milestone:<id>` counts towards that instalment; any other payment on the bill fills the
    instalments in order (advance first).
    """
    payments = list(expense.payments.values_list("amount_paise", "reference"))
    paid = sum(amount for amount, _ in payments)
    status = derive_status(paid, expense.amount_paise)
    if expense.status != status:
        expense.status = status
        expense.save(update_fields=["status"])

    plans = list(expense.vendorpaymentplan_set.order_by("part", "id"))  # ADVANCE sorts before FINAL
    for plan_id, covered in allocate_to_plans(plans, payments).items():
        plan = next(p for p in plans if p.pk == plan_id)
        new_status = derive_status(covered, plan.amount_paise)
        if plan.status != new_status:
            plan.status = new_status
            plan.save(update_fields=["status"])
    return expense


# ---------------------------------------------------------------- recording payments

def _existing_for_key(key: str, **target):
    """The payment already saved for this Idempotency-Key, or None. A key reused for something else is refused."""
    if not key:
        return None
    payment = Payment.objects.filter(retry_key=key).first()
    if payment is None:
        return None
    for field, value in target.items():
        if getattr(payment, f"{field}_id") != value:
            raise Conflict("This Idempotency-Key was already used for a different payment.")
    return payment


def _check_amount(amount: int, remaining: int):
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise ValidationError({"amount_paise": ["Enter a whole number of paise greater than zero."]})
    if amount > remaining:
        raise Overpayment(f"Overpayment: only {remaining} paise is still due.")


def _validate_method(method: str) -> str:
    method = (method or "").upper()
    if method not in METHODS:
        raise ValidationError({"method": [f"Choose one of: {', '.join(METHODS)}."]})
    return method


def _insert_payment(**fields) -> tuple[Payment, bool]:
    """Creates the payment; if the same retry key won a race, returns that one instead."""
    try:
        with transaction.atomic():
            return Payment.objects.create(**fields), True
    except IntegrityError:
        key = fields.get("retry_key")
        existing = Payment.objects.filter(retry_key=key).first() if key else None
        if existing is None:
            raise
        return existing, False


def record_invoice_payment(invoice_id: int, amount_paise: int, method: str, reference: str = "", paid_at=None,
                           idempotency_key: str | None = None) -> tuple[Payment, bool]:
    """Money received from the couple. Returns (payment, created); created is False for a replayed key."""
    method = _validate_method(method)
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
        existing = _existing_for_key(idempotency_key, invoice=invoice.pk)
        if existing:
            return existing, False
        remaining = invoice.amount_paise - _paid_sum(invoice.payments.all())
        _check_amount(amount_paise, remaining)
        payment, created = _insert_payment(
            wedding_id=invoice.wedding_id, invoice=invoice, direction=Payment.Direction.IN,
            amount_paise=amount_paise, method=method, reference=reference or "",
            paid_at=paid_at or timezone.now(), retry_key=idempotency_key or None)
        recompute_invoice(invoice)
    return payment, created


def record_expense_payment(expense_id: int, amount_paise: int, method: str, reference: str = "", paid_at=None,
                           idempotency_key: str | None = None, milestone: VendorPaymentPlan | None = None
                           ) -> tuple[Payment, bool]:
    """Money paid to a vendor. `milestone` tags the payment as one of the advance / final instalments."""
    method = _validate_method(method)
    with transaction.atomic():
        expense = Expense.objects.select_for_update().get(pk=expense_id)
        existing = _existing_for_key(idempotency_key, expense=expense.pk)
        if existing:
            return existing, False
        remaining = expense.amount_paise - _paid_sum(expense.payments.all())
        if milestone is not None:
            tag = f"milestone:{milestone.pk}"
            milestone_paid = _paid_sum(expense.payments.filter(reference=tag))
            remaining = min(remaining, milestone.amount_paise - milestone_paid)
            reference = tag
        _check_amount(amount_paise, remaining)
        payment, created = _insert_payment(
            wedding_id=expense.wedding_id, expense=expense, direction=Payment.Direction.OUT,
            amount_paise=amount_paise, method=method, reference=reference or "",
            paid_at=paid_at or timezone.now(), retry_key=idempotency_key or None)
        recompute_expense(expense)
    return payment, created


# ---------------------------------------------------------------- invoices

def create_invoice(wedding: Wedding, kind: str, amount_paise: int, due_date=None, note: str = "") -> Invoice:
    if kind not in Invoice.Kind.values:
        raise ValidationError({"type": [f"Choose one of: {', '.join(Invoice.Kind.values)}."]})
    if amount_paise is None or amount_paise <= 0:
        raise ValidationError({"amount_paise": ["Enter an amount greater than zero."]})
    return Invoice.objects.create(wedding=wedding, client_id=wedding.client_id, kind=kind,
                                  amount_paise=amount_paise, due_date=due_date, note=note or "")


def extra_guest_charge(wedding: Wedding, actual_guests: int) -> dict:
    """(actual guests - contracted guests) x the per-guest rate, with a sentence explaining it."""
    extra = actual_guests - wedding.contracted_guests
    if extra <= 0:
        raise Unprocessable("No extra guests: the actual guest count is not above the contracted "
                            f"{wedding.contracted_guests}.")
    if wedding.per_guest_rate_paise <= 0:
        raise Unprocessable("This wedding has no per-guest rate, so the extra-guest charge cannot be worked out.")
    amount = extra * wedding.per_guest_rate_paise
    rupees = wedding.per_guest_rate_paise // 100
    note = (f"{extra} extra guests ({actual_guests} actual vs {wedding.contracted_guests} contracted) "
            f"x Rs {rupees:,} per guest")
    return {"extra_guests": extra, "amount_paise": amount, "note": note}


def create_extra_guest_invoice(wedding: Wedding, actual_guests: int, due_date=None) -> Invoice:
    charge = extra_guest_charge(wedding, actual_guests)
    return create_invoice(wedding, Invoice.Kind.EXTRA_GUESTS, charge["amount_paise"], due_date, charge["note"])


def update_invoice(invoice: Invoice, data: dict) -> Invoice:
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if "amount_paise" in data:
            paid = _paid_sum(invoice.payments.all())
            if data["amount_paise"] < paid:
                raise Conflict("The invoice cannot be lowered below what has already been received.")
            invoice.amount_paise = data["amount_paise"]
        for field in ("due_date", "note"):
            if field in data:
                setattr(invoice, field, data[field])
        if "type" in data:
            invoice.kind = data["type"]
        invoice.save()
        return recompute_invoice(invoice)


# ---------------------------------------------------------------- expenses

def similar_bill_warnings(vendor_id, amount_paise: int, due_date, exclude_id=None) -> list[str]:
    """Same vendor, same amount, due within a week of this one: probably the same bill entered twice."""
    if not vendor_id:
        return []
    centre = due_date or timezone.localdate()
    near = Expense.objects.filter(vendor_id=vendor_id, amount_paise=amount_paise,
                                  due_date__gte=centre - timedelta(days=DUPLICATE_WINDOW_DAYS),
                                  due_date__lte=centre + timedelta(days=DUPLICATE_WINDOW_DAYS))
    if exclude_id:
        near = near.exclude(pk=exclude_id)
    return [f"A bill for the same vendor and amount is already due on {e.due_date:%d %b %Y} ({e.description}). "
            f"Check this is not a duplicate." for e in near[:3]]


def _check_bill_unique(vendor_id, bill_ref: str, exclude_id=None):
    if vendor_id and bill_ref:
        clash = Expense.objects.filter(vendor_id=vendor_id, bill_number=bill_ref)
        if exclude_id:
            clash = clash.exclude(pk=exclude_id)
        if clash.exists():
            raise Conflict("This bill reference already exists for this vendor")


def create_expense(wedding: Wedding, category: str, description: str, amount_paise: int, vendor_id=None,
                   bill_ref: str = "", due_date=None) -> tuple[Expense, list[str]]:
    if amount_paise is None or amount_paise <= 0:
        raise ValidationError({"amount_paise": ["Enter an amount greater than zero."]})
    bill_ref = (bill_ref or "").strip()
    _check_bill_unique(vendor_id, bill_ref)
    warnings = similar_bill_warnings(vendor_id, amount_paise, due_date)
    try:
        with transaction.atomic():
            expense = Expense.objects.create(wedding=wedding, vendor_id=vendor_id, category=category,
                                             description=description, amount_paise=amount_paise,
                                             bill_number=bill_ref, due_date=due_date)
    except IntegrityError:  # two people saved the same bill at the same moment
        raise Conflict("This bill reference already exists for this vendor") from None
    return expense, warnings


def update_expense(expense: Expense, data: dict) -> tuple[Expense, list[str]]:
    with transaction.atomic():
        expense = Expense.objects.select_for_update().get(pk=expense.pk)
        vendor_id = data.get("vendor_id", expense.vendor_id)
        bill_ref = (data.get("bill_ref", expense.bill_number) or "").strip()
        _check_bill_unique(vendor_id, bill_ref, exclude_id=expense.pk)
        if "amount_paise" in data:
            if data["amount_paise"] < _paid_sum(expense.payments.all()):
                raise Conflict("The bill cannot be lowered below what has already been paid.")
            expense.amount_paise = data["amount_paise"]
        for field in ("category", "description", "due_date"):
            if field in data:
                setattr(expense, field, data[field])
        expense.vendor_id, expense.bill_number = vendor_id, bill_ref
        try:
            with transaction.atomic():
                expense.save()
        except IntegrityError:
            raise Conflict("This bill reference already exists for this vendor") from None
        recompute_expense(expense)
    return expense, similar_bill_warnings(vendor_id, expense.amount_paise, expense.due_date, exclude_id=expense.pk)


def delete_expense(expense: Expense):
    if expense.payments.exists():
        raise Conflict("This bill has payments recorded, so it cannot be deleted.")
    with transaction.atomic():
        expense.vendorpaymentplan_set.all().delete()
        expense.delete()


# ---------------------------------------------------------------- planned bills and instalments (used by quotations)

def create_planned_expense(wedding=None, vendor=None, category: str = "", amount_paise: int = 0, description: str = "",
                           due_date=None, *, wedding_id=None, vendor_id=None) -> Expense:
    """The bill we expect from a vendor once they are chosen. Takes objects or ids."""
    wedding_id = _pk(wedding) or wedding_id
    vendor_id = _pk(vendor) or vendor_id
    return Expense.objects.create(wedding_id=wedding_id, vendor_id=vendor_id, category=category,
                                  description=description or category, amount_paise=amount_paise, due_date=due_date)


@transaction.atomic
def create_milestones(wedding=None, vendor=None, expense=None, total_paise: int = 0, advance_pct: int = 30,
                      advance_due=None, final_due=None, *, wedding_id=None, vendor_id=None
                      ) -> list[VendorPaymentPlan]:
    """Splits a vendor's bill into an ADVANCE and a FINAL instalment that add up to exactly the total.

    The advance is `advance_pct` percent (rounded down); the final instalment takes the rounding remainder.
    Both are linked to the vendor's one planned bill, so planned expenses are never counted twice.
    """
    if not 0 <= advance_pct <= 100:
        raise ValidationError({"advance_pct": ["Enter a whole number from 0 to 100."]})
    wedding_id = _pk(wedding) or wedding_id
    vendor_id = _pk(vendor) or vendor_id
    if expense is None:
        expense = create_planned_expense(wedding_id=wedding_id, vendor_id=vendor_id, amount_paise=total_paise,
                                         category="Vendor", due_date=final_due)
    advance = total_paise * advance_pct // 100
    plans = [
        VendorPaymentPlan.objects.create(wedding_id=wedding_id, vendor_id=vendor_id, part="ADVANCE",
                                         expense=expense, amount_paise=advance, due_date=advance_due),
        VendorPaymentPlan.objects.create(wedding_id=wedding_id, vendor_id=vendor_id, part="FINAL",
                                         expense=expense, amount_paise=total_paise - advance, due_date=final_due),
    ]
    return plans


def pay_milestone(plan_id: int, amount_paise: int | None = None, method: str = "BANK", reference: str = "",
                  idempotency_key: str | None = None) -> tuple[Payment, bool]:
    """Pays an advance / final instalment (the whole remaining part when no amount is given)."""
    plan = VendorPaymentPlan.objects.select_related("expense").get(pk=plan_id)
    if plan.expense_id is None:
        raise Conflict("This instalment has no bill to pay against.")
    if amount_paise is None:
        paid = _paid_sum(plan.expense.payments.filter(reference=f"milestone:{plan.pk}"))
        amount_paise = plan.amount_paise - paid
        if amount_paise <= 0:
            raise Conflict("This instalment is already paid.")
    return record_expense_payment(plan.expense_id, amount_paise, method, reference, idempotency_key=idempotency_key,
                                  milestone=plan)


# ---------------------------------------------------------------- reports

def _by_wedding(queryset, field="amount_paise") -> dict:
    rows = queryset.values("wedding_id").annotate(total=Coalesce(Sum(field), 0))
    return {row["wedding_id"]: row["total"] for row in rows}


def _margin(profit: int, revenue: int):
    return round(profit * 100 / revenue, 1) if revenue else 0


def get_wedding_financials(wedding_id: int) -> dict:
    """Revenue, expenses and profit of one wedding, from SQL sums and whole-number maths only.

    estimated profit = invoiced - planned expenses (the figure on the dashboard);
    actual profit    = received - paid to vendors.
    """
    wedding = Wedding.objects.select_related("client").get(pk=wedding_id)
    invoiced = Invoice.objects.filter(wedding_id=wedding_id).aggregate(t=Coalesce(Sum("amount_paise"), 0))["t"]
    received = _paid_sum(Payment.objects.filter(wedding_id=wedding_id, direction=Payment.Direction.IN))
    planned = Expense.objects.filter(wedding_id=wedding_id).aggregate(t=Coalesce(Sum("amount_paise"), 0))["t"]
    paid_out = _paid_sum(Payment.objects.filter(wedding_id=wedding_id, direction=Payment.Direction.OUT))

    categories: dict[str, dict] = {}
    for row in (Expense.objects.filter(wedding_id=wedding_id).values("category")
                .annotate(total=Coalesce(Sum("amount_paise"), 0))):
        categories[row["category"]] = {"category": row["category"], "planned": row["total"], "paid": 0}
    for row in (Payment.objects.filter(wedding_id=wedding_id, direction=Payment.Direction.OUT,
                                       expense__isnull=False).values("expense__category")
                .annotate(total=Coalesce(Sum("amount_paise"), 0))):
        entry = categories.setdefault(row["expense__category"], {"category": row["expense__category"],
                                                                 "planned": 0, "paid": 0})
        entry["paid"] = row["total"]

    estimated, actual = invoiced - planned, received - paid_out
    return {
        "wedding": {"id": wedding.pk, "title": wedding.title, "client_name": wedding.client.couple_name,
                    "guest_count": wedding.guest_count, "contracted_guests": wedding.contracted_guests,
                    "per_guest_rate_paise": wedding.per_guest_rate_paise, "budget_paise": wedding.budget_paise},
        "revenue": {"invoiced": invoiced, "received": received, "outstanding": invoiced - received},
        "expenses": {"planned": planned, "paid": paid_out, "outstanding": planned - paid_out},
        "estimated_profit": estimated,
        "actual_profit": actual,
        "margin_pct": _margin(estimated, invoiced),
        "actual_margin_pct": _margin(actual, received),
        "budget_paise": wedding.budget_paise,
        "by_category": sorted(categories.values(), key=lambda c: c["category"]),
        "upcoming_payments": upcoming_payments(days=30, wedding_id=wedding_id),
    }


def upcoming_payments(days: int = 14, wedding_id: int | None = None, today=None) -> list[dict]:
    """Unpaid instalments and bills due within `days` days (or already late), earliest first.

    A bill that has instalments is listed through its instalments, not twice.
    """
    today = today or timezone.localdate()
    cutoff = today + timedelta(days=days)
    items = []

    plans = (VendorPaymentPlan.objects.exclude(status=PayStatus.PAID)
             .filter(due_date__isnull=False, due_date__lte=cutoff, expense__isnull=False)
             .select_related("wedding", "vendor", "expense"))
    if wedding_id:
        plans = plans.filter(wedding_id=wedding_id)
    by_expense: dict[int, list] = {}
    for plan in plans:
        by_expense.setdefault(plan.expense_id, []).append(plan)
    for expense_id, group in by_expense.items():
        siblings = list(VendorPaymentPlan.objects.filter(expense_id=expense_id).order_by("part", "id"))
        covered = allocate_to_plans(siblings, list(Payment.objects.filter(expense_id=expense_id)
                                                   .values_list("amount_paise", "reference")))
        for plan in group:
            outstanding = plan.amount_paise - covered.get(plan.pk, 0)
            if outstanding <= 0:
                continue
            items.append({
                "kind": "milestone", "id": plan.pk, "expense_id": expense_id, "wedding_id": plan.wedding_id,
                "wedding_title": plan.wedding.title, "vendor_name": plan.vendor.name,
                "description": f"{plan.vendor.name} - {plan.get_part_display().lower()}",
                "due_date": plan.due_date, "outstanding_paise": outstanding, "overdue": plan.due_date < today,
            })

    bills = (Expense.objects.exclude(status=PayStatus.PAID).filter(due_date__isnull=False, due_date__lte=cutoff)
             .annotate(plans=Count("vendorpaymentplan"), paid=Coalesce(Sum("payments__amount_paise"), 0))
             .filter(plans=0).select_related("wedding", "vendor"))
    if wedding_id:
        bills = bills.filter(wedding_id=wedding_id)
    for bill in bills:
        if bill.amount_paise - bill.paid <= 0:
            continue
        items.append({
            "kind": "expense", "id": bill.pk, "expense_id": bill.pk, "wedding_id": bill.wedding_id,
            "wedding_title": bill.wedding.title, "vendor_name": bill.vendor.name if bill.vendor else "",
            "description": bill.description, "due_date": bill.due_date,
            "outstanding_paise": bill.amount_paise - bill.paid, "overdue": bill.due_date < today,
        })
    return sorted(items, key=lambda item: (item["due_date"], item["id"]))


def overview() -> list[dict]:
    """Profit of every wedding (the Finance page and the dashboard use the same sums)."""
    invoiced = _by_wedding(Invoice.objects.all())
    received = _by_wedding(Payment.objects.filter(direction=Payment.Direction.IN))
    planned = _by_wedding(Expense.objects.all())
    paid_out = _by_wedding(Payment.objects.filter(direction=Payment.Direction.OUT))
    rows = []
    for wedding in Wedding.objects.select_related("client"):
        revenue, cost = invoiced.get(wedding.pk, 0), planned.get(wedding.pk, 0)
        got, spent = received.get(wedding.pk, 0), paid_out.get(wedding.pk, 0)
        rows.append({
            "wedding_id": wedding.pk, "title": wedding.title, "client_name": wedding.client.couple_name,
            "date": wedding.start_date, "status": wedding.status, "budget_paise": wedding.budget_paise,
            "invoiced_paise": revenue, "received_paise": got, "planned_expense_paise": cost,
            "paid_expense_paise": spent, "estimated_profit_paise": revenue - cost,
            "actual_profit_paise": got - spent, "margin_pct": _margin(revenue - cost, revenue),
        })
    return rows
