from django.contrib import admin

from quotations.models import Quotation, QuotationItem, QuotationRequest, WeddingVendor


class ItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 0


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ["vendor", "request", "total_paise", "price_per_plate_paise", "status"]
    inlines = [ItemInline]


admin.site.register([QuotationRequest, WeddingVendor])
