"""
Migration: เปลี่ยน ClassScheduleCenter
- DB อยู่ในสถานะถูกต้องแล้ว (id, section มีอยู่แล้ว)
- migration นี้แค่ sync Django state + เพิ่ม unique_together
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('live', '0033_holidaydate_banner_type'),
    ]

    operations = [
        # ─── Sync Django state (DB มีอยู่แล้ว ไม่รัน SQL) ───────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[],   # ไม่ต้องทำอะไรกับ DB
            state_operations=[
                migrations.AlterField(
                    model_name='classschedulecenter',
                    name='course_no',
                    field=models.CharField(max_length=30, verbose_name='รหัสวิชา'),
                ),
                migrations.AddField(
                    model_name='classschedulecenter',
                    name='section',
                    field=models.CharField(
                        blank=True, default='', max_length=10,
                        verbose_name='ตอนเรียน (Section)',
                        help_text='เช่น 01, 02, A, B — ว่างได้ถ้าไม่มี section',
                    ),
                ),
            ],
        ),

        # ─── unique_together — รัน SQL จริง (สร้าง index) ───────────────
        migrations.AlterUniqueTogether(
            name='classschedulecenter',
            unique_together={('course_no', 'section', 'room_name', 'course_day', 'time_start')},
        ),
    ]
