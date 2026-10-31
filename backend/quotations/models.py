from django.db import models
from django.db.models import Q


class RequestStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    CLOSED = "CLOSED", "Closed"


class QuotationStatus(models.TextChoices):
    RECEIVED = "RECEIVED", "Received"
    SELECTED = "SELECTED", "Selected"
    REJECTED = "REJECTED", "Rejected"


class QuotationRequest(models.Model):
    """We ask several vendors of one category (e.g. three caterers) for a price."""

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.CASCADE, related_name="quotation_requests")
    category = models.ForeignKey("vendors.VendorCategory", on_delete=models.PROTECT)
    requirements = models.TextField(blank=True)
    guest_count = models.PositiveIntegerField(null=True, blank=True)
    reply_by = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=6, choices=RequestStatus.choices, default=RequestStatus.OPEN,
                              db_index=True)
    invited_vendors = models.ManyToManyField("vendors.Vendor", blank=True, related_name="quotation_requests")
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wedding.title} - {self.category.name}"


class Quotation(models.Model):
    """One vendor's price for a request."""

    request = models.ForeignKey(QuotationRequest, on_delete=models.CASCADE, related_name="quotations")
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.PROTECT, related_name="quotations")
    total_paise = models.BigIntegerField()
    price_per_plate_paise = models.BigIntegerField(null=True, blank=True)  # for caterers
    menu_notes = models.TextField(blank=True)
    valid_till = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to="quotations/", blank=True)  # the vendor's PDF
    typed_by_hand = models.BooleanField(default=True)  # false when AI read it from the PDF
    status = models.CharField(max_length=8, choices=QuotationStatus.choices, default=QuotationStatus.RECEIVED,
                              db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["request", "vendor"], name="one_quotation_per_vendor"),
            models.CheckConstraint(condition=Q(total_paise__gte=0), name="quotation_total_not_negative"),
        ]

    def __str__(self):
        return f"{self.vendor.name} - {self.total_paise / 100:.0f}"


class QuotationItem(models.Model):
    """A line on a quotation (e.g. 'Welcome drinks x 450')."""

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_paise = models.BigIntegerField()
    total_paise = models.BigIntegerField()


class WeddingVendor(models.Model):
    """The vendor we picked for a wedding (the winning quotation)."""

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.CASCADE, related_name="vendors")
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.PROTECT, related_name="weddings")
    quotation = models.OneToOneField(Quotation, null=True, blank=True, on_delete=models.SET_NULL)
    agreed_amount_paise = models.BigIntegerField()
    status = models.CharField(max_length=20, default="SELECTED")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["wedding", "vendor"], name="vendor_once_per_wedding")]

    def __str__(self):
        return f"{self.vendor.name} for {self.wedding.title}"
