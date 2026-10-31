from datetime import date, timedelta

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import Role, User
from enquiries.models import Enquiry
from notifications.models import Notification
from payments.models import Invoice, Payment
from portal.models import Customer

FUTURE = (date.today() + timedelta(days=120)).isoformat()
SIGNUP = {"name": "Meera", "email": "Meera@Example.com", "phone": "9876543210", "password": "Password123"}


class PortalTestCase(APITestCase):
    def setUp(self):
        cache.clear()  # the sign-up and login limit (20 a minute) counts in the cache, and tests make many of them
        super().setUp()


def signup(client=None, **extra):
    return (client or APIClient()).post("/api/portal/signup/", {**SIGNUP, **extra}, format="json")


def as_customer(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


class AccountTests(PortalTestCase):
    def test_signup_creates_the_account_and_a_crm_enquiry(self):
        res = signup()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["stage"]["key"], "NEW")
        enquiry = Enquiry.objects.get()
        self.assertEqual((enquiry.source, enquiry.status, enquiry.couple_name), ("WEBSITE", "NEW", "Meera"))
        self.assertEqual(Customer.objects.get().email, "meera@example.com")  # stored in lower case

    def test_the_password_is_stored_hashed(self):
        signup()
        customer = Customer.objects.get()
        self.assertNotIn("Password123", customer.password_hash)
        self.assertTrue(customer.check_password("Password123"))

    def test_bad_signups_are_refused(self):
        self.assertEqual(signup(password="short").status_code, 400)
        self.assertEqual(signup(phone="12345").status_code, 400)
        self.assertEqual(signup(name="   ").status_code, 400)
        signup()
        self.assertEqual(signup().status_code, 400)  # the same email again
        self.assertEqual(Customer.objects.count(), 1)

    def test_login_and_the_same_error_for_unknown_email_and_wrong_password(self):
        signup()
        good = APIClient().post("/api/portal/login/", {"email": "MEERA@example.com", "password": "Password123"}, format="json")
        self.assertEqual(good.status_code, 200)
        wrong = APIClient().post("/api/portal/login/", {"email": "meera@example.com", "password": "nope"}, format="json")
        unknown = APIClient().post("/api/portal/login/", {"email": "who@example.com", "password": "Password123"}, format="json")
        self.assertEqual((wrong.status_code, unknown.status_code), (400, 400))
        self.assertEqual(wrong.data, unknown.data)

    def test_me_needs_a_customer_login(self):
        self.assertEqual(APIClient().get("/api/portal/me/").status_code, 401)
        token = signup().data["token"]
        self.assertEqual(as_customer(token).get("/api/portal/me/").data["customer"]["name"], "Meera")


class TokenSeparationTests(PortalTestCase):
    """A customer must never reach staff data, and staff tokens do not work on the customer website."""

    def test_a_customer_token_is_refused_by_every_staff_screen(self):
        customer = as_customer(signup().data["token"])
        for url in ("/api/enquiries/", "/api/clients/", "/api/dashboard/summary/", "/api/users/", "/api/auth/me/",
                    "/api/payments/", "/api/invoices/", "/api/incidents/"):
            self.assertEqual(customer.get(url).status_code, 401, url)

    def test_a_staff_token_is_refused_on_the_customer_website(self):
        planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        token = APIClient().post("/api/auth/login/", {"email": "p@t.com", "password": "Password123"}, format="json").data["access"]
        self.assertEqual(as_customer(token).get("/api/portal/me/").status_code, 401)
        self.assertIsNotNone(planner)

    def test_a_forged_token_is_refused(self):
        self.assertEqual(as_customer("not.a.token").get("/api/portal/me/").status_code, 401)


@override_settings(LIVE_ALERTS=True)
class ProfileTests(PortalTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.founder = User.objects.create_user("f@t.com", "Founder", "Password123", role=Role.FOUNDER)
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)

    def setUp(self):
        super().setUp()
        self.token = signup().data["token"]
        self.me = as_customer(self.token)

    def full_profile(self):
        return {"partner_name": "Aarav", "wedding_date": FUTURE, "venue_city": "Jaipur", "guest_count": 450,
                "services_needed": ["CATERING", "DECOR"], "preferred_contact": "WHATSAPP"}

    def test_planners_are_told_about_a_new_sign_up(self):
        for user in (self.planner, self.founder):
            self.assertTrue(Notification.objects.filter(user=user, message__startswith="New website sign-up: Meera").exists())

    def test_the_profile_is_saved_step_by_step_and_the_percent_grows(self):
        first = self.me.patch("/api/portal/profile/", {"partner_name": "Aarav"}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.data["profile"]["complete"])
        self.assertIn("the wedding date", first.data["profile"]["missing"])
        second = self.me.patch("/api/portal/profile/", {"wedding_date": FUTURE, "venue_city": "Jaipur", "guest_count": 450}, format="json")
        self.assertGreater(second.data["profile"]["percent"], first.data["profile"]["percent"])

    def test_a_finished_profile_lands_in_the_crm_and_alerts_planners_once(self):
        res = self.me.patch("/api/portal/profile/", self.full_profile(), format="json")
        self.assertTrue(res.data["profile"]["complete"])
        enquiry = Enquiry.objects.get()
        self.assertEqual((enquiry.couple_name, enquiry.guest_count, enquiry.venue_city), ("Meera & Aarav", 450, "Jaipur"))
        self.assertEqual(enquiry.services_needed, ["CATERING", "DECOR"])
        self.assertTrue(enquiry.profile_complete)
        self.me.patch("/api/portal/profile/", {"notes": "We love flowers"}, format="json")  # saving again must not alert again
        self.assertEqual(Notification.objects.filter(user=self.planner, message__contains="completed their profile").count(), 1)

    def test_the_planner_sees_the_website_details_in_the_crm(self):
        self.me.patch("/api/portal/profile/", self.full_profile(), format="json")
        staff = APIClient()
        staff.force_authenticate(self.planner)
        row = staff.get("/api/enquiries/").data["results"][0]
        self.assertEqual((row["source"], row["partner_name"], row["preferred_contact"], row["profile_complete"]),
                         ("WEBSITE", "Aarav", "WHATSAPP", True))
        self.assertEqual(row["services_needed"], ["CATERING", "DECOR"])

    def test_bad_profile_values_are_refused(self):
        for bad in ({"wedding_date": "2020-01-01"}, {"guest_count": 0}, {"services_needed": ["ROCKET"]},
                    {"preferred_contact": "PIGEON"}, {"budget_paise": -1}):
            self.assertEqual(self.me.patch("/api/portal/profile/", bad, format="json").status_code, 400, bad)

    def test_a_customer_cannot_change_the_crm_stage_or_win_chance(self):
        self.me.patch("/api/portal/profile/", {"status": "WON", "win_chance": 100, "priority": 3}, format="json")
        enquiry = Enquiry.objects.get()
        self.assertEqual((enquiry.status, enquiry.win_chance, enquiry.priority), ("NEW", 10, 0))


@override_settings(ALLOW_DEMO_PAYMENTS=True)
class PayingFromTheWebsiteTests(PortalTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)

    def setUp(self):
        super().setUp()
        self.me = as_customer(signup().data["token"])
        self.me.patch("/api/portal/profile/", {"partner_name": "Aarav", "wedding_date": FUTURE, "venue_city": "Jaipur",
                                              "guest_count": 300, "services_needed": ["DECOR"],
                                              "preferred_contact": "CALL"}, format="json")
        self.staff = APIClient()
        self.staff.force_authenticate(self.planner)

    def book_the_couple(self):
        enquiry = Enquiry.objects.get()
        converted = self.staff.post(f"/api/enquiries/{enquiry.pk}/convert/", {"create_wedding": True}, format="json")
        wedding_id = converted.data["wedding_id"]
        invoice = self.staff.post(f"/api/weddings/{wedding_id}/invoices/", {"type": "DEPOSIT", "amount_paise": 500000_00}, format="json")
        return invoice.data["id"]

    def test_no_invoices_and_no_status_of_being_a_client_before_the_planner_converts(self):
        self.assertEqual(self.me.get("/api/portal/invoices/").data, [])
        self.assertFalse(self.me.get("/api/portal/me/").data["is_client"])

    def test_converting_the_enquiry_links_the_account_and_shows_the_invoices(self):
        invoice_id = self.book_the_couple()
        me = self.me.get("/api/portal/me/").data
        self.assertTrue(me["is_client"])
        self.assertEqual(me["stage"]["key"], "WON")
        rows = self.me.get("/api/portal/invoices/").data
        self.assertEqual([(r["id"], r["remaining_paise"], r["status"]) for r in rows], [(invoice_id, 500000_00, "UNPAID")])

    def test_pay_now_gives_a_link_and_pressing_it_twice_gives_the_same_link(self):
        invoice_id = self.book_the_couple()
        first = self.me.post(f"/api/portal/invoices/{invoice_id}/pay/").data["path"]
        second = self.me.post(f"/api/portal/invoices/{invoice_id}/pay/").data["path"]
        self.assertTrue(first.startswith("/pay/"))
        self.assertEqual(first, second)

    def test_paying_through_that_link_marks_the_invoice_paid_on_the_website(self):
        invoice_id = self.book_the_couple()
        path = self.me.post(f"/api/portal/invoices/{invoice_id}/pay/").data["path"]
        public = APIClient()
        order = public.post(f"/api{path}/order/").data
        public.post(f"/api{path}/verify/", {"razorpay_order_id": order["order_id"], "razorpay_payment_id": order["mock_payment_id"],
                                           "razorpay_signature": order["mock_signature"]}, format="json")
        self.assertEqual(Payment.objects.get().method, "RAZORPAY")
        row = self.me.get("/api/portal/invoices/").data[0]
        self.assertEqual((row["status"], row["remaining_paise"]), ("PAID", 0))

    def test_a_customer_cannot_pay_or_see_somebody_elses_invoice(self):
        invoice_id = self.book_the_couple()
        other = as_customer(signup(email="other@example.com", name="Other").data["token"])
        self.assertEqual(other.get("/api/portal/invoices/").data, [])
        self.assertEqual(other.post(f"/api/portal/invoices/{invoice_id}/pay/").status_code, 404)
        self.assertEqual(Invoice.objects.count(), 1)
