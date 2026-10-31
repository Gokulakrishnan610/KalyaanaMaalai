from django.contrib import admin

from agreements.models import Agreement


@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):
    list_display = ("title", "wedding", "status", "signed_at")
    list_filter = ("status",)
