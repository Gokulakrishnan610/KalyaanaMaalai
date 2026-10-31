from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from ai_tools import services
from common.permissions import Role, allow_roles
from weddings.models import Wedding

UPLOAD_TYPES = {
    ".pdf": (b"%PDF",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG",),
}


class AIThrottle(UserRateThrottle):
    """AI calls cost money: 20 a minute per person is plenty."""

    scope = "ai"
    rate = "20/min"


class PlannerOnly(APIView):
    permission_classes = [allow_roles(Role.PLANNER)]


class ExtractQuotation(PlannerOnly):
    """Reads an uploaded quotation (PDF or photo, up to 10 MB) and returns a DRAFT in paise. Nothing is saved."""

    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [AIThrottle]

    @extend_schema(request={"multipart/form-data": {"type": "object", "properties": {
        "file": {"type": "string", "format": "binary"}}}}, responses=dict)
    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"file": ["Choose a file to read."]}, status=400)
        if upload.size > services.MAX_UPLOAD_BYTES:
            return Response({"file": ["This file is larger than 10 MB."]}, status=400)
        extension = "." + upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
        signatures = UPLOAD_TYPES.get(extension)
        if signatures is None:
            return Response({"file": ["Upload a PDF, PNG or JPG file."]}, status=400)
        data = upload.read()
        if not data.startswith(signatures):
            return Response({"file": ["This file is not really a " + extension[1:].upper() + "."]}, status=400)
        return Response({"draft": services.extract_quotation(data, upload.name)})


class ChecklistRequest(serializers.Serializer):
    wedding_id = serializers.IntegerField()


class ChecklistTaskInput(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True, max_length=60)
    due_date = serializers.DateField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=["LOW", "MEDIUM", "HIGH"], required=False)
    function_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if value.get("due_date"):
            value["due_date"] = value["due_date"].isoformat()
        return value


class ConfirmRequest(ChecklistRequest):
    tasks = ChecklistTaskInput(many=True, allow_empty=False)


class GenerateChecklist(PlannerOnly):
    """A PREVIEW of 25-40 tasks tailored to the wedding. Falls back to the built-in checklist if AI fails."""

    throttle_classes = [AIThrottle]

    @extend_schema(request=ChecklistRequest, responses=dict)
    def post(self, request):
        data = ChecklistRequest(data=request.data)
        data.is_valid(raise_exception=True)
        wedding = get_object_or_404(Wedding, pk=data.validated_data["wedding_id"])
        return Response(services.generate_checklist(wedding))


class ConfirmChecklist(PlannerOnly):
    """Saves the tasks the planner kept (titles already on the wedding are skipped)."""

    @extend_schema(request=ConfirmRequest, responses=dict)
    def post(self, request):
        data = ConfirmRequest(data=request.data)
        data.is_valid(raise_exception=True)
        wedding = get_object_or_404(Wedding, pk=data.validated_data["wedding_id"])
        return Response(services.confirm_checklist(wedding, data.validated_data["tasks"]), status=201)
