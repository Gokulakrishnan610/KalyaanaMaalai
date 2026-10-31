from django.conf import settings
from django.db import models


class Severity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class IncidentStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    RESOLVED = "RESOLVED", "Resolved"


class Incident(models.Model):
    """A problem reported during a wedding (for example: the florist needs an extra generator)."""

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.CASCADE, related_name="incidents")
    function = models.ForeignKey("weddings.WeddingFunction", null=True, blank=True, on_delete=models.SET_NULL)
    vendor = models.ForeignKey("vendors.Vendor", null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=8, choices=Severity.choices, default=Severity.MEDIUM, db_index=True)
    status = models.CharField(max_length=12, choices=IncidentStatus.choices, default=IncidentStatus.OPEN,
                              db_index=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="reported_incidents")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="assigned_incidents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class IncidentUpdate(models.Model):
    """One line in an incident's history: who did what, and when."""

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="updates")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
