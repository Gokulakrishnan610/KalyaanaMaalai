from django.db import models
from django.db.models import Q
from django.utils import timezone


class PayStatus(models.TextChoices):
    UNPAID = "UNPAID", "Unpaid"
    PARTIAL = "PARTIAL", "Partly paid"
    PAID = "PAID", "Paid"


class Invoice(models.Model):
    """Money the couple owes us: deposit, instalments, extra-guest charges."""

    class Kind(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Booking deposit"
        MILESTONE = "MILESTONE", "Instalment"
        EXTRA_GUESTS = "EXTRA_GUESTS", "Extra guests"
        FINAL = "FINAL", "Final payment"

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.PROTECT, related_name="invoices")
    client = models.ForeignKey("clients.Client", on_delete=models.PROTECT, related_name="invoices")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    amount_paise = models.BigIntegerField()
    due_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=8, choices=PayStatus.choices, default=PayStatus.UNPAID, db_index=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount_paise__gte=0), name="invoice_not_negative")]

    def __str__(self):
        return f"{self.get_kind_display()} - {self.wedding.title}"


class Expense(models.Model):
    """Money we owe a vendor (a bill)."""

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.PROTECT, related_name="expenses")
    vendor = models.ForeignKey("vendors.Vendor", null=True, blank=True, on_delete=models.PROTECT)
    category = models.CharField(max_length=80)
    description = models.CharField(max_length=255)
    amount_paise = models.BigIntegerField()
    bill_number = models.CharField(max_length=80, blank=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=8, choices=PayStatus.choices, default=PayStatus.UNPAID, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount_paise__gte=0), name="expense_not_negative"),
            # the same vendor bill can only be entered once, so it cannot be paid twice
            models.UniqueConstraint(fields=["vendor", "bill_number"], condition=~Q(bill_number=""),
                                    name="one_entry_per_vendor_bill"),
        ]

    def __str__(self):
        return self.description


class Payment(models.Model):
    """A payment received from a couple (IN) or made to a vendor (OUT)."""

    class Direction(models.TextChoices):
        IN = "IN", "Received"
        OUT = "OUT", "Paid out"

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.PROTECT, related_name="payments")
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.PROTECT, related_name="payments")
    expense = models.ForeignKey(Expense, null=True, blank=True, on_delete=models.PROTECT, related_name="payments")
    direction = models.CharField(max_length=3, choices=Direction.choices)
    amount_paise = models.BigIntegerField()
    method = models.CharField(max_length=20)  # cash, UPI, bank, card, Razorpay
    reference = models.CharField(max_length=120, blank=True)
    paid_at = models.DateTimeField(default=timezone.now)
    # the Idempotency-Key sent by the website (or "razorpay:<payment id>"): a retry returns the first payment
    retry_key = models.CharField(max_length=80, null=True, blank=True, unique=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount_paise__gt=0), name="payment_is_positive")]


class VendorPaymentPlan(models.Model):
    """Advance and final instalments we owe a vendor once they are selected."""

    class Part(models.TextChoices):
        ADVANCE = "ADVANCE", "Advance"
        FINAL = "FINAL", "Final"

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.CASCADE, related_name="vendor_instalments")
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.PROTECT)
    part = models.CharField(max_length=8, choices=Part.choices)
    amount_paise = models.BigIntegerField()
    due_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=8, choices=PayStatus.choices, default=PayStatus.UNPAID, db_index=True)
    expense = models.ForeignKey(Expense, null=True, blank=True, on_delete=models.SET_NULL)
