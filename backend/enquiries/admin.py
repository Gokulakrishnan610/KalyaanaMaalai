from django.contrib import admin

from enquiries.models import Enquiry


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ["couple_name", "source", "status", "wedding_date", "guest_count"]
    list_filter = ["source", "status"]
    search_fields = ["couple_name", "phone"]
