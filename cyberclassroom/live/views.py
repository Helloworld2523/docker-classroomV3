import datetime
import json
import os
import time as time_module
from urllib import request

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django import template
#from django.db.models import Count
from . import config
from .models import (Classrooms, ClassScheduleCenter, Locations,
                     LogSubjectInRoom, Count, LiveClassroom, ChatMessage, BannedStudent)
from .profanity import censor_message, has_profanity

from django_ratelimit.decorators import ratelimit
from django.views.decorators.cache import cache_page
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.timezone import localtime, now as tz_now

from django.shortcuts import redirect

def _safe_localtime(dt):
    """แปลง datetime เป็น local time — รองรับทั้ง USE_TZ=True และ USE_TZ=False"""
    from django.conf import settings
    if getattr(settings, 'USE_TZ', True) and hasattr(dt, 'tzinfo') and dt.tzinfo:
        return localtime(dt)
    return dt
from django.db.models import Exists, OuterRef
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

    today_schedule_qs = ClassScheduleCenter.objects.filter(
        room_name=OuterRef('room_name'),
        course_day=IsDayInt,
    )
    data_classroom = (
        Classrooms.objects.filter(room_status="1")
        .annotate(has_today=Exists(today_schedule_qs))
        .order_by('-has_today', 'room_location', 'room_order', 'room_name')
    )

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
        'today_date': now.date(),
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
    from live._wowza_poller import get_cached
    cached = get_cached(room_name)
    if cached['total'] > 0 or cached['updated']:
        return JsonResponse({'sessions_total': cached['total']})
    # fallback → DB (กรณี poller ยังไม่ได้รัน หรือ room อื่นที่ไม่ใช่ rucom)
    try:
        data_c = Count.objects.get(room_name=room_name)
        countOnline = data_c.sessions_total
    except Count.DoesNotExist:
        countOnline = 0
    return JsonResponse({'sessions_total': countOnline})

# @ratelimit(key='ip', rate='10/m', block=True)
def searchRoom(request):
    q=request.GET.get('inpuSearch', '').strip()
    if not q:
        return redirect('/')
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
    # University proxy ส่ง X-Real-IP = client IP จริง
    ip = request.META.get('HTTP_X_REAL_IP')
    if not ip:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else None
    if not ip:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def debug_headers(request):
    """ดู headers ที่ Django รับมา — ลบออกหลังใช้งาน"""
    keys = ['REMOTE_ADDR', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP',
            'HTTP_X_FORWARDED_HOST', 'HTTP_HOST']
    data = {k: request.META.get(k, '—') for k in keys}
    data['get_client_ip'] = get_client_ip(request)
    return JsonResponse(data)


@staff_member_required
def dashboard_stats(request):
    from django.db.models import Count as DCount
    from django.db.models.functions import Substr
    from django.core.cache import cache
    from datetime import datetime, timedelta

    now         = datetime.now()
    today_str   = now.strftime('%Y-%m-%d')
    week_start  = (now - timedelta(days=6)).strftime('%Y-%m-%d')
    month_start = now.strftime('%Y-%m-01')
    days30_start = (now - timedelta(days=29)).strftime('%Y-%m-%d')

    CACHE_KEY = f'dashboard_{today_str}'
    cached = cache.get(CACHE_KEY)
    if cached:
        return render(request, 'live/dashboard.html', cached)

    qs = LogSubjectInRoom.objects

    # ── ตัวเลขสรุป ──────────────────────────────────────────────
    total_today = qs.filter(created_at__startswith=today_str).count()
    total_week  = qs.filter(created_at__gte=week_start).count()
    total_month = qs.filter(created_at__gte=month_start).count()
    unique_ip_today = (
        qs.filter(created_at__startswith=today_str)
          .values('user_ip').distinct().count()
    )

    # ── Top 10 ห้อง วันนี้ ──────────────────────────────────────
    top_rooms = list(
        qs.filter(created_at__startswith=today_str)
          .values('course_no')
          .annotate(cnt=DCount('id'))
          .order_by('-cnt')[:10]
    )

    # ── Peak hour วันนี้ — query เดียว ──────────────────────────
    hourly_qs = (
        qs.filter(created_at__startswith=today_str)
          .annotate(hour=Substr('created_at', 12, 2))
          .values('hour')
          .annotate(cnt=DCount('id'))
          .order_by('hour')
    )
    hour_map = {h['hour']: h['cnt'] for h in hourly_qs}
    all_hours    = [f'{h:02d}' for h in range(24)]
    hour_labels  = [f'{h}:00' for h in all_hours]
    hour_data    = [hour_map.get(h, 0) for h in all_hours]

    # ── Trend 30 วัน — query เดียว (GROUP BY day) ───────────────
    trend_qs = (
        qs.filter(created_at__gte=days30_start)
          .annotate(day=Substr('created_at', 1, 10))
          .values('day')
          .annotate(cnt=DCount('id'))
          .order_by('day')
    )
    trend_map = {r['day']: r['cnt'] for r in trend_qs}
    trend_labels = []
    trend_data   = []
    for i in range(29, -1, -1):
        d = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        trend_labels.append(d[5:])
        trend_data.append(trend_map.get(d, 0))

    # ── Top 10 ห้อง เดือนนี้ ────────────────────────────────────
    top_rooms_month = list(
        qs.filter(created_at__gte=month_start)
          .values('course_no')
          .annotate(cnt=DCount('id'))
          .order_by('-cnt')[:10]
    )

    context = {
        'total_today':      total_today,
        'total_week':       total_week,
        'total_month':      total_month,
        'unique_ip_today':  unique_ip_today,
        'top_rooms':        top_rooms,
        'top_rooms_month':  top_rooms_month,
        'hour_labels':      json.dumps(hour_labels),
        'hour_data':        json.dumps(hour_data),
        'trend_labels':     json.dumps(trend_labels),
        'trend_data':       json.dumps(trend_data),
        'today':            today_str,
    }
    cache.set(CACHE_KEY, context, 300)  # cache 5 นาที
    return render(request, 'live/dashboard.html', context)


    
def _get_chat_info(subjects, now_local):
    from datetime import datetime as _dt
    now_t = now_local.time()

    def _parse(s):
        if not s:
            return None
        s = s.strip()
        for fmt in ('%H:%M', '%H.%M'):
            try:
                return _dt.strptime(s, fmt).time()
            except ValueError:
                continue
        return None

    # คาบที่กำลังสอนอยู่
    for subj in subjects:
        t_start = _parse(subj.time_start)
        t_end   = _parse(subj.time_end)
        if t_start and t_end and t_start <= now_t <= t_end:
            # ตรวจว่ามีคาบอื่นในวันนี้ที่เริ่มหลังคาบนี้จบหรือไม่
            has_next = any(
                _parse(s.time_start) and _parse(s.time_start) > t_end
                for s in subjects
            )
            return {
                'chat_since':       _dt.combine(now_local.date(), t_start).isoformat(),
                'class_end':        _dt.combine(now_local.date(), t_end).isoformat(),
                'class_active':     True,
                'next_class_start': '',
                'is_last_class':    not has_next,
                'is_day_done':      False,
            }

    # หาคาบถัดไปในวันนี้
    next_start = ''
    for subj in subjects:
        t_start = _parse(subj.time_start)
        if t_start and t_start > now_t:
            next_start = t_start.strftime('%H:%M')
            break

    now_iso = now_local.isoformat()
    return {
        'chat_since':       now_iso,
        'class_end':        now_iso,
        'class_active':     False,
        'next_class_start': next_start,
        'is_last_class':    False,
        'is_day_done':      not bool(next_start),  # ไม่มีคาบเหลือในวันนี้
    }


def _get_chat_since(subjects, now_local):
    return _get_chat_info(subjects, now_local)['chat_since']


@ensure_csrf_cookie
def showSubjectInRoom(request, room):
    now = datetime.now()   # local Bangkok time (TZ=Asia/Bangkok)
    today_day_en = now.strftime("%A")
    today_day_int = now.strftime("%w")  # string '0'-'6'
    if today_day_int == '0':
        today_day_int = '7'

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

    
    # งดบรรยายวันนี้: set ของ schedule id ที่มี ClassCancellation วันนี้
    import datetime as _dt
    from .models import ClassCancellation as _CC
    today_date = _dt.date.today()
    cancelled_ids = set(
        _CC.objects.filter(
            schedule__in=data_subject,
            cancel_date=today_date
        ).values_list('schedule_id', flat=True)
    )
    # ดึง reason ด้วย
    cancel_reasons = {
        c.schedule_id: c.reason
        for c in _CC.objects.filter(schedule__in=data_subject, cancel_date=today_date)
    }

    # สร้าง mapping ชื่อวันอังกฤษ
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday','Sunday']
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
        server = config.serverMdeia88  # 202.41.160.88 — ชื่อ attribute มี typo (Mdeia ไม่ใช่ Media)

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
        'room': data_classroom,
        'room_comment': data_classroom.room_comment,
        'sessions_total': countOnline,
        'valid_locations': valid_locations,
        'cancelled_ids':   cancelled_ids,
        'cancel_reasons':  cancel_reasons,
        'today_date':      today_date,
        **_get_chat_info(data_subject, now),
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

def _load_course_search_meta():
    """อ่าน course_search config จาก schedule.json"""
    try:
        with open(SCHEDULE_JSON_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f).get('course_search', {})
        return {
            'years':            cfg.get('years', ['2568']),
            'default_year':     cfg.get('default_year', '2568'),
            'default_semester': cfg.get('default_semester', '1'),
        }
    except Exception:
        return {'years': ['2568'], 'default_year': '2568', 'default_semester': '1'}


@staff_member_required
def course_search_proxy(request):
    """
    Proxy POST ไป ruconnext.ru.ac.th/ru-connext-api-v2/mr30/data
    รับ course_year, course_semester, q จาก request
    """
    import urllib.request as _req
    import urllib.error  as _err

    API_URL = 'https://ruconnext.ru.ac.th/ru-connext-api-v2/mr30/data'
    meta = _load_course_search_meta()

    params = request.POST if request.method == 'POST' else request.GET

    # ถ้าขอแค่ meta
    if params.get('meta_only'):
        return JsonResponse({'meta': meta})

    course_year     = params.get('course_year',     meta['default_year']).strip()
    course_semester = params.get('course_semester', meta['default_semester']).strip()
    q = params.get('q', '').strip().upper()

    payload = json.dumps({
        'course_year':     course_year,
        'course_semester': course_semester,
    }).encode('utf-8')

    req = _req.Request(
        API_URL,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with _req.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
        data = json.loads(raw)
    except _err.URLError as e:
        return JsonResponse({'error': f'เชื่อมต่อ API ไม่ได้: {e.reason}'}, status=502)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'รูปแบบข้อมูลไม่ถูกต้อง'}, status=502)

    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get('RECORD') or data.get('data') or data.get('courses') or data.get('result') or []
    else:
        rows = []

    if q:
        rows = [
            c for c in rows
            if q in str(c.get('COURSENO', '') or c.get('course_no', '')).upper()
            or q in str(c.get('cName', '') or c.get('course_name', '')).upper()
        ]

    result = []
    for c in rows:
        result.append({
            'course_no':   c.get('course_no',     ''),
            'course_name': c.get('show_ru30',     ''),
            'credit':      c.get('course_credit', ''),
            'section':     str(c.get('section',   '')),
            'time_period': c.get('time_period',   ''),
            'course_room': c.get('course_room',   ''),
            'examdate':    c.get('course_examdate',''),
            'day_name_s':  c.get('day_name_s',    ''),
            'instructor':  c.get('course_instructor', ''),
        })
    return JsonResponse({'courses': result, 'total': len(result), 'meta': meta})


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

    # LiveClassroom (managed=False) ไม่มี room_location
    # → lookup จาก Classrooms model แทน
    loc_map = {
        c.room_name.strip().lower(): str(c.room_location_id)
        for c in Classrooms.objects.only('room_name', 'room_location')
    }

    # ต้องให้ตรงกับ showSubjectInRoom ทุก location
    # config.serverMdeia88 — ชื่อตัวแปรมี typo ตั้งแต่ต้น (Mdeia ไม่ใช่ Media)
    SERVER_MAP = {
        '1': config.serverMedia68,   # หัวหมาก
        '2': config.serverMedia65,   # บางนา
        '3': config.serverMedia66,   # คณะนิติศาสตร์
        '5': config.serverMedia66,   # (ตรงกับ showSubjectInRoom: location in [3,5,7])
        '7': config.serverMedia66,   # (ตรงกับ showSubjectInRoom: location in [3,5,7])
        '8': config.serverMedia67,   # campus3 → 202.41.160.67 (ตรงกับ showSubjectInRoom)
        '4': config.serverMdeia88,   # ห้องทดสอบระบบ (serverMdeia88 = 202.41.160.88)
    }
    _default_server = config.serverMedia68  # fallback ปลอดภัย ไม่ใช้ attribute ที่ไม่มีอยู่

    # สร้างลิสต์ก่อน
    live_classrooms = [
        {
            'room_name': room.room_name,
            'room_stream': room.room_stream,
            'viewer_count': viewer_map.get(room.room_name.strip().lower(), 0),
            'stream_url': (
                SERVER_MAP.get(
                    loc_map.get(room.room_name.strip().lower(), ''),
                    _default_server
                )
                + room.room_name.strip().lower()
                + '/playlist.m3u8'
            ),
        }
        for room in rooms
    ]

    # เรียงตาม viewer_count จากมาก -> น้อย
    live_classrooms.sort(key=lambda x: x['viewer_count'], reverse=True)

    context = {
        'live_classrooms': live_classrooms
    }

    return render(request, 'live/monitor.html', context)

@staff_member_required
def monitor_sse(request):
    """
    Server-Sent Events: push ข้อมูลผู้ชมทันทีที่ตัวเลขเปลี่ยน
    - ส่งข้อมูลทันทีถ้า viewer_count เปลี่ยน
    - ส่ง keepalive comment ทุก 15 วิ เพื่อกัน proxy timeout
    - จบ connection เองใน 50 วิ (ต่ำกว่า harakiri=60) แล้ว EventSource reconnect อัตโนมัติ
    """
    def event_stream():
        last_snapshot = None
        start = time_module.time()
        MAX_DURATION = 50  # วินาที — ต่ำกว่า harakiri=60

        while time_module.time() - start < MAX_DURATION:
            rooms = LiveClassroom.objects.filter(room_status='1')
            data = [
                {'room_name': r.room_name, 'viewer_count': r.viewer_count or 0}
                for r in rooms
            ]
            data_str = json.dumps(data, ensure_ascii=False)

            if data_str != last_snapshot:
                last_snapshot = data_str
                yield f'data: {data_str}\n\n'
            else:
                # keepalive comment (ไม่ trigger onmessage)
                elapsed = int(time_module.time() - start)
                if elapsed % 15 == 0:
                    yield ': keepalive\n\n'

            time_module.sleep(1)

        # จบ gracefully — EventSource จะ reconnect อัตโนมัติภายใน 3 วิ
        yield ': reconnect\n\n'

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'   # บอก Nginx อย่า buffer response นี้
    return response


@require_GET
@staff_member_required
def live_viewer_data(request):
    rooms = LiveClassroom.objects.filter(room_status="1")

    # LiveClassroom ไม่มี field viewer_count — ต้องดึงจาก Count model แยก
    viewer_map = {
        c.room_name.strip().lower(): int(c.sessions_total) if str(c.sessions_total).isdigit() else 0
        for c in Count.objects.all()
    }

    # stream_url — ใช้ logic เดียวกับ live_monitor_view
    loc_map = {
        c.room_name.strip().lower(): str(c.room_location_id)
        for c in Classrooms.objects.only('room_name', 'room_location')
    }
    SERVER_MAP = {
        '1': config.serverMedia68,
        '2': config.serverMedia65,
        '3': config.serverMedia66,
        '5': config.serverMedia66,
        '7': config.serverMedia66,
        '8': config.serverMedia67,
        '4': config.serverMdeia88,
    }
    _default = config.serverMedia68

    data = [
        {
            'room_name': room.room_name,
            'viewer_count': viewer_map.get(room.room_name.strip().lower(), 0),
            'stream_url': (
                SERVER_MAP.get(loc_map.get(room.room_name.strip().lower(), ''), _default)
                + room.room_name.strip().lower()
                + '/playlist.m3u8'
            ),
        }
        for room in rooms
    ]
    return JsonResponse({'data': data})


# ═══════════════════════════════════════════════════════════
#  CHAT — Polling-based real-time chat (ไม่ต้องการ WebSocket)
# ═══════════════════════════════════════════════════════════

@require_GET
def chat_fetch(request, room_name):
    """ดึงข้อความใหม่หลังจาก after_id — ถูกเรียกทุก 3 วินาที
    รับ ?after=<id>&since=<ISO datetime> เพื่อกรองเฉพาะข้อความในคาบปัจจุบัน
    """
    after_id  = int(request.GET.get('after', 0))
    since_str = request.GET.get('since', '')

    qs = ChatMessage.objects.filter(room_id=room_name, id__gt=after_id).exclude(message='__ping__')

    if since_str:
        try:
            from datetime import datetime as _dt
            since_dt = _dt.fromisoformat(since_str.split('+')[0])  # ตัด timezone offset ออก
            qs = qs.filter(created_at__gte=since_dt)
        except (ValueError, TypeError):
            pass

    msgs = qs.values('id', 'sender', 'is_teacher', 'message', 'created_at').order_by('id')[:50]
    result = [
        {
            'id':         m['id'],
            'sender':     m['sender'],
            'is_teacher': m['is_teacher'],
            'message':    m['message'],
            'time':       _safe_localtime(m['created_at']).strftime('%H:%M'),
        }
        for m in msgs
    ]
    try:
        room = Classrooms.objects.get(room_name=room_name)
        chat_open = room.chat_open
    except Classrooms.DoesNotExist:
        chat_open = False
    resp = JsonResponse({'messages': result, 'chat_open': chat_open})
    resp['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp['Pragma'] = 'no-cache'
    return resp


@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def chat_send(request, room_name):
    """รับข้อความจาก client — จำกัด 10 ข้อความ/นาที/IP"""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    try:
        data        = json.loads(request.body)
        sender      = data.get('sender', '').strip()[:80]
        message     = data.get('message', '').strip()[:500]
        teacher_pin = data.get('teacher_pin', '').strip()
        std_code    = data.get('std_code', '').strip()[:20]

        if not sender:
            return JsonResponse({'error': 'กรุณาระบุชื่อ'}, status=400)
        if not message:
            return JsonResponse({'error': 'ข้อความว่างเปล่า'}, status=400)

        # ตรวจสอบ ban (เฉพาะนักศึกษาที่ login ด้วย std_code)
        if std_code and BannedStudent.objects.filter(std_code=std_code).exists():
            return JsonResponse({'banned': True}, status=403)

        room = get_object_or_404(Classrooms, room_name=room_name)

        # ตรวจสอบรหัสอาจารย์ — ต้องตรงและ chat_pin ต้องไม่ว่างเปล่า
        is_teacher = bool(
            room.chat_pin and
            teacher_pin and
            room.chat_pin == teacher_pin
        )

        # บล็อกนักศึกษาถ้าอาจารย์ยังไม่เปิดแชท
        if not is_teacher and not room.chat_open:
            return JsonResponse({'error': 'chat_closed', 'message': 'อาจารย์ยังไม่เปิดให้แชท'}, status=403)

        # หาวิชาที่กำลังสอนในขณะนี้
        now_local = datetime.now()
        now_day  = now_local.strftime('%w')   # 0=อาทิตย์ … 6=เสาร์
        if now_day == '0': now_day = '7'      # DB ใช้ '7' สำหรับอาทิตย์
        now_time = now_local.strftime('%H:%M')
        active_course = ''
        try:
            sched = ClassScheduleCenter.objects.filter(
                room_name=room,
                course_day=now_day,
                time_start__lte=now_time,
                time_end__gte=now_time,
            ).first()
            if sched:
                active_course = sched.course_no
        except Exception:
            pass

        # ตรวจคำหยาบ — ถ้าพบและมี std_code ให้ ban ทันที (ยกเว้นอาจารย์)
        found_profanity = has_profanity(message)
        if found_profanity and std_code and not is_teacher:
            BannedStudent.objects.get_or_create(
                std_code=std_code,
                defaults={'ban_reason': f'ใช้ถ้อยคำไม่เหมาะสม: "{message[:100]}"'},
            )
            return JsonResponse({'banned': True}, status=403)

        censored = censor_message(message)
        msg = ChatMessage.objects.create(
            room=room,
            sender=sender,
            is_teacher=is_teacher,
            message=censored,
            message_raw=message if found_profanity else '',
            sender_ip=get_client_ip(request),
            active_course=active_course,
        )
        return JsonResponse({
            'id':         msg.id,
            'sender':     msg.sender,
            'is_teacher': msg.is_teacher,
            'message':    msg.message,
            'time':       _safe_localtime(msg.created_at).strftime('%H:%M'),
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def chat_toggle_open(request, room_name):
    """อาจารย์เปิด/ปิดให้นักศึกษาแชท — ต้องส่ง teacher_pin มาด้วย"""
    try:
        data        = json.loads(request.body)
        teacher_pin = data.get('teacher_pin', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'invalid json'}, status=400)

    room = get_object_or_404(Classrooms, room_name=room_name)

    if not room.chat_pin or room.chat_pin != teacher_pin:
        return JsonResponse({'error': 'unauthorized'}, status=403)

    force_close = data.get('force_close', False)
    if force_close:
        room.chat_open = False
    else:
        room.chat_open = not room.chat_open
    room.save(update_fields=['chat_open'])
    return JsonResponse({'chat_open': room.chat_open})


@require_POST
def chat_student_login(request):
    """
    Login นักศึกษา 2 ขั้น:
      1. POST /api/token/  → ได้ access JWT
      2. GET  /vmstudentall/{std_code}/ → ตรวจ std_status_current + ดึงชื่อ
    คืน {ok, std_code, std_name, std_status}
    """
    import json as _json
    import urllib.request as _urllib_req
    import urllib.error as _urllib_err
    import base64 as _b64

    # สถานะที่อนุญาตให้แชทได้
    ALLOWED_STATUSES = {'A', 'B', 'C'}
    STATUS_LABELS = {
        'A': 'ปัจจุบัน',
        'B': 'ขาดการลงทะเบียน 1 ภาค',
        'C': 'ขาดการลงทะเบียน 2 ภาค',
    }

    try:
        data     = _json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        if not username or not password:
            return JsonResponse({'ok': False, 'detail': 'กรุณากรอก username และ password'}, status=400)

        # ── ขั้น 1: ขอ token ──────────────────────────────────────────
        payload = _json.dumps({'username': username, 'password': password}).encode()
        tok_req = _urllib_req.Request(
            'https://eshub.ru.ac.th/api/token/',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with _urllib_req.urlopen(tok_req, timeout=10) as resp:
            tok = _json.loads(resp.read())
        access = tok.get('access', '')

        # ถอด JWT payload เพื่อดึง std_code
        std_code = username
        parts = access.split('.')
        if len(parts) >= 2:
            b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
            try:
                jwt_payload = _json.loads(_b64.b64decode(b64))
                std_code = str(jwt_payload.get('std_code', username))
            except Exception:
                pass

        # ── ขั้น 2: ดึงข้อมูลนักศึกษา ────────────────────────────────
        std_req = _urllib_req.Request(
            f'https://eshub.ru.ac.th/vmstudentall/{std_code}/',
            headers={'Authorization': f'Bearer {access}'},
            method='GET',
        )
        with _urllib_req.urlopen(std_req, timeout=10) as resp:
            std_data = _json.loads(resp.read())

        # ── ตรวจสอบสถานะ ──────────────────────────────────────────────
        std_status = str(std_data.get('std_status_current', '')).upper()
        if std_status not in ALLOWED_STATUSES:
            label = STATUS_LABELS.get(std_status, f'สถานะ {std_status}')
            return JsonResponse({
                'ok': False,
                'detail': f'ไม่สามารถใช้แชทได้ — สถานะนักศึกษา: {label}',
            }, status=403)

        # ── ดึงชื่อ (ลอง field ไทยก่อน แล้ว fallback อังกฤษ) ────────
        first = (std_data.get('std_firstname_th') or
                 std_data.get('std_firstname')     or '').strip()
        last  = (std_data.get('std_lastname_th')  or
                 std_data.get('std_lastname')      or '').strip()
        std_name = (first + ' ' + last).strip() if (first or last) else std_code

        return JsonResponse({
            'ok':        True,
            'std_code':  std_code,
            'std_name':  std_name,
            'std_status': std_status,
        })

    except _urllib_err.HTTPError as e:
        if e.code == 401:
            return JsonResponse({'ok': False, 'detail': 'รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่'}, status=401)
        return JsonResponse({'ok': False, 'detail': f'eshub ตอบกลับ error {e.code}'}, status=502)
    except Exception:
        return JsonResponse({'ok': False, 'detail': 'เชื่อมต่อ eshub ไม่ได้ กรุณาลองใหม่'}, status=500)


def live_event(request):
    STREAM_URL  = 'http://202.41.160.65:1935/live/rucom/playlist.m3u8'
    VIEWER_ROOM = 'rucom'
    return render(request, 'live/live_event.html', {
        'stream_url':  STREAM_URL,
        'viewer_room': VIEWER_ROOM,
    })
