from rest_framework import serializers

from incidents.models import Incident, IncidentStatus, IncidentUpdate


class IncidentUpdateSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True, default="")

    class Meta:
        model = IncidentUpdate
        fields = ["id", "author", "author_name", "message", "created_at"]


class IncidentSerializer(serializers.ModelSerializer):
    wedding_title = serializers.CharField(source="wedding.title", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default="")
    reported_by_name = serializers.CharField(source="reported_by.name", read_only=True, default="")
    assigned_to_name = serializers.CharField(source="assigned_to.name", read_only=True, default="")
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = ["id", "wedding", "wedding_title", "function", "vendor", "vendor_name", "title", "description",
                  "severity", "status", "is_open", "reported_by", "reported_by_name", "assigned_to",
                  "assigned_to_name", "created_at", "updated_at", "resolved_at"]
        # status, assignee and reporter change through the dedicated actions so each change is logged and alerted
        read_only_fields = ["id", "status", "reported_by", "assigned_to", "created_at", "updated_at",
                            "resolved_at"]

    def get_is_open(self, incident):
        return incident.status != IncidentStatus.RESOLVED

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Say what the problem is.")
        return value.strip()


class IncidentDetailSerializer(IncidentSerializer):
    updates = IncidentUpdateSerializer(many=True, read_only=True)

    class Meta(IncidentSerializer.Meta):
        fields = IncidentSerializer.Meta.fields + ["updates"]


class AssignSerializer(serializers.Serializer):
    user = serializers.IntegerField()


class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=IncidentStatus.choices)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class NoteSerializer(serializers.Serializer):
    note = serializers.CharField()
