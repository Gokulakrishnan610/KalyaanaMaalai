"""The shapes the AI must answer in. OpenAI's structured output makes the model fill exactly these."""
from pydantic import BaseModel, Field


class QuoteLine(BaseModel):
    description: str
    qty: float = 1
    unit_price_rupees: float


class ExtractedQuotation(BaseModel):
    vendor_name: str
    total_rupees: float
    price_per_plate_rupees: float | None = None
    guest_count: int | None = None
    valid_till: str | None = Field(default=None, description="YYYY-MM-DD, only if a calendar date is printed")
    items: list[QuoteLine] = []
    menu_notes: str = ""
    confidence: float = Field(ge=0, le=1, description="How sure you are that you read the document correctly")
    warnings: list[str] = []


class ChecklistTask(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = ""
    category: str = ""
    due_offset_days: int = Field(default=-30, description="Days from the first wedding day; negative = before it")
    priority: str = "MEDIUM"  # LOW | MEDIUM | HIGH
    function_name: str | None = None


class ChecklistResponse(BaseModel):
    tasks: list[ChecklistTask]
