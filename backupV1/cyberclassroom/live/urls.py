from django.urls import path
from . import views

urlpatterns = [
    # path('', views.alert, name='index'),
    
    
    path('', views.index, name='index'),
    path('searchRoom', views.searchRoom, name='searchRoom'),
    path('searchSubject',views.searchSubject,name='searchSubject'),
    path('showSubjectInRoom/<room>/',views.showSubjectInRoom,name='showSubjectInRoom'),
    path('showTime',views.showTime,name='showTime'),
    path('getLocation/<location>/',views.getLocation,name='getLocation'),

    
    
    # สำหรับงานถ่ายทอดสด
    # path('live', views.live, name='live'),
    # path('get-live-viewers/', views.get_live_viewers, name='get-live-viewers'),
    # สำหรับงานถ่ายทอดสด
    path('classschedulecenter',views.get_class_schedule_center),
    # path('class-schedule', get_class_schedule_center),
    # path('searchRoom', views.index, name='searchRoom'),
    # path('searchSubject',views.index,name='searchSubject'),
    # path('showSubjectInRoom/<room>/',views.index,name='showSubjectInRoom'),    
]