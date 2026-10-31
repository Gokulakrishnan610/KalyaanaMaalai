from django.urls import path

from dashboard.views import SummaryView

urlpatterns = [path("dashboard/summary/", SummaryView.as_view())]
