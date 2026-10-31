"""AI helpers: reading a vendor's quotation and writing a wedding checklist.

Rules: the model only READS and SUGGESTS. Amounts are converted to paise here in code (the model's own
arithmetic is never trusted), and every answer is validated before anything is shown. The AI is Groq (an
OpenAI-style chat API). While it is switched off (see `ai_is_live`), or if it fails, answers come from local
fallbacks so the demo never breaks.
"""
import base64
import datetime as dt
import io
import json
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

DEFAULT_MODEL = "openai/gpt-oss-120b"  # reads text and writes the checklist
DEFAULT_VISION_MODEL = "qwen/qwen3.8-27b"  # reads photos and scanned PDFs
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_OUTPUT_TOKENS = 8000
MAX_SCAN_PAGES = 3  # the vision model takes at most 3 images per request
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


def ai_is_live() -> bool:
    """True when Groq should really be called: a key is set and AI is switched on (AI_LIVE, or MOCK_EXTERNALS off)."""
    return bool(settings.GROQ_API_KEY) and settings.AI_LIVE


def _client():
    if not settings.GROQ_API_KEY:
        raise AIUnavailable("GROQ_API_KEY is not set, so AI is unavailable.")
    from groq import Groq
    return Groq(api_key=settings.GROQ_API_KEY, timeout=120)


def _simplify(content: list):
    """Text-only models want a plain string; only a message with images needs the list of parts."""
    if all(part["type"] == "text" for part in content):
        return "\n\n".join(part["text"] for part in content)
    return content


def _parse(system: str, content: list, output_format, vision: bool = False):
    """One Groq call that must answer with JSON in the shape of a Pydantic model. Returns the validated object.

    JSON mode guarantees valid JSON, not the right fields, so the schema is described in the prompt and the answer
    is checked against the model here (a bad answer raises, and the caller retries once).
    """
    model = (settings.GROQ_VISION_MODEL or DEFAULT_VISION_MODEL) if vision else (settings.GROQ_MODEL or DEFAULT_MODEL)
    schema = json.dumps(output_format.model_json_schema())
    response = _client().chat.completions.create(
        model=model, temperature=0, max_completion_tokens=MAX_OUTPUT_TOKENS,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": f"{system}\n\nAnswer with one JSON object that follows this JSON "
                                                f"schema exactly, and nothing else:\n{schema}"},
                  {"role": "user", "content": _simplify(content)}])
    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise ValueError("The answer was cut off.")
    if not choice.message.content:
        raise ValueError("The model returned no answer.")
    return output_format.model_validate_json(choice.message.content)


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
        warnings=["Demo mode: this is a sample reading, not your file. Add GROQ_API_KEY and AI_LIVE=true to .env to use Groq."])


def _system_prompt(category: str | None, preferred_names: list[str]) -> str:
    prompt = (
        "You read vendor quotations for a wedding planner in India. Return only what is printed in the document. "
        "Amounts are in rupees as plain numbers (no symbols or commas). Use null for anything not printed; never "
        "guess. valid_till must be YYYY-MM-DD and only when a calendar date is printed. List every priced line in "
        "items with its quantity and unit price per unit (not the line total). vendor_name is the vendor's business "
        "name only, without words like Quotation or Catering. Put anything doubtful in warnings "
        "and lower the confidence.")
    if category:
        prompt += f" This quotation is from a {category} vendor."
    if preferred_names:
        prompt += (" The planner's form has these standard rows: " + "; ".join(preferred_names) + ". When a line in "
                   "the document is the same thing as one of them, write that row's name EXACTLY as the line's "
                   "description. Keep the document's own wording for lines that match none of them.")
    return prompt


def _pdf_text_and_pages(data: bytes) -> tuple[str, list[bytes]]:
    """The text layer of a PDF, plus (when there is none) up to 3 page images for the vision model."""
    import pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages).strip()
            images = []
            if len(text) < MIN_TEXT_CHARS:
                for page in pdf.pages[:MAX_SCAN_PAGES]:
                    buffer = io.BytesIO()
                    page.to_image(resolution=150).original.save(buffer, format="PNG")
                    images.append(buffer.getvalue())
            return text, images
    except Exception as error:  # noqa: BLE001
        raise Unprocessable("This PDF could not be opened. Is it damaged or password protected?") from error


def _image_block(data: bytes, mime: str) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}}


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


def extract_quotation(file, filename: str | None = None, category: str | None = None,
                      preferred_names: list[str] | None = None) -> dict:
    """Reads a quotation (PDF or image) with Groq and returns a DRAFT (nothing is saved).

    `file` may be raw bytes or an uploaded file. `category` and `preferred_names` (the form's standard row names)
    help the AI name the line items so they land in the right rows. Returns vendor_name, total_paise,
    price_per_plate_paise, guest_count, valid_till, items[{description, qty, unit_price_paise}], menu_notes,
    confidence and warnings.
    """
    data = file if isinstance(file, bytes) else file.read()
    name = filename or getattr(file, "name", "") or "quotation.pdf"
    extension = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    info = {"filename": name, "bytes": len(data)}
    if len(data) > MAX_UPLOAD_BYTES:
        raise Unprocessable("This file is larger than 10 MB.")

    if not ai_is_live():
        draft = _to_draft(_mock_extraction())
        _log("extract_quotation", {**info, "mode": "mock"}, draft, "SUCCESS")
        return draft

    system = _system_prompt(category, preferred_names or [])
    if extension in IMAGE_TYPES:
        content, vision = [{"type": "text", "text": "Read this quotation."}, _image_block(data, IMAGE_TYPES[extension])], True
    else:
        text, page_images = _pdf_text_and_pages(data)
        if page_images:  # a scanned PDF: no text to read, so the vision model looks at the pages
            content = [{"type": "text", "text": "Read this scanned quotation."},
                       *[_image_block(image, "image/png") for image in page_images]]
            vision = True
        else:
            content, vision = [{"type": "text", "text": f"Quotation text:\n{text}"}], False
    model = (settings.GROQ_VISION_MODEL or DEFAULT_VISION_MODEL) if vision else (settings.GROQ_MODEL or DEFAULT_MODEL)
    last_error = None
    for _attempt in range(2):  # one retry when the answer does not validate
        try:
            draft = _to_draft(_parse(system, content, ExtractedQuotation, vision=vision))
            _log("extract_quotation", {**info, "mode": "vision" if vision else "text", "model": model},
                 draft, "SUCCESS")
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
        "Write 25 to 40 specific planning tasks for this wedding. "
        "Tailor them: each function adds its own tasks (a mehendi adds artists and seating; a sangeet adds "
        "choreography and sound checks); large guest counts add crowd, parking and security tasks; use the city "
        "and the vendors already chosen. due_offset_days is days from the first wedding day (negative = before). "
        "priority is LOW, MEDIUM or HIGH. function_name must be one of the listed functions or null. "
        f"No duplicates.\n\nWedding: {context}")
    result = _parse("You are an experienced Indian wedding planner.", [{"type": "text", "text": prompt}],
                    ChecklistResponse)
    if len(result.tasks) < 15:
        raise ValueError("The AI returned too few tasks.")
    return [t.model_dump() for t in result.tasks[:40]]


def generate_checklist(wedding) -> dict:
    """A PREVIEW of tasks (nothing is saved): {source: "ai" | "template", notice, tasks[]}."""
    context = _wedding_context(wedding)
    source, notice, raw = "template", "", None
    if not ai_is_live():
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
