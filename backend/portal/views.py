from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from portal import accounts, services
from portal.auth import CustomerAuthentication, IsCustomer, make_token
from portal.models import Customer, VendorAccount
from portal.serializers import LoginSerializer, ProfileSerializer, SignupSerializer


def customer_data(customer: Customer) -> dict:
    enquiry = customer.enquiry
    return {
        "customer": {"id": customer.pk, "name": customer.name, "email": customer.email, "phone": customer.phone},
        "stage": services.stage_for(enquiry),
        "profile": {**services.profile_status(enquiry), "values": services.profile_values(enquiry)},
        "is_client": customer.client_id is not None,
    }


class OpenView(APIView):
    """Sign up and log in need no token, and are limited per address to slow down password guessing."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "portal_auth"


class SignupView(OpenView):
    @extend_schema(request=SignupSerializer, responses=dict)
    def post(self, request):
        data = SignupSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        customer = services.create_account(**data.validated_data)
        return Response({"token": make_token(customer), **customer_data(customer)}, status=201)


class LoginView(OpenView):
    @extend_schema(request=LoginSerializer, responses=dict)
    def post(self, request):
        data = LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        customer = Customer.objects.filter(email=data.validated_data["email"].lower()).first()
        # the same message for an unknown email and a wrong password, so nobody can find out who has an account
        if customer is None or not customer.check_password(data.validated_data["password"]):
            return Response({"detail": "Wrong email or password."}, status=400)
        customer.last_login_at = timezone.now()
        customer.save(update_fields=["last_login_at"])
        return Response({"token": make_token(customer), **customer_data(customer)})


class CustomerView(APIView):
    authentication_classes = [CustomerAuthentication]
    permission_classes = [IsCustomer]


class Me(CustomerView):
    @extend_schema(responses=dict)
    def get(self, request):
        return Response(customer_data(request.user))


class Profile(CustomerView):
    @extend_schema(request=ProfileSerializer, responses=dict)
    def patch(self, request):
        data = ProfileSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.update_profile(request.user, data.validated_data)
        request.user.refresh_from_db()
        return Response(customer_data(request.user))


class Invoices(CustomerView):
    @extend_schema(responses=dict)
    def get(self, request):
        return Response(services.invoices_for(request.user))


class PayInvoice(CustomerView):
    @extend_schema(request=None, responses=dict)
    def post(self, request, pk):
        return Response({"path": services.pay_path(request.user, pk)})


class ForgotPassword(OpenView):
    @extend_schema(request=None, responses=dict)
    def post(self, request):
        accounts.request_reset(str(request.data.get("email", "")))
        return Response({"detail": "If that email has an account, we have sent a link to it."})


class SetPassword(OpenView):
    """The page behind the emailed link: choose a password, and you are logged in."""

    @extend_schema(request=None, responses=dict)
    def post(self, request):
        kind, account = accounts.set_password(str(request.data.get("token", "")), str(request.data.get("password", "")))
        account.last_login_at = timezone.now()
        account.save(update_fields=["last_login_at"])
        return Response({"kind": kind, "token": make_token(account, kind)})
