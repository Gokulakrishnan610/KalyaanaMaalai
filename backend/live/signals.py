"""Turns changes into live events, so no other app has to know the live feed exists.

    a task is saved        -> task.updated        (and the new assignee gets an alert)
    a vendor checks in     -> vendor.arrival
    a quotation arrives    -> quotation.received  (planners get an alert)
    a payment is recorded  -> payment.recorded    (planners get an alert)
    an alert is saved      -> notification.new    (shown as a pop-up to its readers)
    an incident changes    -> incident.updated

Events are sent only after the database commit, so a browser that reacts to one always finds the new data.
`silenced()` switches all of this off (used while loading demo data).
"""
import contextvars
from contextlib import contextmanager

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from accounts.models import Role
from enquiries.models import Enquiry, FollowUp
from incidents.models import Incident
from live.alerts import notify_roles
from live.bus import publish
from notifications.models import Notification
from payments.models import Expense, Invoice, Payment
from quotations.models import Quotation
from tasks.models import Task
from weddings.models import ScheduleItem, VendorArrival, WeddingFunction

_silent = contextvars.ContextVar("live_silent", default=False)


@contextmanager
def silenced():
    token = _silent.set(True)
    try:
        yield
    finally:
        _silent.reset(token)


def emit(event_type: str, data: dict, audience: dict | None = None) -> None:
    if _silent.get():
        return
    transaction.on_commit(lambda: publish(event_type, data, audience))


def alert(*args, **kwargs) -> None:
    """A saved notification for planners. Off while tests run, so other tests count only what they create."""
    if not _silent.get() and getattr(settings, "LIVE_ALERTS", True):
        notify_roles(*args, **kwargs)


def _rupees(paise: int) -> str:
    return f"₹{paise / 100:,.0f}"


# --- tasks ---------------------------------------------------------------------------------------------------

@receiver(pre_save, sender=Task)
def remember_assignee(sender, instance, **kwargs):
    old = Task.objects.filter(pk=instance.pk).values_list("assigned_to_id", flat=True).first() if instance.pk else None
    instance._old_assignee = old


@receiver(post_save, sender=Task)
def task_saved(sender, instance, created, **kwargs):
    emit("task.updated", {"wedding_id": instance.wedding_id, "task_id": instance.pk, "title": instance.title,
                          "stage": instance.stage, "assigned_to": instance.assigned_to_id, "created": created})
    new, old = instance.assigned_to_id, getattr(instance, "_old_assignee", None)
    if new and new != old and not _silent.get() and getattr(settings, "LIVE_ALERTS", True):
        from notifications.services import notify
        notify(f"You were assigned a task: {instance.title}", channel="inapp", user_id=new, severity="info")


@receiver(post_delete, sender=Task)
def task_deleted(sender, instance, **kwargs):
    emit("task.updated", {"wedding_id": instance.wedding_id, "task_id": instance.pk, "deleted": True})


# --- wedding day ---------------------------------------------------------------------------------------------

@receiver(post_save, sender=VendorArrival)
def vendor_arrival_saved(sender, instance, **kwargs):
    emit("vendor.arrival", {"wedding_id": instance.wedding_id, "arrival_id": instance.pk,
                            "status": instance.status})


@receiver(post_save, sender=ScheduleItem)
@receiver(post_delete, sender=ScheduleItem)
def schedule_item_changed(sender, instance, **kwargs):
    emit("schedule.updated", {"function_id": instance.function_id})


@receiver(post_save, sender=WeddingFunction)
@receiver(post_delete, sender=WeddingFunction)
def function_changed(sender, instance, **kwargs):
    emit("schedule.updated", {"wedding_id": instance.wedding_id})


# --- quotations ----------------------------------------------------------------------------------------------

@receiver(post_save, sender=Quotation)
def quotation_saved(sender, instance, created, **kwargs):
    wedding = instance.request.wedding
    emit("quotation.received" if created else "quotation.updated",
         {"wedding_id": wedding.id, "request_id": instance.request_id, "quotation_id": instance.pk},
         {"roles": [Role.PLANNER]})
    if created:
        alert(f"New quotation: {instance.vendor.name} quoted {_rupees(instance.total_paise)} "
              f"for {wedding.title} ({instance.request.category.name})", key=f"quotation:{instance.pk}")


# --- money ---------------------------------------------------------------------------------------------------

@receiver(post_save, sender=Payment)
def payment_saved(sender, instance, created, **kwargs):
    emit("payment.recorded", {"wedding_id": instance.wedding_id, "direction": instance.direction,
                              "amount_paise": instance.amount_paise}, {"roles": [Role.PLANNER]})
    if created:
        incoming = instance.direction == Payment.Direction.IN
        alert(f"{'Payment received' if incoming else 'Paid out'}: {_rupees(instance.amount_paise)} "
              f"for {instance.wedding.title}", key=f"payment:{instance.pk}")


@receiver(post_save, sender=Invoice)
@receiver(post_save, sender=Expense)
def finance_changed(sender, instance, **kwargs):
    emit("finance.updated", {"wedding_id": instance.wedding_id}, {"roles": [Role.PLANNER]})


# --- alerts, incidents, enquiries ----------------------------------------------------------------------------

@receiver(post_save, sender=Notification)
def notification_saved(sender, instance, created, **kwargs):
    if created:
        audience = {"users": [instance.user_id]} if instance.user_id else None
        emit("notification.new", {"id": instance.pk, "message": instance.message, "severity": instance.severity},
             audience)


@receiver(post_save, sender=Incident)
@receiver(post_delete, sender=Incident)
def incident_changed(sender, instance, **kwargs):
    emit("incident.updated", {"wedding_id": instance.wedding_id, "incident_id": instance.pk,
                              "status": instance.status})


@receiver(post_save, sender=Enquiry)
@receiver(post_save, sender=FollowUp)
def enquiry_changed(sender, instance, **kwargs):
    emit("enquiry.updated", {"id": instance.pk})
