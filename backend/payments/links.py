"""Payment links: the customer opens a link, sees the amount, pays online, and the payment records itself.

    link = create_link(invoice, amount_paise=None, created_by=user)   # planner: make a link to send
    details = public_details(link)                                      # customer: what the page shows
    order = start_payment(link)                                         # customer: presses Pay
    payment = complete_payment(link, order_id, payment_id, signature)   # gateway confirms: recorded, link marked paid
"""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from live.alerts import notify_roles
from payments import razorpay_client, services
from payments.models import Invoice, Payment, PaymentLink
from payments.services import Conflict, Unprocessable

DEFAULT_DAYS = 7
BUSINESS_NAME = "Shaandaar Events"


class SettledElsewhere(Conflict):
    """The customer paid online, but the invoice was settled some other way while they were paying."""

    def __init__(self, amount_paise: int, payment_id: str):
        super().__init__("Your payment went through, but this invoice had already been paid. "
                         "Shaandaar Events has been told and will refund you.")
        self.amount_paise = amount_paise
        self.payment_id = payment_id


def remaining_on(invoice: Invoice) -> int:
    return invoice.amount_paise - sum(p.amount_paise for p in invoice.payments.all())


def effective_status(link: PaymentLink, remaining: int | None = None) -> str:
    """ACTIVE, PAID, CANCELLED, EXPIRED, or SETTLED (the invoice got paid some other way meanwhile)."""
    if link.status != PaymentLink.Status.ACTIVE:
        return link.status
    if link.expires_at < timezone.now():
        return "EXPIRED"
    if (remaining_on(link.invoice) if remaining is None else remaining) <= 0:
        return "SETTLED"
    return PaymentLink.Status.ACTIVE


def payable_now(link: PaymentLink) -> int:
    """What the customer pays today: the link's amount, but never more than the invoice still owes."""
    return max(0, min(link.amount_paise, remaining_on(link.invoice)))


def create_link(invoice: Invoice, amount_paise: int | None = None, created_by=None, days: int = DEFAULT_DAYS) -> PaymentLink:
    remaining = remaining_on(invoice)
    if remaining <= 0:
        raise Conflict("This invoice is already fully paid.")
    amount = remaining if amount_paise is None else amount_paise
    if amount <= 0:
        raise Unprocessable("Enter an amount greater than zero.")
    if amount > remaining:
        raise Conflict(f"The link cannot ask for more than the invoice still owes (Rs {remaining // 100:,}).")
    if not 1 <= days <= 60:
        raise Unprocessable("A link can last from 1 to 60 days.")
    return PaymentLink.objects.create(invoice=invoice, amount_paise=amount, created_by=created_by,
                                      expires_at=timezone.now() + timedelta(days=days))


def cancel_link(link: PaymentLink) -> PaymentLink:
    if link.status == PaymentLink.Status.PAID:
        raise Conflict("This link has already been paid.")
    link.status = PaymentLink.Status.CANCELLED
    link.save(update_fields=["status"])
    return link


def online_payments_available() -> bool:
    """The fake checkout must never be reachable on a real website, or anyone could 'pay' without paying."""
    return not razorpay_client.is_mock() or settings.DEBUG or settings.ALLOW_DEMO_PAYMENTS


def public_details(link: PaymentLink) -> dict:
    """Only what the customer needs to see: who it is for, what for, how much."""
    invoice = link.invoice
    paid = sum(p.amount_paise for p in invoice.payments.all())
    remaining = invoice.amount_paise - paid
    status = effective_status(link, remaining)
    data = {
        "business": BUSINESS_NAME,
        "couple": invoice.client.couple_name,
        "wedding": invoice.wedding.title,
        "wedding_date": invoice.wedding.start_date,
        "for": invoice.get_kind_display(),
        "note": invoice.note,
        "due_date": invoice.due_date,
        "invoice_total_paise": invoice.amount_paise,
        "paid_so_far_paise": paid,
        "amount_paise": link.amount_paise if status == "PAID" else payable_now(link),
        "status": status,
        "expires_at": link.expires_at,
        "demo_mode": razorpay_client.is_mock(),
        "available": online_payments_available(),
        "receipt": None,
    }
    if status == "PAID" and link.payment_id:
        data["receipt"] = {"number": f"RCPT-{link.payment_id:06d}", "paid_at": link.paid_at,
                           "amount_paise": link.payment.amount_paise, "reference": link.payment.reference}
    return data


def start_payment(link: PaymentLink) -> dict:
    """The customer pressed Pay: create the gateway order for the amount due now."""
    if not online_payments_available():
        raise Unprocessable("Online payments are not switched on yet. Please contact Shaandaar Events.")
    status = effective_status(link)
    if status != "ACTIVE":
        raise Conflict({"PAID": "This link has already been paid. Thank you!",
                        "EXPIRED": "This link has expired. Please ask Shaandaar Events for a new one.",
                        "CANCELLED": "This link is no longer valid. Please ask Shaandaar Events for a new one.",
                        "SETTLED": "This invoice has already been paid. Thank you!"}[status])
    amount = payable_now(link)
    order = razorpay_client.create_order(amount, link.invoice_id)
    link.razorpay_order_id = order["order_id"]
    link.save(update_fields=["razorpay_order_id"])
    return order


def complete_payment(link: PaymentLink, order_id: str, payment_id: str, signature: str) -> tuple[Payment, bool]:
    """The gateway says the customer paid: check it is genuine, record the payment, mark the link paid.

    Safe to call twice (the browser may retry): the second call returns the first payment.
    """
    try:
        return _complete(link, order_id, payment_id, signature)
    except SettledElsewhere as problem:
        # the alert is saved here, outside the transaction that was just undone, so it is not lost
        notify_roles(f"REFUND NEEDED: {link.invoice.client.couple_name} paid Rs {problem.amount_paise // 100:,} online "
                     f"({problem.payment_id}) but the invoice was already settled.", roles=(), severity="critical",
                     key=f"refund:{problem.payment_id}", channel="both")
        raise


def _complete(link: PaymentLink, order_id: str, payment_id: str, signature: str) -> tuple[Payment, bool]:
    with transaction.atomic():
        link = PaymentLink.objects.select_for_update(of=("self",)).select_related("invoice__wedding", "invoice__client").get(pk=link.pk)
        if link.status == PaymentLink.Status.PAID and link.payment_id:
            return link.payment, False
        if not razorpay_client.verify_signature(order_id, payment_id, signature):
            raise Unprocessable("The payment could not be verified, so nothing was recorded.")
        if not link.razorpay_order_id or order_id != link.razorpay_order_id:
            raise Unprocessable("This payment does not belong to this link.")
        try:
            order = razorpay_client.order_details(order_id)
        except Exception as error:  # noqa: BLE001 - gateway errors can carry secrets, so they are never shown
            raise Unprocessable("Could not confirm this payment with the gateway. Please try again in a moment.") from error
        if order["receipt"] != str(link.invoice_id):
            raise Unprocessable("This payment belongs to a different invoice.")
        try:
            payment, created = services.record_invoice_payment(
                link.invoice_id, order["amount"], "RAZORPAY", payment_id, idempotency_key=f"razorpay:{payment_id}")
        except Conflict as error:
            raise SettledElsewhere(order["amount"], payment_id) from error
        link.status = PaymentLink.Status.PAID
        link.paid_at = timezone.now()
        link.payment = payment
        link.save(update_fields=["status", "paid_at", "payment"])
    return payment, created
