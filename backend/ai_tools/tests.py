from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import APIException
from rest_framework.test import APITestCase

from accounts.models import Role, User
from ai_tools import services
from ai_tools.models import AIJob
from ai_tools.schemas import ChecklistResponse, ChecklistTask, ExtractedQuotation
from clients.models import Client
from tasks.models import Task
from weddings.models import Wedding, WeddingFunction

SAMPLE_PDF = "demo_data/assets/sample_quotation.pdf"
R = 100


def sample_bytes() -> bytes:
    with open(SAMPLE_PDF, "rb") as handle:
        return handle.read()


class AITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.planner = User.objects.create_user("p@t.com", "Planner", "Password123", role=Role.PLANNER)
        cls.staff = User.objects.create_user("s@t.com", "Staff", "Password123", role=Role.STAFF)
        client = Client.objects.create(couple_name="A & B", phone="9812345670")
        start = timezone.localdate() + timedelta(days=120)
        cls.wedding = Wedding.objects.create(title="A & B", client=client, start_date=start,
                                             end_date=start + timedelta(days=2), city="Jaipur", guest_count=450,
                                             contracted_guests=400, budget_paise=4_000_000 * R)
        for index, name in enumerate(["Mehendi", "Sangeet", "Reception"]):
            at = timezone.now() + timedelta(days=120 + index)
            WeddingFunction.objects.create(wedding=cls.wedding, name=name, starts_at=at,
                                           ends_at=at + timedelta(hours=4), guest_count=450)

    def setUp(self):
        self.client.force_authenticate(self.planner)

    def upload(self, name="q.pdf", content=None, content_type="application/pdf"):
        content = sample_bytes() if content is None else content
        return self.client.post("/api/ai/extract-quotation/", {"file": SimpleUploadedFile(name, content, content_type)},
                                format="multipart")


class PaiseConversionTests(AITestCase):
    def test_rupees_become_whole_paise_without_float_error(self):
        self.assertEqual(services.to_paise(441000), 44_100_000)
        self.assertEqual(services.to_paise(0.1 + 0.2), 30)  # 0.30000000000000004 rupees
        self.assertEqual(services.to_paise(Decimal("19.995")), 2000)
        self.assertEqual(services.to_paise(1234.56), 123_456)
        self.assertIsInstance(services.to_paise(10.5), int)

    def parsed(self, **extra):
        return ExtractedQuotation(vendor_name="X Caterers", total_rupees=1000, confidence=0.9,
                                  items=[{"description": "Menu", "qty": 10, "unit_price_rupees": 100}], **extra)

    def test_matching_items_give_no_warning(self):
        draft = services._to_draft(self.parsed())
        self.assertEqual((draft["total_paise"], draft["warnings"]), (1000 * R, []))
        self.assertEqual(draft["items"][0]["unit_price_paise"], 100 * R)

    def test_items_that_do_not_add_up_to_the_total_add_a_warning(self):
        parsed = self.parsed()
        parsed.total_rupees = 1500
        draft = services._to_draft(parsed)
        self.assertEqual(draft["total_paise"], 1500 * R)  # the document's total is kept, but flagged
        self.assertTrue(any("add up" in w for w in draft["warnings"]))

    def test_nonsense_totals_and_dates_are_handled(self):
        bad = self.parsed()
        bad.total_rupees = 0
        with self.assertRaises(ValueError):
            services._to_draft(bad)
        draft = services._to_draft(self.parsed(valid_till="next month"))
        self.assertIsNone(draft["valid_till"])
        self.assertTrue(any("validity date" in w for w in draft["warnings"]))


@override_settings(AI_LIVE=False)
class ExtractQuotationMockTests(AITestCase):
    def test_sample_pdf_returns_a_validated_draft_in_paise(self):
        res = self.upload()
        self.assertEqual(res.status_code, 200)
        draft = res.data["draft"]
        self.assertEqual(draft["vendor_name"], "Maharaja Feast")
        self.assertEqual((draft["total_paise"], draft["price_per_plate_paise"], draft["guest_count"]),
                         (441_000 * R, 980 * R, 450))
        self.assertEqual(sum(i["qty"] * i["unit_price_paise"] for i in draft["items"]), draft["total_paise"])
        self.assertTrue(0 <= draft["confidence"] <= 1)
        self.assertTrue(all(isinstance(draft[k], int) for k in ("total_paise", "price_per_plate_paise")))

    def test_the_job_is_logged_without_the_file_contents(self):
        self.upload()
        job = AIJob.objects.get(kind="extract_quotation")
        self.assertEqual((job.status, job.input["filename"]), ("SUCCESS", "q.pdf"))
        self.assertEqual(set(job.input), {"filename", "bytes", "mode"})

    def test_the_quotation_form_can_call_it_with_an_upload(self):
        upload = SimpleUploadedFile("q.pdf", sample_bytes(), "application/pdf")
        self.assertEqual(services.extract_quotation(upload)["total_paise"], 441_000 * R)

    def test_bad_uploads_are_refused(self):
        self.assertEqual(self.client.post("/api/ai/extract-quotation/", {}, format="multipart").status_code, 400)
        self.assertEqual(self.upload("q.exe", b"MZ", "application/octet-stream").status_code, 400)
        self.assertEqual(self.upload("fake.pdf", b"not a pdf at all").status_code, 400)
        self.assertEqual(self.upload("big.pdf", b"%PDF" + b"0" * (10 * 1024 * 1024)).status_code, 400)

    def test_staff_cannot_use_ai(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.upload().status_code, 403)


@override_settings(AI_LIVE=True, GROQ_API_KEY="test-key", GROQ_MODEL="", GROQ_VISION_MODEL="")
class ExtractQuotationRealPathTests(AITestCase):
    """The OpenAI call is replaced, so these check our own retry, validation and conversion code."""

    def good(self):
        return ExtractedQuotation(vendor_name="V", total_rupees=500, confidence=0.8,
                                  items=[{"description": "Menu", "qty": 5, "unit_price_rupees": 100}])

    def test_one_bad_answer_is_retried_then_succeeds(self):
        bad = self.good()
        bad.total_rupees = -1
        with mock.patch.object(services, "_parse", side_effect=[bad, self.good()]) as parse:
            draft = services.extract_quotation(sample_bytes(), "sample.pdf")
        self.assertEqual((parse.call_count, draft["total_paise"]), (2, 500 * R))

    def test_two_bad_answers_give_422_with_a_helpful_message(self):
        bad = self.good()
        bad.total_rupees = 0
        with mock.patch.object(services, "_parse", return_value=bad):
            res = self.upload()
        self.assertEqual(res.status_code, 422)
        self.assertIn("type the quotation in", res.data["detail"])
        self.assertEqual(AIJob.objects.get().status, "FAILED")

    def capture(self):
        captured = {}

        def fake(system, content, output_format, vision=False):
            captured.update(system=system, content=content, vision=vision)
            return self.good()

        return captured, mock.patch.object(services, "_parse", side_effect=fake)

    def test_a_pdf_with_text_goes_to_the_text_model_as_plain_text(self):
        captured, patched = self.capture()
        with patched:
            services.extract_quotation(sample_bytes(), "sample.pdf")
        self.assertFalse(captured["vision"])
        self.assertEqual([part["type"] for part in captured["content"]], ["text"])
        self.assertIn("Maharaja Feast", captured["content"][0]["text"])

    def test_an_image_goes_to_the_vision_model_as_a_data_url(self):
        captured, patched = self.capture()
        with patched:
            services.extract_quotation(b"\x89PNG\r\n\x1a\n" + b"0" * 50, "photo.png")
        self.assertTrue(captured["vision"])
        self.assertEqual([part["type"] for part in captured["content"]], ["text", "image_url"])
        self.assertTrue(captured["content"][1]["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_a_scanned_pdf_is_shown_to_the_vision_model_page_by_page(self):
        captured, patched = self.capture()
        with patched, mock.patch.object(services, "_pdf_text_and_pages", return_value=("", [b"page1", b"page2"])):
            services.extract_quotation(sample_bytes(), "scan.pdf")
        self.assertTrue(captured["vision"])
        self.assertEqual([part["type"] for part in captured["content"]], ["text", "image_url", "image_url"])

    def test_the_forms_row_names_and_category_are_given_to_the_ai(self):
        captured, patched = self.capture()
        with patched:
            services.extract_quotation(sample_bytes(), "sample.pdf", category="Caterer",
                                       preferred_names=["Buffet menu", "Welcome drinks"])
        self.assertIn("Caterer", captured["system"])
        self.assertIn("Buffet menu; Welcome drinks", captured["system"])
        self.assertIn("EXACTLY", captured["system"])

    def test_the_view_passes_category_and_row_labels_through(self):
        with mock.patch.object(services, "_parse", return_value=self.good()) as parse:
            res = self.client.post("/api/quotations/extract/", {
                "file": SimpleUploadedFile("q.pdf", sample_bytes(), "application/pdf"), "category": "Caterer",
                "row_labels": ["Buffet menu", "Dessert station"]}, format="multipart")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["draft"]["total_paise"], 500 * R)
        self.assertIn("Buffet menu; Dessert station", parse.call_args.args[0])

    def test_the_view_shows_the_ais_own_reason_when_it_cannot_read_the_file(self):
        bad = self.good()
        bad.total_rupees = 0
        with mock.patch.object(services, "_parse", return_value=bad):
            res = self.client.post("/api/quotations/extract/", {
                "file": SimpleUploadedFile("q.pdf", sample_bytes(), "application/pdf")}, format="multipart")
        self.assertEqual(res.status_code, 422)
        self.assertIn("type the quotation in", res.data["detail"])

@override_settings(AI_LIVE=True, GROQ_API_KEY="test-key", GROQ_MODEL="", GROQ_VISION_MODEL="")
class GroqRequestTests(AITestCase):
    """Fakes the Groq client itself, to check exactly what we send and how we read the answer."""

    ANSWER = ('{"vendor_name": "V", "total_rupees": 500, "confidence": 0.8, "items": '
              '[{"description": "Menu", "qty": 5, "unit_price_rupees": 100}]}')

    def fake_client(self, content=None, finish_reason="stop"):
        message = mock.Mock(content=self.ANSWER if content is None else content)
        client = mock.Mock()
        client.chat.completions.create.return_value = mock.Mock(
            choices=[mock.Mock(message=message, finish_reason=finish_reason)])
        return client

    def test_a_text_pdf_uses_the_text_model_in_json_mode_with_the_schema(self):
        client = self.fake_client()
        with mock.patch.object(services, "_client", return_value=client):
            draft = services.extract_quotation(sample_bytes(), "sample.pdf", category="Caterer")
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "openai/gpt-oss-120b")
        self.assertEqual((kwargs["response_format"], kwargs["temperature"]), ({"type": "json_object"}, 0))
        system, user = kwargs["messages"]
        self.assertIn("vendor_name", system["content"])  # the schema is described to the model
        self.assertIn("JSON", system["content"])
        self.assertIsInstance(user["content"], str)  # a text-only message is a plain string
        self.assertEqual(draft["total_paise"], 500 * R)

    def test_a_photo_uses_the_vision_model(self):
        client = self.fake_client()
        with mock.patch.object(services, "_client", return_value=client):
            services.extract_quotation(b"\x89PNG\r\n\x1a\n" + b"0" * 50, "photo.png")
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "qwen/qwen3.8-27b")
        self.assertEqual([p["type"] for p in kwargs["messages"][1]["content"]], ["text", "image_url"])

    @override_settings(GROQ_MODEL="llama-3.3-70b-versatile", GROQ_VISION_MODEL="some/vision-model")
    def test_both_models_can_be_changed_in_settings(self):
        client = self.fake_client()
        with mock.patch.object(services, "_client", return_value=client):
            services.extract_quotation(sample_bytes(), "sample.pdf")
            services.extract_quotation(b"\x89PNG\r\n\x1a\n" + b"0" * 50, "photo.png")
        models = [call.kwargs["model"] for call in client.chat.completions.create.call_args_list]
        self.assertEqual(models, ["llama-3.3-70b-versatile", "some/vision-model"])

    def test_text_that_is_not_the_right_json_is_retried_then_reported(self):
        client = self.fake_client(content='{"vendor_name": "V"}')  # no total
        with mock.patch.object(services, "_client", return_value=client):
            with self.assertRaises(APIException) as caught:
                services.extract_quotation(sample_bytes(), "sample.pdf")
        self.assertEqual((caught.exception.status_code, client.chat.completions.create.call_count), (422, 2))

    def test_a_cut_off_answer_is_retried_then_reported(self):
        client = self.fake_client(finish_reason="length")
        with mock.patch.object(services, "_client", return_value=client):
            with self.assertRaises(APIException) as caught:
                services.extract_quotation(sample_bytes(), "sample.pdf")
        self.assertEqual((caught.exception.status_code, client.chat.completions.create.call_count), (422, 2))

    @override_settings(GROQ_API_KEY="")
    def test_without_a_key_the_sample_is_returned_not_an_error(self):
        self.assertEqual(services.extract_quotation(sample_bytes(), "sample.pdf")["vendor_name"], "Maharaja Feast")


@override_settings(AI_LIVE=False)
class ChecklistTests(AITestCase):
    def preview(self):
        return self.client.post("/api/ai/generate-checklist/", {"wedding_id": self.wedding.pk}, format="json")

    def confirm(self, tasks):
        return self.client.post("/api/ai/generate-checklist/confirm/", {"wedding_id": self.wedding.pk, "tasks": tasks},
                                format="json")

    def test_preview_has_25_to_40_tailored_tasks_and_saves_nothing(self):
        res = self.preview()
        self.assertEqual(res.status_code, 200)
        tasks = res.data["tasks"]
        self.assertTrue(25 <= len(tasks) <= 40, len(tasks))
        titles = " | ".join(t["title"].lower() for t in tasks)
        self.assertIn("mehendi artists", titles)  # the mehendi function
        self.assertIn("parking", titles)  # 450 guests
        self.assertIn("choreographer", titles)  # the sangeet function
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(res.data["source"], "template")

    def test_a_small_wedding_without_a_mehendi_gets_different_tasks(self):
        small = Wedding.objects.create(title="Small", client=self.wedding.client, start_date=self.wedding.start_date,
                                       end_date=self.wedding.start_date, city="Udaipur", guest_count=80,
                                       contracted_guests=80)
        titles = " | ".join(t["title"].lower() for t in services.generate_checklist(small)["tasks"])
        self.assertNotIn("mehendi", titles)
        self.assertNotIn("parking", titles)

    def test_every_task_has_a_valid_priority_and_a_due_date_not_in_the_past(self):
        for task in self.preview().data["tasks"]:
            self.assertIn(task["priority"], ("LOW", "MEDIUM", "HIGH"))
            self.assertGreaterEqual(task["due_date"], timezone.localdate().isoformat())

    def test_confirm_creates_tasks_without_duplicates(self):
        tasks = self.preview().data["tasks"]
        Task.objects.create(wedding=self.wedding, title=tasks[0]["title"].upper())  # already on the board
        res = self.confirm(tasks[:5] + tasks[:2])
        self.assertEqual(res.status_code, 201)
        self.assertEqual((res.data["created"], res.data["skipped"]), (4, 3))
        self.assertEqual(Task.objects.filter(wedding=self.wedding).count(), 5)
        self.assertEqual(self.confirm(tasks[:5]).data["created"], 0)

    def test_preview_leaves_out_titles_already_on_the_board(self):
        first = self.preview().data["tasks"][0]["title"]
        Task.objects.create(wedding=self.wedding, title=first)
        self.assertNotIn(first, [t["title"] for t in self.preview().data["tasks"]])

    def test_confirm_links_a_task_to_its_function(self):
        tasks = [t for t in self.preview().data["tasks"] if t["function_name"] == "Mehendi"][:1]
        self.confirm(tasks)
        self.assertEqual(Task.objects.get().function.name, "Mehendi")

    def test_confirm_needs_a_task_and_a_real_wedding(self):
        self.assertEqual(self.confirm([]).status_code, 400)
        res = self.client.post("/api/ai/generate-checklist/", {"wedding_id": 9999}, format="json")
        self.assertEqual(res.status_code, 404)


@override_settings(AI_LIVE=True, GROQ_API_KEY="test-key", GROQ_MODEL="", GROQ_VISION_MODEL="")
class ChecklistFallbackTests(AITestCase):
    def preview(self):
        return self.client.post("/api/ai/generate-checklist/", {"wedding_id": self.wedding.pk}, format="json")

    def test_when_the_ai_fails_the_built_in_checklist_is_returned(self):
        with mock.patch.object(services, "_parse", side_effect=ConnectionError("offline")):
            res = self.preview()
        self.assertEqual((res.status_code, res.data["source"]), (200, "template"))
        self.assertGreaterEqual(len(res.data["tasks"]), 25)
        self.assertIn("built-in", res.data["notice"])

    def test_a_thin_ai_answer_also_falls_back(self):
        thin = ChecklistResponse(tasks=[ChecklistTask(title="Only one task")])
        with mock.patch.object(services, "_parse", return_value=thin):
            self.assertEqual(self.preview().data["source"], "template")

    def test_a_good_ai_answer_is_used(self):
        answer = ChecklistResponse(tasks=[ChecklistTask(title=f"AI task number {i}", due_offset_days=-10 - i,
                                                        priority="HIGH") for i in range(26)])
        with mock.patch.object(services, "_parse", return_value=answer):
            res = self.preview()
        self.assertEqual((res.data["source"], len(res.data["tasks"])), ("ai", 26))
