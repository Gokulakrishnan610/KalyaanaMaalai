"""Clients we onboard ourselves, agreements, mail templates and the vendor login."""
import re
from datetime import date, timedelta

from django.core import mail as django_mail
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.models import Role, User
from agreements.models import Agreement
from enquiries.models import Enquiry
from mailer.models import EmailLog
from mailer.templates import TEMPLATES
from payments.models import Expense, Invoice
from portal.models import Customer, VendorAccount
from portal.tests import PortalTestCase, as_customer
from quotations.models import QuotationRequest, WeddingVendor
from vendors.models import Vendor, VendorCategory
from weddings.models import Wedding

FUTURE = date.today() + timedelta(days=120)


def link_token(log: EmailLog) -> str:
    return re.search(r"token=([^\"'&\s<]+)", log.html).group(1)


class OnboardingCase(PortalTestCase):
    def setUp(self):
        super().setUp()
        self.planner = User.objects.create_user("pl@t.com", "Priya Planner", "Password123", role=Role.PLANNER)
        self.staff = APIClient()
        self.staff.force_authenticate(self.planner)

    def phone_enquiry(self, email="anu@example.com"):
        return Enquiry.objects.create(couple_name="Anu & Vijay", phone="9812345670", email=email, source="INSTAGRAM",
                                      wedding_date=FUTURE, guest_count=200, venue_city="Chennai", budget_paise=50000000,
                                      owner=self.planner)

    def convert(self, enquiry, wedding=True):
        return self.staff.post(f"/api/enquiries/{enquiry.pk}/convert/", {"create_wedding": wedding}, format="json")


class ClientAccountTests(OnboardingCase):
    def test_converting_an_instagram_enquiry_creates_a_login_and_emails_it(self):
        enquiry = self.phone_enquiry()
        self.assertEqual(self.staff.get(f"/api/enquiries/{enquiry.pk}/").data["portal_account"], "none")
        self.assertEqual(self.convert(enquiry).status_code, 200)
        customer = Customer.objects.get(email="anu@example.com")
        enquiry.refresh_from_db()
        self.assertEqual((customer.enquiry, customer.client), (enquiry, enquiry.client))
        self.assertEqual(customer.password_hash, "")
        log = EmailLog.objects.get(template="client_welcome")
        self.assertEqual(log.to, "anu@example.com")
        self.assertIn("Anu &amp; Vijay wedding", log.html)
        self.assertEqual(self.staff.get(f"/api/enquiries/{enquiry.pk}/").data["portal_account"], "invited")

    def test_the_emailed_link_sets_a_password_once_and_logs_in(self):
        self.convert(self.phone_enquiry())
        token = link_token(EmailLog.objects.get(template="client_welcome"))
        # nobody can log in before choosing a password
        no_password = APIClient().post("/api/portal/login/", {"email": "anu@example.com", "password": ""}, format="json")
        self.assertEqual(no_password.status_code, 400)
        res = APIClient().post("/api/portal/set-password/", {"token": token, "password": "BrandNew123"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(as_customer(res.data["token"]).get("/api/portal/me/").data["is_client"], True)
        again = APIClient().post("/api/portal/set-password/", {"token": token, "password": "Another1234"}, format="json")
        self.assertEqual(again.status_code, 400)  # the link works once

    def test_no_email_means_no_account_and_a_clear_message_when_inviting(self):
        enquiry = self.phone_enquiry(email="")
        self.convert(enquiry)
        self.assertFalse(Customer.objects.exists())
        res = self.staff.post(f"/api/enquiries/{enquiry.pk}/invite/")
        self.assertEqual(res.status_code, 400)

    def test_resend_invite_sends_another_email(self):
        enquiry = self.phone_enquiry()
        self.convert(enquiry)
        self.assertEqual(self.staff.post(f"/api/enquiries/{enquiry.pk}/invite/").status_code, 200)
        self.assertEqual(EmailLog.objects.filter(template="client_welcome").count(), 2)

    def test_a_website_signup_converted_later_does_not_get_a_second_account(self):
        from portal.tests import signup

        signup()
        enquiry = Enquiry.objects.get()
        enquiry.email, enquiry.owner = "meera@example.com", self.planner
        enquiry.save()
        self.convert(enquiry, wedding=False)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertIsNotNone(Customer.objects.get().client_id)

    def test_forgot_password_never_reveals_who_has_an_account(self):
        self.assertEqual(APIClient().post("/api/portal/forgot-password/", {"email": "nobody@example.com"}).status_code, 200)
        self.assertFalse(EmailLog.objects.exists())


class MailTemplateTests(OnboardingCase):
    def test_every_template_renders_with_sample_values(self):
        for name in TEMPLATES:
            res = self.staff.get(f"/api/mail-templates/{name}/")
            self.assertEqual(res.status_code, 200, name)
            self.assertIn("KalyaanaMaalai", res.data["html"])
            self.assertNotIn("{{", res.data["html"])

    def test_a_sent_email_is_logged_and_delivered(self):
        self.convert(self.phone_enquiry())
        self.assertEqual(EmailLog.objects.get(template="client_welcome").status, "SENT")
        self.assertEqual(len(django_mail.outbox), 1)

    def test_invoice_and_payment_emails_go_to_the_client(self):
        enquiry = self.phone_enquiry()
        self.convert(enquiry)
        wedding = Wedding.objects.get()
        with self.captureOnCommitCallbacks(execute=True):
            self.staff.post(f"/api/weddings/{wedding.pk}/invoices/", {"type": "DEPOSIT", "amount_paise": 500000}, format="json")
        self.assertTrue(EmailLog.objects.filter(template="invoice_issued", to="anu@example.com").exists())


class AgreementTests(OnboardingCase):
    def setUp(self):
        super().setUp()
        self.convert(self.phone_enquiry())
        self.wedding = Wedding.objects.get()
        token = link_token(EmailLog.objects.get(template="client_welcome"))
        res = APIClient().post("/api/portal/set-password/", {"token": token, "password": "BrandNew123"}, format="json")
        self.customer = as_customer(res.data["token"])
        self.agreement = Agreement.objects.get()

    def sign_payload(self, code, **extra):
        return {"name": "Anu Kumar", "signature": "data:image/png;base64,iVBORw0KGgo=", "code": code, "agreed": True, **extra}

    def request_code(self):
        django_mail.outbox.clear()
        self.assertEqual(self.customer.post(f"/api/portal/agreements/{self.agreement.pk}/code/").status_code, 200)
        return re.search(r">(\d{6})<", EmailLog.objects.filter(template="agreement_otp").latest("id").html).group(1)

    def test_converting_with_a_wedding_prepares_a_draft_filled_from_the_wedding(self):
        self.assertEqual(self.agreement.status, "DRAFT")
        self.assertIn("200 guests", self.agreement.body)
        self.assertIn("Anu & Vijay", self.agreement.body)

    def test_the_client_cannot_see_a_draft(self):
        self.assertEqual(self.customer.get("/api/portal/agreements/").data, [])
        self.assertEqual(self.customer.get(f"/api/portal/agreements/{self.agreement.pk}/").status_code, 404)

    def test_full_signing_flow_keeps_proof(self):
        sent = self.staff.post(f"/api/agreements/{self.agreement.pk}/send/")
        self.assertEqual(sent.data["status"], "SENT")
        self.assertTrue(EmailLog.objects.filter(template="agreement_ready", to="anu@example.com").exists())
        code = self.request_code()
        res = self.customer.post(f"/api/portal/agreements/{self.agreement.pk}/sign/", self.sign_payload(code), format="json",
                                 HTTP_USER_AGENT="TestBrowser/1.0")
        self.assertEqual(res.status_code, 200, res.data)
        certificate = res.data["certificate"]
        self.assertEqual((res.data["status"], certificate["signed_by"], certificate["company_signer"]), ("SIGNED", "Anu Kumar", "Priya Planner"))
        self.assertEqual((certificate["device"], certificate["text_unchanged"]), ("TestBrowser/1.0", True))
        self.assertTrue(EmailLog.objects.filter(template="agreement_signed").exists())

    def test_wrong_code_is_refused_and_the_code_locks_after_five_tries(self):
        self.staff.post(f"/api/agreements/{self.agreement.pk}/send/")
        code = self.request_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(self.customer.post(f"/api/portal/agreements/{self.agreement.pk}/sign/", self.sign_payload(wrong), format="json").status_code, 400)
        locked = self.customer.post(f"/api/portal/agreements/{self.agreement.pk}/sign/", self.sign_payload(code), format="json")
        self.assertEqual(locked.status_code, 400)
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.status, "SENT")

    def test_signature_and_tick_box_are_required(self):
        self.staff.post(f"/api/agreements/{self.agreement.pk}/send/")
        code = self.request_code()
        url = f"/api/portal/agreements/{self.agreement.pk}/sign/"
        self.assertEqual(self.customer.post(url, self.sign_payload(code, signature="not an image"), format="json").status_code, 400)
        self.assertEqual(self.customer.post(url, self.sign_payload(code, agreed=False), format="json").status_code, 400)

    def test_a_signed_agreement_cannot_be_edited_cancelled_or_signed_again(self):
        self.staff.post(f"/api/agreements/{self.agreement.pk}/send/")
        code = self.request_code()
        self.customer.post(f"/api/portal/agreements/{self.agreement.pk}/sign/", self.sign_payload(code), format="json")
        self.assertEqual(self.staff.patch(f"/api/agreements/{self.agreement.pk}/", {"body": "changed"}, format="json").status_code, 400)
        self.assertEqual(self.staff.post(f"/api/agreements/{self.agreement.pk}/cancel/").status_code, 400)
        again = self.customer.post(f"/api/portal/agreements/{self.agreement.pk}/sign/", self.sign_payload(code), format="json")
        self.assertEqual(again.status_code, 400)

    def test_tampering_with_the_text_after_signing_is_detected(self):
        self.staff.post(f"/api/agreements/{self.agreement.pk}/send/")
        code = self.request_code()
        self.customer.post(f"/api/portal/agreements/{self.agreement.pk}/sign/", self.sign_payload(code), format="json")
        Agreement.objects.filter(pk=self.agreement.pk).update(body="a different text")
        self.assertFalse(self.staff.get(f"/api/agreements/{self.agreement.pk}/").data["certificate"]["text_unchanged"])

    def test_another_couple_cannot_open_or_sign_this_agreement(self):
        self.staff.post(f"/api/agreements/{self.agreement.pk}/send/")
        from portal.tests import signup

        other = as_customer(signup(email="other@example.com").data["token"])
        self.assertEqual(other.get(f"/api/portal/agreements/{self.agreement.pk}/").status_code, 404)
        self.assertEqual(other.post(f"/api/portal/agreements/{self.agreement.pk}/code/").status_code, 404)


class VendorPortalTests(OnboardingCase):
    def setUp(self):
        super().setUp()
        category = VendorCategory.objects.get_or_create(name="Caterer")[0]
        self.vendor = Vendor.objects.create(name="Royal Caterers", category=category, phone="9812345671", email="royal@example.com")
        self.convert(self.phone_enquiry())
        self.wedding = Wedding.objects.get()

    def login(self):
        invited = self.staff.post(f"/api/vendors/{self.vendor.pk}/invite/")
        self.assertEqual(invited.status_code, 200)
        # the password is shown to the staff member and emailed to the vendor
        self.assertIn(invited.data["login"]["password"], EmailLog.objects.get(template="vendor_invite").html)
        res = APIClient().post("/api/portal/vendor/login/", invited.data["login"], format="json")
        self.assertEqual(res.status_code, 200)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")
        return client

    def test_invite_needs_an_email_and_creates_a_pending_account(self):
        Vendor.objects.filter(pk=self.vendor.pk).update(email="")
        self.assertEqual(self.staff.post(f"/api/vendors/{self.vendor.pk}/invite/").status_code, 400)
        Vendor.objects.filter(pk=self.vendor.pk).update(email="royal@example.com")
        res = self.staff.post(f"/api/vendors/{self.vendor.pk}/invite/")
        self.assertEqual(res.data["portal_account"], "invited")
        self.assertEqual(VendorAccount.objects.get().email, "royal@example.com")

    def test_adding_a_vendor_with_an_email_creates_the_login_at_once(self):
        res = self.staff.post("/api/vendors/", {"name": "New Decor", "category_id": self.vendor.category_id, "phone": "9812345679",
                                                "email": "decor@example.com"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["login"]["email"], "decor@example.com")
        self.assertTrue(VendorAccount.objects.filter(email="decor@example.com").exists())

    def test_vendor_changes_the_generated_password(self):
        vendor = self.login()
        wrong = vendor.post("/api/portal/vendor/password/", {"current": "nope", "new": "NewPassword1"}, format="json")
        self.assertEqual(wrong.status_code, 400)
        generated = APIClient().post("/api/portal/vendor/login/", {"email": "royal@example.com", "password": "x"}, format="json")
        self.assertEqual(generated.status_code, 400)

    def test_vendor_logs_in_and_sees_their_booking_and_payments(self):
        with self.captureOnCommitCallbacks(execute=True):
            WeddingVendor.objects.create(wedding=self.wedding, vendor=self.vendor, agreed_amount_paise=900000)
        Expense.objects.create(wedding=self.wedding, vendor=self.vendor, category="Caterer", description="Food", amount_paise=900000)
        vendor = self.login()
        self.assertEqual(vendor.get("/api/portal/vendor/me/").data["vendor"]["name"], "Royal Caterers")
        self.assertEqual(vendor.get("/api/portal/vendor/bookings/").data[0]["agreed_amount_paise"], 900000)
        self.assertEqual(vendor.get("/api/portal/vendor/payments/").data["bills"][0]["remaining_paise"], 900000)
        self.assertTrue(EmailLog.objects.filter(template="vendor_booked", to="royal@example.com").exists())

    def test_vendor_answers_a_quotation_request_and_sees_only_their_own(self):
        other = Vendor.objects.create(name="Other Caterers", category=self.vendor.category, phone="9812345672", email="o@example.com")
        request = QuotationRequest.objects.create(wedding=self.wedding, category=self.vendor.category, guest_count=200)
        request.invited_vendors.set([self.vendor, other])
        self.staff.post(f"/api/quotation-requests/{request.pk}/send/")
        vendor = self.login()
        rows = vendor.get("/api/portal/vendor/requests/").data
        self.assertEqual(len(rows), 1)
        res = vendor.post(f"/api/portal/vendor/requests/{request.pk}/quote/", {"total_paise": 700000}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["my_quotation"]["total_paise"], 700000)
        self.assertEqual(request.quotations.get().vendor, self.vendor)

    def test_tokens_do_not_cross_over_between_vendor_customer_and_staff(self):
        vendor = self.login()
        self.assertIn(vendor.get("/api/portal/me/").status_code, (401, 403))
        self.assertIn(vendor.get("/api/enquiries/").status_code, (401, 403))
        self.assertIn(self.staff.get("/api/portal/vendor/me/").status_code, (401, 403))
