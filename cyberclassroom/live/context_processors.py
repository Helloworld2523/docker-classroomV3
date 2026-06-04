from datetime import date
from .models import HolidayDate


def holiday_context(request):
    """
    ตรวจว่าวันนี้อยู่ในช่วงวันหยุดราชการที่กำหนดไว้หรือไม่
    - today_holiday = None           → วันปกติ
    - today_holiday = HolidayDate    → อยู่ในช่วงวันหยุด
    """
    try:
        today = date.today()
        holiday = HolidayDate.objects.filter(
            date_start__lte=today,
            date_end__gte=today,
        ).first()
    except Exception:
        holiday = None
    return {'today_holiday': holiday}
