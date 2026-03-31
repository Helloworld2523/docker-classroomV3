from django import template
from datetime import datetime

register = template.Library()

@register.simple_tag(takes_context=True)
def get_room_schedule(context, room):
    today_weekday = datetime.today().weekday() + 1
    # ดึงข้อมูลที่กรองแล้ว
    schedules = room.classschedulecenter_set.filter(course_day=today_weekday).order_by('time_start')
    
    # เพิ่ม schedules ลงใน context เพื่อให้ template เข้าถึงได้
    context['today_schedules'] = schedules
    context['is_today_schedule_empty'] = not schedules.exists()
    return '' # simple_tag ต้อง return string แต่เราใส่ข้อมูลใน context แล้ว