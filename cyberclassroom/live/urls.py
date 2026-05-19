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
    path('get-live-viewers/<str:room_name>/', views.get_live_room_viewers, name='get-live-viewers'),
    # Chat polling endpoints
    path('chat/<str:room_name>/messages/', views.chat_fetch, name='chat_fetch'),
    path('chat/<str:room_name>/send/',     views.chat_send,  name='chat_send'),
    # path('not-available/', views.not_available, name='not_available'),
    path('live-monitor/', views.live_monitor_view, name='live_monitor'),
    path('viewer-data/', views.live_viewer_data, name='live_viewer_data'),
    path('monitor-sse/', views.monitor_sse, name='monitor_sse'),  # SSE real-time push
    path('schedule-editor/', views.schedule_editor, name='schedule_editor'),
    path('debug-headers/', views.debug_headers, name='debug_headers'),
    path('dashboard/', views.dashboard_stats, name='dashboard'),
    # สำหรับงานถ่ายทอดสด
    # path('live', views.live, name='live'),
    # path('get-live-viewers/', views.get_live_viewers, name='get-live-viewers'),
    # สำหรับงานถ่ายทอดสด
    # path('classschedulecenter',views.get_class_schedule_center),
    # path('class-schedule', get_class_schedule_center),
    # path('searchRoom', views.index, name='searchRoom'),
    # path('searchSubject',views.index,name='searchSubject'),
    # path('showSubjectInRoom/<room>/',views.index,name='showSubjectInRoom'),    
    # path('test-error-500/', views.test_error_500/', views.test_error_500, name='test_error_500'),
]
