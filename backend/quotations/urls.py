from django.urls import path

from quotations import views

# "quotations/extract/" must come before "quotations/<id>/"
urlpatterns = [
    path("quotation-requests/", views.AllRequests.as_view()),
    path("weddings/<int:wedding_id>/quotation-requests/", views.WeddingRequests.as_view()),
    path("weddings/<int:wedding_id>/vendors/", views.WeddingVendors.as_view()),
    path("quotation-requests/<int:pk>/", views.RequestDetail.as_view()),
    path("quotation-requests/<int:pk>/send/", views.RequestSend.as_view()),
    path("quotation-requests/<int:pk>/quotations/", views.RequestQuotations.as_view()),
    path("quotation-requests/<int:pk>/compare/", views.RequestCompare.as_view()),
    path("quotations/extract/", views.QuotationExtract.as_view()),
    path("quotations/<int:pk>/", views.QuotationDetail.as_view()),
    path("quotations/<int:pk>/upload/", views.QuotationUpload.as_view()),
    path("quotations/<int:pk>/select/", views.QuotationSelect.as_view()),
]
