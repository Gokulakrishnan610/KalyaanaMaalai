from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "message", "severity", "channel", "created_at", "read_at", "is_read"]

    def get_is_read(self, obj) -> bool:
        return obj.read_at is not None


def visible_to(user):
    """What this user sees in the bell: their own alerts plus the ones sent to everyone."""
    return Notification.objects.filter(Q(user=user) | Q(user__isnull=True))


class NotificationList(APIView):
    """Newest first. `?unread=1` shows only unread ones; `?limit=` (default 30, max 100)."""

    @extend_schema(responses=dict)
    def get(self, request):
        queryset = visible_to(request.user)
        unread_count = queryset.filter(read_at__isnull=True).count()
        if request.query_params.get("unread") in ("1", "true"):
            queryset = queryset.filter(read_at__isnull=True)
        try:
            limit = min(max(int(request.query_params.get("limit", 30)), 1), 100)
        except ValueError:
            limit = 30
        return Response({"unread_count": unread_count,
                         "results": NotificationSerializer(queryset.order_by("-created_at", "-id")[:limit],
                                                           many=True).data})


class NotificationRead(APIView):
    @extend_schema(request=None, responses=NotificationSerializer)
    def patch(self, request, pk):
        notification = get_object_or_404(visible_to(request.user), pk=pk)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


class NotificationReadAll(APIView):
    @extend_schema(request=None, responses=dict)
    def post(self, request):
        updated = visible_to(request.user).filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"marked_read": updated, "unread_count": 0})
