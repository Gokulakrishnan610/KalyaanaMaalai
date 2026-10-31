from datetime import date, timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import Role, User
from clients.models import Client
from notifications.models import Notification
from payments import razorpay_client
from payments.models import Expense, Invoice, Payment, PaymentLink, VendorPaymentPlan
from vendors.models import Vendor, VendorCategory
from weddings.models import Wedding

R = 100  # paise per rupee


class Base(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.founder = User.objects.create_user("f@t.com", "Founder", "Password123", role=Role.FOUNDER)
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)
        cls.couple = Client.objects.create(couple_name="Aarav & Meera", phone="9876543210")
        cls.wedding = Wedding.objects.create(
            title="Aarav & Meera - Jaipur", client=cls.couple, start_date=date.today() + timedelta(days=60),
            end_date=date.today() + timedelta(days=62), city="Jaipur", guest_count=100, contracted_guests=100)

    def setUp(self):
        self.invoice = Invoice.objects.create(wedding=self.wedding, client=self.couple, kind="MILESTONE",
                                              amount_paise=100_000 * R, due_date=date.today() + timedelta(days=10))
        self.client.force_authenticate(self.planner)

    def pay_offline(self, rupees, **extra):
        return self.client.post(f"/api/invoices/{self.invoice.pk}/payments/",
                                {"amount_paise": rupees * R, "method": "UPI", **extra}, format="json")

    def make_link(self, **body):
        return self.client.post(f"/api/invoices/{self.invoice.pk}/payment-links/", body, format="json")


class OfflinePaymentRulesTests(Base):
    def test_cheque_is_an_offline_method(self):
        self.assertEqual(self.pay_offline(1000, method="CHEQUE", reference="000123").status_code, 201)

    def test_nobody_can_type_in_an_online_payment(self):
        res = self.client.post(f"/api/invoices/{self.invoice.pk}/payments/",
                               {"amount_paise": 100 * R, "method": "RAZORPAY", "reference": "fake"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)

    def test_a_payment_cannot_be_dated_in_the_future(self):
        future = (timezone.now() + timedelta(days=30)).isoformat()
        self.assertEqual(self.pay_offline(1000, paid_at=future).status_code, 400)

    def test_who_recorded_an_offline_payment_is_kept(self):
        self.pay_offline(1000)
        self.assertEqual(Payment.objects.get().recorded_by, self.planner)

    def test_only_one_booking_deposit_per_wedding(self):
        body = {"type": "DEPOSIT", "amount_paise": 500 * R}
        self.assertEqual(self.client.post(f"/api/weddings/{self.wedding.pk}/invoices/", body, format="json").status_code, 201)
        self.assertEqual(self.client.post(f"/api/weddings/{self.wedding.pk}/invoices/", body, format="json").status_code, 409)

    def test_an_invoice_made_by_mistake_can_be_deleted_until_it_has_payments(self):
        spare = Invoice.objects.create(wedding=self.wedding, client=self.couple, kind="FINAL", amount_paise=500 * R)
        self.assertEqual(self.client.delete(f"/api/invoices/{spare.pk}/").status_code, 204)
        self.pay_offline(1000)
        self.assertEqual(self.client.delete(f"/api/invoices/{self.invoice.pk}/").status_code, 409)

    def test_staff_cannot_delete_invoices_or_undo_payments(self):
        self.pay_offline(1000)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.delete(f"/api/invoices/{self.invoice.pk}/").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/payments/{Payment.objects.get().pk}/").status_code, 403)


class UndoPaymentTests(Base):
    def test_undoing_a_payment_puts_the_balance_back_and_tells_the_founder(self):
        self.pay_offline(100_000)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")
        res = self.client.delete(f"/api/payments/{Payment.objects.get().pk}/")
        self.assertEqual(res.status_code, 204)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "UNPAID")
        alert = Notification.objects.get(user=self.founder)
        self.assertIn("was removed by Planner", alert.message)

    def test_undoing_a_vendor_payment_restores_the_bill_and_instalments(self):
        vendor = Vendor.objects.create(name="Rasoi Royale", category=VendorCategory.objects.get_or_create(name="Caterer")[0])
        expense = Expense.objects.create(wedding=self.wedding, vendor=vendor, category="Caterer", description="Catering",
                                         amount_paise=100_000 * R)
        plan = VendorPaymentPlan.objects.create(wedding=self.wedding, vendor=vendor, part="ADVANCE",
                                                amount_paise=30_000 * R, expense=expense)
        self.client.post(f"/api/milestones/{plan.pk}/pay/", {"method": "BANK"}, format="json")
        plan.refresh_from_db()
        self.assertEqual(plan.status, "PAID")
        self.client.delete(f"/api/payments/{Payment.objects.get().pk}/")
        plan.refresh_from_db()
        expense.refresh_from_db()
        self.assertEqual((plan.status, expense.status), ("UNPAID", "UNPAID"))

    def test_an_online_payment_cannot_be_undone(self):
        online = Payment.objects.create(wedding=self.wedding, invoice=self.invoice, direction="IN",
                                        amount_paise=1000 * R, method="RAZORPAY", reference="pay_x")
        self.assertEqual(self.client.delete(f"/api/payments/{online.pk}/").status_code, 409)


class CreatePaymentLinkTests(Base):
    def test_a_link_defaults_to_everything_still_owed(self):
        self.pay_offline(40_000)
        res = self.make_link()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["amount_paise"], 60_000 * R)
        self.assertEqual(res.data["status"], "ACTIVE")
        self.assertTrue(res.data["path"].startswith("/pay/"))
        self.assertGreater(len(res.data["token"]), 30)

    def test_a_link_can_ask_for_a_smaller_amount_but_never_more_than_owed(self):
        self.assertEqual(self.make_link(amount_paise=25_000 * R).data["amount_paise"], 25_000 * R)
        self.assertEqual(self.make_link(amount_paise=999_000 * R).status_code, 409)
        self.assertEqual(self.make_link(amount_paise=0).status_code, 400)

    def test_no_link_for_an_invoice_that_is_already_paid(self):
        self.pay_offline(100_000)
        self.assertEqual(self.make_link().status_code, 409)

    def test_staff_cannot_create_or_cancel_links_but_can_look(self):
        link_id = self.make_link().data["id"]
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.make_link().status_code, 403)
        self.assertEqual(self.client.post(f"/api/payment-links/{link_id}/cancel/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/invoices/{self.invoice.pk}/payment-links/").status_code, 200)

    def test_a_cancelled_link_stops_working(self):
        link = self.make_link().data
        self.assertEqual(self.client.post(f"/api/payment-links/{link['id']}/cancel/").data["status"], "CANCELLED")
        self.assertEqual(APIClient().get(f"/api/pay/{link['token']}/").data["status"], "CANCELLED")


@override_settings(ALLOW_DEMO_PAYMENTS=True)
class CustomerPaysThroughTheLinkTests(Base):
    """The customer is not logged in: everything below uses an anonymous client."""

    def setUp(self):
        super().setUp()
        self.link = self.make_link().data
        self.customer = APIClient()
        self.url = f"/api/pay/{self.link['token']}/"

    def pay(self):
        order = self.customer.post(self.url + "order/").data
        return order, self.customer.post(self.url + "verify/", {
            "razorpay_order_id": order["order_id"], "razorpay_payment_id": order["mock_payment_id"],
            "razorpay_signature": order["mock_signature"]}, format="json")

    def test_the_page_shows_the_amount_and_nothing_private(self):
        data = self.customer.get(self.url).data
        self.assertEqual((data["amount_paise"], data["couple"], data["status"]), (100_000 * R, "Aarav & Meera", "ACTIVE"))
        self.assertEqual(data["for"], "Instalment")
        private = {"id", "invoice_id", "client_phone", "client_email", "token", "created_by_name", "budget_paise"}
        self.assertFalse(private & set(data))

    def test_an_unknown_link_is_not_found(self):
        self.assertEqual(self.customer.get("/api/pay/not-a-real-token/").status_code, 404)

    def test_paying_records_the_payment_and_marks_everything_paid_with_no_manual_step(self):
        order, res = self.pay()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "PAID")
        self.assertTrue(res.data["receipt"]["number"].startswith("RCPT-"))
        payment = Payment.objects.get()
        self.assertEqual((payment.method, payment.amount_paise, payment.direction), ("RAZORPAY", 100_000 * R, "IN"))
        self.assertIsNone(payment.recorded_by)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")
        self.assertEqual(PaymentLink.objects.get().status, "PAID")

    def test_paying_twice_records_it_once(self):
        order, first = self.pay()
        again = self.customer.post(self.url + "verify/", {
            "razorpay_order_id": order["order_id"], "razorpay_payment_id": order["mock_payment_id"],
            "razorpay_signature": order["mock_signature"]}, format="json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(Payment.objects.count(), 1)

    def test_a_paid_link_cannot_start_another_payment(self):
        self.pay()
        self.assertEqual(self.customer.post(self.url + "order/").status_code, 409)

    def test_a_forged_confirmation_records_nothing(self):
        order = self.customer.post(self.url + "order/").data
        res = self.customer.post(self.url + "verify/", {
            "razorpay_order_id": order["order_id"], "razorpay_payment_id": order["mock_payment_id"],
            "razorpay_signature": "0" * 64}, format="json")
        self.assertEqual(res.status_code, 422)
        self.assertEqual(Payment.objects.count(), 0)

    def test_a_confirmation_for_some_other_order_is_refused(self):
        self.customer.post(self.url + "order/")
        other_order = razorpay_client.create_order(100_000 * R, self.invoice.pk)  # a genuine order, but not this link's
        res = self.customer.post(self.url + "verify/", {
            "razorpay_order_id": other_order["order_id"], "razorpay_payment_id": other_order["mock_payment_id"],
            "razorpay_signature": other_order["mock_signature"]}, format="json")
        self.assertEqual(res.status_code, 422)
        self.assertEqual(Payment.objects.count(), 0)

    def test_an_expired_link_cannot_be_paid(self):
        PaymentLink.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.customer.get(self.url).data["status"], "EXPIRED")
        self.assertEqual(self.customer.post(self.url + "order/").status_code, 409)

    def test_the_amount_shrinks_if_part_of_it_is_paid_in_cash_meanwhile(self):
        self.pay_offline(30_000)
        self.assertEqual(self.customer.get(self.url).data["amount_paise"], 70_000 * R)
        order, res = self.pay()
        self.assertEqual(Payment.objects.get(method="RAZORPAY").amount_paise, 70_000 * R)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")

    def test_a_link_for_an_invoice_settled_in_cash_says_so(self):
        self.pay_offline(100_000)
        self.assertEqual(self.customer.get(self.url).data["status"], "SETTLED")
        self.assertEqual(self.customer.post(self.url + "order/").status_code, 409)

    def test_if_cash_arrives_after_the_customer_started_paying_the_founder_is_told_to_refund(self):
        order = self.customer.post(self.url + "order/").data
        self.pay_offline(100_000)  # cash is recorded while the customer is at the payment screen
        res = self.customer.post(self.url + "verify/", {
            "razorpay_order_id": order["order_id"], "razorpay_payment_id": order["mock_payment_id"],
            "razorpay_signature": order["mock_signature"]}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertTrue(Notification.objects.filter(user=self.founder, message__startswith="REFUND NEEDED").exists())

    def test_a_part_payment_link_leaves_the_rest_to_collect(self):
        small = self.make_link(amount_paise=25_000 * R).data
        order = self.customer.post(f"/api/pay/{small['token']}/order/").data
        self.customer.post(f"/api/pay/{small['token']}/verify/", {
            "razorpay_order_id": order["order_id"], "razorpay_payment_id": order["mock_payment_id"],
            "razorpay_signature": order["mock_signature"]}, format="json")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PARTIAL")
        self.assertEqual(self.customer.get(self.url).data["amount_paise"], 75_000 * R)

    def test_the_planner_sees_the_link_as_paid_and_the_ledger_marks_it(self):
        self.pay()
        links = self.client.get(f"/api/invoices/{self.invoice.pk}/payment-links/").data
        self.assertEqual(links[0]["status"], "PAID")
        ledger = self.client.get("/api/payments/").data["results"][0]
        self.assertEqual((ledger["source"], ledger["party"], ledger["can_undo"]), ("LINK", "Aarav & Meera", False))


class DemoCheckoutSafetyTests(Base):
    def test_the_fake_checkout_is_off_unless_it_is_dev_or_switched_on(self):
        link = self.make_link().data
        customer = APIClient()
        self.assertFalse(customer.get(f"/api/pay/{link['token']}/").data["available"])
        self.assertEqual(customer.post(f"/api/pay/{link['token']}/order/").status_code, 422)  # tests run with DEBUG off


class ListsForThePaymentsPageTests(Base):
    def test_all_invoices_with_filters_and_customer_details(self):
        paid = Invoice.objects.create(wedding=self.wedding, client=self.couple, kind="DEPOSIT", amount_paise=500 * R,
                                      status="PAID")
        late = Invoice.objects.create(wedding=self.wedding, client=self.couple, kind="FINAL", amount_paise=900 * R,
                                      due_date=date.today() - timedelta(days=3))
        self.make_link()
        everything = self.client.get("/api/invoices/").data
        self.assertEqual(len(everything), 3)
        row = next(r for r in everything if r["id"] == self.invoice.pk)
        self.assertEqual((row["client_name"], row["client_phone"], row["link"]["status"]), ("Aarav & Meera", "9876543210", "ACTIVE"))
        self.assertEqual([r["id"] for r in self.client.get("/api/invoices/?status=overdue").data], [late.pk])
        self.assertEqual([r["id"] for r in self.client.get("/api/invoices/?status=paid").data], [paid.pk])
        self.assertEqual(len(self.client.get("/api/invoices/?status=open").data), 2)
        self.assertEqual(len(self.client.get(f"/api/invoices/?wedding={self.wedding.pk + 99}").data), 0)

    def test_vendor_bills_come_with_their_instalments(self):
        vendor = Vendor.objects.create(name="Spice Route", category=VendorCategory.objects.get_or_create(name="Caterer")[0])
        expense = Expense.objects.create(wedding=self.wedding, vendor=vendor, category="Caterer", description="Catering",
                                         amount_paise=100_000 * R)
        VendorPaymentPlan.objects.create(wedding=self.wedding, vendor=vendor, part="ADVANCE", amount_paise=30_000 * R, expense=expense)
        VendorPaymentPlan.objects.create(wedding=self.wedding, vendor=vendor, part="FINAL", amount_paise=70_000 * R, expense=expense)
        bills = self.client.get(f"/api/finance/vendor-bills/?wedding={self.wedding.pk}").data
        self.assertEqual([i["part"] for i in bills[0]["instalments"]], ["ADVANCE", "FINAL"])
        self.assertEqual(bills[0]["wedding_title"], "Aarav & Meera - Jaipur")

    def test_the_ledger_lists_manual_payments_with_who_recorded_them_and_filters_by_direction(self):
        self.pay_offline(5000, reference="UTR9")
        vendor = Vendor.objects.create(name="DJ Raj", category=VendorCategory.objects.get_or_create(name="DJ & Sound")[0])
        expense = Expense.objects.create(wedding=self.wedding, vendor=vendor, category="DJ", description="DJ", amount_paise=9000 * R)
        self.client.post(f"/api/expenses/{expense.pk}/payments/", {"amount_paise": 3000 * R, "method": "CASH"}, format="json")
        everything = self.client.get("/api/payments/").data
        self.assertEqual(everything["count"], 2)
        incoming = self.client.get("/api/payments/?direction=IN").data["results"]
        self.assertEqual((incoming[0]["source"], incoming[0]["recorded_by_name"], incoming[0]["reference"]), ("MANUAL", "Planner", "UTR9"))
        outgoing = self.client.get("/api/payments/?direction=OUT").data["results"]
        self.assertEqual((outgoing[0]["party"], outgoing[0]["can_undo"]), ("DJ Raj", True))


class LedgerHidesInternalTagsTests(Base):
    def test_the_internal_instalment_tag_is_not_shown_as_a_reference(self):
        vendor = Vendor.objects.create(name="DJ Raj", category=VendorCategory.objects.get_or_create(name="DJ & Sound")[0])
        expense = Expense.objects.create(wedding=self.wedding, vendor=vendor, category="DJ", description="DJ", amount_paise=9000 * R)
        plan = VendorPaymentPlan.objects.create(wedding=self.wedding, vendor=vendor, part="ADVANCE", amount_paise=3000 * R, expense=expense)
        self.client.post(f"/api/milestones/{plan.pk}/pay/", {"method": "BANK"}, format="json")
        row = self.client.get("/api/payments/?direction=OUT").data["results"][0]
        self.assertEqual(row["reference"], "")
