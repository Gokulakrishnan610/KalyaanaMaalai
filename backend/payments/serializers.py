from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import serializers

from payments.models import Expense, Invoice, Payment, PaymentLink, VendorPaymentPlan
from payments.services import MANUAL_METHODS

# a person can only type in offline methods; RAZORPAY is recorded by the gateway flow, never by hand
METHOD_CHOICES = [(m, m) for m in MANUAL_METHODS]


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

    def validate_paid_at(self, value):
        if value > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError("A payment cannot be dated in the future.")
        return value


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


# ---------------------------------------------------------------- payment links

class PaymentLinkSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.name", read_only=True, default="")

    class Meta:
        model = PaymentLink
        fields = ["id", "invoice_id", "token", "path", "amount_paise", "status", "expires_at", "created_at",
                  "paid_at", "created_by_name"]

    def get_status(self, link) -> str:
        from payments.links import effective_status
        return effective_status(link)

    def get_path(self, link) -> str:
        return f"/pay/{link.token}"  # the website puts its own address in front


class PaymentLinkInput(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1, required=False)
    days = serializers.IntegerField(min_value=1, max_value=60, required=False, default=7)


class PublicOrderResult(serializers.Serializer):
    order_id = serializers.CharField()
    amount = serializers.IntegerField()
    currency = serializers.CharField()
    key_id = serializers.CharField()
    mock = serializers.BooleanField()
    mock_payment_id = serializers.CharField(required=False)
    mock_signature = serializers.CharField(required=False)


# ---------------------------------------------------------------- lists for the Payments page

class InvoiceRowSerializer(InvoiceSerializer):
    """An invoice with the customer's details and its latest payment link, for the all-weddings list."""

    wedding_title = serializers.CharField(source="wedding.title")
    client_name = serializers.CharField(source="client.couple_name")
    client_phone = serializers.CharField(source="client.phone")
    client_email = serializers.CharField(source="client.email")
    overdue = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()

    class Meta(InvoiceSerializer.Meta):
        fields = InvoiceSerializer.Meta.fields + ["wedding_title", "client_name", "client_phone", "client_email",
                                                  "overdue", "link"]

    def get_overdue(self, obj) -> bool:
        return bool(obj.due_date and obj.due_date < timezone.localdate() and obj.status != "PAID")

    def get_link(self, obj):
        latest = next(iter(obj.links.all()), None)  # links are ordered newest first
        return PaymentLinkSerializer(latest).data if latest else None


class VendorBillSerializer(ExpenseSerializer):
    """A vendor bill with its advance and final instalments underneath."""

    wedding_title = serializers.CharField(source="wedding.title")
    instalments = serializers.SerializerMethodField()

    class Meta(ExpenseSerializer.Meta):
        fields = ExpenseSerializer.Meta.fields + ["wedding_title", "instalments"]

    def get_instalments(self, obj):
        plans = sorted(obj.vendorpaymentplan_set.all(), key=lambda p: (p.part, p.pk))
        paid = [(p.amount_paise, p.reference) for p in obj.payments.all()]  # uses the prefetched payments
        from payments.services import allocate_to_plans
        covered = allocate_to_plans(plans, paid)
        return MilestoneSerializer(plans, many=True, context={"covered": covered}).data


class LedgerSerializer(serializers.ModelSerializer):
    """One line of the payment history: money in from a customer, or money out to a vendor."""

    wedding_title = serializers.CharField(source="wedding.title")
    party = serializers.SerializerMethodField()
    what = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    recorded_by_name = serializers.CharField(source="recorded_by.name", read_only=True, default="")
    can_undo = serializers.SerializerMethodField()
    reference = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["id", "wedding_id", "wedding_title", "direction", "party", "what", "amount_paise", "method",
                  "reference", "paid_at", "source", "recorded_by_name", "can_undo"]

    def get_reference(self, obj) -> str:
        # "milestone:7" is a private tag that links a payment to an instalment: people should not see it
        return "" if obj.reference.startswith("milestone:") else obj.reference

    def get_party(self, obj) -> str:
        if obj.invoice_id:
            return obj.invoice.client.couple_name
        return obj.expense.vendor.name if obj.expense and obj.expense.vendor_id else (obj.expense.description if obj.expense else "")

    def get_what(self, obj) -> str:
        if obj.invoice_id:
            return obj.invoice.get_kind_display()
        return obj.expense.description if obj.expense else ""

    def get_source(self, obj) -> str:
        if getattr(obj, "payment_link", None):
            return "LINK"  # the customer paid through a payment link
        return "ONLINE" if obj.method == "RAZORPAY" else "MANUAL"

    def get_can_undo(self, obj) -> bool:
        return obj.method != "RAZORPAY"
