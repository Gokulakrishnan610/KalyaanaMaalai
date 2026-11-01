"""The bulk demo data must stay valid as the models change: loaded twice it adds nothing, and the money, statuses,
dates and bookings in it agree with the rules the app itself uses."""
import io
from datetime import timedelta

from django.core.management import call_command
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.test import TestCase
from django.utils import timezone

from agreements.models import Agreement
from agreements.services import fingerprint
from clients.models import Client
from enquiries.models import Enquiry
from mailer.models import EmailLog
from mailer.templates import TEMPLATES
from payments.models import Expense, Invoice, Payment, VendorPaymentPlan
from payments.services import allocate_to_plans, derive_status
from portal.models import Customer, VendorAccount
from quotations.models import WeddingVendor
from tasks.models import Task
from weddings.models import ScheduleItem, VendorArrival, Wedding, WeddingFunction

COUNT = 22  # enough to include every wedding status, today's wedding and a repeat client


class BulkDemoDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_demo_data", bulk=COUNT, stdout=io.StringIO())
        cls.bulk = Wedding.objects.filter(client__email__endswith="@bulk.demo")

    def test_loads_the_requested_weddings_and_leaves_aarav_and_meera_alone(self):
        self.assertEqual(self.bulk.count(), COUNT)
        starter = Wedding.objects.get(title="Aarav & Meera - Jaipur")
        self.assertEqual((starter.tasks.count(), starter.functions.count()), (32, 3))

    def test_a_second_load_adds_nothing(self):
        before = (Wedding.objects.count(), Task.objects.count(), Payment.objects.count(), Enquiry.objects.count(),
                  Agreement.objects.count(), Customer.objects.count(), EmailLog.objects.count(), VendorAccount.objects.count())
        call_command("load_demo_data", bulk=COUNT, stdout=io.StringIO())
        after = (Wedding.objects.count(), Task.objects.count(), Payment.objects.count(), Enquiry.objects.count(),
                 Agreement.objects.count(), Customer.objects.count(), EmailLog.objects.count(), VendorAccount.objects.count())
        self.assertEqual(before, after)

    def test_invoice_and_bill_statuses_match_the_payments(self):
        for invoice in Invoice.objects.filter(wedding__in=self.bulk).annotate(paid=Coalesce(Sum("payments__amount_paise"), 0)):
            self.assertEqual(invoice.status, derive_status(invoice.paid, invoice.amount_paise), invoice.pk)
            self.assertLessEqual(invoice.paid, invoice.amount_paise)
        for bill in Expense.objects.filter(wedding__in=self.bulk).prefetch_related("payments", "vendorpaymentplan_set"):
            payments = [(p.amount_paise, p.reference) for p in bill.payments.all()]
            self.assertEqual(bill.status, derive_status(sum(a for a, _ in payments), bill.amount_paise), bill.pk)
            plans = sorted(bill.vendorpaymentplan_set.all(), key=lambda p: (p.part, p.pk))
            if plans:
                self.assertEqual(sum(p.amount_paise for p in plans), bill.amount_paise)
                covered = allocate_to_plans(plans, payments)
                for plan in plans:
                    self.assertEqual(plan.status, derive_status(covered[plan.pk], plan.amount_paise), plan.pk)

    def test_every_booked_vendor_has_one_bill_and_two_instalments(self):
        for booking in WeddingVendor.objects.filter(wedding__in=self.bulk).select_related("quotation"):
            self.assertEqual(booking.quotation.status, "SELECTED")
            self.assertEqual(booking.quotation.total_paise, booking.agreed_amount_paise)
            self.assertEqual(Expense.objects.filter(wedding=booking.wedding, vendor=booking.vendor).count(), 1)
            self.assertEqual(VendorPaymentPlan.objects.filter(wedding=booking.wedding, vendor=booking.vendor).count(), 2)

    def test_no_venue_is_double_booked_and_schedules_fit_their_function(self):
        functions = list(WeddingFunction.objects.filter(venue__isnull=False).order_by("venue_id", "starts_at"))
        for earlier, later in zip(functions, functions[1:], strict=False):
            if earlier.venue_id == later.venue_id:
                self.assertGreaterEqual(later.starts_at, earlier.ends_at)
        self.assertFalse(ScheduleItem.objects.filter(function__wedding__in=self.bulk).filter(
            Q(starts_at__lt=F("function__starts_at")) | Q(ends_at__gt=F("function__ends_at"))).exists())

    def test_check_in_statuses_agree_with_the_times(self):
        now = timezone.now()
        for arrival in VendorArrival.objects.filter(wedding__in=self.bulk):
            deadline = arrival.expected_at + timedelta(minutes=arrival.grace_minutes)
            if arrival.status == "PENDING":
                self.assertIsNone(arrival.arrived_at)
                self.assertGreater(arrival.expected_at, now)
            elif arrival.status == "ON_TIME":
                self.assertLessEqual(arrival.arrived_at, deadline)
            else:
                self.assertIsNotNone(arrival.late_alert_sent_at)
                self.assertTrue(arrival.arrived_at is None or arrival.arrived_at > deadline)

    def test_past_weddings_are_over_and_nothing_is_dated_in_the_future(self):
        today, now = timezone.localdate(), timezone.now()
        self.assertFalse(self.bulk.filter(status="COMPLETED", end_date__gte=today).exists())
        self.assertFalse(self.bulk.filter(status__in=["CONFIRMED", "PLANNING"], end_date__lt=today).exists())
        self.assertFalse(Payment.objects.filter(paid_at__gt=now).exists())
        self.assertFalse(Task.objects.filter(created_at__gt=now + timedelta(minutes=1)).exists())

    def test_every_status_the_app_shows_is_present(self):
        statuses = set(self.bulk.values_list("status", flat=True))
        self.assertTrue({"COMPLETED", "CONFIRMED", "PLANNING", "CANCELLED"} <= statuses)
        self.assertEqual(set(Enquiry.objects.values_list("status", flat=True)) >= {"WON", "NEW", "LOST"}, True)
        self.assertTrue({"PAID", "PARTIAL", "UNPAID"} <= set(Invoice.objects.values_list("status", flat=True)))

    def test_every_wedding_has_one_agreement_that_matches_its_status(self):
        now = timezone.now()
        for wedding in self.bulk:
            agreements = list(wedding.agreements.all())
            self.assertEqual(len(agreements), 1, wedding.title)
            agreement = agreements[0]
            self.assertIn(wedding.title, agreement.body)
            if agreement.status == Agreement.Status.SIGNED:
                self.assertTrue(agreement.sent_at < agreement.signed_at <= now)
                self.assertTrue(agreement.signer_name and agreement.signature and agreement.signer_email)
                self.assertEqual(agreement.body_hash, fingerprint(agreement))  # the text has not changed since signing
            elif agreement.status == Agreement.Status.DRAFT:
                self.assertIsNone(agreement.sent_at)
            else:
                self.assertIsNone(agreement.signed_at)
            if wedding.status == "COMPLETED":
                self.assertNotIn(agreement.status, (Agreement.Status.DRAFT, Agreement.Status.VOID))

    def test_every_client_has_a_customer_login_and_vendors_have_logins(self):
        for client in Client.objects.filter(email__endswith="@bulk.demo"):
            customer = Customer.objects.get(client=client)
            self.assertEqual(customer.email, client.email)
            self.assertIsNotNone(customer.invited_at)
            if customer.last_login_at:
                self.assertTrue(customer.password_hash)  # you cannot have logged in without a password
        self.assertTrue(VendorAccount.objects.exists())
        self.assertFalse(VendorAccount.objects.filter(last_login_at__isnull=False, password_hash="").exists())

    def test_the_email_log_matches_the_money_and_the_agreements(self):
        clients = list(Client.objects.filter(email__endswith="@bulk.demo").values_list("email", flat=True))
        self.assertFalse(EmailLog.objects.exclude(template__in=list(TEMPLATES)).exists())
        self.assertEqual(EmailLog.objects.filter(template="invoice_issued", to__in=clients).count(),
                         Invoice.objects.filter(wedding__in=self.bulk).count())
        self.assertEqual(EmailLog.objects.filter(template="payment_receipt", to__in=clients).count(),
                         Payment.objects.filter(wedding__in=self.bulk, direction="IN").count())
        self.assertEqual(EmailLog.objects.filter(template="agreement_signed", to__in=clients).count(),
                         Agreement.objects.filter(wedding__in=self.bulk, status="SIGNED").count())
        self.assertFalse(EmailLog.objects.filter(created_at__gt=timezone.now() + timedelta(minutes=1)).exists())
        self.assertFalse(EmailLog.objects.filter(status="SENT", sent_at__isnull=True).exists())
