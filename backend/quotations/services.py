"""The rules for quotations: totals, comparison, picking the winner.

Views stay thin and call these functions, so the tests can call them directly too.
"""
import logging
import re
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from payments.models import Expense, Payment, PayStatus, VendorPaymentPlan
from quotations.models import (
    Quotation,
    QuotationItem,
    QuotationRequest,
    QuotationStatus,
    RequestStatus,
    WeddingVendor,
)
from vendors.models import Vendor
from vendors.performance import punctuality_for, with_stats

logger = logging.getLogger(__name__)

# best value = 60% price, 25% rating, 15% punctuality (each scaled 0..1 across the quotes being compared)
WEIGHTS = {"price": 0.60, "rating": 0.25, "punctuality": 0.15}
CATERER = "Caterer"
RECOMMENDED_CATERER_QUOTES = 3


class Conflict(APIException):
    status_code = 409
    default_detail = "This conflicts with what is already saved."
    default_code = "conflict"


# ---------------------------------------------------------------- saving a quotation

def implied_total(per_plate, has_items, guest_count):
    """Price per plate x guests, only for quotes that have no line items."""
    if has_items or not per_plate or not guest_count:
        return None
    return per_plate * guest_count


@transaction.atomic
def save_quotation(request: QuotationRequest, vendor: Vendor, data: dict):
    """One quotation per vendor per request: a second save for the same vendor updates the first."""
    if request.status == RequestStatus.CLOSED:
        raise Conflict("This request is closed, so quotations can no longer be added.")
    if vendor.category_id != request.category_id:
        raise ValidationError({"vendor_id": [f"{vendor.name} is not a {request.category.name}."]})
    quotation = Quotation.objects.filter(request=request, vendor=vendor).first()
    created = quotation is None
    if created:
        quotation = Quotation(request=request, vendor=vendor)
    elif quotation.status == QuotationStatus.SELECTED:
        raise Conflict("This quotation is already selected and can no longer be changed.")
    if created:
        quotation.total_paise = None
    write_quotation(quotation, data)
    request.invited_vendors.add(vendor)  # a vendor who quotes counts as invited
    return quotation, created


def write_quotation(quotation: Quotation, data: dict):
    """Applies `data` and saves. The server decides the total: the sum of the line items when there are any,
    otherwise the typed total, otherwise price per plate x guests."""
    items = data.get("items")  # None = leave the existing lines alone, [] = remove them
    guests = quotation.request.guest_count
    for field in ("price_per_plate_paise", "menu_notes", "valid_till", "typed_by_hand"):
        if field in data:
            setattr(quotation, field, data[field])
    if data.get("total_paise") is not None:
        quotation.total_paise = data["total_paise"]

    if items:
        quotation.total_paise = sum(i["quantity"] * i["unit_price_paise"] for i in items)
    elif items is None and quotation.pk and quotation.items.exists():
        quotation.total_paise = item_sum(quotation)
    if quotation.total_paise is None:
        if quotation.price_per_plate_paise and guests:
            quotation.total_paise = quotation.price_per_plate_paise * guests
        else:
            raise ValidationError({"total_paise": ["Enter the total, add line items, or give a price per plate "
                                                   "(with the request's guest count)."]})
    quotation.save()

    if items is not None:
        quotation.items.all().delete()
        QuotationItem.objects.bulk_create([
            QuotationItem(quotation=quotation, description=i["description"].strip(), quantity=i["quantity"],
                          unit_price_paise=i["unit_price_paise"], total_paise=i["quantity"] * i["unit_price_paise"])
            for i in items
        ])


def item_sum(quotation: Quotation) -> int:
    return sum(i.total_paise for i in quotation.items.all())


# ---------------------------------------------------------------- comparing

def normalise(description: str) -> str:
    """'Welcome  Drinks!' and 'welcome drinks' line up in the comparison table."""
    return re.sub(r"[^a-z0-9]+", " ", description.lower()).strip()


def _min_max(values: list[float]) -> list[float]:
    """Scales to 0..1. When every value is equal nobody is better, so everyone gets 1."""
    low, high = min(values), max(values)
    if high == low:
        return [1.0] * len(values)
    return [(v - low) / (high - low) for v in values]


def _fill_missing(values: list):
    """A vendor with no rating yet gets the average of the others, so being new is neither a bonus nor a penalty."""
    known = [v for v in values if v is not None]
    fallback = sum(known) / len(known) if known else 0.0
    return [fallback if v is None else v for v in values]


def best_value_scores(totals: list[int], ratings: list, punctualities: list) -> list[float]:
    """score = 0.60*price + 0.25*rating + 0.15*punctuality, each min-max scaled (a lower price is better)."""
    price = [1 - s if len(set(totals)) > 1 else 1.0 for s in _min_max([float(t) for t in totals])]
    rating = _min_max(_fill_missing(ratings))
    punctual = _min_max(_fill_missing(punctualities))
    return [WEIGHTS["price"] * p + WEIGHTS["rating"] * r + WEIGHTS["punctuality"] * c
            for p, r, c in zip(price, rating, punctual, strict=True)]


def compare(request: QuotationRequest, today=None) -> dict:
    today = today or timezone.localdate()
    quotes = list(request.quotations.select_related("vendor__category").prefetch_related("items").order_by("id"))
    vendor_ids = [q.vendor_id for q in quotes]
    stats = {v.pk: v for v in with_stats(Vendor.objects.filter(pk__in=vendor_ids))}
    punctuality = punctuality_for(vendor_ids)
    guests = request.guest_count

    rows, order = {}, []
    for index, quote in enumerate(quotes):
        for item in quote.items.all():
            key = normalise(item.description)
            if key not in rows:
                rows[key] = {"key": key, "description": item.description.strip(), "values": [None] * len(quotes)}
                order.append(key)
            cell = rows[key]["values"][index]
            if cell is None:  # two lines with the same name on one quote add up
                rows[key]["values"][index] = {"qty": item.quantity, "unit_price_paise": item.unit_price_paise,
                                              "total_paise": item.total_paise}
            else:
                cell["qty"] += item.quantity
                cell["total_paise"] += item.total_paise

    vendor_info = []
    for quote in quotes:
        vendor = stats[quote.vendor_id]
        pct = punctuality.get(quote.vendor_id, {}).get("punctuality_pct")
        rating = None if vendor.avg_rating is None else round(vendor.avg_rating, 2)
        vendor_info.append({"id": vendor.pk, "name": vendor.name, "city": vendor.city, "avg_rating": rating,
                            "punctuality_pct": pct})

    scores = []
    if quotes:
        # expired quotes cannot win "best value" unless every quote has expired
        eligible = [i for i, q in enumerate(quotes) if not (q.valid_till and q.valid_till < today)]
        pool = eligible or list(range(len(quotes)))
        pool_scores = best_value_scores([quotes[i].total_paise for i in pool],
                                        [vendor_info[i]["avg_rating"] for i in pool],
                                        [vendor_info[i]["punctuality_pct"] for i in pool])
        scores = [None] * len(quotes)
        for i, s in zip(pool, pool_scores, strict=True):
            scores[i] = round(s, 4)
    best = None
    if scores:
        candidates = [i for i, s in enumerate(scores) if s is not None]
        best = max(candidates, key=lambda i: (scores[i], -quotes[i].total_paise))

    lowest_total = min((q.total_paise for q in quotes), default=None)
    plates = [q.price_per_plate_paise for q in quotes if q.price_per_plate_paise]
    lowest_plate = min(plates, default=None)

    out = []
    for index, quote in enumerate(quotes):
        has_items = bool(quote.items.all())
        out.append({
            "id": quote.pk,
            "status": quote.status,
            "vendor": vendor_info[index],
            "total_paise": quote.total_paise,
            "price_per_plate_paise": quote.price_per_plate_paise,
            "implied_total_paise": implied_total(quote.price_per_plate_paise, has_items, guests),
            "menu_notes": quote.menu_notes,
            "valid_till": quote.valid_till,
            "file_url": quote.file.url if quote.file else None,
            "typed_by_hand": quote.typed_by_hand,
            "score": scores[index] if scores else None,
            "flags": {
                "lowest_total": quote.total_paise == lowest_total and len(quotes) > 1,
                "lowest_per_plate": bool(quote.price_per_plate_paise) and quote.price_per_plate_paise == lowest_plate
                                    and len(plates) > 1,
                "expired": bool(quote.valid_till and quote.valid_till < today),
                "best_value": index == best,
            },
        })
    return {
        "request": {"id": request.pk, "wedding_id": request.wedding_id, "category": request.category.name,
                    "guest_count": guests, "status": request.status},
        "weights": WEIGHTS,
        "quotations": out,
        "item_rows": [rows[k] for k in order],
    }


# ---------------------------------------------------------------- picking the winner

def _has_payments(booking: WeddingVendor) -> bool:
    mine = {"wedding": booking.wedding, "vendor": booking.vendor}
    return (Payment.objects.filter(wedding=booking.wedding, direction=Payment.Direction.OUT,
                                   expense__vendor=booking.vendor).exists()
            or Expense.objects.filter(**mine).exclude(status=PayStatus.UNPAID).exists()
            or VendorPaymentPlan.objects.filter(**mine).exclude(status=PayStatus.UNPAID).exists())


def _unplan(booking: WeddingVendor):
    """Takes back the planned bill and the advance/final instalments of a vendor we are replacing."""
    VendorPaymentPlan.objects.filter(wedding=booking.wedding, vendor=booking.vendor).delete()
    Expense.objects.filter(wedding=booking.wedding, vendor=booking.vendor, status=PayStatus.UNPAID).delete()
    booking.delete()


def _plan_payments(booking: WeddingVendor, advance_pct: int):
    """Asks the finance part to plan the vendor's bill: a planned expense plus an advance and a final instalment.

    Uses payments.services when it exists (Member 4). Until then it writes the same rows itself so the
    Finance tab already shows them. A failure here is logged and never undoes the selection.
    """
    wedding, vendor = booking.wedding, booking.vendor
    advance_due = timezone.localdate() + timedelta(days=7)
    final_due = wedding.start_date - timedelta(days=3)
    description = f"{vendor.name} ({vendor.category.name})"
    try:
        with transaction.atomic():
            try:
                from payments import services as finance
                create_expense, create_milestones = finance.create_planned_expense, finance.create_milestones
            except (ImportError, AttributeError):
                expense = Expense.objects.create(
                    wedding=wedding, vendor=vendor, category=vendor.category.name, description=description,
                    amount_paise=booking.agreed_amount_paise, due_date=final_due)
                advance = booking.agreed_amount_paise * advance_pct // 100
                VendorPaymentPlan.objects.create(wedding=wedding, vendor=vendor, part="ADVANCE", expense=expense,
                                                 amount_paise=advance, due_date=advance_due)
                VendorPaymentPlan.objects.create(wedding=wedding, vendor=vendor, part="FINAL", expense=expense,
                                                 amount_paise=booking.agreed_amount_paise - advance,
                                                 due_date=final_due)
                return
            expense = create_expense(wedding=wedding, vendor=vendor, category=vendor.category.name,
                                     description=description, amount_paise=booking.agreed_amount_paise,
                                     due_date=final_due)
            create_milestones(wedding=wedding, vendor=vendor, expense=expense,
                              total_paise=booking.agreed_amount_paise, advance_pct=advance_pct,
                              advance_due=advance_due, final_due=final_due)
    except Exception:  # noqa: BLE001 - finance trouble must not block choosing a vendor
        logger.exception("Could not plan payments for %s on wedding %s", vendor, wedding.pk)


@transaction.atomic
def select_quotation(quotation: Quotation, advance_pct: int = 30):
    """Picks the winning quotation. Returns (WeddingVendor, created).

    In one transaction: this quotation becomes SELECTED, the others REJECTED, the request closes and the
    vendor is booked on the wedding with a planned expense and instalments. Choosing the same quotation again
    changes nothing. Switching to another one takes back the first vendor, but only while nothing has been
    paid to them.
    """
    request = QuotationRequest.objects.select_for_update().select_related("wedding", "category").get(
        pk=quotation.request_id)
    wedding = request.wedding

    current = (WeddingVendor.objects.select_for_update().select_related("vendor__category", "wedding")
               .filter(quotation__request=request).first())
    if current and current.quotation_id == quotation.pk:
        return current, False

    stale = [current] if current else []
    same_vendor = WeddingVendor.objects.filter(wedding=wedding, vendor=quotation.vendor).exclude(
        pk=current.pk if current else None).select_related("vendor__category", "wedding").first()
    if same_vendor:
        stale.append(same_vendor)
    for booking in stale:
        if _has_payments(booking):
            raise Conflict("Payments already recorded for the current vendor")
    for booking in stale:
        _unplan(booking)

    request.quotations.exclude(pk=quotation.pk).update(status=QuotationStatus.REJECTED)
    quotation.status = QuotationStatus.SELECTED
    quotation.save(update_fields=["status"])
    request.status = RequestStatus.CLOSED
    request.save(update_fields=["status"])

    booking = WeddingVendor.objects.create(wedding=wedding, vendor=quotation.vendor, quotation=quotation,
                                           agreed_amount_paise=quotation.total_paise)
    _plan_payments(booking, advance_pct)
    return booking, True


# ---------------------------------------------------------------- sending requests

def notify_vendors(request: QuotationRequest):
    """Emails each invited vendor (real mode) or leaves a bell notification (mock mode). Returns how many."""
    vendors = list(request.invited_vendors.all())
    wedding = request.wedding
    from django.conf import settings as django_settings

    def send():
        from mailer import services as mail

        for vendor in vendors:
            mail.send("vendor_quotation_request", vendor.email, vendor=vendor.name, category=request.category.name,
                      wedding=wedding.title, date=f"{wedding.start_date:%d %b %Y}",
                      reply_by=f"{request.reply_by:%d %b %Y}" if request.reply_by else "",
                      link=f"{django_settings.FRONTEND_URL}/vendor/requests")

    transaction.on_commit(send)
    live = not settings.MOCK_EXTERNALS and bool(settings.EMAIL_HOST)
    if live:
        return len([v for v in vendors if v.email])
    _notify(f"Quotation request sent to {len(vendors)} {request.category.name.lower()}(s) for {wedding.title}.")
    return len(vendors)


def _notify(message: str):
    try:
        from notifications import services as alerts
        alerts.notify(message)
    except (ImportError, AttributeError):
        from notifications.models import Notification
        Notification.objects.create(message=message)
    except Exception:  # noqa: BLE001
        logger.exception("Could not create a notification")
