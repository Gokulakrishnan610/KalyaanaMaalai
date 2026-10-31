from rest_framework import serializers

from accounts.models import User
from clients.models import Client
from vendors.models import Vendor
from weddings.eventday import delay_minutes
from weddings.models import ScheduleItem, TeamMember, VendorArrival, Venue, Wedding, WeddingFunction
from weddings.services import ROLES, task_counts_by_stage


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["id", "name", "city", "capacity", "address"]


class FunctionSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source="venue.name", read_only=True, default=None)

    class Meta:
        model = WeddingFunction
        fields = ["id", "wedding", "name", "starts_at", "ends_at", "venue", "venue_name", "guest_count"]
        read_only_fields = ["id", "wedding"]

    def validate(self, attrs):
        starts = attrs.get("starts_at", self.instance.starts_at if self.instance else None)
        ends = attrs.get("ends_at", self.instance.ends_at if self.instance else None)
        if starts and ends and ends <= starts:
            raise serializers.ValidationError({"ends_at": "The end must be after the start."})
        return attrs


class TeamMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = TeamMember
        fields = ["id", "user_id", "user_name", "role_label"]


class AssignmentInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role_label = serializers.ChoiceField(choices=ROLES)


class AssignmentListSerializer(serializers.Serializer):
    """The body of PUT /weddings/{id}/assignments/ is a bare list; this checks it as a whole."""

    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError("Send a list of {user_id, role_label}.")
        rows = AssignmentInputSerializer(data=data, many=True)
        rows.is_valid(raise_exception=True)
        rows = rows.validated_data
        ids = [row["user_id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("A person can only have one role on a wedding.")
        found = set(User.objects.filter(pk__in=ids, is_active=True).values_list("id", flat=True))
        missing = sorted(set(ids) - found)
        if missing:
            raise serializers.ValidationError(f"Unknown or inactive user ids: {missing}.")
        return rows


class WeddingSerializer(serializers.ModelSerializer):
    """List and form shape. `default_functions` is only used when creating."""

    client_name = serializers.CharField(source="client.couple_name", read_only=True)
    progress_pct = serializers.SerializerMethodField()
    next_function_date = serializers.SerializerMethodField()
    default_functions = serializers.BooleanField(write_only=True, required=False, default=False)
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    contracted_guests = serializers.IntegerField(required=False, min_value=0)

    class Meta:
        model = Wedding
        fields = [
            "id", "title", "client", "client_name", "start_date", "end_date", "city", "guest_count",
            "contracted_guests", "per_guest_rate_paise", "budget_paise", "status", "progress_pct",
            "next_function_date", "default_functions", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_progress_pct(self, wedding) -> int:
        total = getattr(wedding, "task_total", None)
        if total is None:
            return 0
        return round(wedding.task_done * 100 / total) if total else 0

    def get_next_function_date(self, wedding):
        at = getattr(wedding, "next_function_at", None)
        return at.date().isoformat() if at else None

    def validate_guest_count(self, value):
        if value <= 0:
            raise serializers.ValidationError("There must be at least 1 guest.")
        return value

    def validate_budget_paise(self, value):
        if value < 0:
            raise serializers.ValidationError("Budget cannot be negative.")
        return value

    def validate_per_guest_rate_paise(self, value):
        if value < 0:
            raise serializers.ValidationError("The rate cannot be negative.")
        return value

    def validate(self, attrs):
        start = attrs.get("start_date", self.instance.start_date if self.instance else None)
        end = attrs.get("end_date", self.instance.end_date if self.instance else None)
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "The end date cannot be before the start date."})
        if self.instance is None and attrs.get("contracted_guests") is None:
            attrs["contracted_guests"] = attrs.get("guest_count")
        return attrs


class WeddingDetailSerializer(WeddingSerializer):
    functions = FunctionSerializer(many=True, read_only=True)
    assignments = serializers.SerializerMethodField()
    task_counts = serializers.SerializerMethodField()

    class Meta(WeddingSerializer.Meta):
        fields = WeddingSerializer.Meta.fields + ["functions", "assignments", "task_counts"]

    def get_assignments(self, wedding):
        return TeamMemberSerializer(wedding.team.select_related("user").order_by("id"), many=True).data

    def get_task_counts(self, wedding) -> dict:
        return task_counts_by_stage(wedding.id)


class ScheduleItemSerializer(serializers.ModelSerializer):
    responsible_name = serializers.CharField(source="responsible.name", read_only=True, default=None)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)

    class Meta:
        model = ScheduleItem
        fields = ["id", "function", "starts_at", "ends_at", "title", "responsible", "responsible_name",
                  "vendor", "vendor_name", "notes"]
        read_only_fields = ["id", "function"]


class CheckinCreateSerializer(serializers.Serializer):
    vendor_id = serializers.PrimaryKeyRelatedField(queryset=Vendor.objects.all(), source="vendor")
    function_id = serializers.PrimaryKeyRelatedField(queryset=WeddingFunction.objects.all(), source="function",
                                                     required=False, allow_null=True)
    scheduled_arrival = serializers.DateTimeField()
    grace_minutes = serializers.IntegerField(min_value=0, max_value=720, required=False)


class CheckinSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    function_name = serializers.CharField(source="function.name", read_only=True, default=None)
    scheduled_arrival = serializers.DateTimeField(source="expected_at")
    actual_arrival = serializers.DateTimeField(source="arrived_at", read_only=True)
    token = serializers.CharField(source="check_in_code", read_only=True)
    public_path = serializers.SerializerMethodField()
    delay_minutes = serializers.SerializerMethodField()

    class Meta:
        model = VendorArrival
        fields = ["id", "wedding", "vendor", "vendor_name", "function", "function_name", "scheduled_arrival",
                  "actual_arrival", "grace_minutes", "status", "delay_minutes", "token", "public_path"]
        read_only_fields = ["id", "wedding", "vendor", "function", "status"]

    def get_public_path(self, arrival) -> str:
        return f"/checkin/{arrival.check_in_code}"

    def get_delay_minutes(self, arrival) -> int | None:
        return delay_minutes(arrival)


class CheckinUpdateSerializer(serializers.Serializer):
    """Planner changes: mark arrived (optionally with the real time), or fix the schedule."""

    arrived = serializers.BooleanField(required=False)
    actual_arrival = serializers.DateTimeField(required=False)
    scheduled_arrival = serializers.DateTimeField(required=False)
    grace_minutes = serializers.IntegerField(min_value=0, max_value=720, required=False)
