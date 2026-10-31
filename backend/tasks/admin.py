from django.contrib import admin

from tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "wedding", "assigned_to", "stage", "due_date"]
    list_filter = ["stage", "priority"]
