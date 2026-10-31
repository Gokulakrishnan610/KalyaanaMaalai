from datetime import date, datetime, time, timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import Role, User
from clients.models import Client
from notifications.models import Notification
from payments.models import Invoice
from tasks.models import Stage, Task
from tasks.services import create_tasks_from_template, move_task
from tasks.template import TEMPLATE
from vendors.models import Vendor, VendorCategory
from weddings import eventday
from weddings.jobs import mark_late_vendors
from weddings.models import ScheduleItem, TeamMember, VendorArrival, Venue, Wedding, WeddingFunction
from weddings.services import get_vendor_punctuality


def at(day: date, hour: int, minute: int = 0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class Base(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.founder = User.objects.create_user("f@t.com", "Founder", "Password123", role=Role.FOUNDER)
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)
        cls.couple = Client.objects.create(couple_name="Aarav & Meera", phone="9876543210", city="Jaipur")
        cls.vendor = Vendor.objects.create(name="Royal Caterers", category=VendorCategory.objects.get_or_create(name="Caterer")[0])

    def make_wedding(self, **extra):
        values = dict(title="Aarav & Meera", client=self.couple, start_date=date(2027, 2, 10),
                      end_date=date(2027, 2, 12), city="Jaipur", guest_count=300, contracted_guests=300)
        values.update(extra)
        return Wedding.objects.create(**values)

    def body(self, **extra):
        values = dict(title="New wedding", client=self.couple.id, start_date="2027-03-01", end_date="2027-03-03",
                      city="Jaipur", guest_count=200, per_guest_rate_paise=250000, budget_paise=100000000)
        values.update(extra)
        return values


class WeddingTests(Base):
    def setUp(self):
        self.client.force_authenticate(self.planner)

    def test_create_wedding_defaults_contracted_guests(self):
        res = self.client.post("/api/weddings/", self.body(), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["contracted_guests"], 200)
        self.assertEqual(res.data["client_name"], "Aarav & Meera")
        self.assertEqual(res.data["functions"], [])

    def test_default_functions_on_consecutive_days(self):
        res = self.client.post("/api/weddings/", self.body(default_functions=True), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        functions = WeddingFunction.objects.filter(wedding_id=res.data["id"]).order_by("starts_at")
        self.assertEqual([f.name for f in functions], ["Mehendi", "Sangeet", "Wedding", "Reception"])
        self.assertEqual([f.starts_at.date() for f in functions], [date(2027, 3, d) for d in (1, 2, 3, 4)])

    def test_date_and_number_validation(self):
        for bad in (dict(end_date="2027-02-01"), dict(guest_count=0), dict(budget_paise=-1)):
            res = self.client.post("/api/weddings/", self.body(**bad), format="json")
            self.assertEqual(res.status_code, 400, bad)
        self.assertEqual(Wedding.objects.count(), 0)

    def test_list_has_progress_and_next_function(self):
        wedding = self.make_wedding()
        WeddingFunction.objects.create(wedding=wedding, name="Sangeet", starts_at=timezone.now() + timedelta(days=3),
                                       ends_at=timezone.now() + timedelta(days=3, hours=4))
        Task.objects.create(wedding=wedding, title="a", stage=Stage.DONE)
        Task.objects.create(wedding=wedding, title="b", stage=Stage.TO_PLAN)
        res = self.client.get("/api/weddings/?q=meera&limit=5")
        row = res.data["results"][0]
        self.assertEqual(row["progress_pct"], 50)
        self.assertEqual(row["next_function_date"], (timezone.now() + timedelta(days=3)).date().isoformat())
        self.assertEqual(res.data["count"], 1)

    def test_delete_is_founder_only_and_blocked_by_invoices(self):
        wedding = self.make_wedding()
        self.assertEqual(self.client.delete(f"/api/weddings/{wedding.id}/").status_code, 403)
        self.client.force_authenticate(self.founder)
        Invoice.objects.create(wedding=wedding, client=self.couple, kind="DEPOSIT", amount_paise=1000)
        self.assertEqual(self.client.delete(f"/api/weddings/{wedding.id}/").status_code, 409)
        Invoice.objects.all().delete()
        self.assertEqual(self.client.delete(f"/api/weddings/{wedding.id}/").status_code, 204)

    def test_venue_overlap_is_rejected_with_409(self):
        venue = Venue.objects.create(name="Fort Palace")
        first = self.make_wedding()
        other = self.make_wedding(title="Other")
        day = date(2027, 2, 10)
        ok = self.client.post(f"/api/weddings/{first.id}/functions/", dict(
            name="Sangeet", venue=venue.id, starts_at=at(day, 18).isoformat(), ends_at=at(day, 22).isoformat()),
            format="json")
        self.assertEqual(ok.status_code, 201, ok.data)
        clash = self.client.post(f"/api/weddings/{other.id}/functions/", dict(
            name="Reception", venue=venue.id, starts_at=at(day, 21).isoformat(), ends_at=at(day, 23).isoformat()),
            format="json")
        self.assertEqual(clash.status_code, 409)
        self.assertIn("Fort Palace", clash.data["detail"])
        back_to_back = self.client.post(f"/api/weddings/{other.id}/functions/", dict(
            name="Reception", venue=venue.id, starts_at=at(day, 22).isoformat(), ends_at=at(day, 23).isoformat()),
            format="json")
        self.assertEqual(back_to_back.status_code, 201)

    def test_assignments_replace_whole_team(self):
        wedding = self.make_wedding()
        TeamMember.objects.create(wedding=wedding, user=self.staff, role_label="COORDINATOR")
        url = f"/api/weddings/{wedding.id}/assignments/"
        res = self.client.put(url, [{"user_id": self.planner.id, "role_label": "LEAD_PLANNER"}], format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(TeamMember.objects.filter(wedding=wedding).values_list("user_id", flat=True)),
                         [self.planner.id])
        bad = self.client.put(url, [{"user_id": 9999, "role_label": "LEAD_PLANNER"}], format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(TeamMember.objects.filter(wedding=wedding).count(), 1)  # old team untouched

    def test_progress_updates_when_a_task_moves_to_done(self):
        wedding = self.make_wedding()
        task = Task.objects.create(wedding=wedding, title="a", due_date=date(2020, 1, 1))
        Task.objects.create(wedding=wedding, title="b")
        url = f"/api/weddings/{wedding.id}/progress/"
        first = self.client.get(url).data
        self.assertEqual((first["total"], first["done"], first["pct"], first["overdue"]), (2, 0, 0, 1))
        self.client.patch(f"/api/tasks/{task.id}/move/", {"stage": "DONE", "position": 0}, format="json")
        second = self.client.get(url).data
        self.assertEqual((second["done"], second["pct"], second["overdue"]), (1, 50, 0))
        self.assertEqual(second["by_stage"]["DONE"], 1)


class TaskTests(Base):
    def setUp(self):
        self.client.force_authenticate(self.planner)
        self.wedding = self.make_wedding()

    def test_template_creates_30_tasks_with_dates_and_assignees(self):
        TeamMember.objects.create(wedding=self.wedding, user=self.planner, role_label="LEAD_PLANNER")
        created = create_tasks_from_template(self.wedding.id)
        self.assertEqual(len(created), len(TEMPLATE))
        self.assertGreaterEqual(len(created), 25)
        venue = Task.objects.get(wedding=self.wedding, title="Finalize venue")
        self.assertEqual(venue.due_date, self.wedding.start_date - timedelta(days=150))
        self.assertEqual(venue.assigned_to, self.planner)
        briefing = Task.objects.get(wedding=self.wedding, title="Conduct day-of briefing")
        self.assertEqual(briefing.due_date, self.wedding.start_date - timedelta(days=1))
        caterer = Task.objects.get(wedding=self.wedding, title="Book caterer")
        self.assertIsNone(caterer.assigned_to)  # nobody holds VENDOR_LEAD

    def test_template_is_idempotent_and_ignores_case(self):
        Task.objects.create(wedding=self.wedding, title="FINALIZE VENUE")
        first = create_tasks_from_template(self.wedding.id)
        self.assertEqual(len(first), len(TEMPLATE) - 1)
        self.assertEqual(create_tasks_from_template(self.wedding.id), [])
        self.assertEqual(Task.objects.filter(wedding=self.wedding).count(), len(TEMPLATE))

    def test_template_endpoint_dry_run_writes_nothing(self):
        url = f"/api/weddings/{self.wedding.id}/tasks/from-template/"
        preview = self.client.post(url + "?dry_run=true", {}, format="json")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data["count"], len(TEMPLATE))
        self.assertEqual(Task.objects.count(), 0)
        real = self.client.post(url, {}, format="json")
        self.assertEqual(real.status_code, 201)
        self.assertEqual(self.client.post(url, {}, format="json").data["count"], 0)

    def test_move_reorders_and_compacts(self):
        a, b, c = (Task.objects.create(wedding=self.wedding, title=t, position=i)
                   for i, t in enumerate("abc"))
        Task.objects.create(wedding=self.wedding, title="d", stage=Stage.DONE, position=0)
        res = self.client.patch(f"/api/tasks/{a.id}/move/", {"stage": "DONE", "position": 0}, format="json")
        self.assertEqual(res.status_code, 200)
        done = list(Task.objects.filter(stage=Stage.DONE).order_by("position").values_list("title", "position"))
        self.assertEqual(done, [("a", 0), ("d", 1)])
        todo = list(Task.objects.filter(stage=Stage.TO_PLAN).order_by("position").values_list("title", "position"))
        self.assertEqual(todo, [("b", 0), ("c", 1)])  # gap closed
        move_task(c.id, Stage.TO_PLAN, 0)  # reorder inside one column
        todo = list(Task.objects.filter(stage=Stage.TO_PLAN).order_by("position").values_list("title", flat=True))
        self.assertEqual(todo, ["c", "b"])
        listed = self.client.get(f"/api/weddings/{self.wedding.id}/tasks/?stage=TO_PLAN").data
        self.assertEqual([t["title"] for t in listed], ["c", "b"])  # order survives a reload


class CheckinTests(Base):
    def setUp(self):
        self.wedding = self.make_wedding()

    def new_checkin(self, expected_in_minutes=60, grace=15):
        return VendorArrival.objects.create(wedding=self.wedding, vendor=self.vendor, grace_minutes=grace,
                                            expected_at=timezone.now() + timedelta(minutes=expected_in_minutes))

    def test_public_endpoints_need_no_login(self):
        arrival = self.new_checkin()
        anonymous = APIClient()
        info = anonymous.get(f"/api/public/checkin/{arrival.check_in_code}/")
        self.assertEqual(info.status_code, 200)
        self.assertEqual(info.data["vendor_name"], "Royal Caterers")
        self.assertEqual(anonymous.get("/api/public/checkin/nope/").status_code, 404)
        self.assertEqual(anonymous.get(f"/api/weddings/{self.wedding.id}/checkins/").status_code, 401)

    def test_on_time_arrival(self):
        arrival = self.new_checkin(expected_in_minutes=5)
        res = APIClient().post(f"/api/public/checkin/{arrival.check_in_code}/arrive/")
        self.assertEqual(res.status_code, 200)
        arrival.refresh_from_db()
        self.assertEqual(arrival.status, VendorArrival.Status.ON_TIME)

    def test_late_arrival_after_grace(self):
        arrival = self.new_checkin(expected_in_minutes=-30, grace=10)
        APIClient().post(f"/api/public/checkin/{arrival.check_in_code}/arrive/")
        arrival.refresh_from_db()
        self.assertEqual(arrival.status, VendorArrival.Status.LATE)

    def test_arriving_twice_keeps_first_time(self):
        arrival = self.new_checkin(expected_in_minutes=5)
        anonymous = APIClient()
        url = f"/api/public/checkin/{arrival.check_in_code}/arrive/"
        anonymous.post(url)
        arrival.refresh_from_db()
        first = arrival.arrived_at
        again = anonymous.post(url)
        self.assertEqual(again.status_code, 200)
        self.assertTrue(again.data["already_arrived"])
        arrival.refresh_from_db()
        self.assertEqual(arrival.arrived_at, first)

    def test_scheduler_marks_late_and_alerts_exactly_once(self):
        late = self.new_checkin(expected_in_minutes=-30, grace=10)
        fine = self.new_checkin(expected_in_minutes=30)
        self.assertEqual(mark_late_vendors(), 1)
        late.refresh_from_db(), fine.refresh_from_db()
        self.assertEqual(late.status, VendorArrival.Status.LATE)
        self.assertIsNotNone(late.late_alert_sent_at)
        self.assertEqual(fine.status, VendorArrival.Status.PENDING)
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.get()
        self.assertIn("Royal Caterers is late", notification.message)
        self.assertEqual((notification.channel, notification.severity), ("both", "warning"))

    def test_second_scheduler_run_sends_nothing(self):
        self.new_checkin(expected_in_minutes=-30, grace=10)
        mark_late_vendors()
        self.assertEqual(mark_late_vendors(), 0)
        self.assertEqual(Notification.objects.count(), 1)

    def test_alert_already_claimed_is_not_sent_again(self):
        arrival = self.new_checkin(expected_in_minutes=-30, grace=10)
        arrival.late_alert_sent_at = timezone.now()
        arrival.save()
        self.assertEqual(eventday.mark_late_arrivals(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_planner_can_mark_arrived_manually(self):
        arrival = self.new_checkin(expected_in_minutes=-30, grace=10)
        self.client.force_authenticate(self.planner)
        res = self.client.patch(f"/api/checkins/{arrival.id}/", {"arrived": True}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "LATE")
        self.assertGreaterEqual(res.data["delay_minutes"], 29)
        self.assertIsNotNone(res.data["actual_arrival"])

    def test_create_checkin_returns_public_path(self):
        self.client.force_authenticate(self.planner)
        res = self.client.post(f"/api/weddings/{self.wedding.id}/checkins/", dict(
            vendor_id=self.vendor.id, scheduled_arrival=(timezone.now() + timedelta(hours=1)).isoformat()),
            format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["public_path"], f"/checkin/{res.data['token']}")
        self.assertEqual(res.data["grace_minutes"], 15)

    def test_vendor_punctuality(self):
        APIClient().post(f"/api/public/checkin/{self.new_checkin(5).check_in_code}/arrive/")
        APIClient().post(f"/api/public/checkin/{self.new_checkin(-40, 10).check_in_code}/arrive/")
        self.new_checkin(60)  # still pending: not counted
        result = get_vendor_punctuality(self.vendor.id)
        self.assertEqual((result["total"], result["on_time"], result["late"]), (2, 1, 1))
        self.assertGreaterEqual(result["avg_delay_min"], 19)


class ScheduleTests(Base):
    def setUp(self):
        self.client.force_authenticate(self.planner)
        self.wedding = self.make_wedding()
        day = date(2027, 2, 10)
        self.function = WeddingFunction.objects.create(wedding=self.wedding, name="Sangeet",
                                                       starts_at=at(day, 18), ends_at=at(day, 23))
        self.day = day

    def post(self, title, start, end, **extra):
        return self.client.post(f"/api/functions/{self.function.id}/schedule/", dict(
            title=title, starts_at=at(self.day, *start).isoformat(), ends_at=at(self.day, *end).isoformat(),
            **extra), format="json")

    def test_times_are_validated(self):
        self.assertEqual(self.post("Backwards", (20, 0), (19, 0)).status_code, 400)
        self.assertEqual(self.post("Too early", (17, 0), (19, 0)).status_code, 400)
        self.assertEqual(self.post("Fine", (19, 0), (19, 30)).status_code, 201)

    def test_overlap_is_a_warning_not_an_error(self):
        self.post("Welcome", (19, 0), (20, 0), responsible=self.planner.id)
        res = self.post("Dance", (19, 30), (20, 30), responsible=self.planner.id)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.data["warnings"]), 1)
        listed = self.client.get(f"/api/functions/{self.function.id}/schedule/").data
        self.assertEqual([i["title"] for i in listed], ["Welcome", "Dance"])
        self.assertEqual(ScheduleItem.objects.count(), 2)
