from django.urls import path
from rest_framework.routers import DefaultRouter

from agreements import portal_views
from agreements.views import AgreementViewSet

router = DefaultRouter()
router.register("agreements", AgreementViewSet, basename="agreement")

urlpatterns = [
    path("portal/agreements/", portal_views.AgreementList.as_view()),
    path("portal/agreements/<int:pk>/", portal_views.AgreementDetail.as_view()),
    path("portal/agreements/<int:pk>/code/", portal_views.AgreementCode.as_view()),
    path("portal/agreements/<int:pk>/sign/", portal_views.AgreementSign.as_view()),
] + router.urls
