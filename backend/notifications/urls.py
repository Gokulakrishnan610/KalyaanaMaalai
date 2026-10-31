from django.urls import path

from notifications import views

urlpatterns = [
    path("notifications/", views.NotificationList.as_view()),
    path("notifications/read-all/", views.NotificationReadAll.as_view()),
    path("notifications/<int:pk>/read/", views.NotificationRead.as_view()),
]
