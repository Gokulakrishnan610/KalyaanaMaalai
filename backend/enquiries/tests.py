from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from clients.models import Client
from enquiries.models import Enquiry, FollowUp, Status


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


class CrmFieldsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)

    def make(self, **extra):
        data = {"couple_name": "Kabir & Sana", "phone": "9898989898", "source": "CALL"}
        self.client.force_authenticate(self.planner)
        return self.client.post("/api/enquiries/", {**data, **extra}).data

    def test_win_chance_follows_the_stage_unless_set_by_hand(self):
        enquiry = self.make()
        self.assertEqual(enquiry["win_chance"], 10)
        moved = self.client.patch(f"/api/enquiries/{enquiry['id']}/", {"status": "PROPOSAL"}).data
        self.assertEqual(moved["win_chance"], 60)
        manual = self.client.patch(f"/api/enquiries/{enquiry['id']}/", {"status": "CONSULTATION", "win_chance": 75}).data
        self.assertEqual(manual["win_chance"], 75)

    def test_losing_needs_a_reason(self):
        enquiry = self.make()
        url = f"/api/enquiries/{enquiry['id']}/"
        self.assertEqual(self.client.patch(url, {"status": "LOST"}).status_code, 400)
        res = self.client.patch(url, {"status": "LOST", "lost_reason": "BUDGET"})
        self.assertEqual((res.status_code, res.data["win_chance"]), (200, 0))

    def test_priority_and_win_chance_limits(self):
        enquiry = self.make()
        url = f"/api/enquiries/{enquiry['id']}/"
        self.assertEqual(self.client.patch(url, {"priority": 5}).status_code, 400)
        self.assertEqual(self.client.patch(url, {"win_chance": 150}).status_code, 400)

    def test_converting_makes_the_chance_100(self):
        enquiry = self.make()
        res = self.client.post(f"/api/enquiries/{enquiry['id']}/convert/", {}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Enquiry.objects.get(id=enquiry["id"]).win_chance, 100)

    def test_follow_ups_can_be_added_listed_and_marked_done_once(self):
        enquiry = self.make()
        due = timezone.now() - timedelta(hours=1)
        body = {"enquiry": enquiry["id"], "kind": "CALL", "summary": "Ask about venue", "due_at": due.isoformat()}
        created = self.client.post("/api/follow-ups/", body)
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.data["is_overdue"])
        listed = self.client.get("/api/enquiries/?q=Kabir").data["results"][0]
        self.assertIsNotNone(listed["next_follow_up"])
        first = self.client.post(f"/api/follow-ups/{created.data['id']}/done/").data["done_at"]
        again = self.client.post(f"/api/follow-ups/{created.data['id']}/done/").data["done_at"]
        self.assertEqual(first, again)
        self.assertEqual(self.client.get("/api/follow-ups/?open=1").data, [])
        self.assertIsNone(self.client.get("/api/enquiries/?q=Kabir").data["results"][0]["next_follow_up"])

    def test_staff_can_see_but_not_add_follow_ups(self):
        enquiry = self.make()
        FollowUp.objects.create(enquiry_id=enquiry["id"], summary="x", due_at=timezone.now())
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/follow-ups/").status_code, 200)
        body = {"enquiry": enquiry["id"], "summary": "y", "due_at": timezone.now().isoformat()}
        self.assertEqual(self.client.post("/api/follow-ups/", body).status_code, 403)


class ClientIdentityTests(APITestCase):
    """A client is recognised by client name + email, so a returning client is never duplicated."""

    @classmethod
    def setUpTestData(cls):
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)

    def body(self, **extra):
        return {"client_name": "Rohan Mehta", "phone": "9812345670", "email": "rohan@example.com",
                "partner_name": "Ishita Rao", "spouse_email": "ishita@example.com", "source": "CALL",
                "venue_city": "Udaipur", **extra}

    def setUp(self):
        self.client.force_authenticate(self.planner)

    def test_enquiry_keeps_client_and_spouse_details_and_builds_the_couple_name(self):
        res = self.client.post("/api/enquiries/", self.body())
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["couple_name"], "Rohan Mehta & Ishita Rao")
        self.assertEqual((res.data["partner_name"], res.data["spouse_email"]), ("Ishita Rao", "ishita@example.com"))
        self.assertIsNone(res.data["client"])

    def test_a_client_name_is_needed_when_no_couple_name_is_given(self):
        res = self.client.post("/api/enquiries/", self.body(client_name="", partner_name=""))
        self.assertEqual(res.status_code, 400)

    def test_converting_twice_with_the_same_name_and_email_makes_one_client(self):
        first = self.client.post("/api/enquiries/", self.body()).data["id"]
        second = self.client.post("/api/enquiries/", self.body(phone="9000000001", venue_city="Goa")).data["id"]
        one = self.client.post(f"/api/enquiries/{first}/convert/", {}, format="json").data["client"]["id"]
        two = self.client.post(f"/api/enquiries/{second}/convert/", {}, format="json").data["client"]["id"]
        self.assertEqual(one, two)
        self.assertEqual(Client.objects.count(), 1)

    def test_name_and_email_match_ignores_capitals_and_a_new_enquiry_links_to_the_existing_client(self):
        first = self.client.post("/api/enquiries/", self.body()).data["id"]
        self.client.post(f"/api/enquiries/{first}/convert/", {}, format="json")
        again = self.client.post("/api/enquiries/", self.body(client_name="ROHAN MEHTA", email="Rohan@Example.com"))
        self.assertEqual(again.data["client"], Client.objects.get().id)

    def test_same_name_with_a_different_email_is_a_different_client(self):
        a = self.client.post("/api/enquiries/", self.body()).data["id"]
        b = self.client.post("/api/enquiries/", self.body(email="other@example.com")).data["id"]
        self.client.post(f"/api/enquiries/{a}/convert/", {}, format="json")
        self.client.post(f"/api/enquiries/{b}/convert/", {}, format="json")
        self.assertEqual(Client.objects.count(), 2)

    def test_lookup_finds_a_client_by_name_and_email_only(self):
        enquiry = self.client.post("/api/enquiries/", self.body()).data["id"]
        self.client.post(f"/api/enquiries/{enquiry}/convert/", {}, format="json")
        found = self.client.get("/api/clients/lookup/", {"client_name": "rohan mehta", "email": "ROHAN@example.com"})
        self.assertEqual(found.data["client"]["spouse_name"], "Ishita Rao")
        self.assertIsNone(self.client.get("/api/clients/lookup/", {"client_name": "Rohan Mehta"}).data["client"])
        self.assertIsNone(self.client.get("/api/clients/lookup/", {"client_name": "Rohan Mehta",
                                                                    "email": "x@example.com"}).data["client"])

    def test_creating_a_duplicate_client_directly_is_refused(self):
        body = {"couple_name": "Rohan & Ishita", "client_name": "Rohan Mehta", "email": "rohan@example.com",
                "phone": "9812345670"}
        self.assertEqual(self.client.post("/api/clients/", body).status_code, 201)
        self.assertEqual(self.client.post("/api/clients/", body).status_code, 400)

    def test_search_finds_an_enquiry_by_client_spouse_or_email(self):
        self.client.post("/api/enquiries/", self.body())
        for text in ("Mehta", "Ishita", "rohan@example"):
            self.assertEqual(self.client.get("/api/enquiries/", {"q": text}).data["count"], 1, text)

    def test_status_can_be_changed_with_a_single_patch(self):
        enquiry = self.client.post("/api/enquiries/", self.body()).data["id"]
        res = self.client.patch(f"/api/enquiries/{enquiry}/", {"status": "CONTACTED"}, format="json")
        self.assertEqual((res.status_code, res.data["status"], res.data["win_chance"]), (200, "CONTACTED", 20))
        self.assertEqual(self.client.patch(f"/api/enquiries/{enquiry}/", {"status": "LOST"}, format="json").status_code, 400)
