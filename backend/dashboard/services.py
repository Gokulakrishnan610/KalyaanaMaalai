"""Numbers for the founder's dashboard. All money is in paise."""
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from enquiries.models import STAGE_WIN_CHANCE, Enquiry, FollowUp, Status
from incidents.models import Incident, IncidentStatus, Severity
from notifications.models import Notification
from payments.models import Expense, Invoice, Payment, PayStatus
from tasks.models import Stage, Task
from weddings.models import VendorArrival, Wedding, WeddingStatus


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


def recent_activity(limit=8):
    """The latest things that happened, newest first, for the dashboard's activity feed."""
    events = []
    for e in Enquiry.objects.order_by("-created_at")[:limit]:
        events.append({"kind": "enquiry", "text": f"New enquiry from {e.couple_name} via {e.get_source_display()}",
                       "at": e.created_at})
    for p in Payment.objects.select_related("wedding").order_by("-paid_at")[:limit]:
        verb = "received for" if p.direction == Payment.Direction.IN else "paid out for"
        events.append({"kind": "payment", "text": f"Payment of ₹{p.amount_paise / 100:,.0f} {verb} {p.wedding.title}",
                       "at": p.paid_at})
    arrivals = VendorArrival.objects.filter(arrived_at__isnull=False).select_related("vendor", "wedding")
    for a in arrivals.order_by("-arrived_at")[:limit]:
        events.append({"kind": "vendor", "text": f"{a.vendor.name} arrived ({a.get_status_display().lower()}) at {a.wedding.title}",
                       "at": a.arrived_at})
    seen_alerts = set()
    # an alert for several people is saved once per person, so show each message only once
    for n in Notification.objects.order_by("-created_at")[: limit * 4]:
        if n.message not in seen_alerts:
            seen_alerts.add(n.message)
            events.append({"kind": "alert", "text": n.message, "at": n.created_at})
    return sorted(events, key=lambda event: event["at"], reverse=True)[:limit]


def follow_up_summary(now):
    """Open follow-ups: how many are late and the next few coming up."""
    open_ones = FollowUp.objects.filter(done_at__isnull=True).select_related("enquiry")
    upcoming = open_ones.order_by("due_at")[:6]
    return {
        "overdue_follow_ups": open_ones.filter(due_at__lt=now).count(),
        "upcoming_follow_ups": [
            {"id": f.id, "enquiry_id": f.enquiry_id, "couple_name": f.enquiry.couple_name, "kind": f.kind,
             "summary": f.summary, "due_at": f.due_at, "overdue": f.due_at < now}
            for f in upcoming
        ],
    }


def incident_summary():
    """Problems reported during weddings that nobody has resolved yet."""
    unresolved = Incident.objects.exclude(status=IncidentStatus.RESOLVED).select_related("wedding", "assigned_to")
    return {
        "open_incidents": unresolved.count(),
        "critical_incidents": unresolved.filter(severity__in=[Severity.HIGH, Severity.CRITICAL]).count(),
        "recent_incidents": [
            {"id": i.id, "title": i.title, "wedding_title": i.wedding.title, "severity": i.severity,
             "status": i.status, "assigned_to_name": i.assigned_to.name if i.assigned_to else "",
             "created_at": i.created_at}
            for i in unresolved.order_by("-created_at")[:5]
        ],
    }


def pipeline_value():
    """What we expect to earn from open enquiries, weighted by the chance of winning them."""
    open_enquiries = Enquiry.objects.exclude(status__in=[Status.WON, Status.LOST])
    total = sum((e.expected_revenue_paise or 0) * e.win_chance // 100 for e in open_enquiries)
    return {"pipeline_expected_paise": total, "stage_win_chances": {k.value: v for k, v in STAGE_WIN_CHANCE.items()}}


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

    open_tasks = Task.objects.exclude(stage=Stage.DONE)
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
        **follow_up_summary(now),
        **pipeline_value(),
        **incident_summary(),
        "total_weddings": len(rows),
        "ongoing_weddings": Wedding.objects.exclude(
            status__in=[WeddingStatus.COMPLETED, WeddingStatus.CANCELLED]).count(),
        "open_tasks": open_tasks.count(),
        "overdue_tasks": open_tasks.filter(due_date__lt=today).count(),
        "recent_activity": recent_activity(),
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
