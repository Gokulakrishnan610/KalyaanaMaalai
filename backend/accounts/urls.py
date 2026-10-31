from django.urls import path
from rest_framework.routers import DefaultRouter

from accounts.views import LoginView, MeView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/login/", LoginView.as_view()),
    path("auth/me/", MeView.as_view()),
    *router.urls,
]
