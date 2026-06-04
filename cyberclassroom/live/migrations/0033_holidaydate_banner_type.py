from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('live', '0032_holidaydate_date_range'),
    ]

    operations = [
        migrations.AddField(
            model_name='holidaydate',
            name='banner_type',
            field=models.CharField(
                choices=[
                    ('holiday',  '🎌 วันหยุดราชการ'),
                    ('semester', '🎓 ปิดภาคการศึกษา'),
                    ('maintain', '🔧 แจ้งซ่อมบำรุง'),
                    ('general',  '📢 ประกาศทั่วไป'),
                ],
                default='holiday',
                max_length=20,
                verbose_name='ประเภท',
            ),
        ),
        migrations.AlterModelOptions(
            name='holidaydate',
            options={
                'ordering': ['date_start'],
                'verbose_name': 'ประกาศ / แบนเนอร์',
                'verbose_name_plural': 'ประกาศ / แบนเนอร์',
            },
        ),
    ]
