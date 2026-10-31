from django.db import transaction
from django.db.models import ProtectedError, Q, Sum
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from common.permissions import Role, allow_roles, read_for_all_write_for
from payments.models import Payment
from quotations.models import Quotation, WeddingVendor
from vendors.models import Vendor, VendorCategory
from vendors.pagination import VendorPagination
from vendors.performance import performance_for, with_stats
from vendors.serializers import RatingSerializer, VendorCategorySerializer, VendorSerializer
from weddings.models import VendorArrival, VendorRating, Wedding


class VendorCategoryList(ListAPIView):
    queryset = VendorCategory.objects.all()
    serializer_class = VendorCategorySerializer
    pagination_class = None


class VendorViewSet(viewsets.ModelViewSet):
    """The vendor directory. Filter with ?category_id= ?city= ?q= (name, contact, phone); page with ?page= &limit=."""

    serializer_class = VendorSerializer
    pagination_class = VendorPagination

    def get_queryset(self):
        vendors = with_stats(Vendor.objects.select_related("category"))
        params = self.request.query_params
        if params.get("category_id"):
            vendors = vendors.filter(category_id=params["category_id"])
        if params.get("city"):
            vendors = vendors.filter(city__icontains=params["city"])
        if params.get("q"):
            text = params["q"]
            vendors = vendors.filter(Q(name__icontains=text) | Q(contact_person__icontains=text)
                                     | Q(phone__icontains=text))
        return vendors

    def get_permissions(self):
        if self.action == "destroy":
            return [allow_roles()()]
        return [read_for_all_write_for(Role.PLANNER)()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        duplicate = Vendor.objects.filter(name__iexact=data["name"], phone=data["phone"]).exists()
        vendor = serializer.save()
        body = self.get_serializer(self.get_queryset().get(pk=vendor.pk)).data
        # still saved, but the screen can ask "is this the same vendor?"
        body = {**body, "duplicate_warning": duplicate,
                "warnings": ["A vendor with this name and phone already exists."] if duplicate else []}
        return Response(body, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        return Response(self.profile(self.get_object()))

    def destroy(self, request, *args, **kwargs):
        vendor = self.get_object()
        try:
            with transaction.atomic():
                if WeddingVendor.objects.filter(vendor=vendor).exists():
                    return Response({"detail": "This vendor is booked on a wedding, so it cannot be deleted."},
                                    status=status.HTTP_409_CONFLICT)
                vendor.delete()
        except ProtectedError:
            return Response({"detail": "This vendor has quotations or bills, so it cannot be deleted."},
                            status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def profile(self, vendor):
        """Everything the vendor page needs in one call."""
        body = self.get_serializer(vendor).data
        bookings = WeddingVendor.objects.filter(vendor=vendor).select_related("wedding").order_by(
            "-wedding__start_date")
        paid = Payment.objects.filter(direction=Payment.Direction.OUT, expense__vendor=vendor).aggregate(
            t=Coalesce(Sum("amount_paise"), 0))["t"]
        ratings = VendorRating.objects.filter(vendor=vendor).select_related("wedding")
        quotations = Quotation.objects.filter(vendor=vendor).select_related("request__wedding").order_by(
            "-created_at")
        return {
            **body,
            "weddings": [{"id": b.wedding_id, "title": b.wedding.title, "start_date": b.wedding.start_date,
                          "status": b.wedding.status, "agreed_amount_paise": b.agreed_amount_paise,
                          "quotation_id": b.quotation_id} for b in bookings],
            "ratings": RatingSerializer(ratings, many=True).data,
            "quotations": [{"id": q.id, "request_id": q.request_id, "wedding_id": q.request.wedding_id,
                            "wedding_title": q.request.wedding.title, "total_paise": q.total_paise,
                            "price_per_plate_paise": q.price_per_plate_paise, "status": q.status,
                            "created_at": q.created_at} for q in quotations],
            "total_paid_paise": paid,
            "performance": performance_for(vendor),
        }

    @extend_schema(request=RatingSerializer, responses={201: RatingSerializer})
    @action(detail=True, methods=["post"], url_path="ratings")
    def create_rating(self, request, pk=None):
        """Rate a vendor for one wedding. Rating the same wedding again replaces the earlier rating."""
        vendor = self.get_object()
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            wedding = Wedding.objects.get(pk=data["wedding_id"])
        except Wedding.DoesNotExist:
            return Response({"wedding_id": ["This wedding does not exist."]}, status=400)
        worked_there = (WeddingVendor.objects.filter(vendor=vendor, wedding=wedding).exists()
                        or VendorArrival.objects.filter(vendor=vendor, wedding=wedding).exists())
        if not worked_there:
            return Response({"wedding_id": ["This vendor was not booked on that wedding."]}, status=400)
        scores = {key: data[key] for key in ("punctuality", "quality", "pricing")}
        rating, created = VendorRating.objects.update_or_create(
            vendor=vendor, wedding=wedding, defaults={**scores, "comment": data.get("comment", "")})
        return Response(RatingSerializer(rating).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(responses=dict)
    @action(detail=True, methods=["get"], url_path="performance")
    def performance(self, request, pk=None):
        return Response(performance_for(self.get_object()))
