"""Login for customers. A customer token has a different shape from a staff token, so it is refused by every
staff screen, and a staff token is refused here."""
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from portal.models import Customer

TOKEN_DAYS = 7


def make_token(customer: Customer) -> str:
    now = datetime.now(timezone.utc)
    claims = {"customer_id": customer.pk, "typ": "customer", "iat": now, "exp": now + timedelta(days=TOKEN_DAYS)}
    return jwt.encode(claims, settings.SECRET_KEY, algorithm="HS256")


class CustomerAuthentication(BaseAuthentication):
    """Reads "Authorization: Bearer <token>" and returns the Customer."""

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if len(parts) != 2 or parts[0].lower() != b"bearer":
            return None
        try:
            claims = jwt.decode(parts[1], settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.PyJWTError:
            raise AuthenticationFailed("Please log in again.") from None
        if claims.get("typ") != "customer":
            raise AuthenticationFailed("Please log in again.")
        try:
            return Customer.objects.get(pk=claims["customer_id"]), None
        except (Customer.DoesNotExist, KeyError):
            raise AuthenticationFailed("Please log in again.") from None

    def authenticate_header(self, request):
        return "Bearer"


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, Customer)
