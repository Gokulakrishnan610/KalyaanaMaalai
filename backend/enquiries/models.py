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


class LostReason(models.TextChoices):
    BUDGET = "BUDGET", "Budget too low"
    COMPETITOR = "COMPETITOR", "Chose another planner"
    DATE = "DATE", "Date not available"
    NO_RESPONSE = "NO_RESPONSE", "No response"
    OTHER = "OTHER", "Other"


# How likely a couple is to book at each stage (like Odoo's stage probability). Won is 100, Lost is 0.
STAGE_WIN_CHANCE = {
    Status.NEW: 10, Status.CONTACTED: 20, Status.CONSULTATION: 40,
    Status.PROPOSAL: 60, Status.WON: 100, Status.LOST: 0,
}


class Enquiry(models.Model):
    """A couple's first contact, before they become a client."""

    couple_name = models.CharField(max_length=200)  # how the couple is shown, e.g. "Rohan & Ishita"
    # the person who got in touch (the client) and their spouse; phone and email below are the client's
    client_name = models.CharField(max_length=200, blank=True)
    spouse_email = models.EmailField(blank=True)
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
    expected_revenue_paise = models.BigIntegerField(null=True, blank=True)  # what we expect to earn from this wedding
    win_chance = models.PositiveSmallIntegerField(default=10)  # percent
    priority = models.PositiveSmallIntegerField(default=0)  # 0 to 3 stars
    expected_close_date = models.DateField(null=True, blank=True)  # when we expect the couple to decide
    lost_reason = models.CharField(max_length=12, choices=LostReason.choices, blank=True)
    # filled in by the couple themselves on the customer website (see the portal app)
    partner_name = models.CharField(max_length=120, blank=True)
    functions_wanted = models.JSONField(default=list, blank=True)  # ["MEHENDI", "SANGEET", ...]
    services_needed = models.JSONField(default=list, blank=True)  # ["CATERING", "DECOR", ...]
    preferred_contact = models.CharField(max_length=10, blank=True)  # CALL, WHATSAPP or EMAIL
    profile_complete = models.BooleanField(default=False)
    client = models.ForeignKey("clients.Client", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="enquiries")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="enquiries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "enquiries"
        indexes = [models.Index(fields=["-created_at"], name="enquiry_newest_first")]

    def __str__(self):
        return f"{self.couple_name} ({self.get_status_display()})"


class FollowUp(models.Model):
    """A planned call, meeting or message for an enquiry (Odoo calls these activities)."""

    class Kind(models.TextChoices):
        CALL = "CALL", "Call"
        MEETING = "MEETING", "Meeting"
        WHATSAPP = "WHATSAPP", "WhatsApp message"
        EMAIL = "EMAIL", "Email"
        TODO = "TODO", "To do"

    enquiry = models.ForeignKey(Enquiry, on_delete=models.CASCADE, related_name="follow_ups")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.CALL)
    summary = models.CharField(max_length=255)
    due_at = models.DateTimeField(db_index=True)
    done_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["done_at", "due_at"]  # open ones first, soonest first

    def __str__(self):
        return f"{self.get_kind_display()}: {self.summary}"
