"""What a vendor sees on the website after logging in: their bookings, schedule, payments and quotation requests."""
from django.db.models import Avg, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from live.signals import alert
from payments.models import Expense, Payment
from portal.auth import IsVendor, VendorAuthentication, make_token
from portal.views import OpenView
from quotations import services as quotation_services
from quotations.models import Quotation, QuotationRequest, RequestStatus, WeddingVendor
from quotations.serializers import QuotationInputSerializer
from vendors.models import Vendor
from weddings.models import ScheduleItem, VendorArrival, VendorRating


def vendor_data(account) -> dict:
    vendor = account.vendor
    ratings = VendorRating.objects.filter(vendor=vendor)
    average = ratings.aggregate(a=Avg("punctuality"), b=Avg("quality"), c=Avg("pricing"))
    scores = [v for v in average.values() if v is not None]
    return {"vendor": {"id": vendor.pk, "name": vendor.name, "category": vendor.category.name, "contact_person": vendor.contact_person,
                       "phone": vendor.phone, "email": account.email, "city": vendor.city, "notes": vendor.notes},
            "rating": round(sum(scores) / len(scores), 1) if scores else None, "ratings_count": ratings.count()}


class VendorLogin(OpenView):
    @extend_schema(request=None, responses=dict)
    def post(self, request):
        from portal.models import VendorAccount

        account = VendorAccount.objects.select_related("vendor__category").filter(
            email=str(request.data.get("email", "")).strip().lower()).first()
        if account is None or not account.check_password(str(request.data.get("password", ""))):
            return Response({"detail": "Wrong email or password."}, status=400)
        account.last_login_at = timezone.now()
        account.save(update_fields=["last_login_at"])
        return Response({"token": make_token(account, "vendor"), **vendor_data(account)})


class VendorView(APIView):
    authentication_classes = [VendorAuthentication]
    permission_classes = [IsVendor]


class VendorMe(VendorView):
    @extend_schema(responses=dict)
    def get(self, request):
        return Response(vendor_data(request.user))

    @extend_schema(request=None, responses=dict)
    def patch(self, request):
        vendor = request.user.vendor
        for field in ("contact_person", "phone", "city", "notes"):
            if field in request.data:
                setattr(vendor, field, str(request.data[field]).strip()[:500])
        if not vendor.phone:
            raise ValidationError({"phone": "Phone number is needed."})
        vendor.save()
        return Response(vendor_data(request.user))


class VendorPassword(VendorView):
    """The vendor replaces the password we generated for them."""

    @extend_schema(request=None, responses=dict)
    def post(self, request):
        account = request.user
        if not account.check_password(str(request.data.get("current", ""))):
            raise ValidationError({"current": "That is not your current password."})
        new = str(request.data.get("new", ""))
        if len(new) < 8:
            raise ValidationError({"new": "Use at least 8 characters."})
        account.set_password(new)
        account.save(update_fields=["password_hash"])
        return Response({"detail": "Password changed."})


class VendorBookings(VendorView):
    """Weddings we booked this vendor for, with their schedule items and arrival link."""

    @extend_schema(responses=dict)
    def get(self, request):
        vendor = request.user.vendor
        rows = []
        for booking in WeddingVendor.objects.filter(vendor=vendor).select_related("wedding").order_by("wedding__start_date"):
            wedding = booking.wedding
            schedule = ScheduleItem.objects.filter(vendor=vendor, function__wedding=wedding).select_related("function")
            arrivals = VendorArrival.objects.filter(vendor=vendor, wedding=wedding).select_related("function")
            rows.append({
                "wedding": wedding.title, "city": wedding.city, "start_date": wedding.start_date, "end_date": wedding.end_date,
                "guest_count": wedding.guest_count, "agreed_amount_paise": booking.agreed_amount_paise,
                "schedule": [{"function": s.function.name, "title": s.title, "starts_at": s.starts_at, "ends_at": s.ends_at,
                              "notes": s.notes} for s in schedule.order_by("starts_at")],
                "arrivals": [{"function": a.function.name if a.function_id else None, "expected_at": a.expected_at,
                              "arrived_at": a.arrived_at, "status": a.status, "code": a.check_in_code} for a in arrivals],
            })
        return Response(rows)


class VendorPayments(VendorView):
    """What we owe this vendor, and what we have already paid."""

    @extend_schema(responses=dict)
    def get(self, request):
        expenses = Expense.objects.filter(vendor=request.user.vendor).select_related("wedding").order_by("due_date", "id")
        paid = dict(Payment.objects.filter(expense__in=expenses, direction=Payment.Direction.OUT).values_list("expense_id")
                    .annotate(total=Sum("amount_paise")))
        bills = [{"id": e.pk, "wedding": e.wedding.title, "description": e.description, "amount_paise": e.amount_paise,
                  "paid_paise": paid.get(e.pk, 0), "remaining_paise": e.amount_paise - paid.get(e.pk, 0),
                  "due_date": e.due_date, "status": e.status} for e in expenses]
        history = Payment.objects.filter(expense__in=expenses, direction=Payment.Direction.OUT).select_related("wedding").order_by("-paid_at")
        return Response({"bills": bills, "payments": [{"wedding": p.wedding.title, "amount_paise": p.amount_paise,
                                                       "method": p.method, "reference": p.reference, "paid_at": p.paid_at}
                                                      for p in history]})


def request_row(quotation_request: QuotationRequest, vendor: Vendor) -> dict:
    mine = quotation_request.quotations.filter(vendor=vendor).first()
    wedding = quotation_request.wedding
    return {"id": quotation_request.pk, "wedding": wedding.title, "date": wedding.start_date, "city": wedding.city,
            "category": quotation_request.category.name, "requirements": quotation_request.requirements,
            "guest_count": quotation_request.guest_count, "reply_by": quotation_request.reply_by,
            "open": quotation_request.status == RequestStatus.OPEN,
            "my_quotation": None if mine is None else {
                "total_paise": mine.total_paise, "price_per_plate_paise": mine.price_per_plate_paise,
                "menu_notes": mine.menu_notes, "valid_till": mine.valid_till, "status": mine.status}}


class VendorRequests(VendorView):
    """Quotation requests we sent this vendor."""

    @extend_schema(responses=dict)
    def get(self, request):
        vendor = request.user.vendor
        requests = QuotationRequest.objects.filter(invited_vendors=vendor, sent_at__isnull=False).select_related(
            "wedding", "category").order_by("-sent_at")
        return Response([request_row(r, vendor) for r in requests])


class VendorQuote(VendorView):
    """The vendor sends (or updates) their own price."""

    @extend_schema(request=QuotationInputSerializer, responses=dict)
    def post(self, request, pk):
        vendor = request.user.vendor
        try:
            quotation_request = QuotationRequest.objects.select_related("wedding", "category").get(
                pk=pk, invited_vendors=vendor, sent_at__isnull=False)
        except QuotationRequest.DoesNotExist:
            raise NotFound("Request not found.") from None
        data = QuotationInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        quotation_services.save_quotation(quotation_request, vendor, data.validated_for_service())
        alert(f"{vendor.name} sent a quotation for {quotation_request.wedding.title} ({quotation_request.category.name})",
              key=f"vendor-quote:{quotation_request.pk}:{vendor.pk}:{timezone.now():%Y%m%d%H%M}")
        return Response(request_row(quotation_request, vendor))
