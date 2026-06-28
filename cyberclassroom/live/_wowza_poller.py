"""
Background thread: ดึง viewer count จาก Wowza ทุก 20 วินาที
- เก็บใน _cache dict (อ่านเร็ว ไม่กด DB ทุก request)
- UPDATE live_count table ด้วย (ให้ระบบอื่นอ่านได้)
- เฉพาะห้อง rucom สำหรับงานถ่ายทอดสดปฐมนิเทศ
"""
import threading
import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

WOWZA_URL      = 'http://202.41.160.65:8086/connectioncounts?flat'
WOWZA_USER     = 'chai_songwut'
WOWZA_PASS     = '0815822498'
POLL_INTERVAL  = 20   # วินาที
TARGET_ROOM    = 'rucom'

# ── In-memory cache ────────────────────────────────────────────
_cache = {}   # { room_name: {'total': int, 'cupertino': int, 'updated': str} }
_lock  = threading.Lock()


def get_cached(room_name: str) -> dict:
    with _lock:
        return dict(_cache.get(room_name.lower(), {'total': 0, 'cupertino': 0, 'updated': ''}))


def _update_db(room_name, sessions_cupertino, sessions_total, dt_string):
    try:
        import django
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute(
                'UPDATE live_count SET sessions_cupertino=%s, sessions_total=%s, updated=%s WHERE room_name=%s',
                (sessions_cupertino, sessions_total, dt_string, room_name),
            )
    except Exception as e:
        logger.warning('wowza_poller: DB update failed — %s', e)


def _poll():
    while True:
        try:
            resp = requests.get(WOWZA_URL, auth=(WOWZA_USER, WOWZA_PASS), timeout=10)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                dt_string = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

                for stream in root.findall('Stream'):
                    name        = (stream.get('streamName') or '').strip().lower()
                    cupertino   = stream.get('sessionsCupertino', '0')
                    total       = stream.get('sessionsTotal', '0')

                    with _lock:
                        _cache[name] = {
                            'total':     int(total)     if str(total).isdigit()     else 0,
                            'cupertino': int(cupertino) if str(cupertino).isdigit() else 0,
                            'updated':   dt_string,
                        }

                    if name == TARGET_ROOM:
                        _update_db(name, cupertino, total, dt_string)
                        logger.info('wowza_poller: %s → %s viewers', name, total)
            else:
                logger.warning('wowza_poller: HTTP %s', resp.status_code)

        except Exception as e:
            logger.warning('wowza_poller: poll error — %s', e)

        threading.Event().wait(POLL_INTERVAL)


def start():
    t = threading.Thread(target=_poll, name='wowza-poller', daemon=True)
    t.start()
    logger.info('wowza_poller: started (interval=%ss)', POLL_INTERVAL)
