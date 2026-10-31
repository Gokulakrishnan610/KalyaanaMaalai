from django.conf import settings
from django.db import models


class Source(models.TextChoices):
    CALL = "CALL", "Phone call"
    INSTAGRAM = "INSTAGRAM", "Instagram"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    REFERRAL = "REFERRAL", "Referral"
    WEBSITE = "WEBSITE", "Website"


class Status(models.TextChoices):
    NEW = "NEW", "New"
    CONTACTED = "CONTACTED", "Contacted"
    CONSULTATION = "CONSULTATION", "Consultation booked"
    PROPOSAL = "PROPOSAL", "Proposal sent"
    WON = "WON", "Won"
    LOST = "LOST", "Lost"


class Enquiry(models.Model):
    """A couple's first contact, before they become a client."""

    couple_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    source = models.CharField(max_length=12, choices=Source.choices, db_index=True)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.NEW, db_index=True)
    wedding_date = models.DateField(null=True, blank=True)
    guest_count = models.PositiveIntegerField(null=True, blank=True)
    budget_paise = models.BigIntegerField(null=True, blank=True)  # money is always whole paise
    venue_city = models.CharField(max_length=120, blank=True)
    consultation_at = models.DateTimeField(null=True, blank=True)  # first meeting
    notes = models.TextField(blank=True)
    client = models.ForeignKey("clients.Client", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="enquiries")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="enquiries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "enquiries"

    def __str__(self):
        return f"{self.couple_name} ({self.get_status_display()})"
