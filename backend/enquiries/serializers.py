from django.utils import timezone
from rest_framework import serializers

from common.validators import check_phone
from enquiries.models import STAGE_WIN_CHANCE, Enquiry, FollowUp, Status


class EnquirySerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.couple_name", read_only=True, default=None)
    owner_name = serializers.CharField(source="owner.name", read_only=True, default=None)

    next_follow_up = serializers.SerializerMethodField()

    class Meta:
        model = Enquiry
        fields = [
            "id", "couple_name", "phone", "email", "source", "status", "wedding_date", "guest_count",
            "budget_paise", "venue_city", "consultation_at", "notes", "expected_revenue_paise", "win_chance",
            "priority", "expected_close_date", "lost_reason", "next_follow_up", "client", "client_name",
            "owner", "owner_name", "created_at",
        ]
        read_only_fields = ["id", "client", "created_at"]  # the client is set by "convert"

    def get_next_follow_up(self, enquiry):
        """Due time of the earliest follow-up that is not done yet (None if there is none)."""
        if hasattr(enquiry, "next_follow_up_at"):  # the list view fills this in with one query
            return enquiry.next_follow_up_at
        open_ones = enquiry.follow_ups.filter(done_at__isnull=True).order_by("due_at").first()
        return open_ones.due_at if open_ones else None

    def validate_phone(self, value):
        return check_phone(value)

    def validate_priority(self, value):
        if not 0 <= value <= 3:
            raise serializers.ValidationError("Priority is 0 to 3 stars.")
        return value

    def validate_win_chance(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Win chance is a percentage from 0 to 100.")
        return value

    def validate(self, attrs):
        current = self.instance.status if self.instance else None
        status = attrs.get("status", current or Status.NEW)
        if "status" in attrs and attrs["status"] != current and "win_chance" not in attrs:
            attrs["win_chance"] = STAGE_WIN_CHANCE[status]  # a new stage resets the chance, unless set by hand
        if status == Status.LOST:
            reason = attrs.get("lost_reason", self.instance.lost_reason if self.instance else "")
            if not reason:
                raise serializers.ValidationError({"lost_reason": "Say why this enquiry was lost."})
        return attrs

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


class FollowUpSerializer(serializers.ModelSerializer):
    enquiry_name = serializers.CharField(source="enquiry.couple_name", read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = FollowUp
        fields = ["id", "enquiry", "enquiry_name", "kind", "summary", "due_at", "done_at", "is_overdue",
                  "created_at"]
        read_only_fields = ["id", "done_at", "created_at"]

    def get_is_overdue(self, follow_up):
        return follow_up.done_at is None and follow_up.due_at < timezone.now()
