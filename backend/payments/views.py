from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from common.pagination import StandardPagination
from common.permissions import Role, read_for_all_write_for
from payments import links, razorpay_client, services
from payments.models import Expense, Invoice, Payment, PaymentLink, VendorPaymentPlan
from payments.serializers import (
    ExpenseInput,
    ExpensePatch,
    ExpenseSerializer,
    ExtraGuestsInput,
    InvoiceInput,
    InvoicePatch,
    InvoiceRowSerializer,
    InvoiceSerializer,
    LedgerSerializer,
    MilestonePayInput,
    MilestoneSerializer,
    PaymentInput,
    PaymentLinkInput,
    PaymentLinkSerializer,
    PaymentSerializer,
    PublicOrderResult,
    RazorpayVerifyInput,
    VendorBillSerializer,
    with_paid,
)
from weddings.models import Wedding


class FinanceView(APIView):
    """Anyone logged in may look; planners and the founder may change money records."""

    permission_classes = [read_for_all_write_for(Role.PLANNER)]


def _key(request):
    return request.headers.get("Idempotency-Key") or None


def _payment_response(payment, created):
    return Response(PaymentSerializer(payment).data, status=201 if created else 200)


def _invoice(pk):
    return get_object_or_404(with_paid(Invoice.objects.all()), pk=pk)


def _expense(pk):
    return get_object_or_404(with_paid(Expense.objects.select_related("vendor")), pk=pk)


# ---------------------------------------------------------------- wedding-level lists

class WeddingFinance(FinanceView):
    """Revenue, expenses, profit and the money due soon for one wedding."""

    @extend_schema(responses=dict)
    def get(self, request, wedding_id):
        get_object_or_404(Wedding, pk=wedding_id)
        return Response(services.get_wedding_financials(wedding_id))


class WeddingInvoices(FinanceView):
    @extend_schema(responses=InvoiceSerializer(many=True))
    def get(self, request, wedding_id):
        queryset = with_paid(Invoice.objects.filter(wedding_id=wedding_id)).order_by("created_at", "id")
        return Response(InvoiceSerializer(queryset, many=True).data)

    @extend_schema(request=InvoiceInput, responses=InvoiceSerializer)
    def post(self, request, wedding_id):
        wedding = get_object_or_404(Wedding, pk=wedding_id)
        data = InvoiceInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        invoice = services.create_invoice(wedding, v["type"], v["amount_paise"], v.get("due_date"),
                                          v.get("note", ""))
        return Response(InvoiceSerializer(_invoice(invoice.pk)).data, status=201)


class ExtraGuestInvoice(FinanceView):
    """Charges for guests above the contracted number. Send `"preview": true` to see the amount without saving."""

    @extend_schema(request=ExtraGuestsInput, responses=dict)
    def post(self, request, wedding_id):
        wedding = get_object_or_404(Wedding, pk=wedding_id)
        data = ExtraGuestsInput(data=request.data)
        data.is_valid(raise_exception=True)
        guests = data.validated_data["actual_guests"]
        if data.validated_data["preview"]:
            return Response(services.extra_guest_charge(wedding, guests))
        invoice = services.create_extra_guest_invoice(wedding, guests, data.validated_data.get("due_date"))
        return Response(InvoiceSerializer(_invoice(invoice.pk)).data, status=201)


class WeddingExpenses(FinanceView):
    @extend_schema(responses=ExpenseSerializer(many=True))
    def get(self, request, wedding_id):
        queryset = with_paid(Expense.objects.filter(wedding_id=wedding_id).select_related("vendor"))
        return Response(ExpenseSerializer(queryset.order_by("due_date", "id"), many=True).data)

    @extend_schema(request=ExpenseInput, responses=ExpenseSerializer)
    def post(self, request, wedding_id):
        wedding = get_object_or_404(Wedding, pk=wedding_id)
        data = ExpenseInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        expense, warnings = services.create_expense(wedding, v["category"], v["description"], v["amount_paise"],
                                                    v.get("vendor_id"), v.get("bill_ref", ""), v.get("due_date"))
        return Response({**ExpenseSerializer(_expense(expense.pk)).data, "warnings": warnings}, status=201)


class WeddingMilestones(FinanceView):
    @extend_schema(responses=MilestoneSerializer(many=True))
    def get(self, request, wedding_id):
        plans = list(VendorPaymentPlan.objects.filter(wedding_id=wedding_id).select_related("vendor")
                     .order_by("due_date", "id"))
        covered = {}
        for expense_id in {p.expense_id for p in plans if p.expense_id}:
            siblings = sorted((p for p in plans if p.expense_id == expense_id), key=lambda p: (p.part, p.pk))
            paid = Payment.objects.filter(expense_id=expense_id).values_list("amount_paise", "reference")
            covered.update(services.allocate_to_plans(siblings, list(paid)))
        return Response(MilestoneSerializer(plans, many=True, context={"covered": covered}).data)


# ---------------------------------------------------------------- one invoice

class InvoiceDetail(FinanceView):
    @extend_schema(request=InvoicePatch, responses=InvoiceSerializer)
    def patch(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        data = InvoicePatch(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        services.update_invoice(invoice, data.validated_data)
        return Response(InvoiceSerializer(_invoice(pk)).data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        services.delete_invoice(get_object_or_404(Invoice, pk=pk))
        return Response(status=204)


class InvoicePayments(FinanceView):
    @extend_schema(responses=PaymentSerializer(many=True))
    def get(self, request, pk):
        get_object_or_404(Invoice, pk=pk)
        queryset = Payment.objects.filter(invoice_id=pk).order_by("paid_at", "id")
        return Response(PaymentSerializer(queryset, many=True).data)

    @extend_schema(request=PaymentInput, responses=PaymentSerializer)
    def post(self, request, pk):
        get_object_or_404(Invoice, pk=pk)
        data = PaymentInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        payment, created = services.record_invoice_payment(
            pk, v["amount_paise"], v["method"], v.get("reference", ""), v.get("paid_at"), _key(request),
            recorded_by=request.user)
        return _payment_response(payment, created)


# ---------------------------------------------------------------- one expense

class ExpenseDetail(FinanceView):
    @extend_schema(request=ExpensePatch, responses=ExpenseSerializer)
    def patch(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk)
        data = ExpensePatch(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        _, warnings = services.update_expense(expense, data.validated_data)
        return Response({**ExpenseSerializer(_expense(pk)).data, "warnings": warnings})

    @extend_schema(responses=None)
    def delete(self, request, pk):
        services.delete_expense(get_object_or_404(Expense, pk=pk))
        return Response(status=204)


class ExpensePayments(FinanceView):
    @extend_schema(responses=PaymentSerializer(many=True))
    def get(self, request, pk):
        get_object_or_404(Expense, pk=pk)
        queryset = Payment.objects.filter(expense_id=pk).order_by("paid_at", "id")
        return Response(PaymentSerializer(queryset, many=True).data)

    @extend_schema(request=PaymentInput, responses=PaymentSerializer)
    def post(self, request, pk):
        get_object_or_404(Expense, pk=pk)
        data = PaymentInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        payment, created = services.record_expense_payment(
            pk, v["amount_paise"], v["method"], v.get("reference", ""), v.get("paid_at"), _key(request),
            recorded_by=request.user)
        return _payment_response(payment, created)


class MilestonePay(FinanceView):
    """Pays an advance / final instalment. Without an amount it pays what is left of that instalment."""

    @extend_schema(request=MilestonePayInput, responses=PaymentSerializer)
    def post(self, request, pk):
        get_object_or_404(VendorPaymentPlan, pk=pk)
        data = MilestonePayInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        payment, created = services.pay_milestone(pk, v.get("amount_paise"), v["method"], v.get("reference", ""),
                                                  _key(request), recorded_by=request.user)
        return _payment_response(payment, created)


# ---------------------------------------------------------------- across weddings

class UpcomingPayments(FinanceView):
    """Unpaid instalments and bills due in the next `?days=` (default 14) or already late."""

    @extend_schema(responses=dict)
    def get(self, request):
        try:
            days = min(max(int(request.query_params.get("days", 14)), 0), 365)
        except ValueError:
            days = 14
        return Response(services.upcoming_payments(days))


class FinanceOverview(FinanceView):
    @extend_schema(responses=dict)
    def get(self, request):
        rows = services.overview()
        keys = ("invoiced_paise", "received_paise", "planned_expense_paise", "paid_expense_paise",
                "estimated_profit_paise", "actual_profit_paise")
        return Response({"totals": {key: sum(r[key] for r in rows) for key in keys}, "weddings": rows})


# ---------------------------------------------------------------- Razorpay

class RazorpayOrder(FinanceView):
    """Starts an online payment for what is still owed on the invoice."""

    @extend_schema(request=Serializer, responses=dict)
    def post(self, request, pk):
        invoice = _invoice(pk)
        remaining = invoice.amount_paise - invoice.paid
        if remaining <= 0:
            raise services.Conflict("This invoice is already fully paid.")
        return Response(razorpay_client.create_order(remaining, invoice.pk))


class RazorpayVerify(FinanceView):
    """Checks the signature, then records one payment. Calling it twice records it only once."""

    @extend_schema(request=RazorpayVerifyInput, responses=PaymentSerializer)
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        data = RazorpayVerifyInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        if not razorpay_client.verify_signature(v["razorpay_order_id"], v["razorpay_payment_id"],
                                                v["razorpay_signature"]):
            return Response({"detail": "The payment signature is not valid, so no payment was recorded."},
                            status=400)
        try:
            order = razorpay_client.order_details(v["razorpay_order_id"])
        except Exception:  # noqa: BLE001 - never echo gateway errors (they can carry secrets)
            return Response({"detail": "Could not confirm this order with Razorpay."}, status=502)
        if order["receipt"] != str(invoice.pk):
            return Response({"detail": "This payment belongs to a different invoice."}, status=400)
        with transaction.atomic():
            payment, created = services.record_invoice_payment(
                invoice.pk, order["amount"], "RAZORPAY", v["razorpay_payment_id"],
                idempotency_key=f"razorpay:{v['razorpay_payment_id']}")
        return _payment_response(payment, created)


# ---------------------------------------------------------------- lists for the Payments page

class AllInvoices(FinanceView):
    """Customer invoices across weddings. ?wedding=<id>  ?status=open|unpaid|partial|paid|overdue"""

    @extend_schema(responses=InvoiceRowSerializer(many=True))
    def get(self, request):
        queryset = with_paid(Invoice.objects.select_related("wedding", "client").prefetch_related("links"))
        params = request.query_params
        if params.get("wedding"):
            queryset = queryset.filter(wedding_id=params["wedding"])
        wanted = params.get("status", "")
        if wanted == "open":
            queryset = queryset.exclude(status="PAID")
        elif wanted == "overdue":
            queryset = queryset.exclude(status="PAID").filter(due_date__lt=timezone.localdate())
        elif wanted in ("unpaid", "partial", "paid"):
            queryset = queryset.filter(status=wanted.upper())
        return Response(InvoiceRowSerializer(queryset.order_by("due_date", "id"), many=True).data)


class VendorBills(FinanceView):
    """What we owe vendors, each bill with its instalments. ?wedding=<id>  ?status=open|overdue|paid"""

    @extend_schema(responses=VendorBillSerializer(many=True))
    def get(self, request):
        queryset = with_paid(Expense.objects.select_related("vendor", "wedding").prefetch_related("vendorpaymentplan_set", "payments"))
        if request.query_params.get("wedding"):
            queryset = queryset.filter(wedding_id=request.query_params["wedding"])
        # filtering here, not in the browser, keeps the answer small when there are hundreds of paid bills
        wanted = request.query_params.get("status", "")
        if wanted == "open":
            queryset = queryset.exclude(status="PAID")
        elif wanted == "overdue":
            queryset = queryset.exclude(status="PAID").filter(due_date__lt=timezone.localdate())
        elif wanted == "paid":
            queryset = queryset.filter(status="PAID")
        return Response(VendorBillSerializer(queryset.order_by("due_date", "id"), many=True).data)


class PaymentLedger(FinanceView):
    """Every payment, newest first. ?wedding=<id>  ?direction=IN|OUT"""

    @extend_schema(responses=LedgerSerializer(many=True))
    def get(self, request):
        queryset = Payment.objects.select_related("wedding", "invoice__client", "expense__vendor", "recorded_by",
                                                  "payment_link").order_by("-paid_at", "-id")
        params = request.query_params
        if params.get("wedding"):
            queryset = queryset.filter(wedding_id=params["wedding"])
        if params.get("direction") in ("IN", "OUT"):
            queryset = queryset.filter(direction=params["direction"])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(LedgerSerializer(page, many=True).data)


class PaymentDetail(FinanceView):
    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        """Undo a payment typed in by mistake (the founder is told)."""
        services.undo_payment(get_object_or_404(Payment, pk=pk), request.user)
        return Response(status=204)


# ---------------------------------------------------------------- payment links (staff side)

class InvoiceLinks(FinanceView):
    @extend_schema(responses=PaymentLinkSerializer(many=True))
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        return Response(PaymentLinkSerializer(invoice.links.all(), many=True).data)

    @extend_schema(request=PaymentLinkInput, responses=PaymentLinkSerializer)
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice.objects.select_related("client", "wedding"), pk=pk)
        data = PaymentLinkInput(data=request.data)
        data.is_valid(raise_exception=True)
        link = links.create_link(invoice, data.validated_data.get("amount_paise"), request.user,
                                 data.validated_data["days"])
        return Response(PaymentLinkSerializer(link).data, status=201)


class LinkCancel(FinanceView):
    @extend_schema(request=Serializer, responses=PaymentLinkSerializer)
    def post(self, request, pk):
        return Response(PaymentLinkSerializer(links.cancel_link(get_object_or_404(PaymentLink, pk=pk))).data)


# ---------------------------------------------------------------- payment links (the customer's side, no login)

class PublicView(APIView):
    """No login: the long random token in the address is the only key. Rate limited, and shows nothing else."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_pay"

    def link(self, token):
        return get_object_or_404(PaymentLink.objects.select_related("invoice__wedding", "invoice__client", "payment"),
                                 token=token)


class PublicLinkDetails(PublicView):
    @extend_schema(responses=dict)
    def get(self, request, token):
        response = Response(links.public_details(self.link(token)))
        response["Cache-Control"] = "no-store"
        response["X-Robots-Tag"] = "noindex"
        return response


class PublicLinkOrder(PublicView):
    @extend_schema(request=Serializer, responses=PublicOrderResult)
    def post(self, request, token):
        return Response(links.start_payment(self.link(token)))


class PublicLinkVerify(PublicView):
    @extend_schema(request=RazorpayVerifyInput, responses=dict)
    def post(self, request, token):
        link = self.link(token)
        data = RazorpayVerifyInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        links.complete_payment(link, v["razorpay_order_id"], v["razorpay_payment_id"], v["razorpay_signature"])
        link.refresh_from_db()
        return Response(links.public_details(self.link(token)))
