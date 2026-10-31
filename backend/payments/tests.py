from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from clients.models import Client
from dashboard.services import build_summary
from notifications.models import Notification
from payments import razorpay_client, services
from payments.jobs import remind_due_payments
from payments.models import Expense, Invoice, Payment, PayStatus
from vendors.models import Vendor, VendorCategory
from weddings.models import Wedding

R = 100  # paise per rupee


class FinanceTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)
        client = Client.objects.create(couple_name="A & B", phone="9812345670")
        start = timezone.localdate() + timedelta(days=60)
        cls.wedding = Wedding.objects.create(
            title="A & B", client=client, start_date=start, end_date=start, city="Jaipur", guest_count=450,
            contracted_guests=400, per_guest_rate_paise=2500 * R, budget_paise=4_000_000 * R)
        cls.vendor = Vendor.objects.create(name="Rasoi Royale", category=VendorCategory.objects.get(name="Caterer"))

    def setUp(self):
        self.client.force_authenticate(self.planner)

    def invoice(self, amount=100_000, kind="DEPOSIT"):
        return Invoice.objects.create(wedding=self.wedding, client=self.wedding.client, kind=kind,
                                      amount_paise=amount * R)

    def expense(self, amount=100_000, **extra):
        return Expense.objects.create(wedding=self.wedding, vendor=self.vendor, category="Caterer",
                                      description="Catering", amount_paise=amount * R, **extra)

    def pay_invoice(self, invoice, amount, key=None, method="UPI"):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return self.client.post(f"/api/invoices/{invoice.pk}/payments/",
                                {"amount_paise": amount * R, "method": method}, format="json", **headers)

    def pay_expense(self, expense, amount, key=None):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return self.client.post(f"/api/expenses/{expense.pk}/payments/",
                                {"amount_paise": amount * R, "method": "BANK"}, format="json", **headers)


class StatusTests(FinanceTestCase):
    def test_invoice_status_follows_the_payments(self):
        invoice = self.invoice(100_000)
        self.assertEqual(invoice.status, PayStatus.UNPAID)
        self.pay_invoice(invoice, 40_000)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PayStatus.PARTIAL)
        self.pay_invoice(invoice, 60_000)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PayStatus.PAID)

    def test_lowering_an_invoice_to_what_is_paid_makes_it_paid(self):
        invoice = self.invoice(100_000)
        self.pay_invoice(invoice, 40_000)
        res = self.client.patch(f"/api/invoices/{invoice.pk}/", {"amount_paise": 40_000 * R}, format="json")
        self.assertEqual((res.status_code, res.data["status"]), (200, "PAID"))
        low = self.client.patch(f"/api/invoices/{invoice.pk}/", {"amount_paise": 10_000 * R}, format="json")
        self.assertEqual(low.status_code, 409)

    def test_derive_status_uses_whole_paise(self):
        self.assertEqual(services.derive_status(0, 5), PayStatus.UNPAID)
        self.assertEqual(services.derive_status(1, 5), PayStatus.PARTIAL)
        self.assertEqual(services.derive_status(5, 5), PayStatus.PAID)


class OverpaymentTests(FinanceTestCase):
    def test_client_payment_above_the_balance_is_rejected(self):
        invoice = self.invoice(100_000)
        self.pay_invoice(invoice, 70_000)
        res = self.pay_invoice(invoice, 30_001)
        self.assertEqual(res.status_code, 409)
        self.assertIn("Overpayment", res.data["detail"])
        self.assertEqual(Payment.objects.filter(invoice=invoice).count(), 1)
        self.assertEqual(self.pay_invoice(invoice, 30_000).status_code, 201)

    def test_vendor_payment_above_the_balance_is_rejected(self):
        expense = self.expense(100_000)
        self.assertEqual(self.pay_expense(expense, 100_001).status_code, 409)
        self.assertEqual(Payment.objects.count(), 0)

    def test_zero_and_unknown_methods_are_rejected(self):
        invoice = self.invoice()
        self.assertEqual(self.client.post(f"/api/invoices/{invoice.pk}/payments/",
                                          {"amount_paise": 0, "method": "UPI"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(f"/api/invoices/{invoice.pk}/payments/",
                                          {"amount_paise": 100, "method": "BITCOIN"}, format="json").status_code, 400)

    def test_staff_can_look_but_not_pay(self):
        invoice = self.invoice()
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(f"/api/weddings/{self.wedding.pk}/invoices/").status_code, 200)
        self.assertEqual(self.pay_invoice(invoice, 1000).status_code, 403)


class DuplicateBillTests(FinanceTestCase):
    def post_bill(self, **extra):
        body = {"vendor_id": self.vendor.pk, "category": "Caterer", "description": "Catering",
                "amount_paise": 50_000 * R, **extra}
        return self.client.post(f"/api/weddings/{self.wedding.pk}/expenses/", body, format="json")

    def test_same_vendor_and_bill_reference_is_rejected(self):
        self.assertEqual(self.post_bill(bill_ref="INV-1").status_code, 201)
        res = self.post_bill(bill_ref="INV-1")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["detail"], "This bill reference already exists for this vendor")
        self.assertEqual(Expense.objects.count(), 1)

    def test_same_reference_for_another_vendor_is_fine(self):
        other = Vendor.objects.create(name="Spice Route", category=self.vendor.category)
        self.post_bill(bill_ref="INV-1")
        res = self.client.post(f"/api/weddings/{self.wedding.pk}/expenses/", {
            "vendor_id": other.pk, "category": "Caterer", "description": "x", "amount_paise": 100,
            "bill_ref": "INV-1"}, format="json")
        self.assertEqual(res.status_code, 201)

    def test_editing_into_a_duplicate_reference_is_rejected(self):
        self.post_bill(bill_ref="INV-1")
        second = self.post_bill(bill_ref="INV-2").data["id"]
        res = self.client.patch(f"/api/expenses/{second}/", {"bill_ref": "INV-1"}, format="json")
        self.assertEqual(res.status_code, 409)

    def test_same_vendor_and_amount_due_within_a_week_adds_a_warning(self):
        due = timezone.localdate() + timedelta(days=10)
        first = self.post_bill(bill_ref="A", due_date=due.isoformat())
        near = self.post_bill(bill_ref="B", due_date=(due + timedelta(days=5)).isoformat())
        far = self.post_bill(bill_ref="C", due_date=(due + timedelta(days=30)).isoformat())
        self.assertEqual(first.data["warnings"], [])
        self.assertEqual(len(near.data["warnings"]), 1)
        self.assertEqual(far.data["warnings"], [])

    def test_a_bill_with_payments_cannot_be_deleted(self):
        expense = self.expense()
        self.pay_expense(expense, 1000)
        self.assertEqual(self.client.delete(f"/api/expenses/{expense.pk}/").status_code, 409)
        other = self.expense()
        self.assertEqual(self.client.delete(f"/api/expenses/{other.pk}/").status_code, 204)


class IdempotencyTests(FinanceTestCase):
    def test_replayed_key_returns_the_original_payment(self):
        expense = self.expense(100_000)
        first = self.pay_expense(expense, 30_000, key="abc-123")
        again = self.pay_expense(expense, 30_000, key="abc-123")
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(first.data["id"], again.data["id"])
        self.assertEqual(Payment.objects.count(), 1)
        expense.refresh_from_db()
        self.assertEqual(expense.status, PayStatus.PARTIAL)

    def test_same_key_for_a_different_bill_is_refused(self):
        a, b = self.expense(), self.expense()
        self.pay_expense(a, 1000, key="k1")
        self.assertEqual(self.pay_expense(b, 1000, key="k1").status_code, 409)

    def test_different_keys_make_separate_payments(self):
        expense = self.expense(100_000)
        self.pay_expense(expense, 10_000, key="k1")
        self.pay_expense(expense, 10_000, key="k2")
        self.assertEqual(Payment.objects.count(), 2)

    def test_replay_does_not_trip_the_overpayment_check(self):
        invoice = self.invoice(100_000)
        self.pay_invoice(invoice, 100_000, key="full")
        self.assertEqual(self.pay_invoice(invoice, 100_000, key="full").status_code, 200)


class ExtraGuestTests(FinanceTestCase):
    def post(self, guests, **extra):
        return self.client.post(f"/api/weddings/{self.wedding.pk}/invoices/extra-guests/",
                                {"actual_guests": guests, **extra}, format="json")

    def test_charges_the_guests_above_the_contract(self):
        res = self.post(450)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["amount_paise"], 50 * 2500 * R)
        self.assertEqual(res.data["type"], "EXTRA_GUESTS")
        self.assertIn("50 extra guests", res.data["note"])

    def test_no_extra_guests_is_unprocessable(self):
        for guests in (400, 350):
            res = self.post(guests)
            self.assertEqual(res.status_code, 422)
            self.assertIn("No extra guests", res.data["detail"])
        self.assertEqual(Invoice.objects.count(), 0)

    def test_preview_shows_the_amount_without_saving(self):
        res = self.post(410, preview=True)
        self.assertEqual((res.status_code, res.data["amount_paise"], res.data["extra_guests"]),
                         (200, 10 * 2500 * R, 10))
        self.assertEqual(Invoice.objects.count(), 0)


class MilestoneTests(FinanceTestCase):
    def test_instalments_add_up_to_the_total_with_the_remainder_in_the_final(self):
        for total in (100_001, 333_333, 1, 999_999):
            expense = services.create_planned_expense(wedding=self.wedding, vendor=self.vendor, category="Caterer",
                                                      amount_paise=total)
            advance, final = services.create_milestones(wedding=self.wedding, vendor=self.vendor, expense=expense,
                                                        total_paise=total, advance_pct=30)
            self.assertEqual(advance.amount_paise + final.amount_paise, total)
            self.assertEqual(advance.amount_paise, total * 30 // 100)
            self.assertEqual(final.amount_paise, total - advance.amount_paise)

    def test_paying_each_instalment_updates_its_status_and_the_bill(self):
        expense = services.create_planned_expense(wedding=self.wedding, vendor=self.vendor, category="Caterer",
                                                  amount_paise=1000 * R)
        advance, final = services.create_milestones(wedding=self.wedding, vendor=self.vendor, expense=expense,
                                                    total_paise=1000 * R, advance_pct=30)
        res = self.client.post(f"/api/milestones/{advance.pk}/pay/", {"method": "BANK"}, format="json")
        self.assertEqual((res.status_code, res.data["amount_paise"]), (201, 300 * R))
        advance.refresh_from_db(), final.refresh_from_db(), expense.refresh_from_db()
        self.assertEqual((advance.status, final.status, expense.status), ("PAID", "UNPAID", "PARTIAL"))
        again = self.client.post(f"/api/milestones/{advance.pk}/pay/", {"method": "BANK"}, format="json")
        self.assertEqual(again.status_code, 409)  # nothing left of the advance
        self.client.post(f"/api/milestones/{final.pk}/pay/", {"method": "BANK"}, format="json")
        expense.refresh_from_db()
        self.assertEqual(expense.status, "PAID")

    def test_milestone_list_shows_what_was_paid(self):
        expense = services.create_planned_expense(wedding=self.wedding, vendor=self.vendor, category="Caterer",
                                                  amount_paise=1000 * R)
        advance, _ = services.create_milestones(wedding=self.wedding, vendor=self.vendor, expense=expense,
                                                total_paise=1000 * R)
        services.pay_milestone(advance.pk)
        rows = self.client.get(f"/api/weddings/{self.wedding.pk}/milestones/").data
        self.assertEqual([(r["part"], r["paid_paise"], r["remaining_paise"]) for r in rows],
                         [("ADVANCE", 300 * R, 0), ("FINAL", 0, 700 * R)])


class FinancialsTests(FinanceTestCase):
    def test_profit_is_whole_paise_and_matches_the_dashboard(self):
        invoice = self.invoice(1_000_001)  # odd amounts must stay exact
        self.pay_invoice(invoice, 600_001)
        paid_bill = self.expense(300_001)
        self.pay_expense(paid_bill, 100_000)
        data = services.get_wedding_financials(self.wedding.pk)
        self.assertEqual(data["revenue"], {"invoiced": 1_000_001 * R, "received": 600_001 * R,
                                           "outstanding": 400_000 * R})
        self.assertEqual(data["expenses"], {"planned": 300_001 * R, "paid": 100_000 * R, "outstanding": 200_001 * R})
        self.assertEqual(data["estimated_profit"], 700_000 * R)
        self.assertEqual(data["actual_profit"], 500_001 * R)
        self.assertEqual(data["margin_pct"], 70.0)
        self.assertEqual(data["by_category"], [{"category": "Caterer", "planned": 300_001 * R, "paid": 100_000 * R}])
        for value in (data["estimated_profit"], data["actual_profit"]):
            self.assertIsInstance(value, int)
        row = next(r for r in build_summary()["per_wedding"] if r["wedding_id"] == self.wedding.pk)
        self.assertEqual(row["profit_paise"], data["estimated_profit"])

    def test_wedding_with_no_invoices_has_zero_margin_not_an_error(self):
        data = services.get_wedding_financials(self.wedding.pk)
        self.assertEqual((data["estimated_profit"], data["margin_pct"]), (0, 0))

    def test_upcoming_payments_are_in_due_order_with_overdue_flag(self):
        today = timezone.localdate()
        late = self.expense(1000, due_date=today - timedelta(days=2))
        soon = self.expense(2000, due_date=today + timedelta(days=3))
        self.expense(3000, due_date=today + timedelta(days=40))  # outside the window
        paid = self.expense(4000, due_date=today)
        self.pay_expense(paid, 4000)
        rows = self.client.get("/api/finance/upcoming-payments/?days=14").data
        self.assertEqual([r["id"] for r in rows], [late.pk, soon.pk])
        self.assertEqual([r["overdue"] for r in rows], [True, False])

    def test_overview_lists_every_wedding(self):
        self.invoice(1000)
        res = self.client.get("/api/finance/overview/").data
        self.assertEqual(res["weddings"][0]["invoiced_paise"], 1000 * R)
        self.assertEqual(res["totals"]["invoiced_paise"], 1000 * R)


@override_settings(MOCK_EXTERNALS=True)
class RazorpayTests(FinanceTestCase):
    def order(self, invoice):
        return self.client.post(f"/api/invoices/{invoice.pk}/razorpay/order/").data

    def verify(self, invoice, order, **override):
        body = {"razorpay_order_id": order["order_id"], "razorpay_payment_id": order["mock_payment_id"],
                "razorpay_signature": order["mock_signature"], **override}
        return self.client.post(f"/api/invoices/{invoice.pk}/razorpay/verify/", body, format="json")

    def test_order_is_for_the_remaining_balance(self):
        invoice = self.invoice(100_000)
        self.pay_invoice(invoice, 25_000)
        order = self.order(invoice)
        self.assertEqual((order["amount"], order["currency"], order["mock"]), (75_000 * R, "INR", True))

    def test_verifying_twice_records_exactly_one_payment(self):
        invoice = self.invoice(100_000)
        order = self.order(invoice)
        first, second = self.verify(invoice, order), self.verify(invoice, order)
        self.assertEqual((first.status_code, second.status_code), (201, 200))
        self.assertEqual(first.data["id"], second.data["id"])
        payment = Payment.objects.get()
        self.assertEqual((payment.method, payment.reference, payment.amount_paise),
                         ("RAZORPAY", order["mock_payment_id"], 100_000 * R))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, PayStatus.PAID)

    def test_tampered_signature_is_rejected_and_records_nothing(self):
        invoice = self.invoice(100_000)
        order = self.order(invoice)
        res = self.verify(invoice, order, razorpay_signature="0" * 64)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)

    def test_a_signature_for_a_different_payment_id_is_rejected(self):
        invoice = self.invoice(100_000)
        order = self.order(invoice)
        self.assertEqual(self.verify(invoice, order, razorpay_payment_id="pay_other").status_code, 400)

    def test_an_order_for_another_invoice_cannot_pay_this_one(self):
        mine, other = self.invoice(100_000), self.invoice(100_000)
        order = self.order(other)
        res = self.verify(mine, order)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)

    def test_signature_check_accepts_valid_and_rejects_tampered(self):
        good = razorpay_client.sign("order_1", "pay_1")
        self.assertTrue(razorpay_client.verify_signature("order_1", "pay_1", good))
        self.assertFalse(razorpay_client.verify_signature("order_1", "pay_1", good[:-1] + ("0" if good[-1] != "0" else "1")))
        self.assertFalse(razorpay_client.verify_signature("order_2", "pay_1", good))
        self.assertFalse(razorpay_client.verify_signature("order_1", "pay_1", ""))

    def test_paid_invoice_cannot_start_another_order(self):
        invoice = self.invoice(1000)
        self.pay_invoice(invoice, 1000)
        self.assertEqual(self.client.post(f"/api/invoices/{invoice.pk}/razorpay/order/").status_code, 409)


class ReminderJobTests(FinanceTestCase):
    def test_one_alert_per_item_per_day_for_late_and_due_soon_bills(self):
        today = timezone.localdate()
        self.expense(1000, due_date=today - timedelta(days=1))
        self.expense(2000, due_date=today + timedelta(days=2))
        self.expense(3000, due_date=today + timedelta(days=20))
        self.assertEqual(remind_due_payments(today), 2)
        self.assertEqual(remind_due_payments(today), 0)  # same day: nothing new
        self.assertEqual(remind_due_payments(today + timedelta(days=1)), 2)  # next day: reminded again
        severities = set(Notification.objects.values_list("severity", flat=True))
        self.assertEqual(severities, {"critical", "warning"})
