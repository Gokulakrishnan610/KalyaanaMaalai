from rest_framework.routers import DefaultRouter

from enquiries.views import EnquiryViewSet

router = DefaultRouter()
router.register("enquiries", EnquiryViewSet, basename="enquiry")

urlpatterns = router.urls
