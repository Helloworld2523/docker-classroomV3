import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cyberclassroom.settings')
django.setup()
from django.db import connection

with connection.cursor() as c:
    # แก้ live_chatmessage ให้ตรงกับ live_classrooms (utf8_general_ci)
    print('Converting live_chatmessage to utf8_general_ci...')
    c.execute("ALTER TABLE live_chatmessage CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci")
    print('Done.')

    c.execute("SHOW TABLE STATUS LIKE 'live_chatmessage'")
    row = c.fetchone()
    print('live_chatmessage collation now:', row[14] if row else 'not found')
