from django.contrib import admin

from weddings.models import (
    ScheduleItem,
    TeamMember,
    VendorArrival,
    VendorRating,
    Venue,
    Wedding,
    WeddingFunction,
)


class FunctionInline(admin.TabularInline):
    model = WeddingFunction
    extra = 0


@admin.register(Wedding)
class WeddingAdmin(admin.ModelAdmin):
    list_display = ["title", "client", "start_date", "city", "guest_count", "status"]
    list_filter = ["status", "city"]
    inlines = [FunctionInline]


admin.site.register([Venue, TeamMember, ScheduleItem, VendorArrival, VendorRating])
