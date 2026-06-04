from django.db import migrations


class Migration(migrations.Migration):
    """
    แก้ตาราง live_holidaydate ใน DB โดยตรง:
    - เปลี่ยน column `date` → `date_start`
    - เพิ่ม column `date_end`
    (Django migration state คิดว่ามีอยู่แล้วจาก 0030 ที่ถูกแก้ไข)
    """

    dependencies = [
        ('live', '0031_holiday_date_range'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE live_holidaydate CHANGE `date` `date_start` date NOT NULL",
                    reverse_sql="ALTER TABLE live_holidaydate CHANGE `date_start` `date` date NOT NULL",
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE live_holidaydate ADD COLUMN `date_end` date NOT NULL DEFAULT '2026-01-01'",
                    reverse_sql="ALTER TABLE live_holidaydate DROP COLUMN `date_end`",
                ),
            ],
            state_operations=[],  # state ถูกต้องอยู่แล้วจาก migration 0030 ที่อัปเดต
        ),
    ]
