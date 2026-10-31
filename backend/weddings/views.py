from django.db import transaction
from django.db.models import ProtectedError, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination
from common.permissions import Role, allow_roles, read_for_all_write_for
from weddings import eventday, services
from weddings.models import ScheduleItem, TeamMember, VendorArrival, Venue, Wedding, WeddingFunction
from weddings.serializers import (
    AssignmentListSerializer,
    CheckinCreateSerializer,
    CheckinSerializer,
    CheckinUpdateSerializer,
    FunctionSerializer,
    ScheduleItemSerializer,
    TeamMemberSerializer,
    VenueSerializer,
    WeddingDetailSerializer,
    WeddingSerializer,
)

PLANNERS = read_for_all_write_for(Role.PLANNER)  # staff may look, planners and the founder change things


class LimitPagination(StandardPagination):
    """Weddings list uses ?page= and ?limit=."""

    page_size_query_param = "limit"


def _wedding_or_404(wedding_id) -> Wedding:
    try:
        return Wedding.objects.get(pk=wedding_id)
    except Wedding.DoesNotExist:
        raise NotFound("Wedding not found.") from None


# --- weddings --------------------------------------------------------------------------------

class WeddingList(generics.ListCreateAPIView):
    """Weddings. Filter with ?status= and search with ?q= (title, city or couple name)."""

    permission_classes = [PLANNERS]
    pagination_class = LimitPagination
    serializer_class = WeddingSerializer

    def get_queryset(self):
        weddings = services.wedding_queryset().order_by("start_date", "id")
        params = self.request.query_params
        if params.get("status"):
            weddings = weddings.filter(status=params["status"])
        if params.get("q"):
            q = params["q"]
            weddings = weddings.filter(Q(title__icontains=q) | Q(city__icontains=q)
                                       | Q(client__couple_name__icontains=q))
        return weddings

    def create(self, request, *args, **kwargs):
        body = WeddingSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = dict(body.validated_data)
        with_functions = data.pop("default_functions", False)
        wedding = services.create_wedding(data, default_functions=with_functions)
        return Response(WeddingDetailSerializer(services.get_wedding(wedding.id)).data,
                        status=status.HTTP_201_CREATED)


class WeddingDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WeddingDetailSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return services.wedding_queryset().prefetch_related("functions__venue")

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [allow_roles()()]  # founder only
        return [PLANNERS()]

    def perform_update(self, serializer):
        serializer.validated_data.pop("default_functions", None)
        serializer.save()

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(WeddingDetailSerializer(services.get_wedding(kwargs["pk"])).data)

    def destroy(self, request, *args, **kwargs):
        wedding = self.get_object()
        if services.has_invoices(wedding):
            return Response({"detail": "This wedding has invoices, so it cannot be deleted."},
                            status=status.HTTP_409_CONFLICT)
        try:
            Wedding.objects.filter(pk=wedding.pk).delete()
        except ProtectedError:  # expenses or payments also protect a wedding
            return Response({"detail": "This wedding has payments or expenses, so it cannot be deleted."},
                            status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WeddingProgress(APIView):
    permission_classes = [PLANNERS]

    @extend_schema(responses=dict)
    def get(self, request, wedding_id):
        _wedding_or_404(wedding_id)
        return Response(services.wedding_progress(wedding_id))


# --- functions and venues --------------------------------------------------------------------

class WeddingFunctionList(generics.ListCreateAPIView):
    serializer_class = FunctionSerializer
    permission_classes = [PLANNERS]
    pagination_class = None

    def get_queryset(self):
        return WeddingFunction.objects.filter(wedding_id=self.kwargs["wedding_id"]).select_related("venue")

    def perform_create(self, serializer):
        wedding = _wedding_or_404(self.kwargs["wedding_id"])
        serializer.instance = services.save_function(wedding, dict(serializer.validated_data))


class FunctionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = WeddingFunction.objects.select_related("venue")
    serializer_class = FunctionSerializer
    permission_classes = [PLANNERS]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def perform_update(self, serializer):
        serializer.instance = services.save_function(serializer.instance.wedding, dict(serializer.validated_data),
                                                     serializer.instance)


class VenueList(generics.ListCreateAPIView):
    queryset = Venue.objects.all().order_by("name")
    serializer_class = VenueSerializer
    permission_classes = [PLANNERS]
    pagination_class = None


class VenueDetail(generics.RetrieveUpdateAPIView):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [PLANNERS]
    http_method_names = ["get", "patch", "head", "options"]


# --- team ------------------------------------------------------------------------------------

class WeddingAssignments(APIView):
    """GET the team; PUT a full list [{user_id, role_label}] to replace it."""

    permission_classes = [PLANNERS]

    @extend_schema(responses=TeamMemberSerializer(many=True))
    def get(self, request, wedding_id):
        _wedding_or_404(wedding_id)
        team = TeamMember.objects.filter(wedding_id=wedding_id).select_related("user").order_by("id")
        return Response(TeamMemberSerializer(team, many=True).data)

    @extend_schema(request=AssignmentListSerializer, responses=TeamMemberSerializer(many=True))
    def put(self, request, wedding_id):
        wedding = _wedding_or_404(wedding_id)
        rows = AssignmentListSerializer().to_internal_value(request.data)
        services.replace_assignments(wedding, rows)
        team = TeamMember.objects.filter(wedding=wedding).select_related("user").order_by("id")
        return Response(TeamMemberSerializer(team, many=True).data)


# --- schedule --------------------------------------------------------------------------------

class WeddingScheduleList(generics.ListAPIView):
    """Every run-sheet item of the wedding, for the event-day overview."""

    serializer_class = ScheduleItemSerializer
    permission_classes = [PLANNERS]
    pagination_class = None

    def get_queryset(self):
        return (ScheduleItem.objects.filter(function__wedding_id=self.kwargs["wedding_id"])
                .select_related("responsible", "vendor").order_by("starts_at", "id"))


class FunctionScheduleList(generics.ListCreateAPIView):
    serializer_class = ScheduleItemSerializer
    permission_classes = [PLANNERS]
    pagination_class = None

    def get_queryset(self):
        return (ScheduleItem.objects.filter(function_id=self.kwargs["function_id"])
                .select_related("responsible", "vendor").order_by("starts_at", "id"))

    def create(self, request, *args, **kwargs):
        try:
            function = WeddingFunction.objects.get(pk=kwargs["function_id"])
        except WeddingFunction.DoesNotExist:
            raise NotFound("Function not found.") from None
        body = self.get_serializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        eventday.check_schedule_times(function, data["starts_at"], data["ends_at"])
        item = ScheduleItem.objects.create(function=function, **data)
        return Response({**ScheduleItemSerializer(item).data, "warnings": eventday.overlap_warnings(item)},
                        status=status.HTTP_201_CREATED)


class ScheduleItemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = ScheduleItem.objects.select_related("function", "responsible", "vendor")
    serializer_class = ScheduleItemSerializer
    permission_classes = [PLANNERS]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def update(self, request, *args, **kwargs):
        item = self.get_object()
        body = self.get_serializer(item, data=request.data, partial=True)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        eventday.check_schedule_times(item.function, data.get("starts_at", item.starts_at),
                                      data.get("ends_at", item.ends_at))
        item = body.save()
        return Response({**ScheduleItemSerializer(item).data, "warnings": eventday.overlap_warnings(item)})


# --- vendor check-in -------------------------------------------------------------------------

class WeddingCheckins(APIView):
    permission_classes = [PLANNERS]

    @extend_schema(responses=CheckinSerializer(many=True))
    def get(self, request, wedding_id):
        _wedding_or_404(wedding_id)
        rows = (VendorArrival.objects.filter(wedding_id=wedding_id).select_related("vendor", "function")
                .order_by("expected_at", "id"))
        return Response(CheckinSerializer(rows, many=True).data)

    @extend_schema(request=CheckinCreateSerializer, responses=CheckinSerializer)
    def post(self, request, wedding_id):
        wedding = _wedding_or_404(wedding_id)
        body = CheckinCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        arrival = eventday.create_checkin(wedding, data["vendor"], data["scheduled_arrival"],
                                          data.get("function"), data.get("grace_minutes"))
        return Response(CheckinSerializer(arrival).data, status=status.HTTP_201_CREATED)


class CheckinDetail(APIView):
    """PATCH {"arrived": true} marks a vendor arrived by hand (optionally with "actual_arrival")."""

    permission_classes = [PLANNERS]

    @extend_schema(request=CheckinUpdateSerializer, responses=CheckinSerializer)
    def patch(self, request, pk):
        body = CheckinUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        with transaction.atomic():
            try:
                arrival = VendorArrival.objects.select_for_update().get(pk=pk)
            except VendorArrival.DoesNotExist:
                raise NotFound("Check-in not found.") from None
            if "scheduled_arrival" in data:
                arrival.expected_at = data["scheduled_arrival"]
            if "grace_minutes" in data:
                arrival.grace_minutes = data["grace_minutes"]
            if data.get("arrived") or "actual_arrival" in data:
                # a planner may correct the time, unlike the vendor's own button
                arrival.arrived_at = data.get("actual_arrival") or arrival.arrived_at or timezone.now()
            if arrival.arrived_at is not None:
                arrival.status = eventday.arrival_status(arrival.expected_at, arrival.grace_minutes,
                                                         arrival.arrived_at)
            arrival.save()
        return Response(CheckinSerializer(VendorArrival.objects.select_related("vendor", "function").get(pk=pk)).data)


# --- public (no login): what a vendor sees when they open their link ---------------------------

def _public_view(arrival: VendorArrival) -> dict:
    return {
        "vendor_name": arrival.vendor.name,
        "wedding_name": arrival.wedding.title,
        "function_name": arrival.function.name if arrival.function_id else None,
        "scheduled_arrival": arrival.expected_at,
        "actual_arrival": arrival.arrived_at,
        "status": arrival.status,
        "already_arrived": arrival.arrived_at is not None,
    }


def _by_code(token: str) -> VendorArrival:
    try:
        return VendorArrival.objects.select_related("vendor", "wedding", "function").get(check_in_code=token)
    except VendorArrival.DoesNotExist:
        raise NotFound("This check-in link is not valid.") from None


@extend_schema(responses=dict)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_checkin(request, token):
    return Response(_public_view(_by_code(token)))


@extend_schema(request=None, responses=dict)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_arrive(request, token):
    """The vendor taps "I have arrived". Tapping again changes nothing."""
    eventday.record_arrival(token)
    return Response(_public_view(_by_code(token)))
