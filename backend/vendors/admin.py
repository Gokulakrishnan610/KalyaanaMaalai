from django.contrib import admin

from vendors.models import Vendor, VendorCategory


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "city", "phone"]
    list_filter = ["category"]
    search_fields = ["name"]


admin.site.register(VendorCategory)
