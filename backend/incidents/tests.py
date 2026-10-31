from datetime import date, timedelta

from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import Role, User
from clients.models import Client
from incidents.models import Incident
from live import bus
from notifications.models import Notification
from weddings.models import Wedding


@override_settings(LIVE_ALERTS=True)
class IncidentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.founder = User.objects.create_user("f@t.com", "Founder", "Password123", role=Role.FOUNDER)
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.coordinator = User.objects.create_user("c@t.com", "Coordinator", "Password123", role=Role.STAFF)
        cls.other = User.objects.create_user("o@t.com", "Other Staff", "Password123", role=Role.STAFF)
        client = Client.objects.create(couple_name="Aarav & Meera", phone="9876543210")
        cls.wedding = Wedding.objects.create(
            title="Aarav & Meera", client=client, start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=6), city="Jaipur", guest_count=100, contracted_guests=100)

    def setUp(self):
        bus.get_bus().events.clear()

    def report(self, **extra):
        self.client.force_authenticate(self.coordinator)
        body = {"wedding": self.wedding.id, "title": "Florist needs an extra generator", "severity": "HIGH", **extra}
        return self.client.post("/api/incidents/", body)

    def test_a_coordinator_reports_and_planners_are_alerted_at_once(self):
        with self.captureOnCommitCallbacks(execute=True):  # live events are sent after the commit
            res = self.report()
        self.assertEqual(res.status_code, 201)
        self.assertEqual((res.data["status"], res.data["reported_by"]), ("OPEN", self.coordinator.id))
        for planner in (self.planner, self.founder):
            self.assertTrue(Notification.objects.filter(user=planner, message__contains="generator").exists())
        self.assertFalse(Notification.objects.filter(user=self.other).exists())
        self.assertTrue(any(e["type"] == "incident.updated" for e in bus.get_bus().events))

    def test_a_title_is_required(self):
        self.assertEqual(self.report(title="  ").status_code, 400)

    def test_planner_assigns_and_the_assignee_is_alerted(self):
        incident_id = self.report().data["id"]
        self.client.force_authenticate(self.planner)
        res = self.client.post(f"/api/incidents/{incident_id}/assign/", {"user": self.other.id}, format="json")
        self.assertEqual((res.status_code, res.data["status"]), (200, "ASSIGNED"))
        self.assertTrue(Notification.objects.filter(user=self.other, message__contains="assigned an incident").exists())

    def test_coordinator_cannot_assign(self):
        incident_id = self.report().data["id"]
        res = self.client.post(f"/api/incidents/{incident_id}/assign/", {"user": self.other.id}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_only_planners_or_the_assignee_change_the_status(self):
        incident_id = self.report().data["id"]
        self.client.force_authenticate(self.planner)
        self.client.post(f"/api/incidents/{incident_id}/assign/", {"user": self.other.id}, format="json")
        self.client.force_authenticate(self.coordinator)  # reported it, but is not the assignee
        self.assertEqual(self.client.post(f"/api/incidents/{incident_id}/status/", {"status": "IN_PROGRESS"},
                                          format="json").status_code, 403)
        self.client.force_authenticate(self.other)
        res = self.client.post(f"/api/incidents/{incident_id}/status/", {"status": "IN_PROGRESS"}, format="json")
        self.assertEqual(res.data["status"], "IN_PROGRESS")

    def test_resolving_sets_the_time_alerts_the_reporter_and_keeps_a_history(self):
        incident_id = self.report().data["id"]
        self.client.force_authenticate(self.planner)
        res = self.client.post(f"/api/incidents/{incident_id}/status/",
                               {"status": "RESOLVED", "note": "Generator delivered"}, format="json")
        self.assertIsNotNone(res.data["resolved_at"])
        self.assertFalse(res.data["is_open"])
        self.assertTrue(Notification.objects.filter(user=self.coordinator, message__startswith="Resolved").exists())
        detail = self.client.get(f"/api/incidents/{incident_id}/").data
        messages = [u["message"] for u in detail["updates"]]
        self.assertEqual(len(messages), 2)
        self.assertIn("Generator delivered", messages[-1])

    def test_filters_and_staff_cannot_delete(self):
        first = self.report().data["id"]
        self.report(title="DJ speaker broke", severity="LOW")
        self.client.force_authenticate(self.planner)
        self.client.post(f"/api/incidents/{first}/status/", {"status": "RESOLVED"}, format="json")
        self.assertEqual(self.client.get("/api/incidents/?open=1").data["count"], 1)
        self.assertEqual(self.client.get(f"/api/incidents/?wedding={self.wedding.id}").data["count"], 2)
        self.assertEqual(self.client.delete(f"/api/incidents/{first}/").status_code, 403)
        self.client.force_authenticate(self.founder)
        self.assertEqual(self.client.delete(f"/api/incidents/{first}/").status_code, 204)

    def test_notes_are_added_by_anyone_and_must_not_be_empty(self):
        incident_id = self.report().data["id"]
        res = self.client.post(f"/api/incidents/{incident_id}/note/", {"note": "Vendor is on the way"}, format="json")
        self.assertEqual(len(res.data["updates"]), 2)
        self.assertEqual(self.client.post(f"/api/incidents/{incident_id}/note/", {"note": " "}, format="json").status_code, 400)
        self.assertEqual(Incident.objects.count(), 1)
