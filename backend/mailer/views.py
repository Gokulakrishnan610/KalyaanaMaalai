from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import Role, allow_roles
from mailer import services
from mailer.models import EmailLog
from mailer.templates import TEMPLATES


class StaffOnly(APIView):
    permission_classes = [allow_roles(Role.PLANNER)]


class TemplateList(StaffOnly):
    def get(self, request):
        return Response([{"name": name, "subject": subject, "when": when} for name, (subject, when) in TEMPLATES.items()])


class TemplatePreview(StaffOnly):
    def get(self, request, name):
        if name not in TEMPLATES:
            raise Http404
        return Response(services.preview(name))


class MailLog(StaffOnly):
    def get(self, request):
        logs = EmailLog.objects.all()[:50]
        return Response([{"id": e.pk, "template": e.template, "to": e.to, "subject": e.subject, "status": e.status,
                          "created_at": e.created_at} for e in logs])
