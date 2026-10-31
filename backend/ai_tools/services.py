"""AI helpers: reading a vendor's quotation and writing a wedding checklist.

Rules: the model only READS and SUGGESTS. Amounts are converted to paise here in code (the model's own
arithmetic is never trusted), and every answer is validated before anything is shown. While MOCK_EXTERNALS is
true, or if the AI fails, answers come from local fallbacks so the demo never breaks.
"""
import base64
import datetime as dt
import io
import logging
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from pydantic import ValidationError as PydanticError
from rest_framework.exceptions import APIException

from ai_tools.checklist_template import build_template
from ai_tools.models import AIJob
from ai_tools.schemas import ChecklistResponse, ExtractedQuotation

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MIN_TEXT_CHARS = 40  # a PDF with less text than this is treated as a scan
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


class Unprocessable(APIException):
    status_code = 422
    default_detail = "Could not read this file."


class AIUnavailable(APIException):
    status_code = 503
    default_detail = "The AI service is not available right now. Please type the details in."


# ---------------------------------------------------------------- shared helpers

def to_paise(rupees) -> int:
    """Rupees (as the model wrote them) to whole paise, rounding half up. Never uses float multiplication."""
    return int((Decimal(str(rupees)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _client():
    if not settings.OPENAI_API_KEY:
        raise AIUnavailable("OPENAI_API_KEY is not set, so AI is unavailable.")
    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=60)


def _parse(messages: list, response_format):
    """One OpenAI structured-output call at temperature 0. Returns the parsed Pydantic object."""
    completion = _client().beta.chat.completions.parse(
        model=settings.OPENAI_MODEL or DEFAULT_MODEL, messages=messages, response_format=response_format,
        temperature=0)
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("The model returned no structured answer.")
    return parsed


def _log(kind: str, input_info: dict, output, status: str):
    try:
        AIJob.objects.create(kind=kind, input=input_info, output=output, status=status)
    except Exception:  # noqa: BLE001 - logging must never break the feature
        logger.exception("Could not save the AI job log")


# ---------------------------------------------------------------- quotation reading

SAMPLE_DRAFT = {  # what seed/sample_quotation.pdf (Maharaja Feast) says, used while AI is mocked
    "vendor_name": "Maharaja Feast", "total_rupees": 441000, "price_per_plate_rupees": 980, "guest_count": 450,
    "valid_till": None, "menu_notes": "3 starters, live jalebi counter on request.",
    "items": [("Rajasthani thali style veg menu", 450, 780), ("Welcome drinks", 450, 80),
              ("Dessert station", 1, 18000), ("Mocktail bar", 1, 36000)],
}


def _mock_extraction() -> ExtractedQuotation:
    d = SAMPLE_DRAFT
    return ExtractedQuotation(
        vendor_name=d["vendor_name"], total_rupees=d["total_rupees"], price_per_plate_rupees=d["price_per_plate_rupees"],
        guest_count=d["guest_count"], valid_till=d["valid_till"], menu_notes=d["menu_notes"], confidence=0.95,
        items=[{"description": a, "qty": b, "unit_price_rupees": c} for a, b, c in d["items"]],
        warnings=["Demo mode: this is a sample reading, not your file. Turn off MOCK_EXTERNALS to use real AI."])


def _pdf_text_and_pages(data: bytes) -> tuple[str, list[bytes]]:
    """The text layer of a PDF, plus (when there is none) up to 3 page images for the vision model."""
    import pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages).strip()
            images = []
            if len(text) < MIN_TEXT_CHARS:
                for page in pdf.pages[:3]:
                    buffer = io.BytesIO()
                    page.to_image(resolution=150).original.save(buffer, format="PNG")
                    images.append(buffer.getvalue())
            return text, images
    except Exception as error:  # noqa: BLE001
        raise Unprocessable("This PDF could not be opened. Is it damaged or password protected?") from error


def _messages(text: str, images: list[tuple[bytes, str]]) -> list:
    instructions = (
        "You read vendor quotations for a wedding planner in India. Return only what is printed in the document. "
        "Amounts are in rupees as numbers (no symbols or commas). Use null for anything not printed; never guess. "
        "valid_till must be YYYY-MM-DD and only when a calendar date is printed. List every priced line in items "
        "with its quantity and unit price. Put anything doubtful in warnings and lower the confidence.")
    content = [{"type": "text", "text": text or "Read the attached quotation."}]
    for data, mime in images:
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}})
    return [{"role": "system", "content": instructions}, {"role": "user", "content": content}]


def _to_draft(parsed: ExtractedQuotation) -> dict:
    """Validated model answer -> the draft the forms use. Money is converted to paise here."""
    if parsed.total_rupees <= 0:
        raise ValueError("The total must be above zero.")
    warnings = list(parsed.warnings)
    items = []
    for line in parsed.items:
        if line.unit_price_rupees < 0 or line.qty <= 0:
            raise ValueError("A line has a negative price or zero quantity.")
        qty = int(line.qty) if float(line.qty).is_integer() else line.qty
        items.append({"description": line.description.strip(), "qty": qty, "quantity": qty,
                      "unit_price_paise": to_paise(line.unit_price_rupees)})
    total_paise = to_paise(parsed.total_rupees)
    if items:
        line_sum = sum(int((Decimal(str(i["qty"])) * i["unit_price_paise"]).quantize(Decimal(1), ROUND_HALF_UP))
                       for i in items)
        if line_sum != total_paise:
            warnings.append(f"The line items add up to Rs {line_sum / 100:,.2f} but the document total is "
                            f"Rs {total_paise / 100:,.2f}. Please check both.")
    valid_till = None
    if parsed.valid_till:
        try:
            valid_till = dt.date.fromisoformat(parsed.valid_till).isoformat()
        except ValueError:
            warnings.append(f"Could not read the validity date '{parsed.valid_till}'.")
    return {
        "vendor_name": parsed.vendor_name.strip(), "total_paise": total_paise,
        "price_per_plate_paise": None if parsed.price_per_plate_rupees is None else to_paise(
            parsed.price_per_plate_rupees),
        "guest_count": parsed.guest_count, "valid_till": valid_till, "items": items,
        "menu_notes": parsed.menu_notes.strip(), "confidence": round(parsed.confidence, 2), "warnings": warnings,
    }


def extract_quotation(file, filename: str | None = None) -> dict:
    """Reads a quotation (PDF or image) and returns a DRAFT (nothing is saved).

    `file` may be raw bytes or an uploaded file. Returns vendor_name, total_paise, price_per_plate_paise,
    guest_count, valid_till, items[{description, qty, unit_price_paise}], menu_notes, confidence and warnings.
    """
    data = file if isinstance(file, bytes) else file.read()
    name = filename or getattr(file, "name", "") or "quotation.pdf"
    extension = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    info = {"filename": name, "bytes": len(data)}
    if len(data) > MAX_UPLOAD_BYTES:
        raise Unprocessable("This file is larger than 10 MB.")

    if settings.MOCK_EXTERNALS:
        draft = _to_draft(_mock_extraction())
        _log("extract_quotation", {**info, "mode": "mock"}, draft, "SUCCESS")
        return draft

    if extension in IMAGE_TYPES:
        text, images = "", [(data, IMAGE_TYPES[extension])]
    else:
        text, page_images = _pdf_text_and_pages(data)
        images = [(image, "image/png") for image in page_images]
        text = f"Quotation text:\n{text}" if text else ""

    last_error = None
    for _attempt in range(2):  # one retry when the answer does not validate
        try:
            draft = _to_draft(_parse(_messages(text, images), ExtractedQuotation))
            _log("extract_quotation", {**info, "mode": "vision" if images else "text"}, draft, "SUCCESS")
            return draft
        except (PydanticError, ValueError) as error:
            last_error = error
        except APIException:
            raise
        except Exception as error:  # noqa: BLE001 - network, quota, bad key ...
            logger.warning("Quotation extraction failed (%s)", type(error).__name__)
            _log("extract_quotation", info, {"error": type(error).__name__}, "FAILED")
            raise AIUnavailable from error
    _log("extract_quotation", info, {"error": str(last_error)[:300]}, "FAILED")
    raise Unprocessable("The AI could not read a clear quotation from this file. Try a clearer copy, "
                        "or type the quotation in by hand.")


# ---------------------------------------------------------------- checklist

def _wedding_context(wedding) -> dict:
    from quotations.models import WeddingVendor
    functions = [{"name": f.name, "guests": f.guest_count} for f in wedding.functions.all()]
    vendors = [f"{b.vendor.name} ({b.vendor.category.name})"
               for b in WeddingVendor.objects.filter(wedding=wedding).select_related("vendor__category")]
    return {"title": wedding.title, "city": wedding.city, "guests": wedding.guest_count,
            "budget_rupees": wedding.budget_paise // 100, "start_date": wedding.start_date.isoformat(),
            "days": (wedding.end_date - wedding.start_date).days + 1, "functions": functions, "vendors": vendors}


def _normal(title: str) -> str:
    return " ".join(title.lower().split())


def _ai_checklist(context: dict) -> list[dict]:
    prompt = (
        "You are an experienced Indian wedding planner. Write 25 to 40 specific planning tasks for this wedding. "
        "Tailor them: each function adds its own tasks (a mehendi adds artists and seating; a sangeet adds "
        "choreography and sound checks); large guest counts add crowd, parking and security tasks; use the city "
        "and the vendors already chosen. due_offset_days is days from the first wedding day (negative = before). "
        "priority is LOW, MEDIUM or HIGH. function_name must be one of the listed functions or null. "
        f"No duplicates.\n\nWedding: {context}")
    result = _parse([{"role": "user", "content": prompt}], ChecklistResponse)
    if len(result.tasks) < 15:
        raise ValueError("The AI returned too few tasks.")
    return [t.model_dump() for t in result.tasks[:40]]


def generate_checklist(wedding) -> dict:
    """A PREVIEW of tasks (nothing is saved): {source: "ai" | "template", notice, tasks[]}."""
    context = _wedding_context(wedding)
    source, notice, raw = "template", "", None
    if settings.MOCK_EXTERNALS or not settings.OPENAI_API_KEY:
        notice = "AI is switched off, so this is the built-in checklist tailored to your wedding."
    else:
        try:
            raw = _ai_checklist(context)
            source = "ai"
        except Exception as error:  # noqa: BLE001 - the demo must never break
            logger.warning("Checklist AI failed (%s); using the built-in checklist", type(error).__name__)
            notice = "The AI could not be reached, so this is the built-in checklist instead."
    if raw is None:
        raw = build_template(wedding, [f["name"] for f in context["functions"]],
                             [v.split(" (")[0] for v in context["vendors"]])

    existing = {_normal(t) for t in wedding.tasks.values_list("title", flat=True)}
    today = timezone.localdate()
    tasks, skipped = [], 0
    for task in raw:
        key = _normal(task["title"])
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        due = max(wedding.start_date + dt.timedelta(days=task["due_offset_days"]), today)
        tasks.append({**task, "priority": task["priority"] if task["priority"] in ("LOW", "MEDIUM", "HIGH")
                      else "MEDIUM", "due_date": due.isoformat()})
    _log("generate_checklist", {"wedding_id": wedding.pk, "source": source},
         {"tasks": len(tasks), "skipped_duplicates": skipped}, "SUCCESS")
    return {"source": source, "notice": notice, "skipped_duplicates": skipped, "tasks": tasks}


@transaction.atomic
def confirm_checklist(wedding, tasks: list[dict]) -> dict:
    """Saves the tasks the planner kept. Titles that already exist on the wedding are skipped."""
    from django.db.models import Max

    from tasks.models import Stage, Task

    existing = {_normal(t) for t in wedding.tasks.values_list("title", flat=True)}
    functions = {f.name.lower(): f for f in wedding.functions.all()}
    fresh = []
    for task in tasks:
        key = _normal(task["title"])
        if key in existing:
            continue
        existing.add(key)
        fresh.append(task)
    # AI tasks have their own titles, dates and functions, so they are saved here instead of through
    # tasks.services.create_tasks_from_template (which only knows the standard template)
    last = Task.objects.filter(wedding=wedding, stage=Stage.TO_PLAN).aggregate(last=Max("position"))["last"]
    position = 0 if last is None else last + 1
    rows = []
    for index, task in enumerate(fresh):
        due = task.get("due_date")
        rows.append(Task(
            wedding=wedding, title=task["title"][:255], description=task.get("description", ""),
            category=task.get("category", "")[:60], priority=task.get("priority") or "MEDIUM",
            due_date=dt.date.fromisoformat(due) if due else None,
            function=functions.get((task.get("function_name") or "").lower()), position=position + index))
    Task.objects.bulk_create(rows)
    return {"created": len(rows), "skipped": len(tasks) - len(fresh)}
