from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('live', '0028_chatmessage_message_raw'),
    ]

    operations = [
        migrations.CreateModel(
            name='BannedStudent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('std_code', models.CharField(max_length=20, unique=True, verbose_name='รหัสนักศึกษา')),
                ('banned_at', models.DateTimeField(auto_now_add=True, verbose_name='เวลาที่ถูก ban')),
                ('ban_reason', models.TextField(blank=True, default='ใช้ถ้อยคำไม่เหมาะสมในระบบแชท', verbose_name='เหตุผล')),
            ],
            options={
                'verbose_name': 'นักศึกษาที่ถูกระงับแชท',
                'verbose_name_plural': 'รายชื่อนักศึกษาที่ถูกระงับแชท',
            },
        ),
    ]
