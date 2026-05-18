from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('live', '0025_auto_20260518_0957'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='sender_ip',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='IP ผู้ส่ง'),
        ),
    ]
