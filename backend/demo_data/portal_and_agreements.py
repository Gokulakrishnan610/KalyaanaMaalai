"""Logins for couples and vendors, and the agreements: one waiting for a signature (Nithilan & Ramya, who go
through the real "convert to client" step) and one already signed (Aarav & Meera). Safe to run twice."""
import hashlib
from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from agreements import services as agreement_services
from agreements.models import Agreement
from clients.models import Client
from demo_data.people_and_enquiries import DEMO_PASSWORD
from enquiries.models import Enquiry, FollowUp, Source, Status
from enquiries.services import convert_to_client
from payments import services as payment_services
from portal.models import Customer, VendorAccount
from quotations.models import QuotationRequest
from vendors.models import Vendor, VendorCategory
from weddings.models import Wedding

# a tiny drawn "signature" so the signed demo agreement shows a picture
SIGNATURE = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")

VENDOR_LOGINS = ["Rasoi Royale", "Spice Route Catering", "Petals & Pillars Decor", "Royal Mandap Decor", "DJ Rhythm Raj",
                 "Lens & Lehenga Studio"]


def slug(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())


def customer(name, email, phone, enquiry, client=None):
    account, _ = Customer.objects.get_or_create(email=email, defaults=dict(name=name, phone=phone, enquiry=enquiry, client=client))
    account.set_password(DEMO_PASSWORD)
    account.invited_at = account.invited_at or timezone.now()
    account.save()
    return account


def load():
    planner = User.objects.get(email="planner@shaandaar.demo")

    # --- Aarav & Meera: already booked, agreement signed
    meera_client = Client.objects.get(couple_name="Aarav & Meera")
    meera_enquiry = Enquiry.objects.get(couple_name="Aarav & Meera")
    meera_enquiry.partner_name, meera_enquiry.email = "Aarav", "aarav.meera@example.com"
    meera_enquiry.services_needed = ["VENUE", "CATERING", "DECOR", "PHOTOGRAPHY"]
    meera_enquiry.functions_wanted = ["MEHENDI", "SANGEET", "RECEPTION"]
    meera_enquiry.preferred_contact, meera_enquiry.profile_complete = "WHATSAPP", True
    meera_enquiry.save()
    customer("Meera", "aarav.meera@example.com", "9876543210", meera_enquiry, meera_client)
    wedding = Wedding.objects.get(client=meera_client)
    if not wedding.agreements.exists():
        agreement = agreement_services.create_draft(wedding, planner)
        agreement.status, agreement.sent_at, agreement.company_signer = Agreement.Status.SIGNED, timezone.now() - timedelta(days=20), planner.name
        agreement.signed_at, agreement.signer_name, agreement.signer_email = timezone.now() - timedelta(days=19), "Meera Kapoor", "aarav.meera@example.com"
        agreement.signature, agreement.signer_ip, agreement.signer_agent = SIGNATURE, "103.21.58.14", "Demo browser"
        agreement.body_hash = agreement_services.fingerprint(agreement)
        agreement.save()

    # --- Nithilan & Ramya: converted through the real step, so the agreement is waiting for their signature
    enquiry, created = Enquiry.objects.get_or_create(
        couple_name="Nithilan & Ramya",
        defaults=dict(phone="9840011223", email="nithilan.ramya@example.com", source=Source.INSTAGRAM, status=Status.PROPOSAL,
                      partner_name="Ramya", wedding_date=timezone.localdate() + timedelta(days=95), guest_count=320,
                      venue_city="Chennai", budget_paise=3_000_000_00, owner=planner, win_chance=60, priority=3,
                      services_needed=["VENUE", "CATERING", "DECOR", "MAKEUP"], functions_wanted=["ENGAGEMENT", "WEDDING", "RECEPTION"],
                      preferred_contact="WHATSAPP", profile_complete=True, expected_revenue_paise=300_000_00))
    if created or enquiry.client_id is None:
        client, wedding = convert_to_client(enquiry, create_wedding=True)
        wedding.per_guest_rate_paise, wedding.contracted_guests = 2200_00, 300
        wedding.save()
        payment_services.create_invoice(wedding, "DEPOSIT", 300_000_00, timezone.localdate() + timedelta(days=7), "Booking deposit")
        payment_services.create_invoice(wedding, "MILESTONE", 900_000_00, timezone.localdate() + timedelta(days=45))
        for agreement in wedding.agreements.all():  # rebuild the text now that the payment schedule exists
            agreement.body = agreement_services.default_body(wedding)
            agreement.save(update_fields=["body"])
            agreement.status, agreement.sent_at, agreement.company_signer = Agreement.Status.SENT, timezone.now(), planner.name
            agreement.save(update_fields=["status", "sent_at", "company_signer"])
        # ask two decorators for a price, so the vendor pages have a request to answer
        decor = VendorCategory.objects.get(name="Decorator")
        request = QuotationRequest.objects.create(wedding=wedding, category=decor, guest_count=320, sent_at=timezone.now(),
                                                  reply_by=timezone.localdate() + timedelta(days=10),
                                                  requirements="Stage and mandap for the wedding, entrance arch, table centrepieces.")
        request.invited_vendors.set(Vendor.objects.filter(name__in=["Petals & Pillars Decor", "Royal Mandap Decor"]))
    FollowUp.objects.get_or_create(enquiry=enquiry, summary="Confirm the agreement is signed",
                                   defaults=dict(kind="CALL", due_at=timezone.now() + timedelta(days=2), created_by=planner))
    customer("Nithilan", "nithilan.ramya@example.com", "9840011223", enquiry, enquiry.client)

    # --- a couple who signed up on the website and has only just started
    web_enquiry, _ = Enquiry.objects.get_or_create(
        couple_name="Anjali & Dev", defaults=dict(phone="9811122233", email="anjali.dev@example.com", source=Source.WEBSITE,
                                                   status=Status.NEW, partner_name="Dev", venue_city="Bengaluru", guest_count=180,
                                                   wedding_date=timezone.localdate() + timedelta(days=200), win_chance=10))
    customer("Anjali", "anjali.dev@example.com", "9811122233", web_enquiry)

    # --- vendor logins
    for name in VENDOR_LOGINS:
        vendor = Vendor.objects.get(name=name)
        vendor.email = f"{slug(name)}@vendors.demo"
        vendor.save(update_fields=["email"])
        account, _ = VendorAccount.objects.get_or_create(vendor=vendor, defaults=dict(email=vendor.email))
        account.set_password(DEMO_PASSWORD)
        account.invited_at = account.invited_at or timezone.now()
        account.save()
