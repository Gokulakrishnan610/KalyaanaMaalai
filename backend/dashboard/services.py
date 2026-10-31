"""Numbers for the founder's dashboard. All money is in paise."""
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from enquiries.models import Enquiry, Status
from payments.models import Expense, Invoice, Payment, PayStatus
from tasks.models import Stage, Task
from weddings.models import VendorArrival, Wedding


def _sum_by_wedding(queryset, field="amount_paise"):
    """{wedding_id: total} for any model that has a wedding and a money column."""
    rows = queryset.values("wedding_id").annotate(total=Coalesce(Sum(field), 0))
    return {row["wedding_id"]: row["total"] for row in rows}


def _task_counts(stage=None):
    tasks = Task.objects.all() if stage is None else Task.objects.filter(stage=stage)
    return {row["wedding_id"]: row["n"] for row in tasks.values("wedding_id").annotate(n=Count("id"))}


def wedding_rows():
    invoiced = _sum_by_wedding(Invoice.objects.all())
    received = _sum_by_wedding(Payment.objects.filter(direction=Payment.Direction.IN))
    expenses = _sum_by_wedding(Expense.objects.all())
    total_tasks, done_tasks = _task_counts(), _task_counts(Stage.DONE)

    rows = []
    for wedding in Wedding.objects.select_related("client"):
        revenue = invoiced.get(wedding.id, 0)
        cost = expenses.get(wedding.id, 0)
        profit = revenue - cost
        tasks = total_tasks.get(wedding.id, 0)
        rows.append({
            "wedding_id": wedding.id,
            "title": wedding.title,
            "client_name": wedding.client.couple_name,
            "date": wedding.start_date,
            "status": wedding.status,
            "revenue_paise": revenue,
            "received_paise": received.get(wedding.id, 0),
            "expense_paise": cost,
            "profit_paise": profit,
            "margin_pct": round(profit * 100 / revenue, 1) if revenue else 0,
            "progress_pct": round(done_tasks.get(wedding.id, 0) * 100 / tasks) if tasks else 0,
        })
    return rows


def upcoming_vendor_payments(today, days=7):
    """Unpaid vendor bills due within a week (or already overdue), soonest first."""
    bills = (
        Expense.objects.exclude(status=PayStatus.PAID)
        .filter(due_date__isnull=False, due_date__lte=today + timedelta(days=days))
        .select_related("wedding", "vendor")
        .annotate(paid=Coalesce(Sum("payments__amount_paise"), 0))
        .order_by("due_date")[:10]
    )
    return [
        {
            "expense_id": bill.id,
            "wedding_id": bill.wedding_id,
            "wedding_title": bill.wedding.title,
            "vendor_name": bill.vendor.name if bill.vendor else "",
            "description": bill.description,
            "due_date": bill.due_date,
            "outstanding_paise": bill.amount_paise - bill.paid,
            "overdue": bill.due_date < today,
        }
        for bill in bills
    ]


def build_summary():
    now = timezone.now()
    today = timezone.localdate()
    rows = wedding_rows()

    revenue = sum(r["revenue_paise"] for r in rows)
    received = sum(r["received_paise"] for r in rows)
    expenses = sum(r["expense_paise"] for r in rows)

    by_source = list(Enquiry.objects.values("source").annotate(count=Count("id")).order_by("-count"))
    total_enquiries = sum(item["count"] for item in by_source)
    won = Enquiry.objects.filter(status=Status.WON).count()

    consultations = Enquiry.objects.filter(consultation_at__gte=now).order_by("consultation_at")[:5]
    return {
        "active_enquiries": Enquiry.objects.exclude(status__in=[Status.WON, Status.LOST]).count(),
        "enquiries_by_source": by_source,
        "conversion_rate": round(won * 100 / total_enquiries, 1) if total_enquiries else 0,
        "weddings_by_status": {
            row["status"]: row["count"] for row in Wedding.objects.values("status").annotate(count=Count("id"))
        },
        "upcoming_weddings": [
            {"id": r["wedding_id"], "title": r["title"], "date": r["date"]}
            for r in sorted((r for r in rows if r["date"] >= today), key=lambda r: r["date"])[:5]
        ],
        "total_revenue_paise": revenue,
        "total_received_paise": received,
        "total_expenses_paise": expenses,
        "total_profit_paise": revenue - expenses,
        "outstanding_client_paise": revenue - received,
        "upcoming_vendor_payments": upcoming_vendor_payments(today),
        "late_vendors_today": VendorArrival.objects.filter(status=VendorArrival.Status.LATE,
                                                           expected_at__date=today).count(),
        "upcoming_consultations": [
            {"id": e.id, "couple_name": e.couple_name, "consultation_at": e.consultation_at}
            for e in consultations
        ],
        "per_wedding": rows,
    }
