from django.urls import path
from rest_framework.routers import DefaultRouter

from vendors.views import VendorCategoryList, VendorViewSet

router = DefaultRouter()
router.register("vendors", VendorViewSet, basename="vendor")

urlpatterns = [path("vendor-categories/", VendorCategoryList.as_view())] + router.urls
