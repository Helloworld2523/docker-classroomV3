import json
import os
from django import template
from datetime import datetime

register = template.Library()

# path ของ schedule.json (relative to this file → live/data/schedule.json)
_SCHEDULE_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'schedule.json')

def _read_schedule_json():
    try:
        with open(_SCHEDULE_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

@register.simple_tag
def get_hero_schedule():
    """
    คืนค่า dict ของ hero schedule จาก schedule.json
    ใช้ใน template แบบ:  {% get_hero_schedule as hero %}
    จากนั้น  {{ hero.central.term }}  {{ hero.regional.date_range }}  ฯลฯ
    """
    data = _read_schedule_json()
    default = {
        'central':  {'term': '', 'date_range': '', 'link': '', 'link_text': ''},
        'regional': {'term': '', 'date_range': '', 'link': '', 'link_text': ''},
    }
    hero = data.get('hero', {})
    default['central'].update(hero.get('central', {}))
    default['regional'].update(hero.get('regional', {}))
    return default

@register.simple_tag(takes_context=True)
def get_room_schedule(context, room):
    today_weekday = datetime.today().weekday() + 1
    # ดึงข้อมูลที่กรองแล้ว
    schedules = room.classschedulecenter_set.filter(course_day=today_weekday).order_by('time_start')

    # เพิ่ม schedules ลงใน context เพื่อให้ template เข้าถึงได้
    context['today_schedules'] = schedules
    context['is_today_schedule_empty'] = not schedules.exists()
    return '' # simple_tag ต้อง return string แต่เราใส่ข้อมูลใน context แล้ว