"""The steps of an incident. Each one saves the change, adds a line to the history and alerts the right people."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import User
from incidents.models import Incident, IncidentStatus, IncidentUpdate, Severity
from live.alerts import notify_roles
from notifications.services import notify


def _log(incident: Incident, author, message: str) -> None:
    IncidentUpdate.objects.create(incident=incident, author=author, message=message)


def _where(incident: Incident) -> str:
    return incident.wedding.title


@transaction.atomic
def report(incident: Incident, reporter: User) -> Incident:
    """Save a new incident and alert every planner at once. Serious ones also go to Telegram."""
    incident.reported_by = reporter
    incident.save()
    _log(incident, reporter, "Reported the incident.")
    serious = incident.severity in (Severity.HIGH, Severity.CRITICAL)
    notify_roles(
        f"Incident at {_where(incident)}: {incident.title} ({incident.get_severity_display().lower()})",
        severity="critical" if serious else "warning", key=f"incident:{incident.pk}:new",
        channel="both" if serious else "inapp",
    )
    return incident


@transaction.atomic
def assign(incident: Incident, assignee: User, by: User) -> Incident:
    incident.assigned_to = assignee
    if incident.status == IncidentStatus.OPEN:
        incident.status = IncidentStatus.ASSIGNED
    incident.save()
    _log(incident, by, f"Assigned to {assignee.name}.")
    if assignee.id != by.id:
        notify(f"You were assigned an incident at {_where(incident)}: {incident.title}", channel="inapp",
               user_id=assignee.id, severity="warning")
    return incident


@transaction.atomic
def change_status(incident: Incident, status: str, by: User, note: str = "") -> Incident:
    if status not in IncidentStatus.values:
        raise ValidationError({"status": "Choose Open, Assigned, In progress or Resolved."})
    if status == incident.status and not note:
        return incident
    incident.status = status
    incident.resolved_at = timezone.now() if status == IncidentStatus.RESOLVED else None
    incident.save()
    label = IncidentStatus(status).label
    _log(incident, by, f"Marked as {label.lower()}." + (f" {note}" if note else ""))
    if status == IncidentStatus.RESOLVED and incident.reported_by_id and incident.reported_by_id != by.id:
        notify(f"Resolved: {incident.title} at {_where(incident)}", channel="inapp",
               user_id=incident.reported_by_id, severity="info")
    return incident


def add_note(incident: Incident, by: User, note: str) -> Incident:
    if not note.strip():
        raise ValidationError({"note": "Write something first."})
    _log(incident, by, note.strip())
    incident.save(update_fields=["updated_at"])  # so everyone's screen refreshes the history
    return incident
