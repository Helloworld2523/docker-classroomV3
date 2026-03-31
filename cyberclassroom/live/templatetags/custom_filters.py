from django import template
from datetime import datetime, time # Import time ด้วย

register = template.Library()

@register.filter
def is_current_class_time(schedule):
    """
    ตรวจสอบว่าเวลาปัจจุบันอยู่ในช่วงเวลาเริ่มต้นและสิ้นสุดของตารางเรียนหรือไม่
    รองรับรูปแบบเวลาเป็นสตริง 'HH.MM' หรือ 'HH:MM' หรือเป็น datetime.time objects

    Args:
        schedule: อ็อบเจกต์ตารางเรียนที่มีคุณสมบัติ time_start และ time_end.

    Returns:
        True ถ้าเวลาปัจจุบันอยู่ในช่วงเวลาเรียน, False ถ้าไม่ใช่ หรือข้อมูลไม่ถูกต้อง.
    """
    now = datetime.now()
    current_time = now.time() # ดึงเฉพาะเวลาปัจจุบันออกมา (datetime.time object)
    today_weekday = now.weekday() + 1 # วันปัจจุบันในรูปแบบตัวเลข (1=จันทร์, 7=อาทิตย์)

    # ตรวจสอบว่าวันนี้ตรงกับวันของตารางเรียนหรือไม่
    # สมมติว่า schedule.course_day เป็น int (1-7)
    if  int(schedule.course_day) != today_weekday:
        return False # ถ้าวันไม่ตรงกัน ก็ไม่ต้องตรวจสอบเวลาต่อ
    
    start_time_obj = None
    end_time_obj = None

    # Helper function สำหรับแปลงสตริงเวลา
    def parse_time_string(time_str_val):
        if not time_str_val:
            return None
        
        # ลองแปลงรูปแบบ 'HH:MM' ก่อน (ถ้ามี)
        if ':' in time_str_val:
            try:
                return datetime.strptime(time_str_val, '%H:%M').time()
            except ValueError:
                pass # ถ้าไม่ใช่ format นี้ ก็ไปลอง format อื่น

        # ลองแปลงรูปแบบ 'HH.MM'
        if '.' in time_str_val:
            try:
                return datetime.strptime(time_str_val, '%H.%M').time()
            except ValueError:
                pass # ถ้าไม่ใช่ format นี้ ก็คืนค่า None

        return None # ถ้าไม่ตรงกับ format ไหนเลย

    # แปลง time_start ให้เป็น datetime.time object
    if isinstance(schedule.time_start, time): # ถ้าเป็น datetime.time object อยู่แล้ว
        start_time_obj = schedule.time_start
    elif isinstance(schedule.time_start, str): # ถ้าเป็น string
        start_time_obj = parse_time_string(schedule.time_start)

    # แปลง time_end ให้เป็น datetime.time object
    if isinstance(schedule.time_end, time): # ถ้าเป็น datetime.time object อยู่แล้ว
        end_time_obj = schedule.time_end
    elif isinstance(schedule.time_end, str): # ถ้าเป็น string
        end_time_obj = parse_time_string(schedule.time_end)

    # ตรวจสอบว่าทั้งเวลาเริ่มต้นและสิ้นสุดถูกแปลงเป็น datetime.time object เรียบร้อยแล้ว
    if start_time_obj and end_time_obj:
        return start_time_obj <= current_time <= end_time_obj
    
    return False # คืนค่า False หากเวลาเริ่มต้น/สิ้นสุดไม่ถูกต้องหรือไม่สามารถแปลงได้