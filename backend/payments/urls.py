from django.urls import path

from payments import views

# "invoices/extra-guests/" must come before "invoices/" under the wedding
urlpatterns = [
    path("weddings/<int:wedding_id>/finance/", views.WeddingFinance.as_view()),
    path("weddings/<int:wedding_id>/invoices/extra-guests/", views.ExtraGuestInvoice.as_view()),
    path("weddings/<int:wedding_id>/invoices/", views.WeddingInvoices.as_view()),
    path("weddings/<int:wedding_id>/expenses/", views.WeddingExpenses.as_view()),
    path("weddings/<int:wedding_id>/milestones/", views.WeddingMilestones.as_view()),
    path("invoices/", views.AllInvoices.as_view()),
    path("invoices/<int:pk>/", views.InvoiceDetail.as_view()),
    path("invoices/<int:pk>/payment-links/", views.InvoiceLinks.as_view()),
    path("payment-links/<int:pk>/cancel/", views.LinkCancel.as_view()),
    path("pay/<str:token>/", views.PublicLinkDetails.as_view()),
    path("pay/<str:token>/order/", views.PublicLinkOrder.as_view()),
    path("pay/<str:token>/verify/", views.PublicLinkVerify.as_view()),
    path("payments/", views.PaymentLedger.as_view()),
    path("payments/<int:pk>/", views.PaymentDetail.as_view()),
    path("finance/vendor-bills/", views.VendorBills.as_view()),
    path("invoices/<int:pk>/payments/", views.InvoicePayments.as_view()),
    path("invoices/<int:pk>/razorpay/order/", views.RazorpayOrder.as_view()),
    path("invoices/<int:pk>/razorpay/verify/", views.RazorpayVerify.as_view()),
    path("expenses/<int:pk>/", views.ExpenseDetail.as_view()),
    path("expenses/<int:pk>/payments/", views.ExpensePayments.as_view()),
    path("milestones/<int:pk>/pay/", views.MilestonePay.as_view()),
    path("finance/upcoming-payments/", views.UpcomingPayments.as_view()),
    path("finance/overview/", views.FinanceOverview.as_view()),
]
