from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from clients.models import Client
from clients.serializers import ClientProfileSerializer, ClientSerializer
from clients.services import find_client
from common.permissions import Role, allow_roles, read_for_all_write_for


class ClientViewSet(viewsets.ModelViewSet):
    """The couples we work for. Search with ?q= (couple or client name, spouse, email, phone, city)."""

    def get_queryset(self):
        clients = Client.objects.all().prefetch_related("enquiries", "weddings")
        text = self.request.query_params.get("q")
        if text:
            clients = clients.filter(Q(couple_name__icontains=text) | Q(client_name__icontains=text)
                                     | Q(spouse_name__icontains=text) | Q(email__icontains=text)
                                     | Q(phone__icontains=text) | Q(city__icontains=text))
        return clients

    @action(detail=False, methods=["get"])
    def lookup(self, request):
        """Is this person already a client? GET /clients/lookup/?client_name=...&email=... (both are needed)."""
        client = find_client(request.query_params.get("client_name", ""), request.query_params.get("email", ""))
        return Response({"client": ClientSerializer(client).data if client else None})

    def get_serializer_class(self):
        return ClientProfileSerializer if self.action == "retrieve" else ClientSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [allow_roles()()]
        return [read_for_all_write_for(Role.PLANNER)()]
