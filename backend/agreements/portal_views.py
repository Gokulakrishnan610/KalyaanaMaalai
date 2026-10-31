"""What the couple sees: their agreements, the emailed code, and signing."""
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from agreements import services
from agreements.models import Agreement
from agreements.serializers import AgreementSerializer, SignSerializer
from portal.views import CustomerView


def client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR")) or None


def mine(customer):
    """Only agreements that were sent to this customer's own client (never drafts)."""
    return Agreement.objects.select_related("wedding__client").filter(wedding__client_id=customer.client_id).exclude(
        status__in=[Agreement.Status.DRAFT, Agreement.Status.VOID]) if customer.client_id else Agreement.objects.none()


class AgreementList(CustomerView):
    def get(self, request):
        return Response(AgreementSerializer(mine(request.user), many=True).data)


class AgreementDetail(CustomerView):
    def get(self, request, pk):
        return Response(AgreementSerializer(get_object_or_404(mine(request.user), pk=pk)).data)


class AgreementCode(CustomerView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "portal_auth"

    def post(self, request, pk):
        services.request_code(get_object_or_404(mine(request.user), pk=pk), request.user.email)
        return Response({"detail": f"We sent a 6-digit code to {request.user.email}."})


class AgreementSign(CustomerView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "portal_auth"

    def post(self, request, pk):
        data = SignSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        agreement = services.sign(get_object_or_404(mine(request.user), pk=pk), email=request.user.email,
                                  ip=client_ip(request), agent=request.META.get("HTTP_USER_AGENT", ""),
                                  **data.validated_data)
        return Response(AgreementSerializer(agreement).data)
