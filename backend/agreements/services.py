"""The agreement steps: write it, send it, email a code, sign it, check it later."""
import hashlib
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from agreements.models import Agreement
from live.signals import alert
from mailer import services as mail

OTP_MINUTES = 10
MAX_OTP_TRIES = 5
MAX_SIGNATURE_CHARS = 300_000
BUSINESS = "Shaandaar Events"


def rupees(paise: int) -> str:
    return f"Rs {paise / 100:,.0f}"


def default_body(wedding) -> str:
    """The standard terms, filled in from the wedding itself so nobody has to retype the facts."""
    client = wedding.client
    functions = ", ".join(f.name for f in wedding.functions.all()) or "as listed in the schedule"
    invoices = list(wedding.invoices.order_by("due_date", "id"))
    schedule = "\n".join(
        f"- {i.get_kind_display()}: {rupees(i.amount_paise)}" + (f", due {i.due_date:%d %b %Y}" if i.due_date else "")
        for i in invoices) or "- The payment schedule will be shared by your planner and added as invoices."
    dates = f"{wedding.start_date:%d %B %Y}" + (f" to {wedding.end_date:%d %B %Y}" if wedding.end_date != wedding.start_date else "")
    rate = (f"Each guest above {wedding.contracted_guests} is charged {rupees(wedding.per_guest_rate_paise)}."
            if wedding.per_guest_rate_paise else "Charges for extra guests will be agreed in writing before the event.")
    return f"""## 1. The parties
This agreement is between {BUSINESS} ("we") and {client.couple_name} ("you"), phone {client.phone}.

## 2. The event
We will plan and manage your wedding "{wedding.title}" in {wedding.city} on {dates}. The functions are: {functions}.

## 3. Guests
This agreement is for {wedding.contracted_guests} guests. {rate}

## 4. Fees and payments
Your budget for this wedding is {rupees(wedding.budget_paise)}. You agree to pay according to this schedule:
{schedule}
Payments can be made online on your account page, by UPI, bank transfer, cheque or cash. Every payment gets a receipt.

## 5. Vendors
We will ask for quotations from vendors and show them to you side by side. A vendor is booked only after you approve the choice. We pay the vendors on your behalf from the payments you make to us.

## 6. Changes
Changes to the date, venue, guest count or functions must be sent to us in writing (a message or email is enough). We will tell you if a change affects the price before we go ahead.

## 7. Cancellation
If you cancel, the booking deposit is not returned. Amounts already paid to vendors for your wedding cannot be recovered by us and are deducted from any refund. The rest of what you paid will be returned within 15 working days.

## 8. Our responsibility
We will take reasonable care to deliver what is written here. We are not responsible for things outside our control, such as weather, government orders, or a vendor that the law does not allow us to replace. If a vendor fails to come, we will find the nearest replacement at no extra planning fee.

## 9. Agreeing online
You agree that signing on our website, after confirming with the code we email to you, is the same as signing on paper. We keep your name, the time, your address on the internet and your drawn signature as proof.
"""


def fingerprint(agreement: Agreement) -> str:
    """A hash of the exact text that was agreed, so a later change to it can be spotted."""
    return hashlib.sha256(f"{agreement.title}\n{agreement.body}".encode()).hexdigest()


def create_draft(wedding, user=None, title: str = "", body: str = "") -> Agreement:
    return Agreement.objects.create(wedding=wedding, title=title or f"Service agreement: {wedding.title}",
                                    body=body or default_body(wedding), created_by=user)


def update_draft(agreement: Agreement, title=None, body=None) -> Agreement:
    if agreement.status != Agreement.Status.DRAFT:
        raise ValidationError("Only a draft can be edited. Cancel this one and make a new agreement instead.")
    if title is not None:
        agreement.title = title
    if body is not None:
        agreement.body = body
    agreement.save(update_fields=["title", "body"])
    return agreement


def client_email(agreement: Agreement) -> str:
    client = agreement.wedding.client
    customer = client.portal_customers.first()
    return (customer.email if customer else client.email) or ""


@transaction.atomic
def send(agreement: Agreement, user) -> Agreement:
    """Sends the agreement for signing. The client also gets a login on the website if they have none yet."""
    if agreement.status not in (Agreement.Status.DRAFT, Agreement.Status.SENT):
        raise ValidationError("This agreement cannot be sent again.")
    client = agreement.wedding.client
    email = client_email(agreement)
    if not email:
        raise ValidationError("The client has no email address. Add one to the client first.")
    from portal.accounts import ensure_customer

    enquiry = client.enquiries.order_by("-created_at").first()
    if not client.portal_customers.exists() and enquiry is not None:
        ensure_customer(enquiry, client, planner=user.name)
    agreement.status = Agreement.Status.SENT
    agreement.sent_at = timezone.now()
    agreement.company_signer = user.name
    agreement.save(update_fields=["status", "sent_at", "company_signer"])
    mail.send("agreement_ready", email, name=client.couple_name, wedding=agreement.wedding.title,
              link=f"{settings.CUSTOMER_SITE_URL}/agreement/{agreement.pk}")
    return agreement


def void(agreement: Agreement) -> Agreement:
    if agreement.status == Agreement.Status.SIGNED:
        raise ValidationError("A signed agreement cannot be cancelled. Make a new agreement if the terms change.")
    agreement.status = Agreement.Status.VOID
    agreement.save(update_fields=["status"])
    return agreement


def request_code(agreement: Agreement, email: str) -> None:
    if agreement.status != Agreement.Status.SENT:
        raise ValidationError("This agreement is not open for signing.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    agreement.otp_hash = make_password(code)
    agreement.otp_expires_at = timezone.now() + timedelta(minutes=OTP_MINUTES)
    agreement.otp_tries = 0
    agreement.save(update_fields=["otp_hash", "otp_expires_at", "otp_tries"])
    mail.send("agreement_otp", email, name=agreement.wedding.client.couple_name, wedding=agreement.wedding.title, otp=code)


def _signature_ok(signature: str) -> bool:
    return bool(re.fullmatch(r"data:image/png;base64,[A-Za-z0-9+/=]+", signature)) and len(signature) <= MAX_SIGNATURE_CHARS


def check_code(agreement: Agreement, code: str) -> None:
    """Checks the emailed code. A wrong try is saved straight away (not rolled back), so tries really are counted."""
    if not agreement.otp_hash or agreement.otp_expires_at is None or agreement.otp_expires_at < timezone.now():
        raise ValidationError({"code": "Ask for a new code. The last one has expired."})
    if agreement.otp_tries >= MAX_OTP_TRIES:
        raise ValidationError({"code": "Too many wrong tries. Ask for a new code."})
    if not check_password(code.strip(), agreement.otp_hash):
        Agreement.objects.filter(pk=agreement.pk).update(otp_tries=agreement.otp_tries + 1)
        raise ValidationError({"code": "That code is not right."})


def sign(agreement: Agreement, *, name: str, email: str, signature: str, code: str, agreed: bool, ip: str | None,
         agent: str) -> Agreement:
    agreement.refresh_from_db()
    if agreement.status != Agreement.Status.SENT:
        raise ValidationError("This agreement is not open for signing.")
    if not agreed:
        raise ValidationError({"agreed": "Please tick the box to say you have read and agree."})
    if len(name.strip()) < 3:
        raise ValidationError({"name": "Type your full name."})
    if not _signature_ok(signature):
        raise ValidationError({"signature": "Please draw your signature in the box."})
    check_code(agreement, code)
    with transaction.atomic():
        agreement = Agreement.objects.select_for_update().get(pk=agreement.pk)
        if agreement.status != Agreement.Status.SENT:  # someone signed in the meantime
            raise ValidationError("This agreement is not open for signing.")
        agreement.status = Agreement.Status.SIGNED
        agreement.signed_at = timezone.now()
        agreement.signer_name = name.strip()
        agreement.signer_email = email
        agreement.signature = signature
        agreement.signer_ip = ip
        agreement.signer_agent = agent[:300]
        agreement.body_hash = fingerprint(agreement)
        agreement.otp_hash, agreement.otp_expires_at = "", None  # a code works once
        agreement.save()
    alert(f"{agreement.wedding.client.couple_name} signed the agreement for {agreement.wedding.title}",
          key=f"agreement-signed:{agreement.pk}")
    mail.send("agreement_signed", email, name=agreement.signer_name, wedding=agreement.wedding.title,
              date=f"{agreement.signed_at:%d %b %Y}", link=f"{settings.CUSTOMER_SITE_URL}/agreement/{agreement.pk}")
    return agreement


def untouched(agreement: Agreement) -> bool:
    """True when the text still matches what was signed."""
    return agreement.status == Agreement.Status.SIGNED and fingerprint(agreement) == agreement.body_hash


def certificate(agreement: Agreement) -> dict | None:
    """The proof kept for a signed agreement."""
    if agreement.status != Agreement.Status.SIGNED:
        return None
    return {"signed_by": agreement.signer_name, "email": agreement.signer_email, "signed_at": agreement.signed_at,
            "ip": agreement.signer_ip, "device": agreement.signer_agent, "hash": agreement.body_hash,
            "text_unchanged": untouched(agreement), "company_signer": agreement.company_signer,
            "company": BUSINESS, "sent_at": agreement.sent_at, "signature": agreement.signature}
