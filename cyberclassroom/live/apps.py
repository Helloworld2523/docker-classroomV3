from django.apps import AppConfig


class LiveConfig(AppConfig):
    name = 'live'
    verbose_name = "ระบบงานการถ่ายทอดสด"

    def ready(self):
        import os
        # รัน thread เฉพาะ process หลัก (ไม่รันซ้ำใน uWSGI worker reload)
        if os.environ.get('RUN_MAIN') != 'true':
            from live import _wowza_poller
            _wowza_poller.start()
