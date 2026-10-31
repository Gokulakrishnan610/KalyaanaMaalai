import asyncio
import json
from datetime import date, timedelta

from asgiref.sync import sync_to_async
from django.db import connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from accounts.models import Role, User
from clients.models import Client
from live import bus
from live.signals import silenced
from live.views import visible_to
from notifications.models import Notification
from payments.models import Invoice, Payment
from quotations.models import Quotation, QuotationRequest
from tasks.models import Task
from vendors.models import Vendor, VendorCategory
from weddings.models import VendorArrival, Wedding


def make_wedding():
    client = Client.objects.create(couple_name="Aarav & Meera", phone="9876543210")
    return Wedding.objects.create(title="Aarav & Meera", client=client, start_date=date.today() + timedelta(days=30),
                                  end_date=date.today() + timedelta(days=31), city="Jaipur", guest_count=100,
                                  contracted_guests=100)


class BusTests(TestCase):
    def setUp(self):
        bus.get_bus().events.clear()

    def test_publish_gives_each_event_a_growing_id(self):
        first = bus.publish("task.updated", {"x": 1})
        second = bus.publish("task.updated", {"x": 2})
        self.assertEqual((first["id"], second["id"]), (1, 2))

    def test_audience_rules(self):
        founder = User(id=1, role=Role.FOUNDER)
        planner = User(id=2, role=Role.PLANNER)
        staff = User(id=3, role=Role.STAFF)
        everyone = {"audience": None}
        planners = {"audience": {"roles": [Role.PLANNER]}}
        just_staff = {"audience": {"users": [3]}}
        self.assertTrue(all(visible_to(u, everyone) for u in (founder, planner, staff)))
        self.assertEqual([visible_to(u, planners) for u in (founder, planner, staff)], [True, True, False])
        self.assertEqual([visible_to(u, just_staff) for u in (founder, planner, staff)], [False, False, True])

    def test_a_broken_bus_never_raises(self):
        class Broken:
            def publish(self, event):
                raise ConnectionError("redis is down")

        real, bus._bus = bus._bus, Broken()
        try:
            self.assertIsNone(bus.publish("x"))
        finally:
            bus._bus = real


class SignalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.founder = User.objects.create_user("f@t.com", "Founder", "Password123", role=Role.FOUNDER)
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)

    def setUp(self):
        bus.get_bus().events.clear()
        self.wedding = make_wedding()

    def types(self):
        return [e["type"] for e in bus.get_bus().events]

    def test_task_changes_are_published_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            task = Task.objects.create(wedding=self.wedding, title="Book DJ")
            task.stage = "IN_PROGRESS"
            task.save()
        events = [e for e in bus.get_bus().events if e["type"] == "task.updated"]
        self.assertEqual([e["data"]["stage"] for e in events], ["TO_PLAN", "IN_PROGRESS"])

    @override_settings(LIVE_ALERTS=True)
    def test_assigning_a_task_alerts_only_the_assignee(self):
        with self.captureOnCommitCallbacks(execute=True):
            task = Task.objects.create(wedding=self.wedding, title="Decor")
            task.assigned_to = self.staff
            task.save()
        alert = Notification.objects.get(user=self.staff)
        self.assertIn("Decor", alert.message)
        notification_events = [e for e in bus.get_bus().events if e["type"] == "notification.new"]
        self.assertEqual(notification_events[0]["audience"], {"users": [self.staff.id]})

    @override_settings(LIVE_ALERTS=True)
    def test_new_quotation_alerts_planners_not_staff(self):
        category, _ = VendorCategory.objects.get_or_create(name="Caterer")
        vendor = Vendor.objects.create(name="Spice Route", category=category)
        request = QuotationRequest.objects.create(wedding=self.wedding, category=category)
        with self.captureOnCommitCallbacks(execute=True):
            Quotation.objects.create(request=request, vendor=vendor, total_paise=500000_00)
        self.assertIn("quotation.received", self.types())
        self.assertTrue(Notification.objects.filter(user=self.planner, message__contains="Spice Route").exists())
        self.assertFalse(Notification.objects.filter(user=self.staff).exists())
        event = next(e for e in bus.get_bus().events if e["type"] == "quotation.received")
        self.assertEqual(event["audience"], {"roles": [Role.PLANNER]})

    @override_settings(LIVE_ALERTS=True)
    def test_payment_updates_planners_only(self):
        invoice = Invoice.objects.create(wedding=self.wedding, client=self.wedding.client, kind="DEPOSIT",
                                         amount_paise=1000_00)
        with self.captureOnCommitCallbacks(execute=True):
            Payment.objects.create(wedding=self.wedding, invoice=invoice, direction="IN", amount_paise=400_00,
                                   method="UPI")
        event = next(e for e in bus.get_bus().events if e["type"] == "payment.recorded")
        self.assertEqual(event["audience"], {"roles": [Role.PLANNER]})
        self.assertTrue(Notification.objects.filter(user=self.planner, message__contains="₹400").exists())

    def test_vendor_arrival_is_published(self):
        category, _ = VendorCategory.objects.get_or_create(name="DJ & Sound")
        vendor = Vendor.objects.create(name="DJ Raj", category=category)
        with self.captureOnCommitCallbacks(execute=True):
            VendorArrival.objects.create(wedding=self.wedding, vendor=vendor,
                                         expected_at=timezone.now() + timedelta(hours=1))
        self.assertIn("vendor.arrival", self.types())

    def test_silenced_blocks_everything(self):
        with silenced(), self.captureOnCommitCallbacks(execute=True):
            Task.objects.create(wedding=self.wedding, title="Quiet")
        self.assertEqual(bus.get_bus().events, [])


class StreamTests(TransactionTestCase):
    # a real commit is needed: the stream reads the user in its own database connection
    def test_stream_needs_a_login_token(self):
        response = self.client.get("/api/live/stream/")
        self.assertEqual(response.status_code, 401)

    def test_stream_sends_events_the_user_may_see(self):
        from rest_framework_simplejwt.tokens import AccessToken

        from live.views import stream

        planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        bus.get_bus().events.clear()
        bus.publish("task.updated", {"title": "visible"})
        bus.publish("payment.recorded", {"title": "planners only"}, {"roles": [Role.PLANNER]})
        bus.publish("notification.new", {"title": "someone else"}, {"users": [planner.id + 99]})

        async def read():
            from django.test import AsyncRequestFactory
            request = AsyncRequestFactory().get("/api/live/stream/", headers={
                "Authorization": f"Bearer {AccessToken.for_user(planner)}"})
            response = await stream(request)
            chunks = []
            async for chunk in response.streaming_content:
                chunks.append(chunk.decode())
                if sum("event:" in c for c in chunks) >= 2:
                    break
            await sync_to_async(connections.close_all)()
            return "".join(chunks)

        text = asyncio.run(asyncio.wait_for(read(), timeout=5))
        self.assertIn("event: task.updated", text)
        self.assertIn("event: payment.recorded", text)
        self.assertNotIn("someone else", text)
        data = json.loads(text.split("event: task.updated\ndata: ")[1].split("\n")[0])
        self.assertEqual(data["data"]["title"], "visible")
