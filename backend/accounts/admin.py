from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class UserAdminPage(UserAdmin):
    list_display = ["name", "email", "role", "is_active"]
    ordering = ["name"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Details", {"fields": ["name", "role"]}),
        ("Access", {"fields": ["is_active", "is_staff", "is_superuser"]}),
    ]
    add_fieldsets = [(None, {"classes": ["wide"], "fields": ["email", "name", "role", "password1", "password2"]})]
    search_fields = ["email", "name"]
    filter_horizontal = []
    list_filter = ["role", "is_active"]
