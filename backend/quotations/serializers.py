from rest_framework import serializers

from quotations.models import Quotation, QuotationItem, QuotationRequest, WeddingVendor
from quotations.services import implied_total
from vendors.models import Vendor, VendorCategory


class ItemSerializer(serializers.ModelSerializer):
    qty = serializers.IntegerField(source="quantity", min_value=1)
    unit_price_paise = serializers.IntegerField(min_value=0)

    class Meta:
        model = QuotationItem
        fields = ["id", "description", "qty", "unit_price_paise", "total_paise"]
        read_only_fields = ["id", "total_paise"]


class QuotationSerializer(serializers.ModelSerializer):
    """What a quotation looks like when sent to the website."""

    request_id = serializers.IntegerField(read_only=True)
    vendor = serializers.SerializerMethodField()
    items = ItemSerializer(many=True, read_only=True)
    implied_total_paise = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    ai_extracted = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = ["id", "request_id", "vendor", "total_paise", "price_per_plate_paise", "implied_total_paise",
                  "menu_notes", "valid_till", "file_url", "ai_extracted", "status", "items", "created_at"]

    def get_vendor(self, quotation):
        return {"id": quotation.vendor_id, "name": quotation.vendor.name}

    def get_implied_total_paise(self, quotation):
        return implied_total(quotation.price_per_plate_paise, bool(quotation.items.all()),
                             quotation.request.guest_count)

    def get_file_url(self, quotation):
        if not quotation.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(quotation.file.url) if request else quotation.file.url

    def get_ai_extracted(self, quotation):
        return not quotation.typed_by_hand


class QuotationInputSerializer(serializers.Serializer):
    """What the 'Add quotation' form sends. `total_paise` is ignored when line items are given."""

    vendor_id = serializers.PrimaryKeyRelatedField(queryset=Vendor.objects.all(), required=False)
    total_paise = serializers.IntegerField(min_value=0, required=False)
    price_per_plate_paise = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    menu_notes = serializers.CharField(required=False, allow_blank=True)
    valid_till = serializers.DateField(required=False, allow_null=True)
    items = ItemSerializer(many=True, required=False)
    ai_extracted = serializers.BooleanField(required=False)

    def validate_items(self, items):
        for item in items:
            if not item["description"].strip():
                raise serializers.ValidationError("Every line needs a description.")
        return items

    def validated_for_service(self):
        """The same data in the names the model uses."""
        data = dict(self.validated_data)
        data.pop("vendor_id", None)
        if "ai_extracted" in data:
            data["typed_by_hand"] = not data.pop("ai_extracted")
        return data


class RequestSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(source="category", queryset=VendorCategory.objects.all())
    category_name = serializers.CharField(source="category.name", read_only=True)
    due_date = serializers.DateField(source="reply_by", required=False, allow_null=True)
    invited_vendor_ids = serializers.PrimaryKeyRelatedField(
        many=True, source="invited_vendors", queryset=Vendor.objects.all(), required=False)
    invited_vendors = serializers.SerializerMethodField()
    received_count = serializers.SerializerMethodField()
    invited_count = serializers.SerializerMethodField()
    wedding_title = serializers.CharField(source="wedding.title", read_only=True)

    class Meta:
        model = QuotationRequest
        fields = ["id", "wedding_id", "wedding_title", "category_id", "category_name", "requirements",
                  "guest_count", "due_date", "status", "sent_at", "created_at", "invited_vendor_ids",
                  "invited_vendors", "received_count", "invited_count"]
        read_only_fields = ["id", "wedding_id", "sent_at", "created_at"]

    def _quotes(self, request):
        return {q.vendor_id: q for q in request.quotations.all()}

    def get_invited_vendors(self, request):
        quotes = self._quotes(request)
        return [{"id": v.id, "name": v.name, "phone": v.phone, "email": v.email,
                 "received": v.id in quotes, "quotation_id": quotes[v.id].id if v.id in quotes else None}
                for v in request.invited_vendors.all()]

    def get_received_count(self, request):
        return len(request.quotations.all())

    def get_invited_count(self, request):
        return len(request.invited_vendors.all())

    def validate(self, attrs):
        category = attrs.get("category") or getattr(self.instance, "category", None)
        wrong = [v.name for v in attrs.get("invited_vendors", []) if category and v.category_id != category.id]
        if wrong:
            raise serializers.ValidationError(
                {"invited_vendor_ids": [f"Not in the {category.name} category: {', '.join(wrong)}."]})
        return attrs


class WeddingVendorSerializer(serializers.ModelSerializer):
    vendor = serializers.SerializerMethodField()
    category = serializers.CharField(source="vendor.category.name", read_only=True)
    request_id = serializers.IntegerField(source="quotation.request_id", read_only=True, default=None)

    class Meta:
        model = WeddingVendor
        fields = ["id", "wedding_id", "vendor", "category", "agreed_amount_paise", "status", "quotation_id",
                  "request_id"]

    def get_vendor(self, booking):
        return {"id": booking.vendor_id, "name": booking.vendor.name}
