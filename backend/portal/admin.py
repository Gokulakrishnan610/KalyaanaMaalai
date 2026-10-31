from django.contrib import admin

from portal.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "phone", "client", "created_at", "last_login_at"]
    search_fields = ["name", "email", "phone"]
    exclude = ["password_hash"]
