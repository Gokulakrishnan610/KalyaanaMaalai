"""Business rules for weddings, functions, the team and progress. Views and serializers stay thin."""
from datetime import datetime, time, timedelta

from django.db import transaction
from django.db.models import Count, Min, Q
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound

from payments.models import Invoice
from tasks.models import Stage, Task
from tasks.services import create_tasks_from_template  # noqa: F401  (other members import it from here)
from weddings.models import (
    TeamMember,
    VendorArrival,
    Venue,
    Wedding,
    WeddingFunction,
)

ROLES = ["LEAD_PLANNER", "COORDINATOR", "DECOR_LEAD", "VENDOR_LEAD"]

# (name, start, end) of the functions made by "add default functions", one day after another
DEFAULT_FUNCTIONS = [
    ("Mehendi", time(11, 0), time(16, 0)),
    ("Sangeet", time(19, 0), time(23, 30)),
    ("Wedding", time(10, 0), time(15, 0)),
    ("Reception", time(19, 0), time(23, 0)),
]


class Conflict(APIException):
    """HTTP 409: the request is fine but clashes with what is already saved."""

    status_code = 409
    default_detail = "This clashes with something that already exists."
    default_code = "conflict"


def wedding_queryset():
    """Weddings with the numbers the list needs, worked out in one query."""
    return Wedding.objects.select_related("client").annotate(
        task_total=Count("tasks", distinct=True),
        task_done=Count("tasks", filter=Q(tasks__stage=Stage.DONE), distinct=True),
        next_function_at=Min("functions__starts_at", filter=Q(functions__ends_at__gte=timezone.now())),
    )


def get_wedding(wedding_id: int) -> Wedding:
    """One wedding with its list numbers (task_total, task_done, next_function_at), or a 404."""
    try:
        return wedding_queryset().get(pk=wedding_id)
    except Wedding.DoesNotExist:
        raise NotFound("Wedding not found.") from None


@transaction.atomic
def create_wedding(data: dict, default_functions: bool = False) -> Wedding:
    """The wedding and its default functions are saved together or not at all."""
    data = dict(data)
    data.setdefault("contracted_guests", data["guest_count"])
    wedding = Wedding.objects.create(**data)
    if default_functions:
        for offset, (name, start, end) in enumerate(DEFAULT_FUNCTIONS):
            day = wedding.start_date + timedelta(days=offset)
            WeddingFunction.objects.create(
                wedding=wedding, name=name, guest_count=wedding.guest_count,
                starts_at=timezone.make_aware(datetime.combine(day, start)),
                ends_at=timezone.make_aware(datetime.combine(day, end)),
            )
    return wedding


def has_invoices(wedding: Wedding) -> bool:
    return Invoice.objects.filter(wedding=wedding).exists()


def task_counts_by_stage(wedding_id: int) -> dict:
    counts = {stage: 0 for stage, _ in Stage.choices}
    rows = Task.objects.filter(wedding_id=wedding_id).values("stage").annotate(n=Count("id"))
    counts.update({row["stage"]: row["n"] for row in rows})
    return counts


def wedding_progress(wedding_id: int) -> dict:
    """{total, done, pct, by_stage, overdue}: a task counts as done only in the DONE column."""
    by_stage = task_counts_by_stage(wedding_id)
    total = sum(by_stage.values())
    done = by_stage[Stage.DONE]
    overdue = (Task.objects.filter(wedding_id=wedding_id, due_date__lt=timezone.localdate())
               .exclude(stage=Stage.DONE).count())
    return {"total": total, "done": done, "pct": round(done * 100 / total) if total else 0,
            "by_stage": by_stage, "overdue": overdue}


# --- functions -------------------------------------------------------------------------------

def save_function(wedding: Wedding, data: dict, instance: WeddingFunction | None = None) -> WeddingFunction:
    """Create or update a function. Refuses (409) a venue that is already booked for an overlapping time.

    The venue row is locked while we check, so two people booking the same venue at once take turns."""
    with transaction.atomic():
        venue = data.get("venue", instance.venue if instance else None)
        starts_at = data.get("starts_at", instance.starts_at if instance else None)
        ends_at = data.get("ends_at", instance.ends_at if instance else None)
        if venue is not None:
            Venue.objects.select_for_update().get(pk=venue.pk)
            clash = (WeddingFunction.objects.filter(venue=venue, starts_at__lt=ends_at, ends_at__gt=starts_at)
                     .exclude(pk=instance.pk if instance else None).select_related("wedding").first())
            if clash:
                raise Conflict(
                    f"{venue.name} is already booked for {clash.name} ({clash.wedding.title}) from "
                    f"{timezone.localtime(clash.starts_at):%d %b %H:%M} to {timezone.localtime(clash.ends_at):%H:%M}."
                )
        if instance is None:
            return WeddingFunction.objects.create(wedding=wedding, **data)
        for field, value in data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


# --- team ------------------------------------------------------------------------------------

@transaction.atomic
def replace_assignments(wedding: Wedding, rows: list[dict]) -> list[TeamMember]:
    """Replace the whole team in one go: either every row is saved or the old team stays."""
    TeamMember.objects.filter(wedding=wedding).delete()
    return TeamMember.objects.bulk_create(
        [TeamMember(wedding=wedding, user_id=row["user_id"], role_label=row["role_label"]) for row in rows]
    )


# --- vendor punctuality (used by the vendors screens) -----------------------------------------

def get_vendor_punctuality(vendor_id: int) -> dict:
    """{total, on_time, late, avg_delay_min} over every check-in of this vendor that is not pending."""
    arrivals = VendorArrival.objects.filter(vendor_id=vendor_id).exclude(status=VendorArrival.Status.PENDING)
    on_time = arrivals.filter(status=VendorArrival.Status.ON_TIME).count()
    late = arrivals.filter(status=VendorArrival.Status.LATE).count()
    delays = [max(0, int((a.arrived_at - a.expected_at).total_seconds() // 60))
              for a in arrivals.filter(arrived_at__isnull=False)]
    return {"total": on_time + late, "on_time": on_time, "late": late,
            "avg_delay_min": round(sum(delays) / len(delays), 1) if delays else 0}
