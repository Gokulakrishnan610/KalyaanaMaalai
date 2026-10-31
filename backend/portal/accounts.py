"""Creating accounts for people we onboard ourselves (a phone call, Instagram, a referral), and the emails that
let them choose a password. A website sign-up already has an account; everyone else gets one when they are converted
to a client (couples) or when we invite them (vendors)."""
import secrets

from django.conf import settings
from django.core import signing
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from mailer import services as mail
from portal.models import Customer, VendorAccount

LINK_DAYS = 3
SALT = "portal-set-password"


def make_link_token(kind: str, account) -> str:
    # the end of the password hash is inside the token, so the link stops working as soon as a password is chosen
    return signing.dumps({"k": kind, "id": account.pk, "p": account.password_hash[-12:]}, salt=SALT)


def read_link_token(token: str):
    try:
        data = signing.loads(token, salt=SALT, max_age=LINK_DAYS * 86400)
    except signing.BadSignature:
        raise ValidationError("This link has expired or was already used. Ask for a new one.") from None
    model = Customer if data["k"] == "customer" else VendorAccount
    account = model.objects.filter(pk=data["id"]).first()
    if account is None or account.password_hash[-12:] != data["p"]:
        raise ValidationError("This link has expired or was already used. Ask for a new one.")
    return data["k"], account


def link_for(kind: str, account) -> str:
    site = settings.FRONTEND_URL if kind == "vendor" else settings.CUSTOMER_SITE_URL  # vendors use the main site
    return f"{site}/set-password?token={make_link_token(kind, account)}"


def account_state(account) -> str:
    """none / invited (not logged in yet) / active."""
    if account is None:
        return "none"
    return "active" if account.last_login_at else "invited"


def invite_customer(customer: Customer, planner: str = "") -> None:
    customer.invited_at = timezone.now()
    customer.save(update_fields=["invited_at"])
    wedding = customer.client.weddings.order_by("-created_at").first() if customer.client_id else None
    mail.send("client_welcome", customer.email, name=customer.name, email=customer.email, planner=planner,
              wedding=wedding.title if wedding else "", link=link_for("customer", customer))


def ensure_customer(enquiry, client, planner: str = "") -> Customer | None:
    """Gives a converted client an account on the customer website and emails the login.

    Returns None when we have no email address for them (the planner sees that on the enquiry)."""
    customer = getattr(enquiry, "portal_customer", None)
    if customer is None:
        if not enquiry.email:
            return None
        customer = Customer.objects.filter(email=enquiry.email.lower()).first()
        if customer is None:
            customer = Customer.objects.create(name=enquiry.couple_name, email=enquiry.email.lower(),
                                               phone=enquiry.phone, enquiry=enquiry, client=client)
            invite_customer(customer, planner)
            return customer
        if customer.enquiry_id is None:
            customer.enquiry = enquiry
    if customer.client_id is None:
        customer.client = client
    customer.save()
    if not customer.password_hash and customer.invited_at is None:
        invite_customer(customer, planner)  # an account made for them earlier, but never emailed
    return customer


def invite_vendor(vendor) -> tuple[VendorAccount, str]:
    """Gives a vendor a login for the main site (next to the founder, planners and staff). A fresh password is made
    each time; it is emailed to the vendor and also returned, so the person who added the vendor can pass it on."""
    if not vendor.email:
        raise ValidationError("Add the vendor's email address first, so we can send them the login.")
    email = vendor.email.lower()
    account = getattr(vendor, "portal_account", None)
    if account is None:
        if VendorAccount.objects.filter(email=email).exists():
            raise ValidationError("Another vendor already uses this email address.")
        account = VendorAccount(vendor=vendor, email=email)
    account.email = email
    password = secrets.token_urlsafe(9)
    account.set_password(password)
    account.invited_at = timezone.now()
    account.save()
    mail.send("vendor_invite", account.email, vendor=vendor.name, email=account.email, password=password,
              link=f"{settings.FRONTEND_URL}/login")
    return account, password


def request_reset(email: str) -> None:
    """Emails a reset link. Says nothing about whether the address exists."""
    email = email.strip().lower()
    for kind, model in (("customer", Customer), ("vendor", VendorAccount)):
        account = model.objects.filter(email=email).first()
        if account is None:
            continue
        name = account.name if kind == "customer" else account.vendor.name
        mail.send("password_reset", account.email, name=name, link=link_for(kind, account))


def set_password(token: str, password: str):
    kind, account = read_link_token(token)
    if len(password) < 8:
        raise ValidationError({"password": "Use at least 8 characters."})
    account.set_password(password)
    account.save(update_fields=["password_hash"])
    return kind, account
