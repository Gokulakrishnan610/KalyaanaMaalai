from django.urls import path

from mailer import views

urlpatterns = [
    path("mail-templates/", views.TemplateList.as_view()),
    path("mail-templates/<str:name>/", views.TemplatePreview.as_view()),
    path("mail-log/", views.MailLog.as_view()),
]
