import datetime
from django.contrib import admin
from django.utils.html import mark_safe
from django.db.models import Case, When, IntegerField

from .models import (
    Classrooms, ClassScheduleCenter, Locations,
    LogSubjectInRoom, Count, LiveClassroom, ChatMessage, BannedStudent,
)
from . import config


# ─── helpers ──────────────────────────────────────────────────────────────────

def _get_server(location_id):
    mapping = {
        1: config.serverMedia68,
        2: config.serverMedia65,
        3: config.serverMedia66,
        4: config.serverMedia68,
        5: config.serverMedia66,
        6: config.serverMedia66,
        7: config.serverMedia66,
        8: config.serverMedia67,
    }
    return mapping.get(location_id, config.serverMedia66)


def _viewer_map():
    """room_name.lower() → int viewer count"""
    return {
        c.room_name.strip().lower(): (
            int(c.sessions_total) if str(c.sessions_total).isdigit() else 0
        )
        for c in Count.objects.all()
    }


def _live_set():
    """set of room_name.lower() that are currently live (room_status='1')"""
    return {
        r.room_name.strip().lower()
        for r in LiveClassroom.objects.filter(room_status='1')
    }


# ─── ClassScheduleCenter inline ───────────────────────────────────────────────

class ClassScheduleCenterInline(admin.TabularInline):
    model = ClassScheduleCenter
    extra = 0
    fields = ('course_no', 'course_name_thai', 'instructor',
              'course_day', 'time_start', 'time_end')
    exclude = ['added_by', 'created_at', 'updated_at']
    ordering = ('time_start',)
    show_change_link = True
    verbose_name = "วิชาในห้องนี้"
    verbose_name_plural = "ตารางวิชาในห้อง"


# ─── ClassroomsAdmin ──────────────────────────────────────────────────────────

class ClassroomsAdmin(admin.ModelAdmin):

    # ── list view ─────────────────────────────────────────
    list_display = (
        'mini_player',        # embedded video (muted, autoplay)
        'room_info',          # name + location in one cell
        'live_badge',         # LIVE / offline badge
        'viewer_count_display',
        'room_status_badge',
        'stream_preview_link',
    )
    list_display_links = ('room_info',)
    list_filter        = ('room_location', 'room_status')
    search_fields      = ('room_name', 'room_stream')
    list_per_page      = 20
    # default ordering handled by get_queryset (live-first, viewer-count-desc)

    # ── change/add view ───────────────────────────────────
    readonly_fields = ('live_status_detail', 'viewer_count_detail', 'live_player_embed')
    fieldsets = (
        ('ข้อมูลห้องเรียน', {
            'fields': ('room_name', 'room_location', 'room_stream',
                       'room_order', 'room_status', 'room_comment'),
        }),
        ('💬 แชทในห้องเรียน', {
            'fields': ('chat_pin',),
            'description': (
                'ตั้งรหัสลับให้อาจารย์พิมพ์เพื่อได้รับ badge "อาจารย์" ในหน้าแชท '
                '(ว่างเปล่า = ปิดฟีเจอร์แชท)'
            ),
        }),
        ('📡 สถานะ Live ปัจจุบัน', {
            'fields': ('live_status_detail', 'viewer_count_detail'),
            'classes': ('collapse',),
            'description': 'ข้อมูลแสดงผลแบบ real-time จากระบบ',
        }),
        ('🎬 ดูสดในหน้า Admin', {
            'fields': ('live_player_embed',),
            'classes': ('collapse',),
        }),
    )
    inlines = [ClassScheduleCenterInline]

    class Media:
        css = {'all': ('live/admin_classrooms.css',)}
        js  = ('live/admin_classrooms.js',)

    # ── smart sort: live-first → viewer-count desc ─────────

    def get_queryset(self, request):
        qs = super(ClassroomsAdmin, self).get_queryset(request)

        # Only apply our custom sort when no column-header sort is active
        if request.GET.get('o'):
            return qs

        live_s = _live_set()
        vmap   = _viewer_map()

        # Sort in Python: (0=live,1=offline) then (-viewers)
        rooms = sorted(
            list(qs),
            key=lambda r: (
                0 if r.room_name.strip().lower() in live_s else 1,
                -vmap.get(r.room_name.strip().lower(), 0),
            )
        )

        if not rooms:
            return qs

        # Preserve the Python-sorted order back into a queryset
        pks = [r.pk for r in rooms]
        preserved = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(pks)],
            output_field=IntegerField()
        )
        return qs.annotate(_sort_order=preserved).order_by('_sort_order')

    # ── list columns ──────────────────────────────────────

    def mini_player(self, obj):
        """Embedded HLS player — muted autoplay, 200×113 px"""
        is_live = obj.room_name.strip().lower() in _live_set()

        if not is_live:
            return mark_safe(
                '<div class="admin-mini-player">'
                '<div class="player-offline">&#9679; ออฟไลน์</div>'
                '</div>'
            )

        server  = _get_server(obj.room_location.id if obj.room_location else 0)
        src     = '{}{}/playlist.m3u8'.format(server, obj.room_name.lower())

        return mark_safe(
            '<div class="admin-mini-player">'
            '<span class="player-live-dot">LIVE</span>'
            '<video data-hlssrc="{src}" muted playsinline preload="none"'
            ' style="width:200px;height:113px;background:#000;border-radius:0 0 6px 6px;">'
            '</video>'
            '</div>'.format(src=src)
        )
    mini_player.short_description = '📺 Preview'
    mini_player.allow_tags = True

    def room_info(self, obj):
        location = obj.room_location.location_name if obj.room_location else '—'
        return mark_safe(
            '<strong style="font-size:0.95rem;">{name}</strong>'
            '<br><span style="color:#64748b;font-size:0.78rem;">{loc}</span>'.format(
                name=obj.room_name,
                loc=location,
            )
        )
    room_info.short_description = 'ห้องเรียน'
    room_info.admin_order_field = 'room_name'

    def live_badge(self, obj):
        is_live = obj.room_name.strip().lower() in _live_set()
        if is_live:
            return mark_safe(
                '<span class="admin-badge badge-live">&#9679; LIVE</span>'
            )
        return mark_safe(
            '<span class="admin-badge badge-offline">&#9675; ออฟไลน์</span>'
        )
    live_badge.short_description = 'Live'

    def viewer_count_display(self, obj):
        count = _viewer_map().get(obj.room_name.strip().lower(), 0)
        if count > 0:
            return mark_safe(
                '<span class="admin-badge badge-viewers">{} คน</span>'.format(count)
            )
        return mark_safe('<span style="color:#94a3b8">—</span>')
    viewer_count_display.short_description = '👥 ผู้ชม'

    def room_status_badge(self, obj):
        if obj.room_status == '1':
            return mark_safe('<span class="admin-badge badge-open">เปิด</span>')
        return mark_safe('<span class="admin-badge badge-closed">ปิด</span>')
    room_status_badge.short_description = 'สถานะ'

    def stream_preview_link(self, obj):
        url = '/showSubjectInRoom/{}/'.format(obj.room_name)
        return mark_safe(
            '<a href="{}" target="_blank" class="admin-stream-link">'
            '&#9654; ดูสด</a>'.format(url)
        )
    stream_preview_link.short_description = 'ลิงก์'
    stream_preview_link.allow_tags = True

    # ── detail readonly fields ─────────────────────────────

    def live_status_detail(self, obj):
        is_live = obj.room_name.strip().lower() in _live_set()
        if is_live:
            return mark_safe(
                '<span class="admin-badge badge-live" style="font-size:1rem;padding:6px 16px;">'
                '&#9679; กำลังถ่ายทอดสดอยู่</span>'
            )
        return mark_safe(
            '<span class="admin-badge badge-offline" style="font-size:1rem;padding:6px 16px;">'
            '&#9675; ไม่ได้ถ่ายทอดสดในขณะนี้</span>'
        )
    live_status_detail.short_description = 'สถานะ Live ปัจจุบัน'

    def viewer_count_detail(self, obj):
        count = _viewer_map().get(obj.room_name.strip().lower(), 0)
        return mark_safe(
            '<strong style="font-size:1.4rem;color:#3b82f6">{}</strong>'
            '<span style="color:#64748b;margin-left:6px">คน</span>'.format(count)
        )
    viewer_count_detail.short_description = 'จำนวนผู้ชมขณะนี้'

    def live_player_embed(self, obj):
        if not obj.room_location:
            return '—'
        server  = _get_server(obj.room_location.id)
        src     = '{}{}/playlist.m3u8'.format(server, obj.room_name.lower())
        room_id = obj.room_name.replace(' ', '_').replace('/', '_')
        return mark_safe(
            '<div style="max-width:640px;margin:8px 0;">'
            '<video id="adminVid_{rid}" data-hlssrc="{src}"'
            ' style="width:100%;max-width:640px;height:360px;background:#000;border-radius:8px;"'
            ' controls muted autoplay playsinline></video>'
            '<p style="font-size:0.72rem;color:#64748b;margin-top:4px;">📡 {src}</p>'
            '</div>'.format(rid=room_id, src=src)
        )
    live_player_embed.short_description = 'ดูการถ่ายทอดสด (HLS)'

    # ── save hook ─────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        now = datetime.datetime.now()
        if not obj.pk:
            obj.created_at = str(now)
        obj.updated_at = str(now)
        obj.added_by   = request.user.username
        super(ClassroomsAdmin, self).save_model(request, obj, form, change)


admin.site.register(Classrooms, ClassroomsAdmin)


# ─── LiveClassroom — read-only live monitor ───────────────────────────────────

class LiveClassroomAdmin(admin.ModelAdmin):
    list_display  = ('room_name', 'live_status_badge', 'viewer_count_col',
                     'room_stream', 'updated_at')
    list_filter   = ('room_status',)
    search_fields = ('room_name',)
    list_per_page = 30
    ordering      = ('room_order', 'room_name')

    class Media:
        css = {'all': ('live/admin_classrooms.css',)}

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def live_status_badge(self, obj):
        if obj.room_status == '1':
            return mark_safe(
                '<span class="admin-badge badge-live">&#9679; LIVE</span>'
            )
        return mark_safe(
            '<span class="admin-badge badge-offline">&#9675; ออฟไลน์</span>'
        )
    live_status_badge.short_description = 'สถานะ'

    def viewer_count_col(self, obj):
        count = _viewer_map().get(obj.room_name.strip().lower(), 0)
        if count > 0:
            return mark_safe(
                '<span class="admin-badge badge-viewers">{} คน</span>'.format(count)
            )
        return mark_safe('<span style="color:#94a3b8">—</span>')
    viewer_count_col.short_description = '👥 ผู้ชม'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        vmap          = _viewer_map()
        live_rooms    = LiveClassroom.objects.filter(room_status='1')
        total_viewers = sum(
            vmap.get(r.room_name.strip().lower(), 0) for r in live_rooms
        )
        extra_context['live_count']    = live_rooms.count()
        extra_context['total_viewers'] = total_viewers
        return super(LiveClassroomAdmin, self).changelist_view(
            request, extra_context=extra_context
        )

    change_list_template = 'live/admin_live_monitor_list.html'


admin.site.register(LiveClassroom, LiveClassroomAdmin)


# ─── Count — read-only viewer stats ──────────────────────────────────────────

class CountAdmin(admin.ModelAdmin):
    list_display  = ('room_name', 'sessions_total', 'sessions_cupertino', 'updated')
    search_fields = ('room_name',)
    list_per_page = 30
    ordering      = ('-sessions_total',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Count, CountAdmin)


# ─── ClassScheduleCenter ──────────────────────────────────────────────────────

class ClassScheduleCenterAdmin(admin.ModelAdmin):
    list_display  = ('course_no', 'course_name_thai', 'instructor',
                     'course_day', 'time_start', 'time_end', 'room_name')
    list_per_page = 25
    list_editable = ('course_day', 'time_start', 'time_end')
    search_fields = ('course_no', 'room_name__room_name', 'course_name_thai', 'instructor')
    list_filter   = ('course_day', 'room_name')
    exclude       = ('added_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        now = datetime.datetime.now()
        if not obj.pk:
            obj.created_at = str(now)
        obj.updated_at = str(now)
        obj.added_by   = request.user.username
        super(ClassScheduleCenterAdmin, self).save_model(request, obj, form, change)


admin.site.register(ClassScheduleCenter, ClassScheduleCenterAdmin)


# ─── Locations ────────────────────────────────────────────────────────────────

class LocationsAdmin(admin.ModelAdmin):
    ordering = ('id',)


admin.site.register(Locations, LocationsAdmin)


# ─── LogSubjectInRoom ─────────────────────────────────────────────────────────

class CreatedAtFilter(admin.SimpleListFilter):
    """กรองตาม created_at (CharField รูปแบบ 'YYYY-MM-DD ...')"""
    title        = 'ช่วงเวลา'
    parameter_name = 'period'

    def lookups(self, request, model_admin):
        return (
            ('today',   'วันนี้'),
            ('week',    '7 วันล่าสุด'),
            ('month',   'เดือนนี้'),
            ('year',    'ปีนี้'),
        )

    def queryset(self, request, queryset):
        import datetime as dt
        now = dt.datetime.now()
        if self.value() == 'today':
            prefix = now.strftime('%Y-%m-%d')
            return queryset.filter(created_at__startswith=prefix)
        if self.value() == 'week':
            days = [(now - dt.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
            from django.db.models import Q
            q = Q()
            for d in days:
                q |= Q(created_at__startswith=d)
            return queryset.filter(q)
        if self.value() == 'month':
            prefix = now.strftime('%Y-%m')
            return queryset.filter(created_at__startswith=prefix)
        if self.value() == 'year':
            prefix = now.strftime('%Y')
            return queryset.filter(created_at__startswith=prefix)
        return queryset


class LogSubjectInRoomAdmin(admin.ModelAdmin):
    list_display         = ('created_at_fmt', 'course_no', 'room_location', 'user_ip')
    list_per_page        = 50
    ordering             = ('-id',)          # PK มี index -> เร็ว
    list_filter          = (CreatedAtFilter, 'room_location')
    search_fields        = ('course_no', 'user_ip')
    list_select_related  = ('room_location',)
    show_full_result_count = False           # ปิด COUNT(*) ทั้งตาราง

    class Media:
        css = {'all': ('live/admin_classrooms.css',)}

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    # -- เพิ่ม URL: /admin/live/logsubjectinroom/analytics-json/ ---------------
    def get_urls(self):
        from django.urls import path
        urls = super(LogSubjectInRoomAdmin, self).get_urls()
        extra = [
            path(
                'analytics-json/',
                self.admin_site.admin_view(self._analytics_json),
                name='live_log_analytics_json',
            ),
        ]
        return extra + urls

    # -- JSON endpoint: ยิง query ที่นี่ ไม่ให้ block changelist ---------------
    def _analytics_json(self, request):
        import datetime as dt
        from django.http import JsonResponse
        from django.core.cache import cache
        from django.db.models import Count as DjCount, Case, When, IntegerField
        from django.db.models.functions import Substr

        now   = dt.datetime.now()
        today = now.strftime('%Y-%m-%d')
        month = now.strftime('%Y-%m')

        CACHE_KEY = 'log_analytics_{}'.format(today)
        CACHE_TTL = 5 * 60

        if request.GET.get('refresh'):
            cache.delete(CACHE_KEY)

        data = cache.get(CACHE_KEY)

        if data is None:
            base = LogSubjectInRoom.objects.all()

            # Q1: วันนี้ + เดือนนี้ ใน 1 query
            stats = base.filter(
                created_at__startswith=month
            ).aggregate(
                month_count=DjCount('id'),
                today_count=DjCount(Case(
                    When(created_at__startswith=today, then=1),
                    output_field=IntegerField(),
                )),
            )

            # Q2: unique IPs วันนี้
            unique_today = (
                base.filter(created_at__startswith=today)
                .values('user_ip').distinct().count()
            )

            # Q3: trend 7 วัน ใน 1 query (Substr + GROUP BY)
            week_start = (now - dt.timedelta(days=6)).strftime('%Y-%m-%d')
            trend_dict = {
                r['day']: r['cnt']
                for r in (
                    base.filter(created_at__gte=week_start)
                    .annotate(day=Substr('created_at', 1, 10))
                    .values('day')
                    .annotate(cnt=DjCount('id'))
                )
            }
            daily_trend = []
            max_v = 1
            for i in range(6, -1, -1):
                d   = (now - dt.timedelta(days=i)).strftime('%Y-%m-%d')
                cnt = trend_dict.get(d, 0)
                daily_trend.append({'date': d[5:], 'count': cnt})
                if cnt > max_v:
                    max_v = cnt
            for item in daily_trend:
                item['pct'] = int(item['count'] * 100 / max_v)

            # Q4: top 10 วิชา เดือนนี้
            top_courses = list(
                base.filter(created_at__startswith=month)
                .values('course_no')
                .annotate(visits=DjCount('id'))
                .order_by('-visits')[:10]
            )
            if top_courses:
                mc = top_courses[0]['visits'] or 1
                for item in top_courses:
                    item['pct'] = int(item['visits'] * 100 / mc)

            # Q5: top 5 สถานที่ เดือนนี้
            top_locations = list(
                base.filter(created_at__startswith=month)
                .values('room_location__location_name')
                .annotate(visits=DjCount('id'))
                .order_by('-visits')[:5]
            )

            data = {
                'today_count'  : stats['today_count']  or 0,
                'month_count'  : stats['month_count']  or 0,
                'unique_today' : unique_today,
                'top_courses'  : top_courses,
                'top_locations': top_locations,
                'daily_trend'  : daily_trend,
                'month_label'  : now.strftime('%B %Y'),
                'today_label'  : today,
                'cached'       : False,
            }
            cache.set(CACHE_KEY, data, CACHE_TTL)
        else:
            data = dict(data)
            data['cached'] = True

        return JsonResponse(data)

    # -- changelist: ไม่ยิง query analytics เลย -- โหลดเร็วทันที -------------
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['analytics_json_url'] = 'analytics-json/'
        return super(LogSubjectInRoomAdmin, self).changelist_view(
            request, extra_context=extra_context
        )

    def created_at_fmt(self, obj):
        val = str(obj.created_at or '').strip()
        return val[:19] if len(val) >= 19 else val
    created_at_fmt.short_description = 'เวลา'
    created_at_fmt.admin_order_field = 'id'

    change_list_template = 'live/admin_log_analytics.html'


admin.site.register(LogSubjectInRoom, LogSubjectInRoomAdmin)


# ─── ChatMessage ──────────────────────────────────────────────────────────────

class ChatMessageAdmin(admin.ModelAdmin):
    list_display    = ('created_at_fmt', 'room', 'course_badge', 'sender_badge', 'message_bubble', 'profanity_badge', 'sender_ip')
    list_filter     = ('is_teacher', 'room')
    search_fields   = ('sender', 'message', 'room__room_name', 'sender_ip')
    ordering        = ('-created_at',)
    list_per_page   = 50
    readonly_fields = ('room', 'sender', 'is_teacher', 'message_full', 'message_raw_display', 'created_at', 'sender_ip')
    date_hierarchy  = 'created_at'
    list_select_related = ('room',)

    class Media:
        css = {'all': ('live/admin_classrooms.css',)}

    def has_add_permission(self, request):
        return False

    def course_badge(self, obj):
        if obj.active_course:
            return mark_safe(
                '<span style="background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe;'
                'border-radius:6px;padding:2px 8px;font-size:.78rem;font-weight:600;">'
                '{}</span>'.format(obj.active_course)
            )
        return mark_safe('<span style="color:#9ca3af;font-size:.78rem;">—</span>')
    course_badge.short_description = 'วิชา'
    course_badge.admin_order_field = 'active_course'

    def created_at_fmt(self, obj):
        from django.conf import settings
        from django.utils.timezone import localtime
        dt = obj.created_at
        if getattr(settings, 'USE_TZ', True) and dt.tzinfo:
            dt = localtime(dt)
        return dt.strftime('%d/%m %H:%M')
    created_at_fmt.short_description = 'เวลา'
    created_at_fmt.admin_order_field = 'created_at'

    def sender_badge(self, obj):
        from django.utils.html import escape
        name = escape(obj.sender)
        if obj.is_teacher:
            return mark_safe(
                '<span style="display:inline-flex;align-items:center;gap:4px;'
                'background:#fef3c7;color:#92400e;border:1px solid #fbbf24;'
                'border-radius:20px;padding:2px 10px;font-size:.8rem;font-weight:600;">'
                '&#9733; {}</span>'.format(name)
            )
        return mark_safe(
            '<span style="display:inline-flex;align-items:center;gap:4px;'
            'background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe;'
            'border-radius:20px;padding:2px 10px;font-size:.8rem;">'
            '&#128100; {}</span>'.format(name)
        )
    sender_badge.short_description = 'ผู้ส่ง'

    def message_bubble(self, obj):
        from django.utils.html import escape
        text = escape(obj.message[:150])
        if obj.is_teacher:
            bg, border, color = '#fffbeb', '#fde68a', '#78350f'
        else:
            bg, border, color = '#f8faff', '#dbeafe', '#1e3a5f'
        return mark_safe(
            '<span style="display:inline-block;background:{};border:1px solid {};'
            'color:{};border-radius:10px;padding:4px 12px;font-size:.85rem;'
            'max-width:420px;word-break:break-word;">{}</span>'.format(
                bg, border, color, text)
        )
    message_bubble.short_description = 'ข้อความ'

    def message_full(self, obj):
        from django.utils.html import escape
        return mark_safe(
            '<div style="background:#f8faff;border:1px solid #dbeafe;border-radius:10px;'
            'padding:12px 16px;font-size:.95rem;white-space:pre-wrap;">{}</div>'.format(
                escape(obj.message))
        )
    message_full.short_description = 'ข้อความ (แสดงผล)'

    def message_raw_display(self, obj):
        from django.utils.html import escape
        if not obj.message_raw:
            return mark_safe('<span style="color:#9ca3af;">—</span>')
        return mark_safe(
            '<div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:10px;'
            'padding:12px 16px;font-size:.95rem;white-space:pre-wrap;color:#be123c;">{}</div>'.format(
                escape(obj.message_raw))
        )
    message_raw_display.short_description = 'ข้อความต้นฉบับ (มีคำหยาบ)'

    def profanity_badge(self, obj):
        if obj.message_raw:
            return mark_safe(
                '<span style="background:#fff1f2;color:#be123c;border:1px solid #fecdd3;'
                'border-radius:6px;padding:2px 8px;font-size:.75rem;font-weight:600;">⚠ มีคำหยาบ</span>'
            )
        return ''
    profanity_badge.short_description = ''

    def get_fields(self, request, obj=None):
        return ('room', 'sender', 'is_teacher', 'message_full', 'message_raw_display', 'created_at', 'sender_ip')

    actions = ['clear_room_chat']

    def clear_room_chat(self, request, queryset):
        rooms = set(queryset.values_list('room_id', flat=True))
        deleted, _ = ChatMessage.objects.filter(room_id__in=rooms).delete()
        self.message_user(request, 'ลบข้อความ {} รายการจาก {} ห้อง'.format(deleted, len(rooms)))
    clear_room_chat.short_description = 'ลบข้อความแชทในห้องที่เลือกทั้งหมด'


admin.site.register(ChatMessage, ChatMessageAdmin)


# ─── BannedStudent ────────────────────────────────────────────────────────────

class BannedStudentAdmin(admin.ModelAdmin):
    list_display    = ('std_code', 'banned_at_fmt', 'ban_reason_short')
    search_fields   = ('std_code', 'ban_reason')
    ordering        = ('-banned_at',)
    readonly_fields = ('banned_at',)
    list_per_page   = 50
    actions         = ['unban_selected']

    def banned_at_fmt(self, obj):
        return obj.banned_at.strftime('%d/%m/%Y %H:%M')
    banned_at_fmt.short_description = 'เวลาที่ถูก ban'
    banned_at_fmt.admin_order_field = 'banned_at'

    def ban_reason_short(self, obj):
        return obj.ban_reason[:80] + ('…' if len(obj.ban_reason) > 80 else '')
    ban_reason_short.short_description = 'เหตุผล'

    def unban_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, 'ปลดแบน {} รหัสนักศึกษา เรียบร้อยแล้ว'.format(count))
    unban_selected.short_description = 'ปลดแบน (unban) รหัสที่เลือก'


admin.site.register(BannedStudent, BannedStudentAdmin)
