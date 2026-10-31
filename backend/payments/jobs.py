"""Timed job: tell the team about vendor payments that are due soon or late (once per item per day)."""
from django.utils import timezone

from notifications.services import notify
from payments import services

REMIND_DAYS = 3


def remind_due_payments(today=None) -> int:
    """Returns how many new alerts were created."""
    today = today or timezone.localdate()
    created = 0
    for item in services.upcoming_payments(days=REMIND_DAYS, today=today):
        who = item["vendor_name"] or item["description"]
        rupees = f"Rs {item['outstanding_paise'] // 100:,}"
        if item["overdue"]:
            text = f"OVERDUE: {rupees} to {who} for {item['wedding_title']} was due {item['due_date']:%d %b}."
            severity = "critical"
        else:
            text = f"Payment due {item['due_date']:%d %b}: {rupees} to {who} for {item['wedding_title']}."
            severity = "warning"
        key = f"due:{item['kind']}:{item['id']}:{today.isoformat()}"
        if notify(text, severity=severity, dedupe_key=key):
            created += 1
    return created
