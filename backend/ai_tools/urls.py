from django.urls import path

from ai_tools import views

# "generate-checklist/confirm/" is a different address from "generate-checklist/"
urlpatterns = [
    path("ai/extract-quotation/", views.ExtractQuotation.as_view()),
    path("ai/generate-checklist/", views.GenerateChecklist.as_view()),
    path("ai/generate-checklist/confirm/", views.ConfirmChecklist.as_view()),
]
