"""The Aarav & Meera wedding with a deposit, a vendor bill and a few tasks, so the dashboard
is not empty. Other members add their own files (see common/management/commands/load_demo_data.py)."""
from datetime import datetime, time, timedelta

from django.utils import timezone

from accounts.models import User
from clients.models import Client
from payments.models import Expense, Invoice, Payment
from tasks.models import Task
from weddings.models import Wedding, WeddingFunction

PAISE = 100  # paise per rupee


def load():
    client = Client.objects.get(couple_name="Aarav & Meera")
    planner = User.objects.get(email="planner@shaandaar.demo")
    first_day = timezone.localdate() + timedelta(days=120)

    wedding, created = Wedding.objects.get_or_create(
        title="Aarav & Meera - Jaipur", client=client,
        defaults=dict(start_date=first_day, end_date=first_day + timedelta(days=2), city="Jaipur",
                      guest_count=450, contracted_guests=400, per_guest_rate_paise=2500 * PAISE,
                      budget_paise=4_500_000 * PAISE),
    )
    if not created:
        return

    for offset, name in enumerate(["Mehendi", "Sangeet", "Reception"]):
        day = first_day + timedelta(days=offset)
        start = timezone.make_aware(datetime.combine(day, time(18, 0)))
        WeddingFunction.objects.create(wedding=wedding, name=name, starts_at=start,
                                       ends_at=start + timedelta(hours=5), guest_count=450)

    deposit = Invoice.objects.create(wedding=wedding, client=client, kind="DEPOSIT",
                                     amount_paise=500_000 * PAISE, status="PAID",
                                     due_date=timezone.localdate())
    Payment.objects.create(wedding=wedding, invoice=deposit, direction="IN", method="UPI",
                           amount_paise=500_000 * PAISE, reference="DEMO-DEPOSIT")
    Invoice.objects.create(wedding=wedding, client=client, kind="MILESTONE", amount_paise=1_500_000 * PAISE,
                           due_date=first_day - timedelta(days=30))
    Expense.objects.create(wedding=wedding, category="Venue", description="Venue booking advance",
                           amount_paise=400_000 * PAISE, due_date=timezone.localdate() + timedelta(days=5))

    for title, stage in [("Finalise venue", "DONE"), ("Book caterer", "IN_PROGRESS"), ("Book DJ", "TO_PLAN"),
                         ("Send invitations", "TO_PLAN")]:
        Task.objects.create(wedding=wedding, title=title, stage=stage, assigned_to=planner)
