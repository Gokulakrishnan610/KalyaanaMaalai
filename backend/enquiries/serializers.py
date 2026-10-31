from django.utils import timezone
from rest_framework import serializers

from common.validators import check_phone
from enquiries.models import Enquiry


class EnquirySerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.couple_name", read_only=True, default=None)
    owner_name = serializers.CharField(source="owner.name", read_only=True, default=None)

    class Meta:
        model = Enquiry
        fields = [
            "id", "couple_name", "phone", "email", "source", "status", "wedding_date", "guest_count",
            "budget_paise", "venue_city", "consultation_at", "notes", "client", "client_name", "owner",
            "owner_name", "created_at",
        ]
        read_only_fields = ["id", "client", "created_at"]  # the client is set by "convert"

    def validate_phone(self, value):
        return check_phone(value)

    def validate_guest_count(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("There must be at least 1 guest.")
        return value

    def validate_budget_paise(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Budget cannot be negative.")
        return value

    def validate_wedding_date(self, value):
        # only check when the date is new or changed, so old enquiries can still be edited
        changed = self.instance is None or self.instance.wedding_date != value
        if value and changed and value < timezone.localdate():
            raise serializers.ValidationError("The wedding date cannot be in the past.")
        return value


class ConvertSerializer(serializers.Serializer):
    """Options for turning an enquiry into a client (and optionally a wedding)."""

    create_wedding = serializers.BooleanField(default=False)
    title = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
