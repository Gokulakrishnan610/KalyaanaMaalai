from django.urls import path

from weddings import views

urlpatterns = [
    path("weddings/", views.WeddingList.as_view()),
    path("weddings/<int:pk>/", views.WeddingDetail.as_view()),
    path("weddings/<int:wedding_id>/progress/", views.WeddingProgress.as_view()),
    path("weddings/<int:wedding_id>/functions/", views.WeddingFunctionList.as_view()),
    path("functions/<int:pk>/", views.FunctionDetail.as_view()),
    path("weddings/<int:wedding_id>/assignments/", views.WeddingAssignments.as_view()),
    path("venues/", views.VenueList.as_view()),
    path("venues/<int:pk>/", views.VenueDetail.as_view()),
    path("weddings/<int:wedding_id>/schedule/", views.WeddingScheduleList.as_view()),
    path("functions/<int:function_id>/schedule/", views.FunctionScheduleList.as_view()),
    path("schedule/<int:pk>/", views.ScheduleItemDetail.as_view()),
    path("weddings/<int:wedding_id>/checkins/", views.WeddingCheckins.as_view()),
    path("checkins/<int:pk>/", views.CheckinDetail.as_view()),
    path("public/checkin/<str:token>/", views.public_checkin),
    path("public/checkin/<str:token>/arrive/", views.public_arrive),
]
