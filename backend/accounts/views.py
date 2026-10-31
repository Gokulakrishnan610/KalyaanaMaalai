from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import Role, User
from accounts.serializers import EditUserSerializer, LoginSerializer, NewUserSerializer, UserSerializer
from common.permissions import allow_roles


class LoginView(APIView):
    """POST email + password. Returns the login token and the user."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: dict})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token = AccessToken.for_user(user)
        return Response({"access": str(token), "user": UserSerializer(user).data})


class MeView(APIView):
    """The logged-in user."""

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """Staff accounts. Planners may list them (for assigning tasks); only the founder changes them."""

    queryset = User.objects.all()
    pagination_class = None  # the list is short and feeds dropdowns

    def get_serializer_class(self):
        if self.action == "create":
            return NewUserSerializer
        if self.action in ("update", "partial_update"):
            return EditUserSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [allow_roles(Role.PLANNER)()]
        return [allow_roles()()]
