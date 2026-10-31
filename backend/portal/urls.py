from django.urls import path

from portal import views

# everything the customer website uses lives under /api/portal/
urlpatterns = [
    path("portal/signup/", views.SignupView.as_view()),
    path("portal/login/", views.LoginView.as_view()),
    path("portal/me/", views.Me.as_view()),
    path("portal/profile/", views.Profile.as_view()),
    path("portal/invoices/", views.Invoices.as_view()),
    path("portal/invoices/<int:pk>/pay/", views.PayInvoice.as_view()),
]
