from django.db import models


class EmailLog(models.Model):
    """Every email we send (or try to), so the team can see what a client was told and when."""

    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    template = models.CharField(max_length=60, db_index=True)
    to = models.EmailField()
    subject = models.CharField(max_length=255)
    html = models.TextField()
    text = models.TextField()
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.QUEUED)
    error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.template} to {self.to} ({self.status})"
