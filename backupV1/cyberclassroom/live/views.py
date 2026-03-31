import datetime
from urllib import request

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse,JsonResponse
from django.shortcuts import render
import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django import template
#from django.db.models import Count
from . import config
from .models import (Classrooms, ClassScheduleCenter, Locations,
                     LogSubjectInRoom,Count)


#from django.db.models import Q
# Create your views here.
def index(request):
    now = datetime.datetime.now()
    IsDayInt=now.strftime("%w")
    data_classroom= Classrooms.objects.filter(room_status="1").order_by('room_location',)

    roomCount= data_classroom.count()

    page = request.GET.get('page', 1)
    paginator = Paginator(data_classroom, 9)
    try:
        users = paginator.page(page)
        classroom_p = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
        classroom_p = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages) 
        classroom_p = paginator.page(paginator.num_pages)   
    # data_classroom= ClassScheduleCenter.objects.annotate(room_name=Count('classrooms'))
    #print(data_classroom)
    # y = config.x + 20
    # my_title = config.my_string
    
    context = {
        'data_classroom': data_classroom,
        'roomCount':roomCount,
        'users': users ,
        'classroom_p': classroom_p,
        'IsDayInt':IsDayInt, 
        'offline':'true',      
    }
    return render(request,'live/index.html',context=context)

def alert(request):
    return render(request,'live/refrain.html')

def live(request):
    try:
        data_c = Count.objects.get(room_name='rucom')
        # print(data_c.sessions_total)
        countOnline = data_c.sessions_total
        # c=data_c.sessions_total
        # print(c)
    except Count.DoesNotExist:
        # Handle the case where no matching record is found
        countOnline=0
    context = {
        'sessions_total':countOnline,
    }
    return render(request,'live/live.html',context=context)

def get_live_viewers(request):
    try:
        data_c = Count.objects.get(room_name='rucom')
        countOnline = data_c.sessions_total
    except Count.DoesNotExist:
        countOnline = 0  # ถ้าไม่มีข้อมูล ให้กำหนดเป็น 0

    return JsonResponse({'sessions_total': countOnline})
    
def searchRoom(request):
    q=request.GET['inpuSearch']
    now = datetime.datetime.now()
    IsDayInt=now.strftime("%w")
    if q != 'campus':
        data_classroom= Classrooms.objects.filter(room_status="1",room_name__icontains=q)
    else :
        data_classroom= Classrooms.objects.filter(room_status="1",room_name__icontains=q) | Classrooms.objects.filter(room_name__icontains="room")

    # data_classroom= Classrooms.objects.filter(room_status="1",room_name__icontains=q)
    roomCount= data_classroom.count()

    page = request.GET.get('page', 1)
    paginator = Paginator(data_classroom, 6)
    try:
        classroom_p = paginator.page(page)
    except PageNotAnInteger:
        classroom_p = paginator.page(1)
    except EmptyPage:
        classroom_p = paginator.page(paginator.num_pages)   

    context = {
        'data_classroom': data_classroom,
        'roomCount':roomCount,
        'q':q,
        'classroom_p': classroom_p,
        'IsDayInt':IsDayInt,  
    }
    return render(request,'live/index.html',context=context) 

def searchSubject(request):
    q=request.GET['inpuSearchSubject']
    data_subject= ClassScheduleCenter.objects.filter(course_no__icontains=q)
    subjectCount= data_subject.count()
    context = {
        'data_subject': data_subject,
        'subjectCount':subjectCount,
        'q':q
    }
    return render(request,'live/searchSubject.html',context=context)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def showSubjectInRoom(request,room):
    x = datetime.datetime.now()
    IsDayString=x.strftime("%A")
    IsDayInt=x.strftime("%w")
    # print(IsDayInt)
    q=room
    data_classroom = Classrooms.objects.get(room_name=q)
    location=data_classroom.room_location_id
    # print(location)
    data_subject= ClassScheduleCenter.objects.filter(room_name=q,course_day=IsDayInt).order_by('-course_day','time_start')
    subjectCount= data_subject.count()
    #print(data_subject.query)
    # data_subject = Classrooms.objects.filter(classschedulecenter__room_name=q,classschedulecenter__course_day=IsDayInt).order_by('-classschedulecenter__course_day')
    # subjectCount= data_subject.count()
    # print(data_subject.query)
    # print(data_subject[0].room_location)
    #แสดงรายการ วิชาที่มีอยู่ในห้องนี้แต่ไม่ได้มีเรียนในวันนี้ทั้งหมด
    data_subjec_out= ClassScheduleCenter.objects.filter(room_name=q).order_by('-course_day','time_start')
    subjectCount_out= data_subjec_out.count()
    if location ==1 :
        # server = config.serverMedia66
        server = config.serverMedia68
        # q=q.lower()
    elif location ==2 :
        server = config.serverMedia65
    elif location ==3 or location == 5 or location == 7 :
        server = config.serverMedia66
    elif location ==8 :
        server = config.serverMedia67
    else :
        server = config.serverMdeia88

    log=LogSubjectInRoom(course_no=q,created_at=x,room_location_id=location,user_ip=get_client_ip(request))
    log.save()

    # data_count=Count.objects.filter(room_name="klb201")
    # # Get the count of the filtered queryset
    # count = data_count.count()

    # print(f"Count of matching rows: {count}")
    # countOnline=0
    try:
        data_c = Count.objects.get(room_name=q.lower())
        # print(data_c.sessions_total)
        countOnline = data_c.sessions_total
        # c=data_c.sessions_total
        # print(c)
    except Count.DoesNotExist:
        # Handle the case where no matching record is found
        countOnline=0
        
    context = {
        'data_subject': data_subject,
        'subjectCount':subjectCount,
        'q':q,
        'IsDayString':IsDayString,
        'data_subjec_out':data_subjec_out,
        'subjectCount_out':subjectCount_out,
        'location':location,
        'server':server,
        'room_comment':data_classroom.room_comment,
        'sessions_total':countOnline
    }
    return render(request,'live/showSubjectInRoom.html',context=context) 

# def live(request):
#     return render(request,'live/live.html') 
    
# @login_required(login_url='admin/login/')
def showTime(request):
    x = datetime.datetime.now()
    IsDayString=x.strftime("%A")
    IsDayInt=x.strftime("%w")
    print(IsDayInt)
    # print("5555")
    # week_days=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    # week_num=datetime.date(2020,7,24).weekday()
    # print(week_days[week_num])

    data_subject= ClassScheduleCenter.objects.filter(course_day=IsDayInt).order_by('-course_day','time_start')
    subjectCount= data_subject.count()
    # print(data_subject.query)
    data_location=Locations.objects.all()
    print(data_location)
  
    context = {
        'IsDayInt':IsDayInt,
        'data_subject': data_subject,
        'data_location':data_location
    }
    return render(request,'live/showTime.html',context=context)     

# @login_required
def getLocation(request,location):
    now = datetime.datetime.now()
    IsDayInt=now.strftime("%w")
    data_classroom= Classrooms.objects.filter(room_status="1",room_location_id=location).order_by('room_name',)
    roomCount= data_classroom.count()

    page = request.GET.get('page', 1)
    paginator = Paginator(data_classroom, 9)
    try:
        users = paginator.page(page)
        classroom_p = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
        classroom_p = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages) 
        classroom_p = paginator.page(paginator.num_pages) 
    # print("getlocation",location)
    location =int(location)
    if location ==1 :
        # server = config.serverMedia66
        server = config.serverMedia68
        # q=q.lower()
    elif location ==2 :
        server = config.serverMedia65
    elif location ==3 or location == 5 or location == 7 :
        server = config.serverMedia66
    else :
        server = config.serverMdeia88

    # print(server)
    context={
        'data_classroom':data_classroom,
        'classroom_p':classroom_p,
        'location':location,
        'server':server,
        'IsDayInt':IsDayInt, 
    }
    return render(request,'live/getLocation.html',context=context)   

def error_404_view(request, exception):
    return render(request, 'live/404.html')

def error_500_view(request):
    return render(request,'live/500.html')

def get_class_schedule_center(request):
    # ดึงข้อมูลทั้งหมดจากตาราง live_classschedulecenter
    class_schedules = ClassScheduleCenter.objects.all().values()
    # แปลงข้อมูลเป็น JSON
    return JsonResponse(list(class_schedules), safe=False)



