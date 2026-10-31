from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from clients.models import Client
from quotations.models import WeddingVendor
from vendors.models import Vendor, VendorCategory
from weddings.models import VendorArrival, VendorRating, Wedding


class VendorTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.founder = User.objects.create_user("f@t.com", "Founder", "Password123", role=Role.FOUNDER)
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)
        cls.caterer = VendorCategory.objects.get(name="Caterer")
        cls.dj = VendorCategory.objects.get(name="DJ & Sound")
        client = Client.objects.create(couple_name="A & B", phone="9812345670")
        today = timezone.localdate()
        cls.wedding = Wedding.objects.create(title="A & B", client=client, start_date=today, end_date=today,
                                             city="Jaipur", guest_count=100, contracted_guests=100)

    def setUp(self):
        self.client.force_authenticate(self.planner)

    def data(self, **extra):
        return {"name": "Rasoi Royale", "category_id": self.caterer.id, "phone": "9876500001",
                "email": "rasoi@example.com", "city": "Jaipur", **extra}

    def test_the_eleven_categories_exist(self):
        res = self.client.get("/api/vendor-categories/")
        self.assertEqual(len(res.data), 11)
        self.assertIn("Mehendi Artist", [c["name"] for c in res.data])

    def test_validation_rejects_bad_phone_email_and_missing_category(self):
        for bad in ({"phone": "12345"}, {"phone": "98765abcde"}, {"email": "nope"}, {"category_id": 9999},
                    {"name": "  "}):
            self.assertEqual(self.client.post("/api/vendors/", self.data(**bad)).status_code, 400, bad)

    def test_duplicate_name_and_phone_still_saves_but_warns(self):
        first = self.client.post("/api/vendors/", self.data())
        second = self.client.post("/api/vendors/", self.data(name="rasoi royale"))
        self.assertFalse(first.data["duplicate_warning"])
        self.assertTrue(second.data["duplicate_warning"])
        self.assertEqual(Vendor.objects.count(), 2)

    def test_list_filters_and_includes_rating_and_wedding_count(self):
        a = Vendor.objects.create(name="Rasoi Royale", category=self.caterer, phone="9876500001", city="Jaipur")
        Vendor.objects.create(name="DJ Neel", category=self.dj, phone="9876500002", city="Delhi")
        VendorRating.objects.create(vendor=a, wedding=self.wedding, punctuality=5, quality=4, pricing=3)
        WeddingVendor.objects.create(wedding=self.wedding, vendor=a, agreed_amount_paise=1)
        res = self.client.get("/api/vendors/", {"category_id": self.caterer.id})
        self.assertEqual(res.data["count"], 1)
        row = res.data["results"][0]
        self.assertEqual((row["avg_rating"], row["weddings_count"], row["category_name"]), (4.0, 1, "Caterer"))
        self.assertEqual(self.client.get("/api/vendors/?city=delhi").data["count"], 1)
        self.assertEqual(self.client.get("/api/vendors/?q=rasoi").data["count"], 1)
        self.assertEqual(len(self.client.get("/api/vendors/?limit=1").data["results"]), 1)

    def test_delete_is_blocked_when_booked_and_founder_only(self):
        v = Vendor.objects.create(name="Rasoi Royale", category=self.caterer, phone="9876500001")
        free = Vendor.objects.create(name="Free", category=self.caterer, phone="9876500009")
        WeddingVendor.objects.create(wedding=self.wedding, vendor=v, agreed_amount_paise=1)
        self.assertEqual(self.client.delete(f"/api/vendors/{free.id}/").status_code, 403)
        self.client.force_authenticate(self.founder)
        self.assertEqual(self.client.delete(f"/api/vendors/{v.id}/").status_code, 409)
        self.assertEqual(self.client.delete(f"/api/vendors/{free.id}/").status_code, 204)

    def test_staff_can_read_but_not_write(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/vendors/").status_code, 200)
        self.assertEqual(self.client.post("/api/vendors/", self.data()).status_code, 403)

    def test_rating_is_saved_once_per_wedding_and_validated(self):
        v = Vendor.objects.create(name="Rasoi Royale", category=self.caterer, phone="9876500001")
        url = f"/api/vendors/{v.id}/ratings/"
        body = {"wedding_id": self.wedding.id, "punctuality": 5, "quality": 4, "pricing": 3, "comment": "Good"}
        self.assertEqual(self.client.post(url, body, format="json").status_code, 400)  # not booked there
        WeddingVendor.objects.create(wedding=self.wedding, vendor=v, agreed_amount_paise=1)
        self.assertEqual(self.client.post(url, body, format="json").status_code, 201)
        self.assertEqual(self.client.post(url, {**body, "quality": 2}, format="json").status_code, 200)
        self.assertEqual(VendorRating.objects.filter(vendor=v).count(), 1)
        self.assertEqual(self.client.post(url, {**body, "quality": 6}, format="json").status_code, 400)

    def test_performance_takes_punctuality_from_check_ins(self):
        v = Vendor.objects.create(name="Rasoi Royale", category=self.caterer, phone="9876500001")
        WeddingVendor.objects.create(wedding=self.wedding, vendor=v, agreed_amount_paise=1)
        VendorRating.objects.create(vendor=v, wedding=self.wedding, punctuality=5, quality=4, pricing=3)
        now = timezone.now()
        for status, delay in (("ON_TIME", 0), ("ON_TIME", 5), ("ON_TIME", 0), ("LATE", 40)):
            VendorArrival.objects.create(wedding=self.wedding, vendor=v, expected_at=now, status=status,
                                         arrived_at=now + timedelta(minutes=delay))
        VendorArrival.objects.create(wedding=self.wedding, vendor=v, expected_at=now)  # PENDING: not counted
        perf = self.client.get(f"/api/vendors/{v.id}/performance/").data
        self.assertEqual(perf["punctuality_pct"], 75.0)
        self.assertEqual(perf["avg_delay_min"], 11.2)
        self.assertEqual((perf["avg_quality"], perf["avg_pricing"], perf["weddings_count"]), (4.0, 3.0, 1))
        self.assertEqual(perf["score"], round(100 * (0.4 * 0.8 + 0.3 * 0.6 + 0.3 * 0.75)))

    def test_profile_has_weddings_ratings_and_performance(self):
        v = Vendor.objects.create(name="Rasoi Royale", category=self.caterer, phone="9876500001")
        WeddingVendor.objects.create(wedding=self.wedding, vendor=v, agreed_amount_paise=5000)
        res = self.client.get(f"/api/vendors/{v.id}/")
        self.assertEqual(res.data["weddings"][0]["agreed_amount_paise"], 5000)
        self.assertEqual(res.data["total_paid_paise"], 0)
        self.assertIsNone(res.data["performance"]["score"])
