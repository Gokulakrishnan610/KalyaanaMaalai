from django.db.models import Q
from rest_framework import viewsets

from clients.models import Client
from clients.serializers import ClientProfileSerializer, ClientSerializer
from common.permissions import Role, allow_roles, read_for_all_write_for


class ClientViewSet(viewsets.ModelViewSet):
    """The couples we work for. Search with ?q= (couple name, phone, city)."""

    def get_queryset(self):
        clients = Client.objects.all().prefetch_related("enquiries", "weddings")
        text = self.request.query_params.get("q")
        if text:
            clients = clients.filter(Q(couple_name__icontains=text) | Q(phone__icontains=text)
                                     | Q(city__icontains=text))
        return clients

    def get_serializer_class(self):
        return ClientProfileSerializer if self.action == "retrieve" else ClientSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [allow_roles()()]
        return [read_for_all_write_for(Role.PLANNER)()]
