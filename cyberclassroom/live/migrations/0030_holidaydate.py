from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('live', '0029_bannedstudent'),
    ]

    operations = [
        migrations.CreateModel(
            name='HolidayDate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_start', models.DateField(verbose_name='วันเริ่มต้น')),
                ('date_end', models.DateField(help_text='ถ้าเป็นวันเดียวให้ใส่วันเดียวกับวันเริ่มต้น', verbose_name='วันสิ้นสุด')),
                ('name', models.CharField(max_length=100, verbose_name='ชื่อวันหยุด')),
                ('note', models.CharField(blank=True, help_text='เช่น ไม่มีการเรียนการสอน / งดถ่ายทอดสด', max_length=200, verbose_name='หมายเหตุ')),
            ],
            options={
                'verbose_name': 'วันหยุดราชการ',
                'verbose_name_plural': 'วันหยุดราชการ',
                'ordering': ['date_start'],
            },
        ),
    ]
