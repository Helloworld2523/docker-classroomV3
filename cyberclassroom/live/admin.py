import datetime
from django.contrib import admin
from django.utils.html import mark_safe
from django.db.models import Case, When, IntegerField

from .models import (
    Classrooms, ClassScheduleCenter, Locations,
    LogSubjectInRoom, Count, LiveClassroom,
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

class LogSubjectInRoomAdmin(admin.ModelAdmin):
    list_display  = ('course_no', 'room_location', 'user_ip', 'created_at')
    list_per_page = 50
    list_filter   = ('room_location',)
    search_fields = ('course_no', 'user_ip')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(LogSubjectInRoom, LogSubjectInRoomAdmin)
