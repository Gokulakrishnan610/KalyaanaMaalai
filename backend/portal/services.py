"""Everything the customer website does, in plain steps."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

from enquiries.models import Enquiry, Source, Status
from live.signals import alert
from payments import links
from payments.models import Invoice, PaymentLink
from portal.models import Customer

# the fields that must be filled before we call the profile complete (budget, functions and notes are optional)
REQUIRED = ["partner_name", "wedding_date", "venue_city", "guest_count", "services_needed", "preferred_contact"]
OPTIONAL = ["budget_paise", "functions_wanted"]
LABELS = {
    "partner_name": "your partner's name", "wedding_date": "the wedding date", "venue_city": "the city",
    "guest_count": "the number of guests", "services_needed": "the services you need",
    "preferred_contact": "how we should contact you", "budget_paise": "your budget",
    "functions_wanted": "the functions you want",
}

# what the couple sees at each CRM stage, and where it sits on the journey bar
STAGES = {
    Status.NEW: (0, "Request received", "We have your details. A planner will contact you soon."),
    Status.CONTACTED: (1, "Planner in touch", "Our planner has reached out to you."),
    Status.CONSULTATION: (2, "Consultation booked", "Your first meeting with our planner is booked."),
    Status.PROPOSAL: (3, "Proposal on its way", "We have prepared a proposal for your wedding."),
    Status.WON: (4, "You are booked", "Your wedding project has started. Your payments appear below."),
    Status.LOST: (-1, "Closed", "This request is closed. You can always write to us again."),
}


@transaction.atomic
def create_account(name: str, email: str, phone: str, password: str) -> Customer:
    """A new account always creates a CRM enquiry, so the planners see the couple straight away."""
    enquiry = Enquiry.objects.create(couple_name=name, phone=phone, email=email, source=Source.WEBSITE,
                                     status=Status.NEW)
    customer = Customer(name=name, email=email, phone=phone, enquiry=enquiry)
    customer.set_password(password)
    customer.save()
    alert(f"New website sign-up: {name} ({phone})", key=f"signup:{customer.pk}")
    return customer


def profile_values(enquiry: Enquiry) -> dict:
    return {
        "partner_name": enquiry.partner_name, "wedding_date": enquiry.wedding_date,
        "venue_city": enquiry.venue_city, "guest_count": enquiry.guest_count, "budget_paise": enquiry.budget_paise,
        "functions_wanted": enquiry.functions_wanted, "services_needed": enquiry.services_needed,
        "preferred_contact": enquiry.preferred_contact, "notes": enquiry.notes,
    }


def profile_status(enquiry: Enquiry) -> dict:
    """How much of the profile is filled, and what is still missing."""
    values = profile_values(enquiry)
    missing = [key for key in REQUIRED if not values[key]]
    filled = len(REQUIRED) - len(missing) + sum(1 for key in OPTIONAL if values[key])
    return {
        "percent": round(filled * 100 / (len(REQUIRED) + len(OPTIONAL))),
        "complete": not missing,
        "missing": [LABELS[key] for key in missing],
    }


@transaction.atomic
def update_profile(customer: Customer, data: dict) -> Enquiry:
    enquiry = Enquiry.objects.select_for_update().get(pk=customer.enquiry_id)
    for field, value in data.items():
        setattr(enquiry, field, value)
    if "partner_name" in data and data["partner_name"]:
        enquiry.couple_name = f"{customer.name} & {data['partner_name']}"
    was_complete = enquiry.profile_complete
    enquiry.profile_complete = profile_status(enquiry)["complete"]
    enquiry.save()
    if enquiry.profile_complete and not was_complete:
        when = enquiry.wedding_date.strftime("%d %b %Y") if enquiry.wedding_date else "date not set"
        alert(f"{enquiry.couple_name} completed their profile: {when}, {enquiry.guest_count} guests, "
              f"{enquiry.venue_city}", key=f"profile:{customer.pk}")
    return enquiry


def stage_for(enquiry: Enquiry) -> dict:
    step, label, hint = STAGES[enquiry.status]
    return {"key": enquiry.status, "step": step, "label": label, "hint": hint,
            "consultation_at": enquiry.consultation_at}


def invoices_for(customer: Customer) -> list[dict]:
    """The customer's invoices once the planner has made them a client."""
    if not customer.client_id:
        return []
    rows = []
    for invoice in Invoice.objects.filter(client_id=customer.client_id).select_related("wedding").order_by("due_date", "id"):
        paid = sum(p.amount_paise for p in invoice.payments.all())
        rows.append({"id": invoice.pk, "label": invoice.get_kind_display(), "note": invoice.note,
                     "wedding": invoice.wedding.title, "due_date": invoice.due_date,
                     "amount_paise": invoice.amount_paise, "paid_paise": paid,
                     "remaining_paise": invoice.amount_paise - paid, "status": invoice.status})
    return rows


def pay_path(customer: Customer, invoice_id: int) -> str:
    """Gets (or makes) a payment link for one of the customer's own invoices and returns its page address."""
    try:
        invoice = Invoice.objects.get(pk=invoice_id, client_id=customer.client_id)
    except Invoice.DoesNotExist:
        raise NotFound("Invoice not found.") from None
    remaining = links.remaining_on(invoice)
    existing = invoice.links.filter(status=PaymentLink.Status.ACTIVE, expires_at__gt=timezone.now(),
                                    amount_paise=remaining).first()
    link = existing or links.create_link(invoice, None, created_by=None, days=2)
    return f"/pay/{link.token}"
