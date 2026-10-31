from django.conf import settings
from django.db import models


class Notification(models.Model):
    """An alert shown in the bell icon (and optionally sent to Telegram)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE,
                             related_name="notifications")  # empty = shown to everyone
    message = models.TextField()
    channel = models.CharField(max_length=20, default="inapp")
    severity = models.CharField(max_length=20, default="info")
    read_at = models.DateTimeField(null=True, blank=True)
    # lets a timed job send the same alert only once (e.g. "due:expense:7:2026-11-02")
    dedupe_key = models.CharField(max_length=120, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message[:60]
