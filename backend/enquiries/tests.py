from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from clients.models import Client
from enquiries.models import Enquiry, Status


class EnquiryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.founder = User.objects.create_user("f@t.com", "Founder", "Password123", role=Role.FOUNDER)
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)
        cls.future = (timezone.localdate() + timedelta(days=90)).isoformat()

    def enquiry_data(self, **extra):
        data = {"couple_name": "Rohan & Ishita", "phone": "9812345670", "source": "INSTAGRAM",
                "wedding_date": self.future, "guest_count": 300, "budget_paise": 250000000,
                "venue_city": "Udaipur"}
        return {**data, **extra}

    def test_planner_creates_enquiry_and_becomes_owner(self):
        self.client.force_authenticate(self.planner)
        res = self.client.post("/api/enquiries/", self.enquiry_data())
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "NEW")
        self.assertEqual(res.data["owner"], self.planner.id)

    def test_validation_rejects_bad_phone_past_date_and_zero_guests(self):
        self.client.force_authenticate(self.planner)
        for bad in ({"phone": "12345"}, {"wedding_date": "2020-01-01"}, {"guest_count": 0},
                    {"budget_paise": -5}):
            res = self.client.post("/api/enquiries/", self.enquiry_data(**bad))
            self.assertEqual(res.status_code, 400, bad)

    def test_staff_can_read_but_not_write_and_only_founder_deletes(self):
        enquiry = Enquiry.objects.create(couple_name="A & B", phone="9812345670", source="CALL")
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/enquiries/").status_code, 200)
        self.assertEqual(self.client.post("/api/enquiries/", self.enquiry_data()).status_code, 403)
        self.client.force_authenticate(self.planner)
        self.assertEqual(self.client.delete(f"/api/enquiries/{enquiry.id}/").status_code, 403)
        self.client.force_authenticate(self.founder)
        self.assertEqual(self.client.delete(f"/api/enquiries/{enquiry.id}/").status_code, 204)

    def test_filter_by_source_status_and_search(self):
        Enquiry.objects.create(couple_name="Kabir & Sana", phone="9898989898", source="CALL")
        Enquiry.objects.create(couple_name="Vikram & Neha", phone="9765432101", source="WHATSAPP",
                               status=Status.PROPOSAL)
        self.client.force_authenticate(self.planner)
        self.assertEqual(self.client.get("/api/enquiries/?source=CALL").data["count"], 1)
        self.assertEqual(self.client.get("/api/enquiries/?status=PROPOSAL").data["count"], 1)
        self.assertEqual(self.client.get("/api/enquiries/?q=Vikram").data["count"], 1)

    def test_convert_makes_one_client_even_when_clicked_twice(self):
        enquiry = Enquiry.objects.create(couple_name="Kabir & Sana", phone="9898989898", source="CALL")
        self.client.force_authenticate(self.planner)
        first = self.client.post(f"/api/enquiries/{enquiry.id}/convert/", {}, format="json")
        second = self.client.post(f"/api/enquiries/{enquiry.id}/convert/", {}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["client"]["id"], second.data["client"]["id"])
        self.assertEqual(Client.objects.count(), 1)
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Status.WON)

    def test_convert_can_also_create_the_wedding(self):
        self.client.force_authenticate(self.planner)
        enquiry_id = self.client.post("/api/enquiries/", self.enquiry_data()).data["id"]
        res = self.client.post(f"/api/enquiries/{enquiry_id}/convert/", {"create_wedding": True}, format="json")
        self.assertIsNotNone(res.data["wedding_id"])
        again = self.client.post(f"/api/enquiries/{enquiry_id}/convert/", {"create_wedding": True}, format="json")
        self.assertEqual(res.data["wedding_id"], again.data["wedding_id"])

    def test_convert_with_wedding_needs_date_guests_and_city(self):
        enquiry = Enquiry.objects.create(couple_name="Kabir & Sana", phone="9898989898", source="CALL")
        self.client.force_authenticate(self.planner)
        res = self.client.post(f"/api/enquiries/{enquiry.id}/convert/", {"create_wedding": True}, format="json")
        self.assertEqual(res.status_code, 400)
