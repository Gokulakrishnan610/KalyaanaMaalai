"""Vendors, three caterer quotations for the Aarav & Meera wedding, and past ratings so scorecards are
not empty. Safe to run twice."""
from datetime import timedelta

from django.utils import timezone

from clients.models import Client
from quotations.models import QuotationRequest, WeddingVendor
from quotations.services import save_quotation
from vendors.models import Vendor, VendorCategory
from weddings.models import VendorArrival, VendorRating, Wedding

R = 100  # paise per rupee

VENDORS = [
    ("Rasoi Royale", "Caterer", "Harish Sharma", "9829010001", "Jaipur"),
    ("Spice Route Catering", "Caterer", "Neha Kapoor", "9829010002", "Jaipur"),
    ("Maharaja Feast", "Caterer", "Gopal Singh", "9829010003", "Jaipur"),
    ("Petals & Pillars Decor", "Decorator", "Ritu Mehra", "9829010004", "Jaipur"),
    ("Royal Mandap Decor", "Decorator", "Sanjay Rathore", "9829010005", "Udaipur"),
    ("DJ Rhythm Raj", "DJ & Sound", "Raj Malhotra", "9829010006", "Jaipur"),
    ("SoundWave Productions", "DJ & Sound", "Kunal Bhatia", "9829010007", "Delhi"),
    ("Lens & Lehenga Studio", "Photographer", "Aditi Rao", "9829010008", "Jaipur"),
    ("Reelcraft Films", "Videographer", "Farhan Qureshi", "9829010009", "Jaipur"),
    ("Glam by Anjali", "Makeup Artist", "Anjali Verma", "9829010010", "Jaipur"),
    ("Henna by Sunita", "Mehendi Artist", "Sunita Devi", "9829010011", "Jaipur"),
    ("Phool Bagh Florals", "Florist", "Mohan Lal", "9829010012", "Jaipur"),
]

# (past wedding, {vendor: (punctuality, quality, pricing, arrival delay in minutes, comment)})
PAST_WEDDINGS = [
    ("Rohit & Sneha - Udaipur", "Rohit & Sneha", 150, {
        "Rasoi Royale": (5, 5, 4, 0, "Food was the talk of the wedding."),
        "Spice Route Catering": (3, 4, 3, 35, "Good food, but service started late."),
        "Petals & Pillars Decor": (5, 4, 4, 5, "Mandap exactly as in the mood board."),
        "DJ Rhythm Raj": (4, 5, 5, 10, "Kept the dance floor full all night."),
        "Lens & Lehenga Studio": (5, 5, 3, 0, "Stunning candid shots."),
    }),
    ("Imran & Zoya - Jaipur", "Imran & Zoya", 250, {
        "Rasoi Royale": (5, 4, 4, 0, ""),
        "Maharaja Feast": (2, 3, 5, 50, "Cheap, but they were over an hour late."),
        "Royal Mandap Decor": (4, 4, 3, 10, ""),
        "SoundWave Productions": (3, 4, 4, 25, "Sound check ran late."),
        "Lens & Lehenga Studio": (5, 5, 3, 0, ""),
        "Glam by Anjali": (4, 5, 4, 5, "Bridal look was flawless."),
    }),
    ("Kunal & Pooja - Delhi", "Kunal & Pooja", 400, {
        "Spice Route Catering": (4, 4, 3, 10, ""),
        "Maharaja Feast": (3, 3, 5, 30, "Menu was repetitive."),
        "Petals & Pillars Decor": (5, 5, 4, 0, "Flowers were fresh and generous."),
        "DJ Rhythm Raj": (5, 5, 5, 0, ""),
        "Reelcraft Films": (4, 5, 4, 15, "Highlight reel delivered in a week."),
        "Henna by Sunita": (5, 5, 5, 0, "Bride's mehendi lasted for days."),
        "Phool Bagh Florals": (4, 4, 4, 10, ""),
    }),
]

# name -> (price per plate in rupees, items as (description, qty, rupees each)); None = no line items
CATERER_QUOTES = {
    "Rasoi Royale": (1150, [("Buffet menu", 450, 850), ("Welcome drinks", 450, 100),
                            ("Live counters (chaat, pasta)", 2, 30000), ("Dessert station", 1, 30000)],
                     "North Indian veg buffet, 4 starters, 2 live counters, dessert station."),
    "Spice Route Catering": (1320, [("Buffet menu", 450, 1000), ("Welcome drinks", 450, 120),
                                    ("Live counters (chaat, pasta)", 2, 27000), ("Midnight snacks", 450, 80)],
                             "Veg and non-veg buffet, 6 starters, midnight snacks."),
    "Maharaja Feast": (980, None, "Rajasthani thali style veg menu, 3 starters. Counters and drinks extra."),
}


def load():
    categories = {c.name: c for c in VendorCategory.objects.all()}
    vendors = {}
    for name, category, contact, phone, city in VENDORS:
        details = dict(category=categories[category], contact_person=contact, phone=phone, city=city,
                       email=f"{phone}@vendors.example.com")
        vendors[name], created = Vendor.objects.get_or_create(name=name, defaults=details)
        if not created:  # an earlier demo file may have made it with just a name: fill in what is missing
            missing = {k: v for k, v in details.items() if k != "category" and not getattr(vendors[name], k)}
            if missing:
                Vendor.objects.filter(pk=vendors[name].pk).update(**missing)

    load_past_weddings(vendors)
    load_caterer_request(vendors, categories["Caterer"])


def load_past_weddings(vendors):
    today = timezone.localdate()
    for index, (title, couple, guests, scores) in enumerate(PAST_WEDDINGS):
        day = today - timedelta(days=200 - 60 * index)
        client, _ = Client.objects.get_or_create(couple_name=couple, defaults=dict(phone=f"98000000{index:02d}",
                                                                                   city="Jaipur"))
        wedding, _ = Wedding.objects.get_or_create(
            title=title, client=client,
            defaults=dict(start_date=day, end_date=day, city="Jaipur", guest_count=guests, contracted_guests=guests,
                          status="COMPLETED"))
        arrival_base = timezone.now() - timedelta(days=200 - 60 * index)
        for vendor_name, (punctuality, quality, pricing, delay, comment) in scores.items():
            vendor = vendors[vendor_name]
            WeddingVendor.objects.get_or_create(wedding=wedding, vendor=vendor,
                                                defaults=dict(agreed_amount_paise=100000 * R, status="COMPLETED"))
            VendorRating.objects.get_or_create(
                vendor=vendor, wedding=wedding,
                defaults=dict(punctuality=punctuality, quality=quality, pricing=pricing, comment=comment))
            if not VendorArrival.objects.filter(wedding=wedding, vendor=vendor).exists():
                VendorArrival.objects.create(
                    wedding=wedding, vendor=vendor, expected_at=arrival_base,
                    arrived_at=arrival_base + timedelta(minutes=delay),
                    status=VendorArrival.Status.LATE if delay > 15 else VendorArrival.Status.ON_TIME)


def load_caterer_request(vendors, caterer_category):
    wedding = Wedding.objects.filter(title="Aarav & Meera - Jaipur").first()
    if wedding is None:
        return
    today = timezone.localdate()
    request, created = QuotationRequest.objects.get_or_create(
        wedding=wedding, category=caterer_category,
        defaults=dict(requirements="Vegetarian-first menu for the Sangeet and Reception, two live counters, "
                                   "dessert station. Jain options for 40 guests.",
                      guest_count=wedding.guest_count, reply_by=today + timedelta(days=10)))
    if not created or request.quotations.exists():
        return
    request.invited_vendors.set([vendors[name] for name in CATERER_QUOTES])
    request.sent_at = timezone.now()
    request.save(update_fields=["sent_at"])
    for name, (per_plate, items, notes) in CATERER_QUOTES.items():
        data = {"price_per_plate_paise": per_plate * R, "menu_notes": notes,
                "valid_till": today + timedelta(days=30)}
        if items:
            data["items"] = [{"description": d, "quantity": q, "unit_price_paise": price * R}
                             for d, q, price in items]
        save_quotation(request, vendors[name], data)
