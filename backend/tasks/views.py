from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from common.permissions import Role, read_for_all_write_for
from tasks.models import Stage, Task
from tasks.serializers import BulkSerializer, MoveSerializer, TaskSerializer, TemplateSerializer
from tasks.services import create_tasks_from_template, move_task, next_position, preview_tasks_from_template
from weddings.models import Wedding

PERMISSION = [read_for_all_write_for(Role.PLANNER)]


class WeddingTaskList(generics.ListCreateAPIView):
    """Tasks of one wedding. Filter with ?stage= ?assignee_id= ?function_id= ?overdue=true. Not paginated."""

    serializer_class = TaskSerializer
    permission_classes = PERMISSION
    pagination_class = None

    def get_queryset(self):
        tasks = (Task.objects.filter(wedding_id=self.kwargs["wedding_id"])
                 .select_related("assigned_to", "function").order_by("stage", "position", "id"))
        params = self.request.query_params
        if params.get("stage"):
            tasks = tasks.filter(stage=params["stage"])
        if params.get("assignee_id"):
            tasks = tasks.filter(assigned_to_id=params["assignee_id"])
        if params.get("function_id"):
            tasks = tasks.filter(function_id=params["function_id"])
        if params.get("overdue") in ("true", "1"):
            tasks = tasks.filter(due_date__lt=timezone.localdate()).exclude(stage=Stage.DONE)
        return tasks

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "wedding_id": int(self.kwargs["wedding_id"])}

    def perform_create(self, serializer):
        with transaction.atomic():
            try:
                wedding = Wedding.objects.select_for_update().get(pk=self.kwargs["wedding_id"])
            except Wedding.DoesNotExist:
                raise NotFound("Wedding not found.") from None
            stage = serializer.validated_data.get("stage", Stage.TO_PLAN)
            serializer.save(wedding=wedding, position=next_position(wedding.id, stage))


class TaskDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.select_related("assigned_to", "function")
    serializer_class = TaskSerializer
    permission_classes = PERMISSION
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def perform_update(self, serializer):
        new_stage = serializer.validated_data.pop("stage", None)
        with transaction.atomic():
            task = serializer.save()
            if new_stage and new_stage != task.stage:
                move_task(task.id, new_stage)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(self.get_serializer(self.get_object()).data)


class TaskMove(APIView):
    """PATCH {"stage": "IN_PROGRESS", "position": 2}: move a card and renumber the columns."""

    permission_classes = PERMISSION

    @extend_schema(request=MoveSerializer, responses=TaskSerializer)
    def patch(self, request, pk):
        body = MoveSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        if not Task.objects.filter(pk=pk).exists():
            raise NotFound("Task not found.")
        task = move_task(pk, body.validated_data["stage"], body.validated_data.get("position"))
        return Response(TaskSerializer(task).data)


class TaskBulk(APIView):
    permission_classes = PERMISSION

    @extend_schema(request=BulkSerializer, responses=dict)
    def post(self, request):
        body = BulkSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        if data["delete"] and request.user.role != Role.FOUNDER:
            return Response({"detail": "Only the founder can delete tasks in bulk."},
                            status=status.HTTP_403_FORBIDDEN)
        if data.get("assigned_to") and not User.objects.filter(pk=data["assigned_to"]).exists():
            return Response({"assigned_to": ["User not found."]}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            tasks = Task.objects.filter(pk__in=data["ids"])
            if data["delete"]:
                count = tasks.count()
                tasks.delete()
                return Response({"deleted": count})
            fields = {key: data[key] for key in ("priority", "due_date") if key in data}
            if "assigned_to" in data:
                fields["assigned_to_id"] = data["assigned_to"]
            updated = tasks.update(**fields) if fields else tasks.count()
            if "stage" in data:
                for task in tasks.order_by("id"):
                    if task.stage != data["stage"]:
                        move_task(task.id, data["stage"])
        return Response({"updated": updated})


class TaskFromTemplate(APIView):
    """POST with ?dry_run=true (or {"dry_run": true}) to preview; without it the missing tasks are created.
    Calling it twice never adds duplicates."""

    permission_classes = PERMISSION

    @extend_schema(request=TemplateSerializer, responses=dict)
    def post(self, request, wedding_id):
        data = dict(request.data) if hasattr(request.data, "keys") else {}
        data = {key: (value[0] if isinstance(value, list) and key == "dry_run" else value)
                for key, value in data.items()}
        if "dry_run" in request.query_params:
            data["dry_run"] = request.query_params["dry_run"]
        options = TemplateSerializer(data=data)
        options.is_valid(raise_exception=True)
        items = options.validated_data.get("items")
        if options.validated_data["dry_run"]:
            planned = preview_tasks_from_template(wedding_id, items)
            for row in planned:
                row["due_date"] = row["due_date"].isoformat()
                row["assigned_to"] = row.pop("assigned_to_id")
            return Response({"dry_run": True, "count": len(planned), "tasks": planned})
        created = create_tasks_from_template(wedding_id, items)
        return Response({"dry_run": False, "count": len(created),
                         "tasks": TaskSerializer(created, many=True).data}, status=status.HTTP_201_CREATED)
