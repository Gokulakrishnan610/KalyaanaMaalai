from django.conf import settings
from django.db import models


class Agreement(models.Model):
    """The service agreement between Shaandaar Events and a couple, signed online.

    The text is fixed once it is sent. When the client signs we keep who, when, from where, a drawn signature, and a
    fingerprint (hash) of the exact text, so any later change to the text can be detected.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SENT = "SENT", "Waiting for signature"
        SIGNED = "SIGNED", "Signed"
        VOID = "VOID", "Cancelled"

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.PROTECT, related_name="agreements")
    title = models.CharField(max_length=200)
    body = models.TextField()  # lines starting with "## " are headings
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    company_signer = models.CharField(max_length=120, blank=True)  # who signs for Shaandaar Events (whoever sent it)

    # what we keep when the client signs
    signed_at = models.DateTimeField(null=True, blank=True)
    signer_name = models.CharField(max_length=120, blank=True)
    signer_email = models.EmailField(blank=True)
    signature = models.TextField(blank=True)  # the drawn signature as a PNG data URL
    signer_ip = models.GenericIPAddressField(null=True, blank=True)
    signer_agent = models.CharField(max_length=300, blank=True)
    body_hash = models.CharField(max_length=64, blank=True)

    # the one-time code emailed before signing (only a hash of it is kept)
    otp_hash = models.CharField(max_length=128, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_tries = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
