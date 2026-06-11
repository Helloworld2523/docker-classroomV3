"""
Migration 0035:
1. Sync Django state: เพิ่ม id AutoField ที่มีอยู่แล้วใน DB เข้า state (database_operations=[])
2. เพิ่ม closed_date, closed_reason บน ClassScheduleCenter
3. สร้าง ClassCancellation model
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('live', '0034_classschedulecenter_new_pk_section'),
    ]

    operations = [
        # ─── 1. Sync id field เข้า Django state (DB มีอยู่แล้ว) ─────────
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='classschedulecenter',
                    name='id',
                    field=models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                    preserve_default=False,
                ),
            ],
        ),

        # ─── 2. เพิ่ม closed_date, closed_reason (รัน SQL จริง) ──────────
        migrations.AddField(
            model_name='classschedulecenter',
            name='closed_date',
            field=models.DateField(
                blank=True, null=True,
                verbose_name='ปิดคอร์สตั้งแต่วันที่',
                help_text='ถ้ากำหนด → วันนั้นและหลังจากนั้นจะแสดง "ปิดคอร์สแล้ว"',
            ),
        ),
        migrations.AddField(
            model_name='classschedulecenter',
            name='closed_reason',
            field=models.CharField(
                blank=True, default='', max_length=200,
                verbose_name='เหตุผลที่ปิดคอร์ส',
            ),
        ),

        # ─── 3. สร้าง ClassCancellation ───────────────────────────────────
        migrations.CreateModel(
            name='ClassCancellation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cancel_date', models.DateField(verbose_name='วันที่งดบรรยาย')),
                ('reason', models.CharField(
                    blank=True, default='', max_length=200,
                    verbose_name='เหตุผล',
                    help_text='เช่น อาจารย์ติดภารกิจ, ป่วย, ไปสัมมนา',
                )),
                ('created_by', models.CharField(blank=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('schedule', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cancellations',
                    to='live.ClassScheduleCenter',
                    verbose_name='วิชา',
                )),
            ],
            options={
                'verbose_name': 'งดบรรยาย',
                'verbose_name_plural': 'งดบรรยาย',
                'ordering': ['-cancel_date'],
                'unique_together': {('schedule', 'cancel_date')},
            },
        ),
    ]
