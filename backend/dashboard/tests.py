from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from clients.models import Client
from payments.models import Expense, Invoice, Payment
from tasks.models import Task
from weddings.models import Wedding


class DashboardTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.founder = User.objects.create_user("f@t.com", "Founder", "Password123", role=Role.FOUNDER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)
        couple = Client.objects.create(couple_name="Aarav & Meera", phone="9876543210")
        cls.wedding = Wedding.objects.create(
            title="Aarav & Meera", client=couple, start_date=date.today() + timedelta(days=60),
            end_date=date.today() + timedelta(days=62), city="Jaipur", guest_count=450, contracted_guests=450)
        invoice = Invoice.objects.create(wedding=cls.wedding, client=couple, kind="DEPOSIT", amount_paise=1000_00)
        Payment.objects.create(wedding=cls.wedding, invoice=invoice, direction="IN", amount_paise=400_00,
                               method="UPI")
        bill = Expense.objects.create(wedding=cls.wedding, category="Catering", description="Caterer advance",
                                      amount_paise=600_00, due_date=timezone.localdate() + timedelta(days=2))
        Payment.objects.create(wedding=cls.wedding, expense=bill, direction="OUT", amount_paise=100_00,
                               method="BANK")
        Task.objects.create(wedding=cls.wedding, title="Book venue", stage="DONE")
        Task.objects.create(wedding=cls.wedding, title="Book DJ", stage="TO_PLAN")

    def test_totals_match_the_wedding_rows(self):
        self.client.force_authenticate(self.founder)
        data = self.client.get("/api/dashboard/summary/").data
        self.assertEqual(data["total_revenue_paise"], 1000_00)
        self.assertEqual(data["total_expenses_paise"], 600_00)
        self.assertEqual(data["total_profit_paise"], 400_00)
        self.assertEqual(data["outstanding_client_paise"], 600_00)
        self.assertEqual(sum(r["profit_paise"] for r in data["per_wedding"]), data["total_profit_paise"])
        row = data["per_wedding"][0]
        self.assertEqual((row["margin_pct"], row["progress_pct"]), (40.0, 50))

    def test_counts_and_activity_feed(self):
        self.client.force_authenticate(self.founder)
        data = self.client.get("/api/dashboard/summary/").data
        self.assertEqual((data["total_weddings"], data["ongoing_weddings"]), (1, 1))
        self.assertEqual((data["open_tasks"], data["overdue_tasks"]), (1, 0))
        self.assertTrue(any(item["kind"] == "payment" for item in data["recent_activity"]))

    def test_upcoming_vendor_payment_shows_only_what_is_still_owed(self):
        self.client.force_authenticate(self.founder)
        bills = self.client.get("/api/dashboard/summary/").data["upcoming_vendor_payments"]
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills[0]["outstanding_paise"], 500_00)
        self.assertFalse(bills[0]["overdue"])

    def test_staff_cannot_open_the_dashboard(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/dashboard/summary/").status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/dashboard/summary/").status_code, 401)
