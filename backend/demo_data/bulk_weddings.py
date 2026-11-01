"""About 450 complete weddings, every one built like Aarav & Meera, covering every case the app handles.

    python manage.py load_demo_data --bulk          # 450 weddings (the default)
    python manage.py load_demo_data --bulk 120      # a smaller set

Each wedding gets a client, a won enquiry with follow-ups, functions at venues, a planning team, the 25-30 task
template (spread over the Kanban by its dates), vendor quotation requests with quotes, the chosen vendors with their
bills and advance/final instalments, customer invoices with payments and payment links, vendor check-ins, run sheets,
vendor ratings and incidents, plus the signed (or waiting) service agreement, the client's website login and the
log of every email sent. Vendors get logins too. Around the weddings sit about 170 enquiries that did not convert (every stage and lost
reason) and customer-website accounts.

The dates are relative to the day you load it: past weddings are completed, nearer ones confirmed, further ones still
being planned, a few cancelled, and one wedding is happening today so the event-day screens have something live.

Safe to run twice: a wedding that is already loaded is skipped. Every number comes from a random generator seeded
per wedding, so the same wedding always looks the same. Nothing here touches the Aarav & Meera records.
"""
import base64
import math
import random
import struct
import zlib
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from itertools import product
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from agreements.models import Agreement
from agreements.services import default_body, fingerprint
from ai_tools.models import AIJob
from clients.models import Client
from demo_data.portal_and_agreements import SIGNATURE
from enquiries.models import (
    STAGE_WIN_CHANCE,
    Enquiry,
    FollowUp,
    LostReason,
    Source,
    Status,
)
from incidents.models import Incident, IncidentStatus, IncidentUpdate
from mailer.models import EmailLog
from mailer.services import render as mail_render
from notifications.models import Notification
from payments.models import Expense, Invoice, Payment, PaymentLink, PayStatus, VendorPaymentPlan
from payments.services import derive_status
from portal.accounts import link_for
from portal.models import Customer, VendorAccount
from quotations.models import (
    Quotation,
    QuotationItem,
    QuotationRequest,
    QuotationStatus,
    RequestStatus,
    WeddingVendor,
)
from tasks.models import Stage, Task
from tasks.template import TEMPLATE
from vendors.models import Vendor, VendorCategory
from weddings.models import (
    ScheduleItem,
    TeamMember,
    VendorArrival,
    VendorRating,
    Venue,
    Wedding,
    WeddingFunction,
    WeddingStatus,
)

R = 100  # paise per rupee
PRICE_SCALE = 0.45  # non-caterer quote sizes, so a whole wedding costs what a real mid-size one does
IST = ZoneInfo("Asia/Kolkata")
UTC = dt_timezone.utc
DEMO_PASSWORD = "Demo@12345"  # same as the other demo accounts; for demo data only
DEFAULT_WEDDINGS = 450

# --------------------------------------------------------------------------------------------- name pools
GROOMS = ["Arjun", "Vihaan", "Aditya", "Ishaan", "Reyansh", "Krish", "Dhruv", "Ayaan", "Siddharth", "Rahul", "Nikhil",
          "Harsh", "Yash", "Manav", "Tushar", "Pranav", "Varun", "Karthik", "Rohit", "Imran", "Aman", "Naveen",
          "Devansh", "Sahil", "Lakshya"]
BRIDES = ["Ananya", "Diya", "Kavya", "Myra", "Saanvi", "Aditi", "Riya", "Tanvi", "Nisha", "Shreya", "Priyanka",
          "Anjali", "Divya", "Kritika", "Simran", "Pallavi", "Ritika", "Sakshi", "Mansi", "Lavanya", "Aisha", "Zara",
          "Bhavna", "Harini", "Ishika"]
SURNAMES = ["Sharma", "Verma", "Mehta", "Kapoor", "Singh", "Reddy", "Iyer", "Nair", "Patel", "Shah", "Joshi", "Gupta",
            "Khan", "Das", "Bose", "Menon", "Rao", "Chopra", "Malhotra", "Bhatia", "Saxena", "Agarwal", "Jain",
            "Thakur", "Rathore", "Pillai", "Desai", "Banerjee", "Kulkarni", "Sethi"]
CITIES = ["Jaipur", "Udaipur", "Jodhpur", "Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Pune",
          "Ahmedabad", "Goa", "Lucknow", "Chandigarh", "Kochi", "Indore"]
CITY_WEIGHTS = [14, 9, 6, 12, 10, 8, 7, 6, 4, 6, 5, 4, 3, 3, 2, 2]
VENUE_PREFIX = ["Royal", "Grand", "Heritage", "Lakeview", "Palm", "Regal", "Sunrise", "Maharaja", "Orchid", "Crystal",
                "Emerald", "Golden"]
VENUE_SUFFIX = ["Palace", "Lawns", "Resort", "Banquets", "Gardens", "Fort", "Haveli", "Convention Centre"]

STAFF_PEOPLE = [  # (name, role)
    ("Neha Kapoor", Role.PLANNER), ("Rahul Verma", Role.PLANNER), ("Aisha Khan", Role.PLANNER),
    ("Vikram Joshi", Role.PLANNER), ("Meera Iyer", Role.PLANNER),
    ("Karan Singh", Role.STAFF), ("Pooja Nair", Role.STAFF), ("Rohit Das", Role.STAFF), ("Sneha Reddy", Role.STAFF),
    ("Arun Patel", Role.STAFF), ("Divya Menon", Role.STAFF), ("Imran Sheikh", Role.STAFF),
]

# category -> (name prefixes, name suffixes, lead minutes before the function, check-in importance)
VENDOR_NAMES = {
    "Caterer": (["Rasoi", "Spice", "Annapurna", "Bhoj", "Swad", "Zaika", "Dawat", "Shahi", "Maharaja", "Tadka"],
                ["Royale", "Route Catering", "Feast", "Kitchen", "Caterers", "Delights", "Bhojnalaya"]),
    "Decorator": (["Petals", "Royal", "Dream", "Blossom", "Mandap", "Regal", "Floral", "Ivory", "Saffron", "Gilded"],
                  ["& Pillars Decor", "Mandap Decor", "Events Decor", "Weaves", "Setups", "Studios"]),
    "DJ & Sound": (["DJ", "Beat", "Bass", "Sonic", "Rhythm", "SoundWave", "Echo", "Pulse", "Vibe", "Tempo"],
                   ["Raj", "Box DJs", "Productions", "Sound Co", "Live", "Studio"]),
    "Photographer": (["Lens", "Candid", "Frame", "Shutter", "Focus", "Memory", "Click", "Aperture", "Moments", "Pixel"],
                     ["& Lehenga Studio", "Stories", "Weddings", "Tales", "Photography", "Co"]),
    "Videographer": (["Reel", "Cine", "Motion", "Story", "Film", "Vow", "Silver", "Frame"],
                     ["craft Films", "Wedding Films", "Pictures", "Reels", "Studio"]),
    "Makeup Artist": (["Glam by", "Bridal by", "Blush by", "Beauty by", "Makeover by"],
                      ["Anjali", "Rhea", "Sana", "Meghna", "Kiran", "Tara", "Isha", "Komal", "Nandini", "Reena"]),
    "Mehendi Artist": (["Henna by", "Mehendi by", "Hastkala by"],
                       ["Sunita", "Rukhsar", "Geeta", "Farah", "Lata", "Pushpa", "Salma", "Radha", "Asha", "Mamta"]),
    "Florist": (["Phool", "Bloom", "Gulab", "Petal", "Marigold", "Jasmine"],
                ["Bagh Florals", "House", "Garlands", "Co", "Creations"]),
    "Transport": (["Royal", "City", "Heritage", "Swift", "Premier", "Vintage"],
                  ["Cars", "Travels", "Ride", "Coaches", "Tours"]),
    "Invitation Printer": (["Card", "Ink", "Paper", "Print", "Invite"],
                           ["Wala", "House", "Studio", "Press", "Co"]),
}
VENDORS_PER_CATEGORY = 16
ARRIVAL_LEAD_MINUTES = {"Decorator": 360, "Caterer": 240, "DJ & Sound": 150, "Photographer": 120, "Videographer": 120,
                        "Makeup Artist": 300, "Mehendi Artist": 180, "Florist": 300, "Transport": 60}
CHECKIN_CATEGORIES = list(ARRIVAL_LEAD_MINUTES)

FUNCTION_TIMES = {  # IST wall-clock start, end
    "Engagement": ((17, 0), (21, 0)), "Haldi": ((10, 0), (13, 0)), "Mehendi": ((11, 0), (16, 0)),
    "Sangeet": ((19, 0), (23, 30)), "Wedding": ((10, 0), (15, 0)), "Reception": ((19, 30), (23, 30)),
}
SCHEDULE_TEMPLATES = {  # (title, minutes after the function starts, minutes long)
    "Sangeet": [("Guests arrive, welcome drinks", 0, 45), ("Sound check and stage ready", 45, 45),
                ("Family dance performances", 90, 60), ("Dinner counters open", 150, 40),
                ("DJ set and open dance floor", 190, 60), ("Last songs and send-off", 250, 30)],
    "Wedding": [("Baraat arrives at the venue", 0, 40), ("Milni and welcome", 40, 30), ("Jaimala on stage", 70, 30),
                ("Pheras and rituals", 100, 90), ("Photo session with families", 190, 45),
                ("Vidaai", 235, 35)],
    "Reception": [("Doors open, welcome drinks", 0, 40), ("Couple's grand entry", 40, 20), ("Cake cutting", 60, 20),
                  ("Dinner service", 80, 90), ("Performances and speeches", 150, 45), ("DJ and dance floor", 195, 45)],
    "Mehendi": [("Artists set up", 0, 30), ("Bride's mehendi", 30, 120), ("Guest mehendi stations open", 60, 150),
                ("Lunch and music", 150, 90), ("Group photos", 240, 30)],
    "Haldi": [("Setup and flowers ready", 0, 30), ("Haldi ceremony", 30, 70), ("Family photos", 100, 40),
              ("Brunch served", 140, 40)],
    "Engagement": [("Guests seated", 0, 30), ("Ring ceremony", 30, 45), ("Family blessings", 75, 40),
                   ("Dinner", 115, 90), ("Music and send-off", 205, 35)],
}
CUSTOM_TASKS = [  # (title, category, offset days, priority)
    ("Confirm groom's sherwani trial", "Personal", -30, "LOW"), ("Book honeymoon flights", "Personal", -50, "LOW"),
    ("Arrange mehendi seating for elders", "Guests", -12, "LOW"), ("Collect family photo list", "Media", -20, "MEDIUM"),
    ("Order welcome hampers for guests", "Guests", -35, "MEDIUM"), ("Fix rain contingency for lawns", "Logistics", -15, "HIGH"),
    ("Arrange dhol and band for baraat", "Rituals", -25, "MEDIUM"), ("Book return transport for elders", "Logistics", 1, "LOW"),
    ("Pack and ship gifts received", "Follow-up", 3, "LOW"), ("Confirm fireworks permission", "Legal", -18, "HIGH"),
    ("Hair and makeup trial for bride", "Beauty", -28, "MEDIUM"), ("Print menu cards and signage", "Decor", -14, "LOW"),
]
INCIDENTS = [  # (title, description, severity)
    ("Generator failed during the sangeet", "Power dropped for 12 minutes; the backup unit was started by hand.", "CRITICAL"),
    ("Caterer ran short of desserts", "The dessert counter emptied early; extra trays were requested from the kitchen.", "MEDIUM"),
    ("Florist delivered the wrong garland colour", "Garlands arrived in orange instead of the agreed marigold and white.", "LOW"),
    ("Makeup artist running late", "The bridal makeup artist was stuck in traffic and the trial slot was pushed back.", "HIGH"),
    ("Sound system feedback on stage", "Loud feedback during speeches; the technician swapped the wireless mic.", "MEDIUM"),
    ("Hotel rooms overbooked", "Six guest rooms were double-booked and families had to be re-allotted.", "HIGH"),
    ("Rain disrupted the mandap set-up", "Open-air set-up was soaked; the team moved the ceremony under the tent.", "CRITICAL"),
    ("Valet parking congestion", "Cars queued back to the main road during the baraat.", "LOW"),
    ("Return gift count was short", "Forty gift boxes missing from the delivery; the vendor sent them by evening.", "MEDIUM"),
    ("Banquet hall power cut", "Lights and AC went off for the reception; the venue switched to its inverter.", "CRITICAL"),
    ("Photographer's memory card error", "One card failed to read; the second shooter's backup saved the footage.", "HIGH"),
    ("More guests than planned at dinner", "About 40 extra guests; the caterer added counters at short notice.", "MEDIUM"),
]
INCIDENT_CYCLE_DONE = [IncidentStatus.RESOLVED, IncidentStatus.RESOLVED, IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED,
                       IncidentStatus.RESOLVED, IncidentStatus.ASSIGNED, IncidentStatus.RESOLVED, IncidentStatus.RESOLVED,
                       IncidentStatus.OPEN, IncidentStatus.RESOLVED]
INCIDENT_CYCLE_LIVE = [IncidentStatus.OPEN, IncidentStatus.ASSIGNED, IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED]
FOLLOW_UP_SUMMARIES = {
    "CALL": ["Intro call about dates and budget", "Check in about the proposal", "Call to confirm the venue visit",
             "Discuss guest list and functions"],
    "MEETING": ["Consultation at the office", "Venue walkthrough with the family", "Menu tasting meeting"],
    "WHATSAPP": ["Send the sample packages on WhatsApp", "Share the quotation PDF", "Send mood-board ideas"],
    "EMAIL": ["Email the proposal and terms", "Send the payment schedule"],
    "TODO": ["Prepare the proposal", "Check venue availability for the date", "Compare vendor options"],
}
SERVICES = ["VENUE", "CATERING", "DECOR", "PHOTO", "MAKEUP", "MUSIC", "MEHENDI", "INVITES", "TRANSPORT", "STAY"]
FUNCTION_KEYS = {"Engagement": "ENGAGEMENT", "Mehendi": "MEHENDI", "Haldi": "HALDI", "Sangeet": "SANGEET",
                 "Wedding": "WEDDING", "Reception": "RECEPTION"}
OFFLINE_METHODS = ["CASH", "UPI", "BANK", "BANK", "CHEQUE", "CARD", "UPI"]


# --------------------------------------------------------------------------------------------- small helpers
def at(day: date, hour: int, minute: int = 0) -> datetime:
    """An Indian wall-clock time on `day`, stored as UTC (the website shows it back in local time)."""
    return datetime.combine(day, time(hour, minute), tzinfo=IST).astimezone(UTC)


def at_dt(day: date, hour: int = 12, minute: int = 0) -> datetime:
    return at(day, hour, minute)


def round_to(value: float, unit: int) -> int:
    return int(value // unit) * unit


def pick(rng: random.Random, weighted: list):
    """`weighted` is [(value, weight), ...]."""
    values, weights = zip(*weighted, strict=True)
    return rng.choices(values, weights=weights, k=1)[0]


def client_email(idx: int) -> str:
    return f"{GROOM_BRIDE_PAIRS[idx][0].lower()}.{SURNAMES[idx % len(SURNAMES)].lower()}{idx:03d}@bulk.demo"


def lead_email(n: int) -> str:
    return f"lead{n:03d}@leads.demo"


_pairs = [p for p in product(GROOMS, BRIDES)]
random.Random(1107).shuffle(_pairs)
GROOM_BRIDE_PAIRS = _pairs


def vendor_profile(name: str) -> dict:
    """How good a vendor is, decided by their name so it never changes: quality, punctuality, price level."""
    r = random.Random("vendor-" + name)
    return {"quality": r.uniform(2.9, 4.9), "punctual": r.uniform(0.5, 0.99), "price": r.uniform(0.8, 1.3)}


class Pools:
    """People, venues and vendors the weddings draw from (created once, reused on later runs)."""

    def __init__(self):
        self.founder = User.objects.filter(role=Role.FOUNDER).order_by("id").first()
        self.password_hash = make_password(DEMO_PASSWORD)
        self.planners: list[User] = []
        self.staff: list[User] = []
        self.venues_by_city: dict[str, list[Venue]] = {}
        self.vendors_by_cat: dict[str, list[Vendor]] = {}
        self.categories: dict[str, VendorCategory] = {}

    def build(self):
        self._users()
        self._venues()
        self._vendors()

    def _users(self):
        for name, role in STAFF_PEOPLE:
            email = f"{name.lower().replace(' ', '.')}@shaandaar.demo"
            user = User.objects.filter(email=email).first() or User.objects.create(
                email=email, name=name, role=role, password=self.password_hash)
            (self.planners if role == Role.PLANNER else self.staff).append(user)
        for user in User.objects.filter(email__in=["planner@shaandaar.demo"]):
            self.planners.append(user)
        for user in User.objects.filter(email="staff@shaandaar.demo"):
            self.staff.append(user)

    def _venues(self):
        rng = random.Random("venues")
        used = set(Venue.objects.values_list("name", flat=True))
        for city in CITIES:
            for _ in range(4):
                for _ in range(20):
                    name = f"{rng.choice(VENUE_PREFIX)} {rng.choice(VENUE_SUFFIX)}"
                    if name not in used:
                        break
                else:
                    name = f"{name} {city}"
                used.add(name)
                venue, _ = Venue.objects.get_or_create(
                    name=name, defaults=dict(city=city, capacity=rng.choice([150, 250, 400, 600, 800, 1200]),
                                             address=f"{rng.randint(1, 99)}, Main Road, {city}"))
        for venue in Venue.objects.exclude(city=""):
            self.venues_by_city.setdefault(venue.city, []).append(venue)

    def _vendors(self):
        self.categories = {c.name: c for c in VendorCategory.objects.all()}
        for category, (prefixes, suffixes) in VENDOR_NAMES.items():
            rng = random.Random("vendors-" + category)
            combos = [f"{p} {s}" for p in prefixes for s in suffixes]
            rng.shuffle(combos)
            if category not in self.categories:
                self.categories[category] = VendorCategory.objects.create(name=category)
            for name in combos[:VENDORS_PER_CATEGORY]:
                city = rng.choices(CITIES, weights=CITY_WEIGHTS, k=1)[0]
                if not Vendor.objects.filter(name=name).exists():
                    phone = f"98{rng.randint(10000000, 99999999)}"
                    Vendor.objects.create(
                        name=name, category=self.categories[category], city=city, phone=phone,
                        contact_person=f"{rng.choice(GROOMS)} {rng.choice(SURNAMES)}",
                        email=f"{phone}@vendors.example.com", notes=rng.choice(
                            ["", "", "Prefers 30% advance.", "Needs 10 days notice.", "Travels outside the city.",
                             "Has its own sound and lights team."]))
        for vendor in Vendor.objects.select_related("category"):
            self.vendors_by_cat.setdefault(vendor.category.name, []).append(vendor)

    def venue_for(self, rng, city, start, end):
        for venue in rng.sample(self.venues_by_city.get(city, []), k=len(self.venues_by_city.get(city, []))):
            if not WeddingFunction.objects.filter(venue=venue, starts_at__lt=end, ends_at__gt=start).exists():
                return venue
        return None

    def vendors_for(self, rng, category, city, count):
        pool = self.vendors_by_cat.get(category, [])
        local = [v for v in pool if v.city == city]
        rest = [v for v in pool if v.city != city]
        rng.shuffle(local)
        rng.shuffle(rest)
        return (local + rest)[:count]


# --------------------------------------------------------------------------------------------- the weddings
def timeline(idx: int, rng: random.Random, today: date):
    """(status, start_date, days). A few fixed cases first so the live screens always have something to show."""
    days = rng.choice([1, 1, 2, 2, 3, 3, 4])
    special = {0: (WeddingStatus.CONFIRMED, today, 2),            # happening today
               1: (WeddingStatus.CONFIRMED, today + timedelta(days=2), 2),
               2: (WeddingStatus.CONFIRMED, today + timedelta(days=5), 3),
               3: (WeddingStatus.CONFIRMED, today - timedelta(days=1), 3)}  # started yesterday, ends tomorrow
    if idx in special:
        return special[idx]
    slot = idx % 20
    if slot <= 10:
        return WeddingStatus.COMPLETED, today - timedelta(days=rng.randint(max(days + 2, 10), 330)), days
    if slot <= 14:
        return WeddingStatus.CONFIRMED, today + timedelta(days=rng.randint(8, 190)), days
    if slot <= 18:
        return WeddingStatus.PLANNING, today + timedelta(days=rng.randint(30, 430)), days
    return WeddingStatus.CANCELLED, today + timedelta(days=rng.randint(-120, 300)), days


def function_plan(rng, days):
    """[(name, day offset)] for a wedding that lasts `days` days."""
    if days == 1:
        return [("Wedding", 0)] + ([("Reception", 0)] if rng.random() < 0.4 else [])
    if days == 2:
        plan = [("Sangeet", 0), ("Wedding", 1)]
        return plan + ([("Reception", 1)] if rng.random() < 0.35 else [])
    if days == 3:
        plan = [("Mehendi", 0), ("Sangeet", 1), ("Wedding", 2)]
        return plan + ([("Reception", 2)] if rng.random() < 0.5 else [])
    plan = [("Haldi", 0), ("Mehendi", 0), ("Sangeet", 1), ("Wedding", 2), ("Reception", 3)]
    return ([("Engagement", 0)] + plan) if rng.random() < 0.25 else plan


def task_stage(rng, due: date, today: date, status: str) -> str:
    delta = (due - today).days
    if status == WeddingStatus.COMPLETED:
        if delta > 0:  # a post-event job still ahead of us
            return pick(rng, [(Stage.TO_PLAN, 55), (Stage.IN_PROGRESS, 35), (Stage.READY, 10)])
        return pick(rng, [(Stage.DONE, 96), (Stage.READY, 2), (Stage.IN_PROGRESS, 1), (Stage.TO_PLAN, 1)])
    if status == WeddingStatus.CANCELLED:
        return pick(rng, [(Stage.DONE, 55), (Stage.TO_PLAN, 40), (Stage.IN_PROGRESS, 5)]) if delta < 0 \
            else pick(rng, [(Stage.TO_PLAN, 85), (Stage.IN_PROGRESS, 15)])
    if delta < -20:
        return pick(rng, [(Stage.DONE, 88), (Stage.IN_PROGRESS, 5), (Stage.READY, 3), (Stage.TO_PLAN, 4)])
    if delta < 0:
        return pick(rng, [(Stage.DONE, 55), (Stage.READY, 15), (Stage.IN_PROGRESS, 15), (Stage.TO_PLAN, 15)])
    if delta < 14:
        return pick(rng, [(Stage.IN_PROGRESS, 45), (Stage.READY, 20), (Stage.TO_PLAN, 30), (Stage.DONE, 5)])
    if delta < 45:
        return pick(rng, [(Stage.TO_PLAN, 65), (Stage.IN_PROGRESS, 25), (Stage.READY, 7), (Stage.DONE, 3)])
    return pick(rng, [(Stage.TO_PLAN, 93), (Stage.IN_PROGRESS, 5), (Stage.DONE, 2)])


def quote_items(rng, category: str, guests: int, price: float, per_plate: int | None):
    """Line items (description, qty, unit paise) typical for the category."""
    if category == "Caterer":
        plate = per_plate or 1000 * R
        lines = [("Buffet menu", guests, int(plate * 0.74)), ("Welcome drinks", guests, int(plate * 0.09))]
        if rng.random() < 0.7:
            lines.append(("Live counters (chaat, pasta)", rng.randint(1, 3), rng.randint(20000, 35000) * R))
        if rng.random() < 0.55:
            lines.append(("Dessert station", 1, rng.randint(20000, 45000) * R))
        if rng.random() < 0.3:
            lines.append(("Midnight snacks", guests, int(plate * 0.07)))
        return lines
    unit = lambda lo, hi: int(rng.randint(lo, hi) * price * PRICE_SCALE) * R  # noqa: E731
    return {
        "Decorator": [("Decoration package", 1, unit(250000, 650000)), ("Stage decoration", rng.randint(1, 3), unit(80000, 240000)),
                      ("Flower decoration", rng.randint(2, 6), unit(25000, 70000)), ("Lighting", rng.randint(1, 4), unit(40000, 120000)),
                      ("Entrance decoration", 1, unit(30000, 90000))],
        "Photographer": [("Candid photography (per day)", rng.randint(1, 4), unit(40000, 110000)),
                         ("Traditional photography", rng.randint(1, 3), unit(25000, 60000)),
                         ("Premium album", rng.randint(1, 2), unit(20000, 45000))],
        "Videographer": [("Wedding film (per day)", rng.randint(1, 4), unit(40000, 100000)),
                         ("Highlights reel", 1, unit(30000, 70000)), ("Drone coverage", 1, unit(15000, 35000))],
        "DJ & Sound": [("DJ and sound (per function)", rng.randint(1, 3), unit(40000, 110000)),
                       ("Dance floor lights", 1, unit(15000, 40000)), ("Live emcee", 1, unit(10000, 30000))],
        "Makeup Artist": [("Bridal makeup", 1, unit(25000, 90000)), ("Family makeup", rng.randint(2, 8), unit(5000, 12000)),
                          ("Hair styling", rng.randint(2, 6), unit(3000, 8000))],
        "Mehendi Artist": [("Bridal mehendi", 1, unit(15000, 45000)), ("Guest mehendi (per hour)", rng.randint(3, 8), unit(2500, 6000))],
        "Florist": [("Mandap flowers", 1, unit(60000, 160000)), ("Garlands and jaimala", rng.randint(2, 6), unit(5000, 15000)),
                    ("Aisle and table flowers", 1, unit(30000, 90000))],
        "Transport": [("Luxury cars (per day)", rng.randint(2, 6), unit(8000, 20000)), ("Guest shuttle buses", rng.randint(1, 4), unit(10000, 25000))],
        "Invitation Printer": [("Printed invitations (per box)", max(50, guests // 4), unit(250, 700)),
                               ("Digital invitation video", 1, unit(5000, 15000))],
    }.get(category, [("Service package", 1, unit(50000, 200000))])


def typical_cost(category: str, guests: int) -> int:
    """What a category usually costs, for planning the contract before every quote is in."""
    if category == "Caterer":
        return 1100 * guests * R
    return {"Decorator": 570_000, "Photographer": 100_000, "Videographer": 85_000, "DJ & Sound": 90_000,
            "Makeup Artist": 70_000, "Mehendi Artist": 30_000, "Florist": 55_000, "Transport": 45_000,
            "Invitation Printer": 30_000}.get(category, 60_000) * R


def requirement_text(category: str, functions: list[str]) -> str:
    base = {"Caterer": "Vegetarian-first menu, live counters and a dessert station; Jain options for some guests.",
            "Decorator": "Mandap, stage and entrance decoration in the couple's colours with warm lighting.",
            "Photographer": "Candid and traditional coverage of every function with an edited album.",
            "Videographer": "Cinematic film with a same-week highlights reel.",
            "DJ & Sound": "DJ, sound and dance-floor lights; a live emcee for the reception.",
            "Makeup Artist": "Bridal makeup and hair, plus family styling on the wedding morning.",
            "Mehendi Artist": "Bridal mehendi and guest stations for the mehendi function.",
            "Florist": "Fresh marigold and rose garlands, jaimala and table flowers.",
            "Transport": "Cars for the family and shuttles between the hotel and venues.",
            "Invitation Printer": "Printed invitation boxes plus a digital invitation video."}[category]
    return f"{base} Functions: {', '.join(functions)}."


class Counter(dict):
    def add(self, key, n=1):
        self[key] = self.get(key, 0) + n


def bulk(model, objs, counter: Counter, key=None):
    """bulk_create, then give every object the created_at it should have (auto_now_add always writes 'now')."""
    if not objs:
        return objs
    model.objects.bulk_create(objs)
    stamped = [o for o in objs if getattr(o, "_ts", None)]
    if stamped:
        for o in stamped:
            o.created_at = o._ts
        model.objects.bulk_update(stamped, ["created_at"])
    counter.add(key or model.__name__, len(objs))
    return objs


NOW = None  # set in load(): nothing created by the seed is dated after this moment


def _past(when):
    return min(when, NOW) if NOW else when


def stamp(obj, when):
    obj._ts = _past(when)
    return obj


def set_created(model, pk, when):
    model.objects.filter(pk=pk).update(created_at=_past(when))


# --------------------------------------------------------------------------------------------- one wedding
def build_wedding(idx: int, pools: Pools, today: date, counter: Counter, now: datetime) -> bool:
    email = client_email(idx)
    # every 41st wedding is a second wedding for the previous couple (a repeat client), so it has no client of its
    # own to look for: it is recognised by the "Vow Renewal" wedding that client already has
    repeat_of = Client.objects.filter(email=client_email(idx - 1)).first() if idx % 41 == 7 and idx > 0 else None
    if repeat_of is not None:
        if Wedding.objects.filter(client=repeat_of, title__contains="Vow Renewal").exists():
            return False
    elif Client.objects.filter(email=email).exists():
        return False
    rng = random.Random(f"bulk-wedding-{idx}")
    groom, bride = GROOM_BRIDE_PAIRS[idx]
    surname = SURNAMES[idx % len(SURNAMES)]
    city = pick(rng, list(zip(CITIES, CITY_WEIGHTS, strict=True)))
    status, start, days = timeline(idx, rng, today)
    end = start + timedelta(days=days - 1)
    planner = rng.choice(pools.planners)

    guests = int(rng.triangular(80, 900, 280))
    extra_case = rng.random() < 0.28
    contracted = round_to(guests * rng.uniform(0.84, 0.95), 5) or guests if extra_case else guests
    rate = rng.randrange(1500, 4600, 100) * R
    budget = round_to(guests * rng.randint(2500, 9000) * R, 100000)
    contract_total = round_to(budget * rng.uniform(0.42, 0.66), 100000)

    if status == WeddingStatus.COMPLETED:
        booked_on = start - timedelta(days=rng.randint(150, 360))
    else:
        booked_on = min(start - timedelta(days=rng.randint(120, 330)), today - timedelta(days=rng.randint(3, 40)))
    enquiry_on = booked_on - timedelta(days=rng.randint(14, 60))

    # ---- client and the won enquiry
    repeat = repeat_of is not None
    if repeat:
        client = repeat_of
    else:
        phone = f"9{(100000000 + idx * 7919) % 1000000000:09d}"
        client = Client.objects.create(
            couple_name=f"{groom} & {bride}", client_name=f"{groom} {surname}", spouse_name=bride,
            spouse_email=f"{bride.lower()}.{surname.lower()}{idx:03d}@bulk.demo", bride_name=bride, groom_name=groom,
            phone=phone, email=email, city=city)
        set_created(Client, client.pk, at_dt(enquiry_on + timedelta(days=rng.randint(5, 20)), 11))
        counter.add("Client")
    couple = client.couple_name
    title = f"{couple} - Vow Renewal ({city})" if repeat else f"{couple} - {city}"
    # a repeat client's second wedding is smaller
    if repeat:
        guests, contracted = min(guests, 150), min(contracted, 150)

    source = pick(rng, [(Source.INSTAGRAM, 28), (Source.WHATSAPP, 22), (Source.REFERRAL, 24), (Source.CALL, 14),
                        (Source.WEBSITE, 12)])
    plan = function_plan(rng, days)
    functions_for_enquiry = [FUNCTION_KEYS[n] for n, _ in plan]
    enquiry = Enquiry.objects.create(
        couple_name=couple, client_name=client.client_name, spouse_email=client.spouse_email, phone=client.phone,
        email=client.email, source=source, status=Status.WON, wedding_date=start, guest_count=guests,
        budget_paise=budget, venue_city=city, consultation_at=at_dt(enquiry_on + timedelta(days=rng.randint(3, 12)), 15),
        notes=rng.choice(["", "", "Prefers a heritage venue.", "Wants an outdoor ceremony.", "Both families vegetarian.",
                          "Destination feel, small guest list.", "Keen on live music at the sangeet."]),
        expected_revenue_paise=contract_total, win_chance=STAGE_WIN_CHANCE[Status.WON], priority=rng.randint(0, 3),
        expected_close_date=booked_on, partner_name=bride, functions_wanted=functions_for_enquiry,
        services_needed=rng.sample(SERVICES, rng.randint(3, 7)), preferred_contact=rng.choice(["CALL", "WHATSAPP", "EMAIL"]),
        profile_complete=True, client=client, owner=planner)
    set_created(Enquiry, enquiry.pk, at_dt(enquiry_on, 10))
    counter.add("Enquiry")
    follow_ups = []
    steps = rng.randint(2, 4)
    for step in range(steps):
        kind = pick(rng, [("CALL", 40), ("MEETING", 20), ("WHATSAPP", 25), ("EMAIL", 8), ("TODO", 7)])
        due = at_dt(enquiry_on + timedelta(days=(booked_on - enquiry_on).days * (step + 1) // (steps + 1)), 11 + step)
        follow_ups.append(stamp(FollowUp(enquiry=enquiry, kind=kind, summary=rng.choice(FOLLOW_UP_SUMMARIES[kind]),
                                         due_at=due, done_at=due + timedelta(hours=rng.randint(0, 20)),
                                         created_by=planner), due - timedelta(days=3)))
    bulk(FollowUp, follow_ups, counter)

    # ---- the wedding, its functions and team
    wedding = Wedding.objects.create(
        title=title, client=client, start_date=start, end_date=end, city=city, guest_count=guests,
        contracted_guests=contracted, per_guest_rate_paise=rate, budget_paise=budget, status=status)
    set_created(Wedding, wedding.pk, at_dt(booked_on, 12))
    counter.add("Wedding")

    functions: list[WeddingFunction] = []
    venues_used: list[Venue] = []
    last_venue = None
    for name, offset in plan:
        day = start + timedelta(days=offset)
        (sh, sm), (eh, em) = FUNCTION_TIMES[name]
        starts, ends = at(day, sh, sm), at(day, eh, em)
        venue = None
        if rng.random() < 0.88:  # about one in eight functions has no venue chosen yet
            if last_venue and rng.random() < 0.5 and not WeddingFunction.objects.filter(
                    venue=last_venue, starts_at__lt=ends, ends_at__gt=starts).exists():
                venue = last_venue
            else:
                venue = pools.venue_for(rng, city, starts, ends)
        last_venue = venue or last_venue
        function = WeddingFunction.objects.create(
            wedding=wedding, name=name, starts_at=starts, ends_at=ends, venue=venue,
            guest_count=max(30, int(guests * rng.uniform(0.4, 1.0))))
        functions.append(function)
        if venue and venue not in venues_used:
            venues_used.append(venue)
    counter.add("WeddingFunction", len(functions))

    team: list[tuple[User, str]] = [(planner, "LEAD_PLANNER")]
    if rng.random() < 0.95:
        team.append((rng.choice(pools.staff), "COORDINATOR"))
    people = [u for u in pools.staff + pools.planners if u.pk not in {t[0].pk for t in team}]
    rng.shuffle(people)
    if rng.random() < 0.45 and people:
        team.append((people.pop(), "DECOR_LEAD"))
    if rng.random() < 0.45 and people:
        team.append((people.pop() if (rng.random() < 0.9 or pools.founder is None) else pools.founder, "VENDOR_LEAD"))
    bulk(TeamMember, [TeamMember(wedding=wedding, user=u, role_label=r) for u, r in team], counter)
    by_role = {role: user for user, role in team}
    members = [u for u, _ in team]

    # ---- vendors: quotation requests, quotes, the vendors chosen, their bills and instalments
    other_items = plan_other_expenses(rng, venues_used, guests, days)
    selected, vendor_cost = build_vendors(rng, pools, wedding, functions, city, status, start, booked_on, today, planner,
                                          counter, guests, members, now)
    # the contract is priced from what the vendors cost: a normal markup, and a few thin or losing weddings
    markup = rng.uniform(1.15, 1.6) if rng.random() > 0.07 else rng.uniform(0.82, 1.05)
    contract_total = max(100_000 * R, round_to((vendor_cost + sum(a for _, _, a in other_items)) * markup, 1000 * R))
    budget = round_to(contract_total * rng.uniform(1.0, 1.3), 100000)
    Wedding.objects.filter(pk=wedding.pk).update(budget_paise=budget)
    Enquiry.objects.filter(pk=enquiry.pk).update(budget_paise=budget, expected_revenue_paise=contract_total)
    wedding.budget_paise = budget

    # ---- tasks
    build_tasks(rng, wedding, functions, by_role, members, status, start, booked_on, today, counter)

    # ---- the money
    build_customer_money(rng, wedding, client, planner, status, start, end, booked_on, today, contract_total, contracted,
                         guests, rate, counter, now)
    build_other_expenses(rng, wedding, other_items, status, start, today, planner, counter, now)

    # ---- the day itself
    arrivals = build_checkins(rng, wedding, functions, selected, status, today, counter, now)
    build_schedule(rng, wedding, functions, selected, members, status, start, today, counter)
    if status == WeddingStatus.COMPLETED:
        build_ratings(rng, wedding, selected, arrivals, counter)
    build_incidents(rng, wedding, functions, selected, members, planner, status, today, counter, now)

    add_new_structure(wedding, pools, today, now, counter)  # agreement, customer login, email history
    return True


def build_vendors(rng, pools, wedding, functions, city, status, start, booked_on, today, planner, counter, guests,
                  members, now):
    """Quotation requests for 4-8 categories. Returns [(vendor, category, WeddingVendor)] for the chosen vendors."""
    must = [c for c, p in [("Caterer", 0.97), ("Decorator", 0.88), ("Photographer", 0.82), ("DJ & Sound", 0.7)]
            if rng.random() < p]
    others = [c for c in VENDOR_NAMES if c not in must]
    rng.shuffle(others)
    categories = must + others[: max(0, rng.randint(4, 8) - len(must))]
    function_names = [f.name for f in functions]
    selected = []
    ai_jobs = []
    quoted = {}  # category -> the middle quote, to price the contract
    for category in categories:
        vendors = pools.vendors_for(rng, category, city, rng.randint(2, 4))
        if len(vendors) < 2:
            continue
        # what is the state of this request?
        if status in (WeddingStatus.COMPLETED,):
            outcome = "selected"
        elif status == WeddingStatus.CONFIRMED:
            outcome = pick(rng, [("selected", 92), ("open_quotes", 8)])
        elif status == WeddingStatus.PLANNING:
            outcome = pick(rng, [("selected", 35), ("open_quotes", 35), ("open_waiting", 20), ("draft", 10)])
        else:
            outcome = pick(rng, [("selected", 30), ("closed_none", 20), ("open_quotes", 30), ("open_waiting", 20)])
        requested_on = min(booked_on + timedelta(days=rng.randint(1, 20)), today - timedelta(days=1))
        sent_at = None if outcome == "draft" else at_dt(requested_on + timedelta(days=rng.randint(0, 3)), 10)
        reply_by = requested_on + timedelta(days=rng.randint(8, 25))
        request = QuotationRequest.objects.create(
            wedding=wedding, category=pools.categories[category], requirements=requirement_text(category, function_names),
            guest_count=guests, reply_by=reply_by, status=RequestStatus.OPEN, sent_at=sent_at)
        request.invited_vendors.set(vendors)
        set_created(QuotationRequest, request.pk, at_dt(requested_on, 9))
        counter.add("QuotationRequest")
        if outcome == "draft":
            continue

        repliers = vendors if outcome != "open_waiting" else vendors[: max(1, len(vendors) - rng.randint(1, 2))]
        if outcome == "open_waiting" and rng.random() < 0.3:
            repliers = []  # nobody has answered yet
        quotes = []
        per_plate_base = rng.randint(700, 2200) * R
        for vendor in repliers:
            profile = vendor_profile(vendor.name)
            plate = int(per_plate_base * profile["price"]) if category == "Caterer" else None
            items = quote_items(rng, category, guests, profile["price"], plate)
            use_items = category != "Caterer" or rng.random() < 0.6
            if use_items:
                total = sum(q * u for _, q, u in items)
            else:
                total = plate * guests
            valid_till = reply_by + timedelta(days=rng.randint(10, 40))
            if outcome in ("open_quotes", "open_waiting") and rng.random() < 0.25:
                valid_till = today - timedelta(days=rng.randint(1, 30))  # an expired quote
            by_hand = rng.random() < 0.85
            quote = Quotation(request=request, vendor=vendor, total_paise=total, price_per_plate_paise=plate,
                              menu_notes=rng.choice(["", "North Indian veg buffet, 4 starters.", "Veg and non-veg buffet.",
                                                     "Counters and drinks extra.", "Includes set-up and take-down."])
                              if category == "Caterer" else rng.choice(["", "Set-up and take-down included.", "Travel extra."]),
                              valid_till=valid_till, typed_by_hand=by_hand, status=QuotationStatus.RECEIVED)
            quotes.append((quote, items if use_items else [], by_hand))
            stamp(quote, at_dt(requested_on + timedelta(days=rng.randint(2, 12)), 14))
        if quotes:
            totals = sorted(q.total_paise for q, _, _ in quotes)
            quoted[category] = totals[len(totals) // 2]
        bulk(Quotation, [q for q, _, _ in quotes], counter)
        line_items = []
        for quote, items, by_hand in quotes:
            for description, qty, unit in items:
                line_items.append(QuotationItem(quotation=quote, description=description, quantity=qty,
                                                unit_price_paise=unit, total_paise=qty * unit))
            if not by_hand:
                ai_jobs.append(AIJob(kind="extract_quotation", status="DONE",
                                     input={"filename": f"{quote.vendor.name.replace(' ', '_')}_quote.pdf"},
                                     output={"vendor": quote.vendor.name, "total_paise": quote.total_paise,
                                             "items": len(items)}))
        bulk(QuotationItem, line_items, counter)

        if outcome in ("selected", "closed_none") and quotes:
            request.status = RequestStatus.CLOSED
            request.save(update_fields=["status"])
        if outcome != "selected" or not quotes:
            continue
        # the winner: the cheapest half of the time, otherwise the best rated
        by_price = min(quotes, key=lambda q: q[0].total_paise)[0]
        by_rating = max(quotes, key=lambda q: vendor_profile(q[0].vendor.name)["quality"])[0]
        winner = by_price if rng.random() < 0.5 else by_rating
        for quote, _, _ in quotes:
            quote.status = QuotationStatus.SELECTED if quote is winner else QuotationStatus.REJECTED
        Quotation.objects.bulk_update([q for q, _, _ in quotes], ["status"])
        booking = WeddingVendor.objects.create(
            wedding=wedding, vendor=winner.vendor, quotation=winner, agreed_amount_paise=winner.total_paise,
            status={"COMPLETED": "COMPLETED", "CANCELLED": "CANCELLED"}.get(status, "SELECTED"))
        counter.add("WeddingVendor")
        selected.append((winner.vendor, category, booking))
        book_vendor_bill(rng, wedding, winner.vendor, category, winner.total_paise, status, start, booked_on, today,
                         planner, requested_on, counter, now)
    bulk(AIJob, ai_jobs, counter)
    estimated_cost = sum(quoted.get(c) or typical_cost(c, guests) for c in categories)
    return selected, estimated_cost


def book_vendor_bill(rng, wedding, vendor, category, total, status, start, booked_on, today, planner, requested_on,
                     counter, now):
    """The bill for a chosen vendor: advance and final instalments, and what has been paid so far."""
    decided_on = min(requested_on + timedelta(days=rng.randint(10, 35)), today)
    advance_pct = rng.choice([20, 25, 30, 30, 40, 50])
    advance = total * advance_pct // 100
    advance_due = min(decided_on + timedelta(days=7), start - timedelta(days=5))
    final_due = start - timedelta(days=3)
    bill_number = f"{''.join(w[0] for w in vendor.name.split()[:3]).upper()}-{rng.randint(100, 9999)}" if rng.random() < 0.65 else ""
    if bill_number and Expense.objects.filter(vendor=vendor, bill_number=bill_number).exists():
        bill_number = ""
    expense = Expense.objects.create(
        wedding=wedding, vendor=vendor, category=category, description=f"{vendor.name} ({category})",
        amount_paise=total, bill_number=bill_number, due_date=final_due, status=PayStatus.UNPAID)
    set_created(Expense, expense.pk, at_dt(decided_on, 12))
    counter.add("Expense")

    # how much of each instalment has been paid
    def paid_for(amount, due):
        if status == WeddingStatus.CANCELLED:
            return amount if (due < today and rng.random() < 0.85) else 0
        if due < today - timedelta(days=2):
            return pick(rng, [(amount, 90), (amount // 2 // R * R, 5), (0, 5)])  # a few part paid or overdue
        if due < today + timedelta(days=14):
            return pick(rng, [(0, 70), (amount // 2 // R * R, 10), (amount, 20)])
        return 0
    paid_advance = paid_for(advance, advance_due)
    paid_final = paid_for(total - advance, final_due) if paid_advance == advance else 0
    plans = [VendorPaymentPlan(wedding=wedding, vendor=vendor, part="ADVANCE", amount_paise=advance, due_date=advance_due,
                               expense=expense, status=derive_status(paid_advance, advance)),
             VendorPaymentPlan(wedding=wedding, vendor=vendor, part="FINAL", amount_paise=total - advance,
                               due_date=final_due, expense=expense, status=derive_status(paid_final, total - advance))]
    bulk(VendorPaymentPlan, plans, counter)
    payments = []
    for plan, paid, due in ((plans[0], paid_advance, advance_due), (plans[1], paid_final, final_due)):
        if paid <= 0:
            continue
        parts = [paid] if paid < 2 * R * 1000 or rng.random() < 0.8 else [paid // 2 // R * R, paid - paid // 2 // R * R]
        for part in parts:
            when = min(at_dt(due - timedelta(days=rng.randint(-6, 6)), rng.randint(10, 18)), now - timedelta(hours=rng.randint(1, 48)))
            payments.append(Payment(wedding=wedding, expense=expense, direction=Payment.Direction.OUT, amount_paise=part,
                                    method=rng.choice(OFFLINE_METHODS), recorded_by=planner,
                                    reference=f"milestone:{plan.pk}", paid_at=when))
    bulk(Payment, payments, counter)
    expense.status = derive_status(paid_advance + paid_final, total)
    expense.save(update_fields=["status"])


def plan_other_expenses(rng, venues_used, guests, days):
    """The bills with no instalments: the venue(s), local logistics, team travel. [(description, category, paise)]"""
    items = [(f"{v.name} booking", "Venue", guests * rng.randint(250, 700) * R * max(1, days // 2)) for v in venues_used[:2]]
    if rng.random() < 0.5:
        items.append(("Local logistics and permits", "Logistics", rng.randint(20, 90) * 1000 * R))
    if rng.random() < 0.35:
        items.append(("Team travel and stay", "Team", rng.randint(15, 60) * 1000 * R))
    return items


def build_other_expenses(rng, wedding, items, status, start, today, planner, counter, now):
    """Creates those bills, paid in part or in full by their dates."""
    expenses = []
    for description, category, amount in items:
        due = start - timedelta(days=rng.randint(5, 25))
        if status == WeddingStatus.CANCELLED:
            paid = amount // 2 // R * R if due < today else 0
        elif due < today - timedelta(days=2):
            paid = pick(rng, [(amount, 85), (amount // 2 // R * R, 10), (0, 5)])
        else:
            paid = pick(rng, [(0, 75), (amount // 2 // R * R, 20), (amount, 5)])
        expense = Expense(wedding=wedding, vendor=None, category=category, description=description, amount_paise=amount,
                          due_date=due, status=derive_status(paid, amount))
        stamp(expense, at_dt(due - timedelta(days=rng.randint(10, 40)), 12))
        expenses.append((expense, paid))
    bulk(Expense, [e for e, _ in expenses], counter)
    payments = []
    for expense, paid in expenses:
        if paid > 0:
            payments.append(Payment(
                wedding=wedding, expense=expense, direction=Payment.Direction.OUT, amount_paise=paid,
                method=rng.choice(OFFLINE_METHODS), recorded_by=planner, reference=f"CHQ-{rng.randint(100000, 999999)}",
                paid_at=min(at_dt(expense.due_date - timedelta(days=rng.randint(0, 5)), 15), now - timedelta(hours=3))))
    bulk(Payment, payments, counter)


def build_customer_money(rng, wedding, client, planner, status, start, end, booked_on, today, contract_total, contracted,
                         guests, rate, counter, now):
    """Deposit, instalment, final and (sometimes) extra-guest invoices, with payments and payment links."""
    deposit = round_to(contract_total * 0.2, 1000 * R)
    milestone = round_to(contract_total * 0.45, 1000 * R)
    plan = [("DEPOSIT", deposit, booked_on, "Booking deposit"),
            ("MILESTONE", milestone, start - timedelta(days=45), "Second instalment"),
            ("FINAL", contract_total - deposit - milestone, end + timedelta(days=7), "Balance after the wedding")]
    if status == WeddingStatus.CANCELLED:
        plan = plan[:2] if rng.random() < 0.4 else plan[:1]
        plan[-1] = (plan[-1][0], plan[-1][1], plan[-1][2], plan[-1][3] + " (wedding later cancelled)")
    extra = guests - contracted
    if extra > 0 and (status == WeddingStatus.COMPLETED or start <= today + timedelta(days=14)) \
            and status != WeddingStatus.CANCELLED:
        plan.append(("EXTRA_GUESTS", extra * rate, end + timedelta(days=3),
                     f"{extra} extra guests ({guests} actual vs {contracted} contracted) x Rs {rate // R:,} per guest"))
    invoices = []
    for kind, amount, due, note in plan:
        if amount <= 0:
            continue
        if status == WeddingStatus.CANCELLED:
            paid = amount if kind == "DEPOSIT" and rng.random() < 0.8 else (amount // 2 // R * R if kind == "MILESTONE" and due < today and rng.random() < 0.4 else 0)
        elif status == WeddingStatus.PLANNING and kind == "DEPOSIT":
            paid = pick(rng, [(amount, 65), (amount // 2 // R * R, 10), (0, 25)])  # not confirmed until the deposit lands
        elif kind == "DEPOSIT":
            paid = amount
        elif due < today - timedelta(days=2):
            paid = pick(rng, [(amount, 88), (amount // 2 // R * R, 7), (0, 5)])
        elif due < today + timedelta(days=30):
            paid = pick(rng, [(0, 60), (amount * 4 // 10 // R * R, 25), (amount, 15)])
        else:
            paid = 0
        invoice = Invoice(wedding=wedding, client=client, kind=kind, amount_paise=amount, due_date=due,
                          status=derive_status(paid, amount), note=note)
        stamp(invoice, at_dt(min(booked_on if kind == "DEPOSIT" else due - timedelta(days=rng.randint(10, 30)), today), 11))
        invoices.append((invoice, paid))
    bulk(Invoice, [i for i, _ in invoices], counter)

    payments, links = [], []
    for invoice, paid in invoices:
        remaining = invoice.amount_paise - paid
        if paid > 0:
            pieces = 1 if paid < 50000 * R or rng.random() < 0.55 else rng.randint(2, 3)
            amounts = [paid // pieces // R * R] * pieces
            amounts[-1] = paid - sum(amounts[:-1])
            for n, part in enumerate(amounts):
                when = min(at_dt(invoice.due_date + timedelta(days=rng.randint(-10, 8) + n * 6), rng.randint(10, 19)),
                           now - timedelta(hours=rng.randint(2, 60)))
                method = rng.choice(OFFLINE_METHODS + ["RAZORPAY", "RAZORPAY"])
                payment = Payment(wedding=wedding, invoice=invoice, direction=Payment.Direction.IN, amount_paise=part,
                                  method=method, recorded_by=None if method == "RAZORPAY" else planner,
                                  reference=f"pay_{rng.randint(10**9, 10**10 - 1)}" if method == "RAZORPAY"
                                  else f"{method[:3]}-{rng.randint(100000, 999999)}", paid_at=when)
                payments.append(payment)
                if method == "RAZORPAY":
                    links.append((payment, invoice, part))
        if remaining > 0 and rng.random() < 0.4 and status != WeddingStatus.CANCELLED:
            state = pick(rng, [("ACTIVE", 55), ("EXPIRED", 20), ("CANCELLED", 25)])
            link = PaymentLink(
                invoice=invoice, amount_paise=remaining,
                status=PaymentLink.Status.CANCELLED if state == "CANCELLED" else PaymentLink.Status.ACTIVE,
                expires_at=now - timedelta(days=rng.randint(1, 20)) if state == "EXPIRED" else now + timedelta(days=rng.randint(1, 7)),
                created_by=planner, razorpay_order_id=f"order_{rng.randint(10**13, 10**14 - 1)}" if rng.random() < 0.5 else "")
            stamp(link, now - timedelta(days=rng.randint(1, 25)))
            links.append((None, invoice, link))
    bulk(Payment, payments, counter)
    paid_links = []
    open_links = []
    for payment, invoice, extra_item in links:
        if payment is not None:
            link = PaymentLink(invoice=invoice, amount_paise=extra_item, status=PaymentLink.Status.PAID,
                               expires_at=payment.paid_at + timedelta(days=7), created_by=planner, paid_at=payment.paid_at,
                               payment=payment, razorpay_order_id=f"order_{rng.randint(10**13, 10**14 - 1)}")
            stamp(link, payment.paid_at - timedelta(hours=rng.randint(1, 30)))
            paid_links.append(link)
        else:
            open_links.append(extra_item)
    bulk(PaymentLink, paid_links + open_links, counter)


def build_tasks(rng, wedding, functions, by_role, members, status, start, booked_on, today, counter):
    drafts = list(TEMPLATE) if rng.random() < 0.85 else rng.sample(list(TEMPLATE), rng.randint(14, len(TEMPLATE) - 1))
    rows = []
    for draft in drafts:
        due = start + timedelta(days=draft.due_offset_days)
        assignee = by_role.get(draft.default_role)
        rows.append((draft.title, draft.description, draft.category, due, draft.priority, assignee, None))
    for title, category, offset, priority in rng.sample(CUSTOM_TASKS, rng.randint(0, 4)):
        function = rng.choice(functions) if rng.random() < 0.6 else None
        rows.append((title, "", category, start + timedelta(days=offset), priority, rng.choice(members) if rng.random() < 0.8 else None, function))
    tasks = []
    for title, description, category, due, priority, assignee, function in rows:
        stage = task_stage(rng, due, today, status)
        task = Task(wedding=wedding, function=function, title=title, description=description, assigned_to=assignee,
                    due_date=due, stage=stage, priority=priority, category=category)
        stamp(task, at_dt(min(max(booked_on, due - timedelta(days=rng.randint(60, 200))), today), 10))
        tasks.append(task)
    positions: dict[str, int] = {}
    for task in sorted(tasks, key=lambda t: (t.due_date, t.title)):
        task.position = positions.get(task.stage, 0)
        positions[task.stage] = task.position + 1
    bulk(Task, tasks, counter)


def build_checkins(rng, wedding, functions, selected, status, today, counter, now):
    """Vendor arrivals. Past functions have the full range of outcomes; the nearest ones have live, pending ones."""
    arrivals = []
    if status == WeddingStatus.CANCELLED:
        return arrivals
    for function in functions:
        day = timezone.localtime(function.starts_at, IST).date()
        days_away = (day - today).days
        if days_away > 14:
            continue
        chosen = [s for s in selected if s[1] in CHECKIN_CATEGORIES]
        rng.shuffle(chosen)
        for vendor, category, _ in chosen[: rng.randint(2, 5)]:
            lead = ARRIVAL_LEAD_MINUTES[category] + rng.choice([0, 0, 15, 30])
            expected = function.starts_at - timedelta(minutes=lead)
            grace = rng.choice([10, 15, 15, 20, 30])
            profile = vendor_profile(vendor.name)
            arrival = VendorArrival(wedding=wedding, vendor=vendor, function=function, expected_at=expected,
                                    grace_minutes=grace, status=VendorArrival.Status.PENDING)
            if expected > now:  # still to come
                pass
            elif rng.random() < 0.02 or (days_away == 0 and rng.random() < 0.12):
                arrival.status = VendorArrival.Status.LATE  # never turned up: the timer flagged them
                arrival.late_alert_sent_at = expected + timedelta(minutes=grace + 1)
            elif rng.random() < profile["punctual"]:
                arrival.arrived_at = expected + timedelta(minutes=rng.randint(-25, grace))
                arrival.status = VendorArrival.Status.ON_TIME
            else:
                arrival.arrived_at = expected + timedelta(minutes=grace + rng.randint(3, 75))
                arrival.status = VendorArrival.Status.LATE
                arrival.late_alert_sent_at = expected + timedelta(minutes=grace + 1)
            if arrival.arrived_at and arrival.arrived_at > now:  # cannot arrive in the future
                arrival.arrived_at = None
                arrival.status = VendorArrival.Status.PENDING
            arrivals.append(arrival)
    bulk(VendorArrival, arrivals, counter)
    recent_late = [a for a in arrivals if a.status == VendorArrival.Status.LATE and a.late_alert_sent_at
                   and a.late_alert_sent_at > now - timedelta(days=21)]
    alerts = []
    for a in recent_late:  # the bell keeps a message for each recent late vendor, like the live timer does
        alert = Notification(message=f"{a.vendor.name} is late for {a.function.name} (due {a.expected_at:%H:%M})",
                             channel="both", severity="warning", dedupe_key=f"seed-late:{a.pk}",
                             read_at=None if a.late_alert_sent_at > now - timedelta(days=3) else a.late_alert_sent_at + timedelta(hours=5))
        stamp(alert, a.late_alert_sent_at)
        alerts.append(alert)
    bulk(Notification, alerts, counter)
    return arrivals


def build_schedule(rng, wedding, functions, selected, members, status, start, today, counter):
    if status == WeddingStatus.CANCELLED and rng.random() < 0.8:
        return
    if status == WeddingStatus.PLANNING and (start - today).days > 90 and rng.random() < 0.6:
        return
    items = []
    for function in functions:
        template = SCHEDULE_TEMPLATES.get(function.name)
        if not template:
            continue
        duration = int((function.ends_at - function.starts_at).total_seconds() // 60)
        for title, offset, length in template[: rng.randint(4, len(template))]:
            if offset + 15 > duration:
                break
            starts = function.starts_at + timedelta(minutes=offset)
            ends = min(starts + timedelta(minutes=length), function.ends_at)
            if ends <= starts:
                continue
            responsible = rng.choice(members) if rng.random() < 0.82 else None
            vendor = rng.choice(selected)[0] if selected and rng.random() < 0.3 else None
            items.append(ScheduleItem(function=function, starts_at=starts, ends_at=ends, title=title,
                                      responsible=responsible, vendor=vendor,
                                      notes=rng.choice(["", "", "", "Confirm with the venue manager.", "Vendor to arrive early."])))
        if items and rng.random() < 0.12:  # the same person double-booked: the app warns about these
            last = items[-1]
            if last.responsible:
                items.append(ScheduleItem(function=function, starts_at=last.starts_at + timedelta(minutes=10),
                                          ends_at=min(last.starts_at + timedelta(minutes=40), function.ends_at),
                                          title="Quick family photo", responsible=last.responsible, notes="Overlaps the item above"))
    bulk(ScheduleItem, [i for i in items if i.ends_at > i.starts_at], counter)


def build_ratings(rng, wedding, selected, arrivals, counter):
    by_vendor = {}
    for a in arrivals:
        by_vendor.setdefault(a.vendor_id, []).append(a)
    ratings = []
    for vendor, _category, _ in selected:
        if rng.random() < 0.15:
            continue  # not every vendor gets rated
        profile = vendor_profile(vendor.name)
        seen = by_vendor.get(vendor.pk, [])
        late = sum(1 for a in seen if a.status == VendorArrival.Status.LATE)
        punctuality = 5 if seen and not late else (2 if seen and late == len(seen) else (3 if seen else rng.randint(3, 5)))
        clamp = lambda x: max(1, min(5, int(round(x))))  # noqa: E731
        ratings.append(VendorRating(
            vendor=vendor, wedding=wedding, punctuality=punctuality,
            quality=clamp(profile["quality"] + rng.uniform(-0.8, 0.8)), pricing=clamp(6 - profile["price"] * 3 + rng.uniform(-0.8, 0.8)),
            comment=rng.choice(["", "", "Great work, would book again.", "Food was the talk of the wedding.",
                                "Good, but arrived later than agreed.", "Stunning set-up.", "Needed a lot of follow-up.",
                                "Smooth and professional."])))
    bulk(VendorRating, ratings, counter)


def build_incidents(rng, wedding, functions, selected, members, planner, status, today, counter, now):
    if status in (WeddingStatus.PLANNING, WeddingStatus.CANCELLED) or rng.random() > 0.14:
        return
    for title, description, severity in rng.sample(INCIDENTS, rng.randint(1, 3)):
        function = rng.choice(functions)
        happened = function.starts_at + timedelta(minutes=rng.randint(30, 200))
        if happened > now:
            continue
        reporter = rng.choice(members)
        assignee = rng.choice(members) if rng.random() < 0.9 else None
        # cycle through the statuses so every one is always present, however few incidents are loaded
        number = counter.get("Incident", 0)
        cycle = INCIDENT_CYCLE_DONE if status == WeddingStatus.COMPLETED else INCIDENT_CYCLE_LIVE
        final = cycle[number % len(cycle)]
        if not assignee and final != IncidentStatus.OPEN:
            assignee = planner
        if final == IncidentStatus.OPEN:
            assignee = None
        resolved_at = happened + timedelta(minutes=rng.randint(20, 240)) if final == IncidentStatus.RESOLVED else None
        incident = Incident.objects.create(
            wedding=wedding, function=function, vendor=rng.choice(selected)[0] if selected and rng.random() < 0.5 else None,
            title=title, description=description, severity=severity, status=final, reported_by=reporter,
            assigned_to=assignee, resolved_at=resolved_at)
        set_created(Incident, incident.pk, happened)
        Incident.objects.filter(pk=incident.pk).update(updated_at=resolved_at or happened + timedelta(minutes=15))
        updates = [(reporter, f"Reported ({severity.lower()}): {description}", happened)]
        if assignee:
            updates.append((planner, f"Assigned to {assignee.name}", happened + timedelta(minutes=8)))
        if final in (IncidentStatus.IN_PROGRESS, IncidentStatus.RESOLVED) and assignee:
            updates.append((assignee, "Status changed to In progress: on it", happened + timedelta(minutes=20)))
        if final == IncidentStatus.RESOLVED and assignee:
            updates.append((assignee, "Resolved: " + rng.choice(["fixed on site", "vendor replaced the item",
                                                                  "backup plan worked", "family informed and happy"]), resolved_at))
        objs = [stamp(IncidentUpdate(incident=incident, author=author, message=message), when) for author, message, when in updates]
        bulk(IncidentUpdate, objs, counter)
        counter.add("Incident")


# --------------------------------------------------------------------------------------------- agreements, logins, emails
# The parts of a wedding that the app added later: the signed service agreement, the client's login on the customer
# website, the vendors' logins, and the log of every email sent. They are built from the app's own helpers
# (default_body, fingerprint, the email renderer), so they always match what the real screens would produce.
# `add_new_structure` runs for every new wedding AND for weddings loaded before these existed, which is how
# running `load_demo_data --bulk` again brings older data up to date.
BROWSERS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) Safari/605.1.15 Mobile",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) Chrome/126.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edg/126.0 Chrome/126.0 Safari/537.36"]


def signature_png(seed: str) -> str:
    """A hand-drawn-looking signature as a PNG data URL (the form the customer site sends), different per person."""
    rng = random.Random("signature-" + seed)
    width, height = 300, 100
    ink = (22, 32, 112)
    alpha = [[0.0] * width for _ in range(height)]

    def dot(cx, cy, radius):
        for y in range(max(0, int(cy - radius - 1)), min(height, int(cy + radius + 2))):
            for x in range(max(0, int(cx - radius - 1)), min(width, int(cx + radius + 2))):
                coverage = max(0.0, min(1.0, radius + 0.5 - math.hypot(x - cx, y - cy)))
                if coverage > alpha[y][x]:
                    alpha[y][x] = coverage

    humps = rng.randint(3, 5)
    amplitude, slant, loop = rng.uniform(16, 30), rng.uniform(-0.22, 0.22), rng.uniform(0.0, 5.0)
    for i in range(1200):
        t = i / 1200
        x = 16 + 268 * t
        envelope = 0.35 + 0.65 * math.sin(math.pi * t)
        y = 52 + amplitude * envelope * math.sin(2 * math.pi * humps * t) + 3.5 * math.sin(2 * math.pi * humps * 2.4 * t + loop)
        dot(x, y + slant * (x - 150), 1.7 + 0.5 * math.sin(2 * math.pi * humps * t) ** 2)
    for i in range(240):  # the underline flourish
        t = i / 240
        dot(34 + 232 * t, 88 - 7 * math.sin(math.pi * t) + 2 * (1 - t), 1.4)
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows += bytes((*ink, int(255 * alpha[y][x])))

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = (bytes([137, 80, 78, 71, 13, 10, 26, 10]) + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(png).decode()


def rupee_text(paise: int) -> str:
    return f"{paise / 100:,.0f}"


def day_text(day) -> str:
    return f"{day:%d %b %Y}"


def make_email(rng, template: str, to: str, when: datetime, **context):
    """One EmailLog row, rendered by the app's own template so subject and body are exactly what would be sent."""
    if not to:
        return None
    subject, html, text = mail_render(template, context)
    chance = rng.random()
    status, error, sent_at = EmailLog.Status.SENT, "", when + timedelta(seconds=rng.randint(1, 6))
    if chance < 0.015:
        status, error, sent_at = EmailLog.Status.FAILED, rng.choice(
            ["SMTPAuthenticationError: username or password not accepted",
             "Connection timed out while contacting the mail server"]), None
    elif chance < 0.019 and when > NOW - timedelta(days=3):
        status, sent_at = EmailLog.Status.QUEUED, None
    row = EmailLog(template=template, to=to, subject=subject, html=html, text=text, status=status, error=error,
                   sent_at=sent_at and _past(sent_at))
    return stamp(row, when)


def ensure_customer(rng, client, enquiry, booked_on, pools, now):
    """The client's login on the customer website. Every converted client has one: active, or invited but not set up."""
    customer = Customer.objects.filter(client=client).first() or Customer.objects.filter(email=client.email).first()
    invited_on = at_dt(booked_on + timedelta(days=1), 11)
    if customer is None:
        free = enquiry is not None and not Customer.objects.filter(enquiry=enquiry).exists()
        customer = Customer(name=client.client_name or client.couple_name, email=client.email, phone=client.phone,
                            enquiry=enquiry if free else None, client=client, invited_at=_past(invited_on))
        if rng.random() < 0.7:  # chose a password
            customer.password_hash = pools.password_hash
            if rng.random() < 0.85:
                customer.last_login_at = now - timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 20))
        customer.save()
        set_created(Customer, customer.pk, invited_on)
        return customer, True
    changed = False
    if customer.client_id is None:
        customer.client, changed = client, True
    if customer.invited_at is None:
        customer.invited_at, changed = _past(invited_on), True
    if changed:
        customer.save()
    return customer, False


def add_new_structure(wedding, pools, today, now, counter) -> bool:
    """Agreement + customer login + email history for one wedding. Skipped when the wedding already has an agreement."""
    if wedding.agreements.exists():
        return False
    wedding.refresh_from_db()
    rng = random.Random(f"structure-{wedding.client.email}-{wedding.title}")
    client = wedding.client
    booked_on = timezone.localtime(wedding.created_at, UTC).date()
    lead = TeamMember.objects.filter(wedding=wedding, role_label="LEAD_PLANNER").select_related("user").first()
    planner = lead.user if lead else pools.planners[0]
    enquiry = Enquiry.objects.filter(client=client, status=Status.WON).order_by("-id").first()
    customer, new_account = ensure_customer(rng, client, enquiry, booked_on, pools, now)
    if new_account:
        counter.add("Customer")
    couple, planner_name = client.couple_name, planner.name
    site = settings.CUSTOMER_SITE_URL
    emails = []

    def mail_to_client(template, when, **context):
        emails.append(make_email(rng, template, customer.email, when, **context))

    # ---- how the couple reached us, and the welcome email that gave them a login
    welcome_at = at_dt(booked_on + timedelta(days=1), 11)
    if enquiry is not None and enquiry.source == Source.WEBSITE and new_account:
        mail_to_client("enquiry_received", at_dt(booked_on - timedelta(days=rng.randint(14, 40)), 10),
                       name=client.groom_name or couple, link=f"{site}/home")
    if new_account:
        mail_to_client("client_welcome", welcome_at, name=client.client_name or couple, email=customer.email,
                       planner=planner_name, wedding=wedding.title, link=link_for("customer", customer))

    # ---- the agreement: signed, waiting, still a draft, or cancelled, depending on where the wedding is
    status = wedding.status
    if status in (WeddingStatus.COMPLETED, WeddingStatus.CONFIRMED):
        state = pick(rng, [("SIGNED", 92), ("SENT", 8)])
    elif status == WeddingStatus.PLANNING:
        state = pick(rng, [("SENT", 55), ("DRAFT", 22), ("SIGNED", 23)])
    else:
        state = pick(rng, [("VOID", 55), ("SIGNED", 45)])
    drafted = at_dt(booked_on + timedelta(days=rng.randint(0, 2)), 12)
    sent = drafted + timedelta(days=rng.randint(1, 3), hours=rng.randint(0, 6))
    signed = sent + timedelta(days=rng.randint(0, 6), hours=rng.randint(1, 20))
    if state in ("SIGNED", "SENT", "VOID") and (sent > now or (state == "SIGNED" and signed > now)):
        state = "SENT" if sent <= now else "DRAFT"  # nothing is dated in the future
    agreement = Agreement(wedding=wedding, title=f"Service agreement: {wedding.title}", body=default_body(wedding),
                          created_by=planner, status=Agreement.Status.DRAFT)
    if state != "DRAFT":
        agreement.status = Agreement.Status.SENT if state != "VOID" else Agreement.Status.VOID
        agreement.sent_at, agreement.company_signer = _past(sent), planner_name
    if state == "SENT" and rng.random() < 0.25:  # a signing code was asked for but not used
        agreement.otp_hash, agreement.otp_expires_at, agreement.otp_tries = (
            pools.password_hash, _past(sent + timedelta(minutes=10)), rng.randint(0, 2))
    if state == "SIGNED":
        agreement.status = Agreement.Status.SIGNED
        agreement.signed_at, agreement.signer_name, agreement.signer_email = _past(signed), client.client_name, customer.email
        agreement.signature, agreement.signer_agent = signature_png(client.client_name), rng.choice(BROWSERS)
        agreement.signer_ip = f"{rng.choice([49, 103, 106, 117, 152])}.{rng.randint(1, 254)}.{rng.randint(1, 254)}.{rng.randint(1, 254)}"
    agreement.save()
    if state == "SIGNED":
        Agreement.objects.filter(pk=agreement.pk).update(body_hash=fingerprint(agreement))
    set_created(Agreement, agreement.pk, drafted)
    counter.add("Agreement")
    link = f"{site}/agreement/{agreement.pk}"
    if state in ("SENT", "SIGNED", "VOID"):
        mail_to_client("agreement_ready", sent, name=couple, wedding=wedding.title, link=link)
    if state == "SIGNED":
        mail_to_client("agreement_otp", signed - timedelta(minutes=rng.randint(2, 9)), name=couple,
                       otp=f"{rng.randint(100000, 999999)}", wedding=wedding.title)
        mail_to_client("agreement_signed", signed, name=client.client_name, wedding=wedding.title,
                       date=day_text(signed), link=link)

    # ---- the money emails: invoices, receipts, reminders, vendor bookings and payments
    for invoice in Invoice.objects.filter(wedding=wedding).order_by("id"):
        mail_to_client("invoice_issued", invoice.created_at, name=couple, title=invoice.get_kind_display(),
                       amount=rupee_text(invoice.amount_paise), due_date=day_text(invoice.due_date) if invoice.due_date else "",
                       wedding=wedding.title, link=f"{site}/home")
        if invoice.status != PayStatus.PAID and invoice.due_date and invoice.due_date < today \
                and status != WeddingStatus.CANCELLED:
            mail_to_client("payment_reminder", at_dt(invoice.due_date + timedelta(days=1), 9), name=couple,
                           title=invoice.get_kind_display(), amount=rupee_text(invoice.amount_paise),
                           due_date=day_text(invoice.due_date), wedding=wedding.title, link=f"{site}/home")
    for payment in Payment.objects.filter(wedding=wedding, direction=Payment.Direction.IN).select_related("invoice").order_by("id"):
        mail_to_client("payment_receipt", payment.paid_at, name=couple, title=payment.invoice.get_kind_display(),
                       amount=rupee_text(payment.amount_paise), receipt=f"RCPT-{payment.pk:05d}", wedding=wedding.title)
    for booking in WeddingVendor.objects.filter(wedding=wedding).select_related("vendor"):
        bill = Expense.objects.filter(wedding=wedding, vendor=booking.vendor).first()
        when = bill.created_at if bill else booked_on
        emails.append(make_email(rng, "vendor_booked", booking.vendor.email, when, vendor=booking.vendor.name,
                                 wedding=wedding.title, date=day_text(wedding.start_date),
                                 link=f"{settings.FRONTEND_URL}/vendor/requests"))
    for payment in Payment.objects.filter(wedding=wedding, direction=Payment.Direction.OUT,
                                          expense__vendor__isnull=False).select_related("expense__vendor").order_by("id"):
        emails.append(make_email(rng, "vendor_payment_sent", payment.expense.vendor.email, payment.paid_at,
                                 vendor=payment.expense.vendor.name, amount=rupee_text(payment.amount_paise),
                                 wedding=wedding.title))
    bulk(EmailLog, [e for e in emails if e], counter)
    return True


def ensure_vendor_accounts(pools, now, counter):
    """Logins for about three in four vendors: some active, some invited but not set up, the rest with none."""
    made = 0
    emails = []
    for vendor in Vendor.objects.filter(portal_account__isnull=True).exclude(email="").order_by("id"):
        rng = random.Random("vendor-account-" + vendor.name)
        if rng.random() < 0.25 or VendorAccount.objects.filter(email=vendor.email.lower()).exists():
            continue
        invited = now - timedelta(days=rng.randint(10, 300), hours=rng.randint(0, 20))
        account = VendorAccount(vendor=vendor, email=vendor.email.lower(), invited_at=invited)
        if rng.random() < 0.65:  # chose a password
            account.password_hash = pools.password_hash
            if rng.random() < 0.8:
                account.last_login_at = now - timedelta(days=rng.randint(0, 90), hours=rng.randint(0, 20))
        account.save()
        set_created(VendorAccount, account.pk, invited)
        emails.append(make_email(rng, "vendor_invite", account.email, invited, vendor=vendor.name, email=account.email,
                                 password="(sent once, in the email)", link=f"{settings.FRONTEND_URL}/login"))
        made += 1
    bulk(EmailLog, [e for e in emails if e], counter)
    counter.add("VendorAccount", made)
    return made


def upgrade_existing(pools, today, now, counter):
    """Brings weddings loaded earlier up to the current structure (idempotent): agreement, login, email history."""
    upgraded = 0
    for wedding in Wedding.objects.filter(client__email__endswith="@bulk.demo").select_related("client").order_by("id"):
        with transaction.atomic():
            if add_new_structure(wedding, pools, today, now, counter):
                upgraded += 1
    # agreements signed with the placeholder one-pixel signature get a real-looking one (the text hash is unaffected)
    for agreement in Agreement.objects.filter(wedding__client__email__endswith="@bulk.demo", signature=SIGNATURE).select_related("wedding__client"):
        Agreement.objects.filter(pk=agreement.pk).update(signature=signature_png(agreement.wedding.client.client_name))
    # a website sign-up that is still only an enquiry also got the "we have your request" email
    emails = []
    for customer in Customer.objects.filter(email__endswith="@portal.demo", client__isnull=True):
        if EmailLog.objects.filter(template="enquiry_received", to=customer.email).exists() or customer.enquiry_id is None:
            continue
        rng = random.Random("signup-mail-" + customer.email)
        emails.append(make_email(rng, "enquiry_received", customer.email, customer.created_at,
                                 name=customer.name, link=f"{settings.CUSTOMER_SITE_URL}/home"))
    bulk(EmailLog, [e for e in emails if e], counter)
    return upgraded


# --------------------------------------------------------------------------------------------- enquiries that did not convert
def build_leads(count: int, pools: Pools, today: date, counter: Counter, now: datetime):
    """Enquiries at every stage with follow-ups (open, overdue and done) and customer-website accounts."""
    made = 0
    for n in range(count):
        if Enquiry.objects.filter(email=lead_email(n)).exists():
            continue
        rng = random.Random(f"bulk-lead-{n}")
        groom, bride = rng.choice(GROOMS), rng.choice(BRIDES)
        surname = rng.choice(SURNAMES)
        status = pick(rng, [(Status.NEW, 25), (Status.CONTACTED, 20), (Status.CONSULTATION, 18), (Status.PROPOSAL, 15),
                            (Status.LOST, 22)])
        created = today - timedelta(days=rng.randint(0, 120))
        wedding_date = today + timedelta(days=rng.randint(40, 520)) if rng.random() < 0.9 else None
        guests = int(rng.triangular(60, 800, 250)) if rng.random() < 0.92 else None
        budget = guests * rng.randint(2500, 9000) * R if guests and rng.random() < 0.9 else None
        owner = rng.choice(pools.planners)
        source = pick(rng, [(Source.INSTAGRAM, 26), (Source.WHATSAPP, 22), (Source.REFERRAL, 18), (Source.CALL, 14),
                            (Source.WEBSITE, 20)])
        enquiry = Enquiry.objects.create(
            couple_name=f"{groom} & {bride}", client_name=f"{groom} {surname}", phone=f"8{rng.randint(100000000, 999999999)}",
            email=lead_email(n), source=source, status=status, wedding_date=wedding_date, guest_count=guests,
            budget_paise=budget, venue_city=rng.choice(CITIES),
            consultation_at=at_dt(today + timedelta(days=rng.randint(-10, 14)), 15) if status == Status.CONSULTATION else None,
            notes=rng.choice(["", "", "Found us on Instagram.", "Cousin's wedding was ours.", "Asked for a destination package."]),
            expected_revenue_paise=int(budget * 0.5) // 100000 * 100000 if budget else None,
            win_chance=STAGE_WIN_CHANCE[status], priority=rng.randint(0, 3),
            expected_close_date=today + timedelta(days=rng.randint(-5, 45)) if status not in (Status.LOST,) else None,
            lost_reason=rng.choice([r for r, _ in LostReason.choices]) if status == Status.LOST else "",
            partner_name=bride, functions_wanted=rng.sample(list(FUNCTION_KEYS.values()), rng.randint(1, 4)),
            services_needed=rng.sample(SERVICES, rng.randint(2, 6)), preferred_contact=rng.choice(["CALL", "WHATSAPP", "EMAIL"]),
            profile_complete=rng.random() < 0.8, owner=owner)
        set_created(Enquiry, enquiry.pk, at_dt(created, rng.randint(9, 20)))
        counter.add("Enquiry (not converted)")
        follow_ups = []
        for _ in range(rng.randint(0, 3)):
            kind = pick(rng, [("CALL", 40), ("MEETING", 20), ("WHATSAPP", 25), ("EMAIL", 8), ("TODO", 7)])
            if status == Status.LOST or rng.random() < 0.4:  # finished
                due = at_dt(created + timedelta(days=rng.randint(1, 20)), 11)
                done = due + timedelta(hours=rng.randint(0, 20))
            elif rng.random() < 0.45:  # overdue
                due, done = now - timedelta(days=rng.randint(1, 12), hours=rng.randint(0, 20)), None
            else:  # coming up
                due, done = now + timedelta(days=rng.randint(0, 14), hours=rng.randint(1, 12)), None
            follow_ups.append(stamp(FollowUp(enquiry=enquiry, kind=kind, summary=rng.choice(FOLLOW_UP_SUMMARIES[kind]),
                                             due_at=due, done_at=done, created_by=owner), min(due, now) - timedelta(days=2)))
        bulk(FollowUp, follow_ups, counter)
        if source == Source.WEBSITE and rng.random() < 0.6:  # they made an account on the customer website
            email = f"{groom.lower()}.{surname.lower()}{n:03d}@portal.demo"
            if not Customer.objects.filter(email=email).exists():
                customer = Customer.objects.create(
                    name=f"{groom} {surname}", email=email, phone=enquiry.phone, password_hash=pools.password_hash,
                    enquiry=enquiry, last_login_at=now - timedelta(days=rng.randint(0, 30)))
                set_created(Customer, customer.pk, at_dt(created, 9))
                counter.add("Customer (website sign-up)")
        made += 1
    return made


# --------------------------------------------------------------------------------------------- entry point
def load(count: int = DEFAULT_WEDDINGS):
    global NOW
    count = int(count or DEFAULT_WEDDINGS)
    today = timezone.localdate()
    now = NOW = timezone.now()
    pools = Pools()
    pools.build()
    counter = Counter()
    created = 0
    for idx in range(count):
        with transaction.atomic():  # a wedding is saved whole or not at all
            if build_wedding(idx, pools, today, counter, now):
                created += 1
    leads = build_leads(round(count * 0.38), pools, today, counter, now)
    ensure_vendor_accounts(pools, now, counter)
    upgraded = upgrade_existing(pools, today, now, counter)
    lines = [f"bulk demo data: {created} weddings added ({count - created} already there), {leads} other enquiries added",
             f"   {upgraded} earlier weddings brought up to the current structure (agreement, login, email history)"]
    lines += [f"   {key:<28}{counter[key]:>8}" for key in sorted(counter)]
    return chr(10).join(lines)
