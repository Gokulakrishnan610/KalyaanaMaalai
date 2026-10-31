from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from clients.serializers import ClientSerializer
from common.permissions import Role, allow_roles, read_for_all_write_for
from enquiries.models import Enquiry
from enquiries.serializers import ConvertSerializer, EnquirySerializer
from enquiries.services import convert_to_client


class EnquiryViewSet(viewsets.ModelViewSet):
    """Couples who got in touch. Filter with ?status= ?source= and search with ?q=."""

    serializer_class = EnquirySerializer

    def get_queryset(self):
        enquiries = Enquiry.objects.select_related("client", "owner")
        params = self.request.query_params
        if params.get("status"):
            enquiries = enquiries.filter(status=params["status"])
        if params.get("source"):
            enquiries = enquiries.filter(source=params["source"])
        if params.get("q"):
            enquiries = enquiries.filter(Q(couple_name__icontains=params["q"]) | Q(phone__icontains=params["q"]))
        return enquiries

    def get_permissions(self):
        if self.action == "destroy":
            return [allow_roles()()]
        return [read_for_all_write_for(Role.PLANNER)()]

    def perform_create(self, serializer):
        # whoever enters the enquiry owns it, unless they picked someone else
        serializer.save(owner=serializer.validated_data.get("owner") or self.request.user)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Make this enquiry a client (and optionally start the wedding)."""
        options = ConvertSerializer(data=request.data)
        options.is_valid(raise_exception=True)
        client, wedding = convert_to_client(self.get_object(), **options.validated_data)
        return Response({"client": ClientSerializer(client).data, "wedding_id": wedding.id if wedding else None})
