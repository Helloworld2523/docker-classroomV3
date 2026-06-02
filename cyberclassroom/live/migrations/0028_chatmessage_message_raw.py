from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('live', '0027_auto_20260519_1406'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='message_raw',
            field=models.TextField(
                blank=True,
                default='',
                help_text='เก็บข้อความก่อน censor — ว่างเปล่าหมายความว่าไม่มีคำหยาบ',
                max_length=500,
                verbose_name='ข้อความต้นฉบับ',
            ),
        ),
    ]
