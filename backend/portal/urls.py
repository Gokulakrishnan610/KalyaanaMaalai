from django.urls import path

from portal import vendor_views, views

# everything the customer website uses lives under /api/portal/
urlpatterns = [
    path("portal/signup/", views.SignupView.as_view()),
    path("portal/login/", views.LoginView.as_view()),
    path("portal/forgot-password/", views.ForgotPassword.as_view()),
    path("portal/set-password/", views.SetPassword.as_view()),
    path("portal/me/", views.Me.as_view()),
    path("portal/profile/", views.Profile.as_view()),
    path("portal/invoices/", views.Invoices.as_view()),
    path("portal/invoices/<int:pk>/pay/", views.PayInvoice.as_view()),
    path("portal/vendor/login/", vendor_views.VendorLogin.as_view()),
    path("portal/vendor/me/", vendor_views.VendorMe.as_view()),
    path("portal/vendor/password/", vendor_views.VendorPassword.as_view()),
    path("portal/vendor/bookings/", vendor_views.VendorBookings.as_view()),
    path("portal/vendor/payments/", vendor_views.VendorPayments.as_view()),
    path("portal/vendor/requests/", vendor_views.VendorRequests.as_view()),
    path("portal/vendor/requests/<int:pk>/quote/", vendor_views.VendorQuote.as_view()),
]
