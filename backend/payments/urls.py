from django.urls import path

from payments import views

# "invoices/extra-guests/" must come before "invoices/" under the wedding
urlpatterns = [
    path("weddings/<int:wedding_id>/finance/", views.WeddingFinance.as_view()),
    path("weddings/<int:wedding_id>/invoices/extra-guests/", views.ExtraGuestInvoice.as_view()),
    path("weddings/<int:wedding_id>/invoices/", views.WeddingInvoices.as_view()),
    path("weddings/<int:wedding_id>/expenses/", views.WeddingExpenses.as_view()),
    path("weddings/<int:wedding_id>/milestones/", views.WeddingMilestones.as_view()),
    path("invoices/<int:pk>/", views.InvoiceDetail.as_view()),
    path("invoices/<int:pk>/payments/", views.InvoicePayments.as_view()),
    path("invoices/<int:pk>/razorpay/order/", views.RazorpayOrder.as_view()),
    path("invoices/<int:pk>/razorpay/verify/", views.RazorpayVerify.as_view()),
    path("expenses/<int:pk>/", views.ExpenseDetail.as_view()),
    path("expenses/<int:pk>/payments/", views.ExpensePayments.as_view()),
    path("milestones/<int:pk>/pay/", views.MilestonePay.as_view()),
    path("finance/upcoming-payments/", views.UpcomingPayments.as_view()),
    path("finance/overview/", views.FinanceOverview.as_view()),
]
