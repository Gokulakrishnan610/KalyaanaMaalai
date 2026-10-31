from django.db import transaction
from rest_framework.exceptions import ValidationError

from clients.models import Client
from enquiries.models import Enquiry, Status
from weddings.models import Wedding


@transaction.atomic
def convert_to_client(enquiry: Enquiry, create_wedding: bool = False, title: str = "",
                      start_date=None, end_date=None):
    """Turn an enquiry into a client. Doing it twice just returns the same client.

    Returns (client, wedding_or_None).
    """
    if enquiry.client_id is None:
        enquiry.client = Client.objects.create(
            couple_name=enquiry.couple_name, phone=enquiry.phone, email=enquiry.email,
            city=enquiry.venue_city,
        )
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
