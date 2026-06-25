from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('live', '0038_auto_20260623_0923'),
    ]

    operations = [
        migrations.AddField(
            model_name='classrooms',
            name='chat_open',
            field=models.BooleanField(
                default=False,
                verbose_name='เปิดให้นักศึกษาแชท',
                help_text='ถ้าปิด → เฉพาะอาจารย์เท่านั้นที่พิมพ์ได้',
            ),
        ),
    ]
