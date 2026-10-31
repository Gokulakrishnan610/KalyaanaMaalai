from django.db.models import Count, Min, Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from clients.serializers import ClientSerializer
from clients.services import find_client
from common.permissions import Role, allow_roles, read_for_all_write_for
from enquiries.models import Enquiry, FollowUp
from enquiries.serializers import ConvertSerializer, EnquirySerializer, FollowUpSerializer
from enquiries.services import convert_to_client


class EnquiryViewSet(viewsets.ModelViewSet):
    """Couples who got in touch. Filter with ?status= ?source= and search with ?q=."""

    serializer_class = EnquirySerializer

    def filtered(self, with_status=True):
        """The enquiries matching ?source= and ?q= (and ?status= unless `with_status` is off, for the tab counts)."""
        enquiries = Enquiry.objects.select_related("client", "owner", "portal_customer").annotate(
            next_follow_up_at=Min("follow_ups__due_at", filter=Q(follow_ups__done_at__isnull=True)))
        params = self.request.query_params
        if with_status and params.get("status"):
            enquiries = enquiries.filter(status=params["status"])
        if params.get("source"):
            enquiries = enquiries.filter(source=params["source"])
        if params.get("q"):
            text = params["q"]
            enquiries = enquiries.filter(
                Q(couple_name__icontains=text) | Q(client_name__icontains=text) | Q(partner_name__icontains=text)
                | Q(email__icontains=text) | Q(spouse_email__icontains=text) | Q(phone__icontains=text))
        return enquiries

    def get_queryset(self):
        return self.filtered().order_by("-created_at")

    @action(detail=False, methods=["get"])
    def counts(self, request):
        """How many enquiries are in each stage, for the tabs. Respects ?source= and ?q= but not ?status=."""
        rows = self.filtered(with_status=False).order_by().values("status").annotate(n=Count("id", distinct=True))
        counts = {row["status"]: row["n"] for row in rows}
        return Response({"ALL": sum(counts.values()), **counts})

    def get_permissions(self):
        if self.action == "destroy":
            return [allow_roles()()]
        return [read_for_all_write_for(Role.PLANNER)()]

    def perform_create(self, serializer):
        # whoever enters the enquiry owns it, unless they picked someone else
        # a returning client (same client name + email) is linked to their existing record, not duplicated
        data = serializer.validated_data
        existing = find_client(data.get("client_name", ""), data.get("email", ""))
        serializer.save(owner=data.get("owner") or self.request.user, client=existing)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Make this enquiry a client (and optionally start the wedding)."""
        options = ConvertSerializer(data=request.data)
        options.is_valid(raise_exception=True)
        client, wedding = convert_to_client(self.get_object(), **options.validated_data)
        return Response({"client": ClientSerializer(client).data, "wedding_id": wedding.id if wedding else None})


    @action(detail=True, methods=["post"])
    def invite(self, request, pk=None):
        """(Re)send the customer-website login to a converted client."""
        from rest_framework.exceptions import ValidationError

        from portal.accounts import account_state, ensure_customer, invite_customer

        enquiry = self.get_object()
        if enquiry.client_id is None:
            raise ValidationError("Convert this enquiry to a client first.")
        if not enquiry.email:
            raise ValidationError("Add the couple's email address first, so we can send them the login.")
        had_account = getattr(enquiry, "portal_customer", None) is not None
        customer = ensure_customer(enquiry, enquiry.client, planner=request.user.name)  # emails a brand new account
        if had_account:
            invite_customer(customer, request.user.name)  # an existing one gets the email again
        return Response({"portal_account": account_state(customer)})


class FollowUpViewSet(viewsets.ModelViewSet):
    """Planned calls and meetings. Filter with ?enquiry=<id> and ?open=1 (not done yet)."""

    serializer_class = FollowUpSerializer
    pagination_class = None

    def get_queryset(self):
        follow_ups = FollowUp.objects.select_related("enquiry")
        params = self.request.query_params
        if params.get("enquiry"):
            follow_ups = follow_ups.filter(enquiry_id=params["enquiry"])
        if params.get("open"):
            follow_ups = follow_ups.filter(done_at__isnull=True)
        return follow_ups

    def get_permissions(self):
        return [read_for_all_write_for(Role.PLANNER)()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def done(self, request, pk=None):
        """Tick a follow-up off. Doing it twice keeps the first time."""
        follow_up = self.get_object()
        if follow_up.done_at is None:
            follow_up.done_at = timezone.now()
            follow_up.save(update_fields=["done_at"])
        return Response(FollowUpSerializer(follow_up).data)
