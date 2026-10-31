from django.conf import settings
from django.db import models


class Stage(models.TextChoices):
    TO_PLAN = "TO_PLAN", "To plan"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    READY = "READY", "Ready"
    DONE = "DONE", "Done"


class Priority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"


class Task(models.Model):
    """One to-do item for a wedding, shown on the task board."""

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.CASCADE, related_name="tasks")
    function = models.ForeignKey("weddings.WeddingFunction", null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="tasks")
    due_date = models.DateField(null=True, blank=True, db_index=True)
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.TO_PLAN, db_index=True)
    priority = models.CharField(max_length=6, choices=Priority.choices, default=Priority.MEDIUM)
    category = models.CharField(max_length=60, blank=True)
    position = models.PositiveIntegerField(default=0)  # order inside its column on the board
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["stage", "position"]

    def __str__(self):
        return self.title
