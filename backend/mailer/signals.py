"""The emails that go out by themselves when something happens. They run after the database commit, so we never
email about something that was rolled back, and a mail problem never breaks the save."""
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from mailer import services as mail
from payments.models import Invoice, Payment
from quotations.models import WeddingVendor


def _rs(paise: int) -> str:
    return f"{paise / 100:,.0f}"


def _client_contact(client):
    """(email, display name) for a client: the website account's email if they have one."""
    customer = client.portal_customers.first()
    return ((customer.email if customer else client.email), client.couple_name)


def _vendor_link() -> str:
    return f"{settings.FRONTEND_URL}/vendor"


@receiver(post_save, sender=Invoice)
def invoice_created(sender, instance, created, **kwargs):
    if not created or kwargs.get("raw"):
        return

    def send():
        email, name = _client_contact(instance.client)
        mail.send("invoice_issued", email, name=name, title=instance.get_kind_display(), amount=_rs(instance.amount_paise),
                  wedding=instance.wedding.title, due_date=f"{instance.due_date:%d %b %Y}" if instance.due_date else "",
                  link=f"{settings.CUSTOMER_SITE_URL}/home")

    transaction.on_commit(send)


@receiver(post_save, sender=Payment)
def payment_recorded(sender, instance, created, **kwargs):
    if not created or kwargs.get("raw"):
        return

    def send():
        if instance.direction == Payment.Direction.IN and instance.invoice_id:
            email, name = _client_contact(instance.wedding.client)
            mail.send("payment_receipt", email, name=name, title=instance.invoice.get_kind_display(),
                      amount=_rs(instance.amount_paise), wedding=instance.wedding.title, receipt=f"RCPT-{instance.pk:05d}")
        elif instance.direction == Payment.Direction.OUT and instance.expense_id and instance.expense.vendor_id:
            vendor = instance.expense.vendor
            mail.send("vendor_payment_sent", vendor.email, vendor=vendor.name, amount=_rs(instance.amount_paise),
                      wedding=instance.wedding.title, link=_vendor_link())

    transaction.on_commit(send)


@receiver(post_save, sender=WeddingVendor)
def vendor_booked(sender, instance, created, **kwargs):
    if not created or kwargs.get("raw"):
        return
    transaction.on_commit(lambda: mail.send(
        "vendor_booked", instance.vendor.email, vendor=instance.vendor.name, wedding=instance.wedding.title,
        date=f"{instance.wedding.start_date:%d %b %Y}", amount=_rs(instance.agreed_amount_paise), link=_vendor_link()))
