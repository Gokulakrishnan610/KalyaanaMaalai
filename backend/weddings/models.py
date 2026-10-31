import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


def new_check_in_code() -> str:
    return uuid.uuid4().hex


class WeddingStatus(models.TextChoices):
    PLANNING = "PLANNING", "Planning"
    CONFIRMED = "CONFIRMED", "Confirmed"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class Venue(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Wedding(models.Model):
    """One wedding we are planning. Almost everything else hangs off this."""

    title = models.CharField(max_length=200)
    client = models.ForeignKey("clients.Client", on_delete=models.PROTECT, related_name="weddings")
    start_date = models.DateField()
    end_date = models.DateField()
    city = models.CharField(max_length=120)
    guest_count = models.PositiveIntegerField()
    contracted_guests = models.PositiveIntegerField()  # guests the agreement was signed for
    per_guest_rate_paise = models.BigIntegerField(default=0)  # charged for each extra guest
    budget_paise = models.BigIntegerField(default=0)
    status = models.CharField(max_length=10, choices=WeddingStatus.choices, default=WeddingStatus.PLANNING,
                              db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_date"]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F("start_date")), name="wedding_end_after_start"),
            models.CheckConstraint(condition=Q(guest_count__gt=0), name="wedding_has_guests"),
        ]

    def __str__(self):
        return self.title


class WeddingFunction(models.Model):
    """One event inside a wedding: Mehendi, Sangeet, Reception ..."""

    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name="functions")
    name = models.CharField(max_length=120)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    venue = models.ForeignKey(Venue, null=True, blank=True, on_delete=models.SET_NULL)
    guest_count = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.wedding.title} - {self.name}"


class TeamMember(models.Model):
    """Which of our staff work on a wedding, and in what role."""

    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name="team")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role_label = models.CharField(max_length=60)  # e.g. Lead planner, Decor lead

    class Meta:
        constraints = [models.UniqueConstraint(fields=["wedding", "user"], name="one_role_per_person")]

    def __str__(self):
        return f"{self.user.name} - {self.role_label}"


class ScheduleItem(models.Model):
    """A minute-by-minute entry in a function's run sheet."""

    function = models.ForeignKey(WeddingFunction, on_delete=models.CASCADE, related_name="schedule")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    title = models.CharField(max_length=255)
    responsible = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL)
    vendor = models.ForeignKey("vendors.Vendor", null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["starts_at"]
        constraints = [models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")),
                                              name="schedule_end_after_start")]

    def __str__(self):
        return self.title


class VendorArrival(models.Model):
    """Tracks whether a vendor turned up on time on the wedding day."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Not arrived yet"
        ON_TIME = "ON_TIME", "On time"
        LATE = "LATE", "Late"

    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name="vendor_arrivals")
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE)
    function = models.ForeignKey(WeddingFunction, null=True, blank=True, on_delete=models.SET_NULL)
    expected_at = models.DateTimeField()
    arrived_at = models.DateTimeField(null=True, blank=True)
    grace_minutes = models.PositiveIntegerField(default=15)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    check_in_code = models.CharField(max_length=64, unique=True, default=new_check_in_code)
    late_alert_sent_at = models.DateTimeField(null=True, blank=True)  # so we alert only once

    class Meta:
        ordering = ["expected_at"]

    def __str__(self):
        return f"{self.vendor.name} ({self.get_status_display()})"


class VendorRating(models.Model):
    """How a vendor performed at one wedding (each score 1 to 5)."""

    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE, related_name="ratings")
    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name="vendor_ratings")
    punctuality = models.PositiveSmallIntegerField()
    quality = models.PositiveSmallIntegerField()
    pricing = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["vendor", "wedding"], name="one_rating_per_vendor_per_wedding"),
            models.CheckConstraint(
                condition=Q(punctuality__range=(1, 5), quality__range=(1, 5), pricing__range=(1, 5)),
                name="rating_between_1_and_5",
            ),
        ]
