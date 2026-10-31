"""Demo users, the Aarav & Meera client, and a few enquiries. Safe to run twice."""
from datetime import timedelta

from django.utils import timezone

from accounts.models import Role, User
from clients.models import Client
from enquiries.models import STAGE_WIN_CHANCE, Enquiry, FollowUp, Source, Status

DEMO_PASSWORD = "Demo@12345"  # for demo data only

PEOPLE = [
    ("Founder Shaandaar", "founder@shaandaar.demo", Role.FOUNDER),
    ("Priya Planner", "planner@shaandaar.demo", Role.PLANNER),
    ("Sam Staff", "staff@shaandaar.demo", Role.STAFF),
]


def load():
    for name, email, role in PEOPLE:
        if not User.objects.filter(email=email).exists():
            User.objects.create_user(email=email, name=name, password=DEMO_PASSWORD, role=role,
                                     is_staff=(role == Role.FOUNDER), is_superuser=(role == Role.FOUNDER))

    planner = User.objects.get(email="planner@shaandaar.demo")
    client, _ = Client.objects.get_or_create(
        couple_name="Aarav & Meera",
        defaults=dict(bride_name="Meera", groom_name="Aarav", phone="9876543210",
                      email="aarav.meera@example.com", city="Jaipur"),
    )

    soon = timezone.now() + timedelta(days=3)
    wedding_day = (timezone.now() + timedelta(days=120)).date()
    # couple, phone, source, stage, guests, budget, city, client, expected fee, priority stars
    enquiries = [
        ("Aarav & Meera", "9876543210", Source.INSTAGRAM, Status.WON, 450, 4_500_000_00, "Jaipur", client, 450_000_00, 3),
        ("Rohan & Ishita", "9812345670", Source.WHATSAPP, Status.CONSULTATION, 300, 2_500_000_00, "Udaipur", None, 250_000_00, 2),
        ("Kabir & Sana", "9898989898", Source.CALL, Status.NEW, 200, 1_800_000_00, "Delhi", None, 180_000_00, 1),
        ("Vikram & Neha", "9765432101", Source.REFERRAL, Status.PROPOSAL, 500, 6_000_000_00, "Jodhpur", None, 600_000_00, 3),
    ]
    for couple, phone, source, status, guests, budget, city, linked_client, fee, stars in enquiries:
        enquiry, created = Enquiry.objects.get_or_create(
            couple_name=couple,
            defaults=dict(phone=phone, source=source, status=status, guest_count=guests, budget_paise=budget,
                          venue_city=city, client=linked_client, owner=planner, wedding_date=wedding_day,
                          consultation_at=soon if status == Status.CONSULTATION else None,
                          expected_revenue_paise=fee, priority=stars, win_chance=STAGE_WIN_CHANCE[status],
                          expected_close_date=wedding_day - timedelta(days=60)),
        )
        if created and status not in (Status.WON, Status.LOST):
            FollowUp.objects.create(enquiry=enquiry, kind="CALL", summary="Check in about the proposal",
                                    due_at=timezone.now() + timedelta(days=1), created_by=planner)
