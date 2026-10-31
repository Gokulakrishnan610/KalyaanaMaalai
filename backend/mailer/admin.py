from django.contrib import admin

from mailer.models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "template", "to", "status")
    list_filter = ("template", "status")
    search_fields = ("to", "subject")
    readonly_fields = [f.name for f in EmailLog._meta.fields]
