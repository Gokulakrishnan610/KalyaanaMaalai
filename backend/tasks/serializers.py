from django.utils import timezone
from rest_framework import serializers

from tasks.models import Priority, Stage, Task


class TaskSerializer(serializers.ModelSerializer):
    assignee_name = serializers.CharField(source="assigned_to.name", read_only=True, default=None)
    function_name = serializers.CharField(source="function.name", read_only=True, default=None)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id", "wedding", "function", "function_name", "title", "description", "assigned_to", "assignee_name",
            "due_date", "stage", "priority", "category", "position", "is_overdue", "created_at",
        ]
        # position changes through the "move" endpoint so the columns stay numbered 0..n
        read_only_fields = ["id", "wedding", "position", "created_at"]

    def get_is_overdue(self, task) -> bool:
        return bool(task.due_date and task.stage != Stage.DONE and task.due_date < timezone.localdate())

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Give the task a title.")
        return value

    def validate_function(self, function):
        wedding_id = self.context.get("wedding_id") or (self.instance and self.instance.wedding_id)
        if function is not None and wedding_id and function.wedding_id != wedding_id:
            raise serializers.ValidationError("That function belongs to a different wedding.")
        return function


class MoveSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Stage.choices)
    position = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class BulkSerializer(serializers.Serializer):
    """Change or delete many tasks at once: {"ids": [1, 2], "delete": true} or {"ids": [1, 2], "stage": "DONE"}."""

    ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=200)
    delete = serializers.BooleanField(default=False)
    stage = serializers.ChoiceField(choices=Stage.choices, required=False)
    priority = serializers.ChoiceField(choices=Priority.choices, required=False)
    assigned_to = serializers.IntegerField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)


class TemplateSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField(default=False)
    items = serializers.ListField(child=serializers.CharField(), required=False, allow_null=True)
