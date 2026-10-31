from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from agreements import services
from agreements.models import Agreement
from agreements.serializers import AgreementSerializer
from common.permissions import Role, read_for_all_write_for
from weddings.models import Wedding


class AgreementViewSet(viewsets.ModelViewSet):
    """Service agreements. Filter with ?wedding=<id> and ?status=. Only drafts can be edited."""

    serializer_class = AgreementSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        agreements = Agreement.objects.select_related("wedding__client")
        params = self.request.query_params
        if params.get("wedding"):
            agreements = agreements.filter(wedding_id=params["wedding"])
        if params.get("status"):
            agreements = agreements.filter(status=params["status"])
        return agreements

    def get_permissions(self):
        return [read_for_all_write_for(Role.PLANNER)()]

    def create(self, request, *args, **kwargs):
        wedding = Wedding.objects.select_related("client").get(pk=request.data.get("wedding"))
        agreement = services.create_draft(wedding, request.user, request.data.get("title", ""), request.data.get("body", ""))
        return Response(self.get_serializer(agreement).data, status=201)

    def partial_update(self, request, *args, **kwargs):
        agreement = services.update_draft(self.get_object(), request.data.get("title"), request.data.get("body"))
        return Response(self.get_serializer(agreement).data)

    @action(detail=False, methods=["get"], url_path="standard-text")
    def standard_text(self, request):
        """The standard terms filled in for a wedding: ?wedding=<id>."""
        wedding = Wedding.objects.select_related("client").get(pk=request.query_params.get("wedding"))
        return Response({"body": services.default_body(wedding)})

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        return Response(self.get_serializer(services.send(self.get_object(), request.user)).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return Response(self.get_serializer(services.void(self.get_object())).data)
