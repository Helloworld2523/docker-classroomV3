from datetime import datetime, time
from django.shortcuts import render

class LearningHoursMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("⏰ LearningHoursMiddleware Called")
        print("📄 PATH =", request.path)
        print("🕒 NOW =", datetime.now().strftime('%H:%M:%S'))

        # ✅ ยกเว้น path ที่ไม่ต้องการตรวจสอบเวลาเรียน
        EXEMPT_PREFIXES = (
            '/admin/',
            '/static/',
            '/media/',
            '/live-monitor/',
            '/get-live-viewers/',
            '/viewer-data/',   # Monitor API polling
            '/monitor-sse/',   # Monitor SSE
            '/live',           # หน้าถ่ายทอดสด — เปิดตลอด (OG crawlers + ผู้ชม)
        )
        if request.path.startswith(EXEMPT_PREFIXES):
            return self.get_response(request)

        now = datetime.now().time()
        start_time = time(7, 0)   # แก้ไขจาก 7:10 เป็น 7:00
        end_time = time(20, 30)   # เวลา 20:30 ตามที่ต้องการ
        if not (start_time <= now <= end_time):
            return render(request, 'live/out_of_learning_time.html', {
                'start_time': start_time.strftime('%H:%M'),
                'end_time': end_time.strftime('%H:%M'),
            })

        return self.get_response(request) 
