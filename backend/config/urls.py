from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# Every app owns its own urls.py. Only Member 1 changes this file.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/", include("accounts.urls")),
    path("api/", include("clients.urls")),
    path("api/", include("enquiries.urls")),
    path("api/", include("weddings.urls")),
    path("api/", include("tasks.urls")),
    path("api/", include("vendors.urls")),
    path("api/", include("quotations.urls")),
    path("api/", include("payments.urls")),
    path("api/", include("ai_tools.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("dashboard.urls")),
    path("api/", include("incidents.urls")),
    path("api/", include("live.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
