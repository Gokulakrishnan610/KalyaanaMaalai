from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, User
from common.permissions import allow_roles
from incidents import services
from incidents.models import Incident, IncidentStatus
from incidents.serializers import (
    AssignSerializer,
    IncidentDetailSerializer,
    IncidentSerializer,
    NoteSerializer,
    StatusSerializer,
)


class IncidentViewSet(viewsets.ModelViewSet):
    """Problems reported during weddings. Filter with ?wedding= ?status= ?open=1 ?mine=1.

    Anyone logged in can report one. Planners assign them and manage them; whoever it is assigned to can
    move it along and resolve it.
    """

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        incidents = Incident.objects.select_related("wedding", "vendor", "reported_by", "assigned_to")
        params = self.request.query_params
        if params.get("wedding"):
            incidents = incidents.filter(wedding_id=params["wedding"])
        if params.get("status"):
            incidents = incidents.filter(status=params["status"])
        if params.get("open"):
            incidents = incidents.exclude(status=IncidentStatus.RESOLVED)
        if params.get("mine"):
            incidents = incidents.filter(assigned_to=self.request.user)
        return incidents.order_by("-created_at")

    def get_serializer_class(self):
        return IncidentDetailSerializer if self.action == "retrieve" else IncidentSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "create", "note"):
            return [IsAuthenticated()]
        if self.action == "status":
            return [IsAuthenticated()]  # checked below: planners or the assignee
        if self.action == "destroy":
            return [allow_roles()()]
        return [allow_roles(Role.PLANNER)()]  # assign, edit

    def perform_create(self, serializer):
        incident = serializer.save()
        services.report(incident, self.request.user)

    @extend_schema(request=AssignSerializer, responses=IncidentSerializer)
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        incident = self.get_object()
        body = AssignSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        assignee = get_object_or_404(User, pk=body.validated_data["user"], is_active=True)
        return Response(IncidentSerializer(services.assign(incident, assignee, request.user)).data)

    @extend_schema(request=StatusSerializer, responses=IncidentSerializer)
    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        incident = self.get_object()
        user = request.user
        if user.role not in (Role.FOUNDER, Role.PLANNER) and incident.assigned_to_id != user.id:
            return Response({"detail": "Only a planner or the person it is assigned to can change this."}, status=403)
        body = StatusSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        updated = services.change_status(incident, body.validated_data["status"], user, body.validated_data["note"])
        return Response(IncidentSerializer(updated).data)

    @extend_schema(request=NoteSerializer, responses=IncidentDetailSerializer)
    @action(detail=True, methods=["post"])
    def note(self, request, pk=None):
        incident = self.get_object()
        body = NoteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        services.add_note(incident, request.user, body.validated_data["note"])
        return Response(IncidentDetailSerializer(self.get_object()).data)
