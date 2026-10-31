"""Realistic money for the Aarav & Meera wedding: a part-paid instalment, five vendor bills with advances paid
and one payment that is overdue, so the dashboard shows real revenue, expenses and profit. Safe to run twice."""
from datetime import timedelta

from django.utils import timezone

from payments import services
from payments.models import Expense, Invoice
from vendors.models import Vendor
from weddings.models import Wedding

R = 100  # paise per rupee

# (vendor, category, bill amount in rupees, bill ref, final due in days from today)
# No caterer here on purpose: the caterer is still being chosen (see vendors_and_quotations.py), and
# selecting the winner creates that bill. Adding one here would count it twice.
VENDOR_BILLS = [
    ("Petals & Pillars Decor", "Decorator", 650_000, "PP-0312", 117),
    ("DJ Rhythm Raj", "DJ & Sound", 180_000, "DJR-88", -6),  # final instalment is overdue
    ("Lens & Lehenga Studio", "Photographer", 240_000, "LL-1107", 117),
]


def load():
    wedding = Wedding.objects.filter(title="Aarav & Meera - Jaipur").first()
    if wedding is None:
        return
    today = timezone.localdate()

    # the instalment invoice is part paid
    instalment = Invoice.objects.filter(wedding=wedding, kind="MILESTONE").first()
    if instalment and not instalment.payments.exists():
        services.record_invoice_payment(instalment.pk, 500_000 * R, "BANK", "DEMO-INSTALMENT-1")

    # the final payment is invoiced for after the wedding
    if not Invoice.objects.filter(wedding=wedding, kind="FINAL").exists():
        services.create_invoice(wedding, "FINAL", 1_000_000 * R, wedding.end_date + timedelta(days=7),
                                "Balance after the wedding")

    # the venue bill from the starter wedding gets half paid
    venue = Expense.objects.filter(wedding=wedding, category="Venue", vendor__isnull=True).first()
    if venue and not venue.payments.exists():
        services.record_expense_payment(venue.pk, venue.amount_paise // 2, "BANK", "DEMO-VENUE-ADVANCE")

    for vendor_name, category, rupees, bill_ref, final_in_days in VENDOR_BILLS:
        vendor = Vendor.objects.filter(name=vendor_name).first()
        if vendor is None or Expense.objects.filter(vendor=vendor, bill_number=bill_ref).exists():
            continue
        total = rupees * R
        final_due = today + timedelta(days=final_in_days)
        expense = services.create_planned_expense(
            wedding=wedding, vendor=vendor, category=category, description=f"{vendor.name} ({category})",
            amount_paise=total, due_date=final_due)
        expense.bill_number = bill_ref
        expense.save(update_fields=["bill_number"])
        advance, _final = services.create_milestones(
            wedding=wedding, vendor=vendor, expense=expense, total_paise=total, advance_pct=30,
            advance_due=today - timedelta(days=20), final_due=final_due)
        services.pay_milestone(advance.pk, method="BANK", reference=f"DEMO-ADV-{bill_ref}")
