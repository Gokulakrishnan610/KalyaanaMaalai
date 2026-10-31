from django.urls import path

from live.views import stream

urlpatterns = [path("live/stream/", stream)]
