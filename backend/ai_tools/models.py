from django.db import models


class AIJob(models.Model):
    """A record of each AI request (quotation reading, checklist writing) for debugging."""

    kind = models.CharField(max_length=40)
    input = models.JSONField(default=dict)
    output = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind} ({self.status})"
