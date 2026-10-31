from django.db import transaction
from rest_framework.exceptions import ValidationError

from clients.models import Client
from clients.services import find_client
from enquiries.models import Enquiry, Status
from weddings.models import Wedding


def client_for(enquiry: Enquiry) -> Client:
    """The client this enquiry belongs to. A client we already have (same client name + email) is reused,
    so a returning client never gets a second record; otherwise a new one is made."""
    existing = find_client(enquiry.client_name, enquiry.email)
    if existing:
        # fill in anything we did not know about them yet, but never overwrite what is there
        for field, value in (("spouse_name", enquiry.partner_name), ("spouse_email", enquiry.spouse_email),
                             ("phone", enquiry.phone), ("city", enquiry.venue_city)):
            if value and not getattr(existing, field):
                setattr(existing, field, value)
        existing.save()
        return existing
    return Client.objects.create(
        couple_name=enquiry.couple_name, client_name=enquiry.client_name, spouse_name=enquiry.partner_name,
        spouse_email=enquiry.spouse_email, phone=enquiry.phone, email=enquiry.email, city=enquiry.venue_city,
    )


@transaction.atomic
def convert_to_client(enquiry: Enquiry, create_wedding: bool = False, title: str = "",
                      start_date=None, end_date=None):
    """Turn an enquiry into a client. Doing it twice just returns the same client.

    Returns (client, wedding_or_None).
    """
    if enquiry.client_id is None:
        enquiry.client = client_for(enquiry)
    # a couple who signed up on the customer website can now see their invoices there
    customer = getattr(enquiry, "portal_customer", None)
    if customer is not None and customer.client_id is None:
        customer.client = enquiry.client
        customer.save(update_fields=["client"])
    enquiry.status = Status.WON
    enquiry.win_chance = 100
    enquiry.lost_reason = ""
    enquiry.save(update_fields=["client", "status", "win_chance", "lost_reason"])

    wedding = None
    if create_wedding:
        start_date = start_date or enquiry.wedding_date
        end_date = end_date or start_date
        if not (start_date and enquiry.guest_count and enquiry.venue_city):
            raise ValidationError("To create a wedding, the enquiry needs a wedding date, guest count and city.")
        wedding, _ = Wedding.objects.get_or_create(
            client=enquiry.client, title=title or f"{enquiry.couple_name} wedding",
            defaults=dict(start_date=start_date, end_date=end_date, city=enquiry.venue_city,
                          guest_count=enquiry.guest_count, contracted_guests=enquiry.guest_count,
                          budget_paise=enquiry.budget_paise or 0),
        )
    return enquiry.client, wedding
