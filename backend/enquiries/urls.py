from rest_framework.routers import DefaultRouter

from enquiries.views import EnquiryViewSet, FollowUpViewSet

router = DefaultRouter()
router.register("enquiries", EnquiryViewSet, basename="enquiry")
router.register("follow-ups", FollowUpViewSet, basename="follow-up")

urlpatterns = router.urls
