from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import serializers

from payments.models import Expense, Invoice, Payment, VendorPaymentPlan
from payments.services import METHODS

METHOD_CHOICES = [(m, m) for m in METHODS]


def with_paid(queryset):
    """Adds `paid` (whole paise received / paid so far) to invoices or expenses."""
    return queryset.annotate(paid=Coalesce(Sum("payments__amount_paise"), 0))


def _paid(obj) -> int:
    return obj.paid if hasattr(obj, "paid") else sum(p.amount_paise for p in obj.payments.all())


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "wedding_id", "invoice_id", "expense_id", "direction", "amount_paise", "method",
                  "reference", "paid_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="kind")
    type_label = serializers.CharField(source="get_kind_display")
    paid_paise = serializers.SerializerMethodField()
    remaining_paise = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ["id", "wedding_id", "type", "type_label", "amount_paise", "paid_paise", "remaining_paise",
                  "due_date", "status", "note", "created_at"]

    def get_paid_paise(self, obj) -> int:
        return _paid(obj)

    def get_remaining_paise(self, obj) -> int:
        return obj.amount_paise - _paid(obj)


class InvoiceInput(serializers.Serializer):
    type = serializers.ChoiceField(choices=Invoice.Kind.choices)
    amount_paise = serializers.IntegerField(min_value=1)
    due_date = serializers.DateField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)


class InvoicePatch(serializers.Serializer):
    type = serializers.ChoiceField(choices=Invoice.Kind.choices, required=False)
    amount_paise = serializers.IntegerField(min_value=1, required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)


class PaymentInput(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=METHOD_CHOICES)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=120)
    paid_at = serializers.DateTimeField(required=False)


class ExtraGuestsInput(serializers.Serializer):
    actual_guests = serializers.IntegerField(min_value=0)
    due_date = serializers.DateField(required=False, allow_null=True)
    preview = serializers.BooleanField(required=False, default=False)


class ExpenseSerializer(serializers.ModelSerializer):
    vendor_id = serializers.IntegerField(read_only=True)
    vendor_name = serializers.SerializerMethodField()
    bill_ref = serializers.CharField(source="bill_number")
    paid_paise = serializers.SerializerMethodField()
    remaining_paise = serializers.SerializerMethodField()
    overdue = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = ["id", "wedding_id", "vendor_id", "vendor_name", "category", "description", "amount_paise",
                  "paid_paise", "remaining_paise", "bill_ref", "due_date", "status", "overdue", "created_at"]

    def get_overdue(self, obj) -> bool:
        return bool(obj.due_date and obj.due_date < timezone.localdate() and obj.status != "PAID")

    def get_vendor_name(self, obj) -> str:
        return obj.vendor.name if obj.vendor_id else ""

    def get_paid_paise(self, obj) -> int:
        return _paid(obj)

    def get_remaining_paise(self, obj) -> int:
        return obj.amount_paise - _paid(obj)


class ExpenseInput(serializers.Serializer):
    vendor_id = serializers.IntegerField(required=False, allow_null=True)
    category = serializers.CharField(max_length=80)
    description = serializers.CharField(max_length=255)
    amount_paise = serializers.IntegerField(min_value=1)
    bill_ref = serializers.CharField(required=False, allow_blank=True, max_length=80)
    due_date = serializers.DateField(required=False, allow_null=True)


class ExpensePatch(ExpenseInput):
    category = serializers.CharField(max_length=80, required=False)
    description = serializers.CharField(max_length=255, required=False)
    amount_paise = serializers.IntegerField(min_value=1, required=False)


class MilestoneSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name")
    part_label = serializers.CharField(source="get_part_display")
    paid_paise = serializers.SerializerMethodField()
    remaining_paise = serializers.SerializerMethodField()
    overdue = serializers.SerializerMethodField()

    class Meta:
        model = VendorPaymentPlan
        fields = ["id", "wedding_id", "vendor_id", "vendor_name", "expense_id", "part", "part_label",
                  "amount_paise", "paid_paise", "remaining_paise", "due_date", "status", "overdue"]

    def get_paid_paise(self, obj) -> int:
        return self.context.get("covered", {}).get(obj.pk, 0)

    def get_remaining_paise(self, obj) -> int:
        return obj.amount_paise - self.get_paid_paise(obj)

    def get_overdue(self, obj) -> bool:
        return bool(obj.due_date and obj.due_date < timezone.localdate() and obj.status != "PAID")


class MilestonePayInput(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1, required=False)
    method = serializers.ChoiceField(choices=METHOD_CHOICES, default="BANK")
    reference = serializers.CharField(required=False, allow_blank=True, max_length=120)


class RazorpayVerifyInput(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
