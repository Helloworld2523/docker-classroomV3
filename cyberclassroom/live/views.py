import datetime
import json
import os
import io
from urllib import request

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse,JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django import template
#from django.db.models import Count
from . import config
from .models import (Classrooms, ClassScheduleCenter, Locations,
                     LogSubjectInRoom,Count,LiveClassroom)

from django_ratelimit.decorators import ratelimit
from django.views.decorators.cache import cache_page
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
#from django.db.models import Q

# --- helper: path to schedule JSON ---
SCHEDULE_JSON_PATH = os.path.join(os.path.dirname(__file__), 'data', 'schedule.json')

def _load_schedule():
    """โหลด schedule.json และคืนค่า dict ถ้าไม่มีไฟล์คืน default เปล่า"""
    try:
        with open(SCHEDULE_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"central": [], "regional": []}

# Create your views here.
def index(request):
    now = datetime.now()
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

    schedule = _load_schedule()

    context = {
        'data_classroom': data_classroom,
        'roomCount':roomCount,
        'users': users ,
        'classroom_p': classroom_p,
        'IsDayInt':IsDayInt,
        'offline':'true',
        'schedule_central':  schedule.get('central', []),
        'schedule_regional': schedule.get('regional', []),
    }
    return render(request,'live/index.html',context=context)


# ─── Admin: Schedule Editor ────────────────────────────────────────────────────
@staff_member_required
def schedule_editor(request):
    """Admin-only view: อ่าน / บันทึก schedule.json"""
    message = None
    error   = None
    raw_json = ''

    if request.method == 'POST':
        raw_json = request.POST.get('json_content', '')
        try:
            parsed = json.loads(raw_json)
            # ตรวจว่ามี key ที่ถูกต้อง
            if not isinstance(parsed, dict):
                raise ValueError("ต้องเป็น JSON object ระดับบนสุด")
            with open(SCHEDULE_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
            message = "บันทึกสำเร็จแล้ว"
            raw_json = json.dumps(parsed, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, ValueError) as e:
            error = f"JSON ไม่ถูกต้อง: {e}"
    else:
        try:
            with open(SCHEDULE_JSON_PATH, 'r', encoding='utf-8') as f:
                raw_json = f.read()
        except Exception:
            raw_json = json.dumps({"central": [], "regional": []}, ensure_ascii=False, indent=2)

    return render(request, 'admin/schedule_editor.html', {
        'raw_json': raw_json,
        'message': message,
        'error':   error,
        'title':   'แก้ไขกำหนดการ',
    })

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

@cache_page(10)  # cache 10 วินาที
def get_live_viewers(request):
    try:
        data_c = Count.objects.get(room_name='rucom')
        countOnline = data_c.sessions_total
    except Count.DoesNotExist:
        countOnline = 0  # ถ้าไม่มีข้อมูล ให้กำหนดเป็น 0

    return JsonResponse({'sessions_total': countOnline})

def get_live_room_viewers(request, room_name):
    try:
        data_c = Count.objects.get(room_name=room_name)
        countOnline = data_c.sessions_total
    except Count.DoesNotExist:
        countOnline = 0  # ถ้าไม่มีข้อมูล ให้กำหนดเป็น 0

    return JsonResponse({'sessions_total': countOnline})

# @ratelimit(key='ip', rate='10/m', block=True)
def searchRoom(request):
    q=request.GET['inpuSearch']
    now = datetime.now()
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

# @ratelimit(key='ip', rate='10/m', block=True)
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


    
def showSubjectInRoom(request, room):
    now = datetime.now()
    today_day_en = now.strftime("%A")
    today_day_int = now.strftime("%w")  # string '0'-'6'

    # แปลงชื่อห้อง
    q = room.lower()

    # ดึงข้อมูลห้อง (หากไม่พบ จะขึ้น 404)
    data_classroom = get_object_or_404(Classrooms, room_name=room)
    location = data_classroom.room_location_id

    # วิชาที่มีสอนวันนี้
    data_subject = ClassScheduleCenter.objects.filter(
        room_name=room,
        course_day=today_day_int
    ).order_by('time_start')
    subjectCount = data_subject.count()

    # สร้าง mapping ชื่อวันอังกฤษ
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    rotated_days = day_order[datetime.today().weekday():] + day_order[:datetime.today().weekday()]

    def get_day_name(day_value):
        try:
            return day_order[int(day_value)]
        except (ValueError, IndexError, TypeError):
            return None

    # ดึงวิชาทุกวัน และเรียงโดยเริ่มจากวันปัจจุบัน
    all_subjects = list(ClassScheduleCenter.objects.filter(room_name=room))
    # เรียงตามลำดับวันจริง (จันทร์→อาทิตย์), แล้วตามเวลาเริ่ม
    data_subjec_out = sorted(
        [obj for obj in all_subjects if get_day_name(obj.course_day)],
        key=lambda obj: (
            day_order.index(get_day_name(obj.course_day)),
            obj.time_start
        )
    )
    subjectCount_out = len(data_subjec_out)

    # กำหนด server
    if location == 1:
        server = config.serverMedia68
    elif location == 2:
        server = config.serverMedia65
    elif location in [3, 5, 7]:
        server = config.serverMedia66
    elif location == 8:
        server = config.serverMedia67
    else:
        server = config.serverMedia88  # แก้คำผิดจาก serverMdeia88

    # บันทึก log
    LogSubjectInRoom.objects.create(
        course_no=room,
        created_at=now,
        room_location_id=location,
        user_ip=get_client_ip(request)
    )

    # ดึงจำนวนผู้ชมสด
    try:
        data_c = Count.objects.get(room_name=q)
        countOnline = data_c.sessions_total
    except Count.DoesNotExist:
        countOnline = 0

    valid_locations = [1, 2, 3, 5, 7, 8]
    # ส่ง context ไปยัง template
    context = {
        'q': room,
        'IsDayString': today_day_en,
        'data_subject': data_subject,
        'subjectCount': subjectCount,
        'data_subjec_out': data_subjec_out,
        'subjectCount_out': subjectCount_out,
        'today_day_en': today_day_en,
        'location': location,
        'server': server,
        'room_comment': data_classroom.room_comment,
        'sessions_total': countOnline,
        'valid_locations': valid_locations,
    }

    return render(request, 'live/showSubjectInRoom.html', context)

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

def error_400_view(request, exception):
    return render(request, 'live/400.html')

def custom_permission_denied_view(request, exception):
    # exception param ต้องมี เพื่อรองรับ signature ของ handler403
    #return render(request, "live/403.html", status=403)
    return render(request, "live/429.html", status=429)

def get_class_schedule_center(request):
    # ดึงข้อมูลทั้งหมดจากตาราง live_classschedulecenter
    class_schedules = ClassScheduleCenter.objects.all().values()
    # แปลงข้อมูลเป็น JSON
    return JsonResponse(list(class_schedules), safe=False)

def test_error_500(request):
    # โค้ดนี้ตั้งใจทำให้เกิด ZeroDivisionError
    1 / 0
    return HttpResponse("This will never be reached")


@csrf_exempt
def caption_view(request):
    """
    รับ audio/wav (WAV bytes) จาก browser → ส่ง Google STT → คืน JSON { text }
    ใช้ SpeechRecognition library (recognize_google, ไม่ต้องมี API key)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    audio_data = request.body
    if len(audio_data) < 44:          # WAV header = 44 bytes ขั้นต่ำ
        return JsonResponse({'text': ''})

    try:
        import speech_recognition as sr
    except ImportError:
        return JsonResponse({'error': 'SpeechRecognition not installed'}, status=503)

    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 200
    recognizer.dynamic_energy_threshold = True

    def _do_stt():
        audio_file = io.BytesIO(audio_data)
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language='th-TH')

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_do_stt)
            text = future.result(timeout=15)   # รอสูงสุด 15 วิ
        return JsonResponse({'text': text})

    except FuturesTimeout:
        return JsonResponse({'text': '', 'warn': 'STT timeout (>15s)'})
    except sr.UnknownValueError:
        return JsonResponse({'text': ''})      # เงียบ / ไม่เข้าใจ
    except sr.RequestError as e:
        return JsonResponse({'error': f'Google STT unavailable: {e}'}, status=503)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def not_available(request):
    start_time = time(22, 10)  # เวลาเปิดระบบ 07:00
    end_time = time(22, 15)  # เวลา ปิดระบบ 20:30
    context = {
        'start_time': start_time.strftime('%H:%M'),
        'end_time': end_time.strftime('%H:%M'),
    }
    return render(request, 'live/out_of_learning_time.html', context)

@staff_member_required
def live_monitor_view(request):
    rooms = LiveClassroom.objects.filter(room_status='1')

    # เตรียม viewer_map
    viewer_map = {
        count.room_name.strip().lower(): int(count.sessions_total) if str(count.sessions_total).isdigit() else 0
        for count in Count.objects.all()
    }

    # สร้างลิสต์ก่อน
    live_classrooms = [
        {
            'room_name': room.room_name,
            'room_stream': room.room_stream,
            'viewer_count': viewer_map.get(room.room_name.strip().lower(), 0)
        }
        for room in rooms
    ]

    # เรียงตาม viewer_count จากมาก -> น้อย
    live_classrooms.sort(key=lambda x: x['viewer_count'], reverse=True)

    context = {
        'live_classrooms': live_classrooms
    }

    return render(request, 'live/monitor.html', context)

@require_GET
@staff_member_required
def live_viewer_data(request):
    rooms = LiveClassroom.objects.filter(room_status="1")
    data = []
    for room in rooms:
        data.append({
            'room_name': room.room_name,
            'viewer_count': room.viewer_count if room.viewer_count else 0,
        })
    return JsonResponse({'data': data})
