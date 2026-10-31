from django.urls import path

from tasks import views

urlpatterns = [
    path("weddings/<int:wedding_id>/tasks/", views.WeddingTaskList.as_view()),
    path("weddings/<int:wedding_id>/tasks/from-template/", views.TaskFromTemplate.as_view()),
    path("tasks/bulk/", views.TaskBulk.as_view()),
    path("tasks/<int:pk>/", views.TaskDetail.as_view()),
    path("tasks/<int:pk>/move/", views.TaskMove.as_view()),
]
