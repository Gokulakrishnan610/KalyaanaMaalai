from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import Role, allow_roles
from dashboard.services import build_summary


class SummaryView(APIView):
    """Everything the founder's dashboard shows, in one call."""

    permission_classes = [allow_roles(Role.PLANNER)]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(build_summary())
