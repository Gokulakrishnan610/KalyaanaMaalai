from django.contrib import admin

from incidents.models import Incident, IncidentUpdate


class UpdateInline(admin.TabularInline):
    model = IncidentUpdate
    extra = 0


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ["title", "wedding", "severity", "status", "assigned_to", "created_at"]
    list_filter = ["status", "severity"]
    inlines = [UpdateInline]
