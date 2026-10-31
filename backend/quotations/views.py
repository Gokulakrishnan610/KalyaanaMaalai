import uuid
from pathlib import Path

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from common.permissions import Role, read_for_all_write_for
from quotations import services
from quotations.models import Quotation, QuotationRequest, QuotationStatus, RequestStatus, WeddingVendor
from quotations.serializers import (
    QuotationInputSerializer,
    QuotationSerializer,
    RequestSerializer,
    WeddingVendorSerializer,
)
from weddings.models import Wedding

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
# extension -> (allowed content types, first bytes of a real file of that kind)
UPLOAD_TYPES = {
    ".pdf": ({"application/pdf"}, (b"%PDF",)),
    ".jpg": ({"image/jpeg"}, (b"\xff\xd8\xff",)),
    ".jpeg": ({"image/jpeg"}, (b"\xff\xd8\xff",)),
    ".png": ({"image/png"}, (b"\x89PNG",)),
}


class PlannerWrites(APIView):
    permission_classes = [read_for_all_write_for(Role.PLANNER)]


def requests_queryset():
    return (QuotationRequest.objects.select_related("wedding", "category")
            .prefetch_related("invited_vendors", "quotations").order_by("-created_at"))


def quotations_queryset():
    return Quotation.objects.select_related("vendor", "request").prefetch_related("items")


def caterer_warnings(category, invited_count) -> list[str]:
    if category.name == services.CATERER and invited_count < services.RECOMMENDED_CATERER_QUOTES:
        return [f"Ask at least {services.RECOMMENDED_CATERER_QUOTES} caterers for a quotation so you can compare "
                f"properly (you invited {invited_count})."]
    return []


class AllRequests(PlannerWrites):
    """All quotation requests, newest first. Filter with ?status=OPEN|CLOSED."""

    @extend_schema(responses=RequestSerializer(many=True))
    def get(self, request):
        queryset = requests_queryset()
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"])
        return Response(RequestSerializer(queryset, many=True).data)


class WeddingRequests(PlannerWrites):
    @extend_schema(responses=RequestSerializer(many=True))
    def get(self, request, wedding_id):
        get_object_or_404(Wedding, pk=wedding_id)
        return Response(RequestSerializer(requests_queryset().filter(wedding_id=wedding_id), many=True).data)

    @extend_schema(request=RequestSerializer, responses={201: RequestSerializer})
    def post(self, request, wedding_id):
        wedding = get_object_or_404(Wedding, pk=wedding_id)
        serializer = RequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invited = serializer.validated_data.pop("invited_vendors", [])
        serializer.validated_data.setdefault("guest_count", wedding.guest_count)
        quotation_request = serializer.save(wedding=wedding)
        quotation_request.invited_vendors.set(invited)
        body = RequestSerializer(requests_queryset().get(pk=quotation_request.pk)).data
        body["warnings"] = caterer_warnings(quotation_request.category, len(invited))
        return Response(body, status=status.HTTP_201_CREATED)


class RequestDetail(PlannerWrites):
    @extend_schema(responses=dict)
    def get(self, request, pk):
        quotation_request = get_object_or_404(requests_queryset(), pk=pk)
        body = RequestSerializer(quotation_request).data
        body["quotations"] = QuotationSerializer(
            quotations_queryset().filter(request=quotation_request).order_by("id"), many=True,
            context={"request": request}).data
        return Response(body)

    @extend_schema(request=RequestSerializer, responses=RequestSerializer)
    def patch(self, request, pk):
        quotation_request = get_object_or_404(requests_queryset(), pk=pk)
        serializer = RequestSerializer(quotation_request, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        invited = serializer.validated_data.pop("invited_vendors", None)
        with transaction.atomic():
            serializer.save()
            if invited is not None:
                quotation_request.invited_vendors.set(invited)
        body = RequestSerializer(requests_queryset().get(pk=pk)).data
        body["warnings"] = caterer_warnings(quotation_request.category, quotation_request.invited_vendors.count())
        return Response(body)


class RequestSend(PlannerWrites):
    @extend_schema(request=None, responses=dict)
    def post(self, request, pk):
        quotation_request = get_object_or_404(requests_queryset(), pk=pk)
        if not quotation_request.invited_vendors.exists():
            return Response({"detail": "Invite at least one vendor before sending."}, status=400)
        with transaction.atomic():
            quotation_request.sent_at = timezone.now()
            quotation_request.save(update_fields=["sent_at"])
            sent_to = services.notify_vendors(quotation_request)
        return Response({**RequestSerializer(requests_queryset().get(pk=pk)).data, "sent_to": sent_to})


class RequestQuotations(PlannerWrites):
    @extend_schema(request=QuotationInputSerializer, responses={201: QuotationSerializer})
    def post(self, request, pk):
        """Adds a vendor's quotation. A second one from the same vendor replaces the first (200 instead of 201)."""
        quotation_request = get_object_or_404(requests_queryset(), pk=pk)
        serializer = QuotationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vendor = serializer.validated_data.get("vendor_id")
        if vendor is None:
            return Response({"vendor_id": ["Choose the vendor."]}, status=400)
        quotation, created = services.save_quotation(quotation_request, vendor, serializer.validated_for_service())
        body = QuotationSerializer(quotations_queryset().get(pk=quotation.pk), context={"request": request}).data
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class RequestCompare(PlannerWrites):
    @extend_schema(responses=dict)
    def get(self, request, pk):
        quotation_request = get_object_or_404(requests_queryset(), pk=pk)
        body = services.compare(quotation_request)
        for quote in body["quotations"]:
            if quote["file_url"]:
                quote["file_url"] = request.build_absolute_uri(quote["file_url"])
        return Response(body)


class QuotationDetail(PlannerWrites):
    @extend_schema(request=QuotationInputSerializer, responses=QuotationSerializer)
    def patch(self, request, pk):
        quotation = get_object_or_404(quotations_queryset(), pk=pk)
        if quotation.status == QuotationStatus.SELECTED:
            raise services.Conflict("This quotation is already selected and can no longer be changed.")
        serializer = QuotationInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            services.write_quotation(quotation, serializer.validated_for_service())
        return Response(QuotationSerializer(quotations_queryset().get(pk=pk), context={"request": request}).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        quotation = get_object_or_404(quotations_queryset(), pk=pk)
        if quotation.status == QuotationStatus.SELECTED:
            raise services.Conflict("This quotation is selected, so it cannot be deleted.")
        quotation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def check_upload(upload):
    """Returns an error message, or None when the file is a PDF/JPG/PNG of at most 10 MB."""
    extension = Path(upload.name or "").suffix.lower()
    if extension not in UPLOAD_TYPES:
        return "Upload a PDF, JPG or PNG file."
    types, signatures = UPLOAD_TYPES[extension]
    if (upload.content_type or "").split(";")[0].strip().lower() not in types:
        return "The file type does not match its name. Upload a PDF, JPG or PNG file."
    if upload.size > MAX_UPLOAD_BYTES:
        return "The file is larger than 10 MB."
    head = upload.read(8)
    upload.seek(0)
    if not any(head.startswith(sig) for sig in signatures):
        return "This does not look like a real PDF, JPG or PNG file."
    return None


class QuotationUpload(PlannerWrites):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string",
                   "format": "binary"}}}}, responses=dict)
    def post(self, request, pk):
        quotation = get_object_or_404(quotations_queryset(), pk=pk)
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"file": ["Choose a file to upload."]}, status=400)
        problem = check_upload(upload)
        if problem:
            return Response({"file": [problem]}, status=400)
        if quotation.file:
            quotation.file.delete(save=False)
        # a random name, so nobody can guess another quotation's file and odd characters never reach the disk
        quotation.file.save(f"{uuid.uuid4().hex}{Path(upload.name).suffix.lower()}", upload, save=True)
        return Response({"file_url": request.build_absolute_uri(quotation.file.url)})


class QuotationExtract(PlannerWrites):
    """Reads a vendor's PDF with AI and returns a DRAFT for the form. Nothing is saved."""

    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string",
                   "format": "binary"}}}}, responses=dict)
    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"file": ["Choose a file to read."]}, status=400)
        problem = check_upload(upload)
        if problem:
            return Response({"file": [problem]}, status=400)
        try:
            from ai_tools.services import extract_quotation
        except (ImportError, AttributeError):
            return Response({"detail": "Reading quotations with AI is not available yet. Please type it in."},
                            status=status.HTTP_501_NOT_IMPLEMENTED)
        try:
            draft = extract_quotation(upload)
        except Exception:  # noqa: BLE001 - a flaky PDF must never block manual entry
            services.logger.exception("Quotation extraction failed")
            return Response({"detail": "Could not read this file. Please type the quotation in."}, status=422)
        return Response({"draft": draft})


class QuotationSelect(PlannerWrites):
    @extend_schema(request=Serializer, responses=dict)
    def post(self, request, pk):
        quotation = get_object_or_404(quotations_queryset().select_related("vendor__category"), pk=pk)
        raw = request.data.get("advance_pct", 30) if hasattr(request.data, "get") else 30
        try:
            advance_pct = int(raw)
        except (TypeError, ValueError):
            return Response({"advance_pct": ["Enter a whole number from 0 to 100."]}, status=400)
        if not 0 <= advance_pct <= 100:
            return Response({"advance_pct": ["Enter a whole number from 0 to 100."]}, status=400)
        booking, created = services.select_quotation(quotation, advance_pct)
        booking = WeddingVendor.objects.select_related("vendor__category", "quotation").get(pk=booking.pk)
        return Response({"created": created, "wedding_vendor": WeddingVendorSerializer(booking).data,
                         "request_status": RequestStatus.CLOSED},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class WeddingVendors(PlannerWrites):
    """The vendors chosen for a wedding (the 'Selected vendors' list on its Vendors tab)."""

    @extend_schema(responses=WeddingVendorSerializer(many=True))
    def get(self, request, wedding_id):
        get_object_or_404(Wedding, pk=wedding_id)
        bookings = WeddingVendor.objects.filter(wedding_id=wedding_id).select_related(
            "vendor__category", "quotation").order_by("id")
        return Response(WeddingVendorSerializer(bookings, many=True).data)
