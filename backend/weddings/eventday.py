"""Run sheet (schedule) and vendor arrival check-in rules."""
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from notifications.models import Notification
from weddings.models import ScheduleItem, VendorArrival, WeddingFunction

log = logging.getLogger(__name__)


# --- schedule --------------------------------------------------------------------------------

def check_schedule_times(function: WeddingFunction, starts_at, ends_at) -> None:
    if starts_at >= ends_at:
        raise ValidationError({"ends_at": "The end must be after the start."})
    if starts_at < function.starts_at or ends_at > function.ends_at:
        raise ValidationError({"starts_at": (
            f"The item must fall inside {function.name} "
            f"({timezone.localtime(function.starts_at):%d %b %H:%M} to {timezone.localtime(function.ends_at):%H:%M}).")})


def overlap_warnings(item: ScheduleItem) -> list[str]:
    """Other items the same person is responsible for at the same time. A warning, never an error."""
    if item.responsible_id is None:
        return []
    clashes = (ScheduleItem.objects
               .filter(responsible_id=item.responsible_id, starts_at__lt=item.ends_at, ends_at__gt=item.starts_at)
               .exclude(pk=item.pk).select_related("function", "responsible"))
    return [f"{item.responsible.name} is also responsible for \"{c.title}\" ({c.function.name}, "
            f"{timezone.localtime(c.starts_at):%H:%M}-{timezone.localtime(c.ends_at):%H:%M})." for c in clashes]


# --- check-in --------------------------------------------------------------------------------

def arrival_status(expected_at, grace_minutes: int, arrived_at) -> str:
    on_time = arrived_at <= expected_at + timedelta(minutes=grace_minutes)
    return VendorArrival.Status.ON_TIME if on_time else VendorArrival.Status.LATE


def delay_minutes(arrival: VendorArrival) -> int | None:
    """Minutes after the scheduled time the vendor arrived (0 if early); None while not arrived."""
    if arrival.arrived_at is None:
        return None
    return max(0, int((arrival.arrived_at - arrival.expected_at).total_seconds() // 60))


def create_checkin(wedding, vendor, scheduled_arrival, function: WeddingFunction | None = None,
                   grace_minutes: int | None = None) -> VendorArrival:
    if function is not None and function.wedding_id != wedding.id:
        raise ValidationError({"function_id": "That function belongs to a different wedding."})
    extra = {} if grace_minutes is None else {"grace_minutes": grace_minutes}
    return VendorArrival.objects.create(wedding=wedding, vendor=vendor, function=function,
                                        expected_at=scheduled_arrival, **extra)


def record_arrival(check_in_code: str, arrived_at=None) -> VendorArrival:
    """Mark a vendor arrived. A second call returns the saved record and keeps the first arrival time.

    The row is locked so two simultaneous taps cannot both write. A planner may pass the real `arrived_at`."""
    with transaction.atomic():
        try:
            arrival = VendorArrival.objects.select_for_update().get(check_in_code=check_in_code)
        except VendorArrival.DoesNotExist:
            raise NotFound("This check-in link is not valid.") from None
        if arrival.arrived_at is not None:
            return arrival
        arrival.arrived_at = arrived_at or timezone.now()
        arrival.status = arrival_status(arrival.expected_at, arrival.grace_minutes, arrival.arrived_at)
        arrival.save(update_fields=["arrived_at", "status"])
        return arrival


def late_message(arrival: VendorArrival) -> str:
    where = f" for {arrival.function.name}" if arrival.function_id else f" for {arrival.wedding.title}"
    return f"{arrival.vendor.name} is late{where} (due {timezone.localtime(arrival.expected_at):%H:%M})"


def send_late_alert(arrival: VendorArrival) -> None:
    """Put the alert in the bell icon. Never raises: a failed alert must not stop the job."""
    try:
        Notification.objects.create(message=late_message(arrival), channel="both", severity="warning")
    except Exception:  # noqa: BLE001
        log.exception("Could not send the late alert for vendor arrival %s", arrival.pk)


def mark_late_arrivals(now=None) -> int:
    """Pending vendors past their grace period become LATE, and each one is alerted exactly once.

    The alert is claimed with a single UPDATE ... WHERE late_alert_sent_at IS NULL, so even two
    schedulers running at the same moment cannot both send it. Returns how many alerts were sent."""
    now = now or timezone.now()
    sent = 0
    pending = VendorArrival.objects.filter(status=VendorArrival.Status.PENDING, arrived_at__isnull=True)
    for arrival in pending.select_related("vendor", "function", "wedding"):
        if arrival.expected_at + timedelta(minutes=arrival.grace_minutes) >= now:
            continue
        with transaction.atomic():
            VendorArrival.objects.filter(pk=arrival.pk, status=VendorArrival.Status.PENDING).update(
                status=VendorArrival.Status.LATE)
            claimed = VendorArrival.objects.filter(pk=arrival.pk, late_alert_sent_at__isnull=True).update(
                late_alert_sent_at=now)
        if claimed:
            send_late_alert(arrival)
            sent += 1
    return sent
