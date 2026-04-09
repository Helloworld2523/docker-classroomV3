from datetime import datetime, time
from django.shortcuts import render

class LearningHoursMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("⏰ LearningHoursMiddleware Called")
        print("📄 PATH =", request.path)
        print("🕒 NOW =", datetime.now().strftime('%H:%M:%S'))

        # ✅ ยกเว้นเส้นทาง /admin และ static/media
        if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/media/') or request.path.startswith('/live-monitor/'):
            return self.get_response(request)

        # ✅ ถ้ายกเว้น API บาง path เช่น /get-live-viewers/
        if request.path.startswith('/get-live-viewers/'):
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
