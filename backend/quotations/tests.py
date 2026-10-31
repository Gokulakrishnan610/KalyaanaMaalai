from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, User
from clients.models import Client
from payments.models import Expense, Payment, VendorPaymentPlan
from quotations import services
from quotations.models import Quotation, QuotationRequest, QuotationStatus, RequestStatus, WeddingVendor
from vendors.models import Vendor, VendorCategory
from weddings.models import VendorArrival, VendorRating, Wedding

RUPEE = 100


class QuotationTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)
        client = Client.objects.create(couple_name="A & B", phone="9812345670")
        start = timezone.localdate() + timedelta(days=60)
        cls.wedding = Wedding.objects.create(title="A & B", client=client, start_date=start, end_date=start,
                                             city="Jaipur", guest_count=400, contracted_guests=400)
        cls.caterer_cat = VendorCategory.objects.get(name="Caterer")
        cls.dj_cat = VendorCategory.objects.get(name="DJ & Sound")
        cls.caterers = [Vendor.objects.create(name=n, category=cls.caterer_cat, phone="9000000000" )
                        for n in ("Rasoi Royale", "Spice Route", "Maharaja Feast")]
        cls.request_obj = QuotationRequest.objects.create(wedding=cls.wedding, category=cls.caterer_cat,
                                                          guest_count=400)
        cls.request_obj.invited_vendors.set(cls.caterers)

    def setUp(self):
        self.client.force_authenticate(self.planner)

    def quote(self, vendor, **data):
        return self.client.post(f"/api/quotation-requests/{self.request_obj.id}/quotations/",
                                {"vendor_id": vendor.id, **data}, format="json")

    def three_quotes(self):
        a = self.quote(self.caterers[0], price_per_plate_paise=1150 * RUPEE, total_paise=460000 * RUPEE).data
        b = self.quote(self.caterers[1], price_per_plate_paise=1320 * RUPEE, total_paise=528000 * RUPEE).data
        c = self.quote(self.caterers[2], price_per_plate_paise=980 * RUPEE, total_paise=392000 * RUPEE).data
        return a, b, c


class SavingTests(QuotationTestCase):
    def test_total_is_the_sum_of_items_not_what_the_client_sent(self):
        res = self.quote(self.caterers[0], total_paise=1, items=[
            {"description": "Menu", "qty": 400, "unit_price_paise": 1000 * RUPEE},
            {"description": "Live counters", "qty": 2, "unit_price_paise": 10000 * RUPEE}])
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["total_paise"], 420000 * RUPEE)
        self.assertEqual(sum(i["total_paise"] for i in res.data["items"]), 420000 * RUPEE)

    def test_second_quotation_from_same_vendor_replaces_the_first(self):
        first = self.quote(self.caterers[0], total_paise=500000 * RUPEE)
        second = self.quote(self.caterers[0], total_paise=450000 * RUPEE, items=[
            {"description": "Menu", "qty": 1, "unit_price_paise": 450000 * RUPEE}])
        self.assertEqual((first.status_code, second.status_code), (201, 200))
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Quotation.objects.filter(request=self.request_obj).count(), 1)
        self.assertEqual(len(second.data["items"]), 1)

    def test_caterer_without_items_gets_implied_total_from_plate_price_and_guests(self):
        res = self.quote(self.caterers[0], price_per_plate_paise=1150 * RUPEE)
        self.assertEqual(res.data["total_paise"], 460000 * RUPEE)
        self.assertEqual(res.data["implied_total_paise"], 460000 * RUPEE)

    def test_needs_a_price_from_somewhere(self):
        self.assertEqual(self.quote(self.caterers[0]).status_code, 400)

    def test_vendor_must_be_in_the_requests_category(self):
        dj = Vendor.objects.create(name="DJ Neel", category=self.dj_cat, phone="9111111111")
        self.assertEqual(self.quote(dj, total_paise=5).status_code, 400)

    def test_patch_items_recomputes_total_and_staff_cannot_write(self):
        quote = self.quote(self.caterers[0], total_paise=10).data
        res = self.client.patch(f"/api/quotations/{quote['id']}/", {"items": [
            {"description": "Menu", "qty": 2, "unit_price_paise": 700}]}, format="json")
        self.assertEqual(res.data["total_paise"], 1400)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.patch(f"/api/quotations/{quote['id']}/", {}, format="json").status_code, 403)
        self.assertEqual(self.client.get(f"/api/quotation-requests/{self.request_obj.id}/").status_code, 200)

    def test_new_caterer_request_with_fewer_than_three_invitees_warns(self):
        res = self.client.post(f"/api/weddings/{self.wedding.id}/quotation-requests/", {
            "category_id": self.caterer_cat.id, "requirements": "Veg", "guest_count": 400,
            "invited_vendor_ids": [self.caterers[0].id]}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.data["warnings"]), 1)
        full = self.client.post(f"/api/weddings/{self.wedding.id}/quotation-requests/", {
            "category_id": self.caterer_cat.id, "invited_vendor_ids": [v.id for v in self.caterers]}, format="json")
        self.assertEqual(full.data["warnings"], [])

    def test_request_list_counts_received_quotations(self):
        self.quote(self.caterers[0], total_paise=5)
        res = self.client.get(f"/api/weddings/{self.wedding.id}/quotation-requests/")
        self.assertEqual(res.data[0]["received_count"], 1)
        self.assertEqual(res.data[0]["invited_count"], 3)

    def test_send_sets_sent_at_and_leaves_a_notification_in_mock_mode(self):
        from notifications.models import Notification
        res = self.client.post(f"/api/quotation-requests/{self.request_obj.id}/send/")
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.data["sent_at"])
        self.assertEqual(Notification.objects.count(), 1)

    def test_cannot_add_quotations_once_the_request_is_closed(self):
        self.client.patch(f"/api/quotation-requests/{self.request_obj.id}/", {"status": "CLOSED"}, format="json")
        self.assertEqual(self.quote(self.caterers[0], total_paise=5).status_code, 409)


class ComparisonTests(QuotationTestCase):
    def test_items_line_up_by_normalised_description_with_gaps_as_null(self):
        self.quote(self.caterers[0], items=[
            {"description": "Welcome Drinks", "qty": 400, "unit_price_paise": 100},
            {"description": "Dessert counter", "qty": 1, "unit_price_paise": 5000}])
        self.quote(self.caterers[1], items=[{"description": "welcome  drinks!", "qty": 400, "unit_price_paise": 90}])
        data = self.client.get(f"/api/quotation-requests/{self.request_obj.id}/compare/").data
        rows = {r["key"]: r for r in data["item_rows"]}
        self.assertEqual(set(rows), {"welcome drinks", "dessert counter"})
        self.assertEqual(rows["welcome drinks"]["values"][0]["unit_price_paise"], 100)
        self.assertEqual(rows["welcome drinks"]["values"][1]["unit_price_paise"], 90)
        self.assertIsNone(rows["dessert counter"]["values"][1])

    def test_flags_mark_lowest_total_and_lowest_plate_price(self):
        self.three_quotes()
        data = self.client.get(f"/api/quotation-requests/{self.request_obj.id}/compare/").data
        by_vendor = {q["vendor"]["name"]: q["flags"] for q in data["quotations"]}
        self.assertTrue(by_vendor["Maharaja Feast"]["lowest_total"])
        self.assertTrue(by_vendor["Maharaja Feast"]["lowest_per_plate"])
        self.assertFalse(by_vendor["Spice Route"]["lowest_total"])
        self.assertEqual(sum(q["flags"]["best_value"] for q in data["quotations"]), 1)
        self.assertEqual(data["weights"], {"price": 0.6, "rating": 0.25, "punctuality": 0.15})

    def test_expired_quotation_is_flagged_and_cannot_be_best_value(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        self.quote(self.caterers[0], total_paise=100, valid_till=yesterday.isoformat())
        self.quote(self.caterers[1], total_paise=900)
        data = self.client.get(f"/api/quotation-requests/{self.request_obj.id}/compare/").data
        flags = {q["vendor"]["name"]: q["flags"] for q in data["quotations"]}
        self.assertTrue(flags["Rasoi Royale"]["expired"])
        self.assertFalse(flags["Rasoi Royale"]["best_value"])
        self.assertTrue(flags["Spice Route"]["best_value"])

    def test_best_value_uses_rating_and_check_in_punctuality(self):
        # Maharaja is cheapest but unreliable; Rasoi costs a bit more and is excellent
        self.three_quotes()
        past = Wedding.objects.create(title="Old", client=self.wedding.client, start_date=timezone.localdate(),
                                      end_date=timezone.localdate(), city="X", guest_count=10, contracted_guests=10)
        for vendor, stars, on_time in ((self.caterers[0], 5, True), (self.caterers[2], 1, False)):
            VendorRating.objects.create(vendor=vendor, wedding=past, punctuality=stars, quality=stars, pricing=stars)
            VendorArrival.objects.create(
                wedding=past, vendor=vendor, expected_at=timezone.now(), arrived_at=timezone.now(),
                status=VendorArrival.Status.ON_TIME if on_time else VendorArrival.Status.LATE)
        # shrink the price gap so rating and punctuality decide it
        Quotation.objects.filter(vendor=self.caterers[0]).update(total_paise=395000 * RUPEE)
        data = self.client.get(f"/api/quotation-requests/{self.request_obj.id}/compare/").data
        best = [q["vendor"]["name"] for q in data["quotations"] if q["flags"]["best_value"]]
        self.assertEqual(best, ["Rasoi Royale"])
        rasoi = next(q for q in data["quotations"] if q["vendor"]["name"] == "Rasoi Royale")
        self.assertEqual(rasoi["vendor"]["punctuality_pct"], 100.0)

    def test_best_value_math_handles_one_quote_and_equal_values(self):
        self.assertEqual(services.best_value_scores([500], [None], [None]), [1.0])
        self.assertEqual(services.best_value_scores([500, 500], [4.0, 4.0], [None, None]), [1.0, 1.0])

    def test_best_value_math_weights(self):
        # A: cheapest, worst rating, worst punctuality.  B: dearest, best rating, best punctuality.
        a, b = services.best_value_scores([100, 200], [1.0, 5.0], [0.0, 100.0])
        self.assertAlmostEqual(a, 0.60)
        self.assertAlmostEqual(b, 0.40)
        # a missing rating counts as the others' average, so it neither helps nor hurts
        scores = services.best_value_scores([100, 100, 100], [5.0, 1.0, None], [None] * 3)
        self.assertAlmostEqual(scores[2], 0.60 + 0.25 * 0.5 + 0.15)

    def test_empty_request_compares_to_nothing(self):
        empty = QuotationRequest.objects.create(wedding=self.wedding, category=self.dj_cat)
        data = self.client.get(f"/api/quotation-requests/{empty.id}/compare/").data
        self.assertEqual(data["quotations"], [])


class SelectionTests(QuotationTestCase):
    def select(self, quotation_id, **body):
        return self.client.post(f"/api/quotations/{quotation_id}/select/", body, format="json")

    def test_selecting_rejects_the_others_closes_the_request_and_books_one_vendor(self):
        a, b, c = self.three_quotes()
        res = self.select(c["id"])
        self.assertEqual(res.status_code, 201)
        statuses = dict(Quotation.objects.values_list("id", "status"))
        self.assertEqual(statuses[c["id"]], QuotationStatus.SELECTED)
        self.assertEqual(statuses[a["id"]], QuotationStatus.REJECTED)
        self.assertEqual(statuses[b["id"]], QuotationStatus.REJECTED)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, RequestStatus.CLOSED)
        booking = WeddingVendor.objects.get()
        self.assertEqual((booking.vendor, booking.agreed_amount_paise), (self.caterers[2], 392000 * RUPEE))

    def test_selecting_plans_the_expense_and_advance_and_final_instalments(self):
        _, _, c = self.three_quotes()
        self.select(c["id"], advance_pct=40)
        expense = Expense.objects.get()
        self.assertEqual(expense.amount_paise, 392000 * RUPEE)
        plans = {p.part: p for p in VendorPaymentPlan.objects.all()}
        self.assertEqual(plans["ADVANCE"].amount_paise, 156800 * RUPEE)
        self.assertEqual(plans["FINAL"].amount_paise, 235200 * RUPEE)
        self.assertEqual(plans["ADVANCE"].due_date, timezone.localdate() + timedelta(days=7))
        self.assertEqual(plans["FINAL"].due_date, self.wedding.start_date - timedelta(days=3))

    def test_default_advance_is_30_percent(self):
        _, _, c = self.three_quotes()
        self.select(c["id"])
        self.assertEqual(VendorPaymentPlan.objects.get(part="ADVANCE").amount_paise, 117600 * RUPEE)

    def test_selecting_twice_creates_nothing_new(self):
        _, _, c = self.three_quotes()
        first = self.select(c["id"])
        second = self.select(c["id"])
        self.assertEqual((first.status_code, second.status_code), (201, 200))
        self.assertEqual(WeddingVendor.objects.count(), 1)
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(VendorPaymentPlan.objects.count(), 2)

    def test_switching_before_any_payment_replaces_the_vendor_and_the_plan(self):
        a, _, c = self.three_quotes()
        self.select(c["id"])
        res = self.select(a["id"])
        self.assertEqual(res.status_code, 201)
        booking = WeddingVendor.objects.get()
        self.assertEqual(booking.vendor, self.caterers[0])
        self.assertEqual(Expense.objects.get().amount_paise, 460000 * RUPEE)
        self.assertEqual(VendorPaymentPlan.objects.count(), 2)
        self.assertEqual(Quotation.objects.get(pk=c["id"]).status, QuotationStatus.REJECTED)

    def test_switching_after_a_payment_is_blocked(self):
        a, _, c = self.three_quotes()
        self.select(c["id"])
        Payment.objects.create(wedding=self.wedding, expense=Expense.objects.get(), direction="OUT",
                               amount_paise=1000 * RUPEE, method="UPI")
        res = self.select(a["id"])
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["detail"], "Payments already recorded for the current vendor")
        self.assertEqual(WeddingVendor.objects.get().vendor, self.caterers[2])
        self.assertEqual(Quotation.objects.get(pk=c["id"]).status, QuotationStatus.SELECTED)

    def test_a_finance_failure_does_not_undo_the_selection(self):
        _, _, c = self.three_quotes()
        with self.assertLogs("quotations.services", level="ERROR"):
            from unittest import mock
            with mock.patch.object(services.Expense.objects, "create", side_effect=RuntimeError("boom")):
                res = self.select(c["id"])
        self.assertEqual(res.status_code, 201)
        self.assertEqual(WeddingVendor.objects.count(), 1)

    def test_bad_advance_is_rejected(self):
        _, _, c = self.three_quotes()
        self.assertEqual(self.select(c["id"], advance_pct=150).status_code, 400)

    def test_wedding_vendor_list_shows_the_choice(self):
        _, _, c = self.three_quotes()
        self.select(c["id"])
        rows = self.client.get(f"/api/weddings/{self.wedding.id}/vendors/").data
        self.assertEqual(rows[0]["vendor"]["name"], "Maharaja Feast")
        self.assertEqual(rows[0]["category"], "Caterer")


class UploadTests(QuotationTestCase):
    def setUp(self):
        super().setUp()
        self.quote_id = self.quote(self.caterers[0], total_paise=5).data["id"]
        self.url = f"/api/quotations/{self.quote_id}/upload/"
        import tempfile
        self._media = tempfile.mkdtemp()
        self._override = override_settings(MEDIA_ROOT=self._media)
        self._override.enable()
        self.addCleanup(self._override.disable)

    def send(self, name, content, content_type):
        return self.client.post(self.url, {"file": SimpleUploadedFile(name, content, content_type)},
                                format="multipart")

    def test_pdf_is_saved_under_a_random_name(self):
        res = self.send("Rasoi Royale quote.pdf", b"%PDF-1.4 test", "application/pdf")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("Rasoi", res.data["file_url"])
        self.assertTrue(res.data["file_url"].endswith(".pdf"))
        self.assertTrue(Quotation.objects.get(pk=self.quote_id).file)

    def test_png_and_jpg_are_accepted(self):
        self.assertEqual(self.send("a.png", b"\x89PNG\r\n\x1a\n", "image/png").status_code, 200)
        self.assertEqual(self.send("a.JPG", b"\xff\xd8\xff\xe0", "image/jpeg").status_code, 200)

    def test_rejects_wrong_extension_content_type_signature_and_size(self):
        self.assertEqual(self.send("a.exe", b"MZ", "application/octet-stream").status_code, 400)
        self.assertEqual(self.send("a.pdf", b"%PDF", "text/html").status_code, 400)
        self.assertEqual(self.send("a.pdf", b"<html>not a pdf</html>", "application/pdf").status_code, 400)
        big = b"%PDF" + b"0" * (10 * 1024 * 1024)
        self.assertEqual(self.send("big.pdf", big, "application/pdf").status_code, 400)
        self.assertFalse(Quotation.objects.get(pk=self.quote_id).file)

    def test_extract_returns_a_draft_and_never_saves(self):
        res = self.client.post("/api/quotations/extract/", {"file": SimpleUploadedFile(
            "q.pdf", b"%PDF-1.4", "application/pdf")}, format="multipart")
        self.assertIn(res.status_code, (200, 501))  # 501 until the AI part is merged
        self.assertEqual(Quotation.objects.count(), 1)
