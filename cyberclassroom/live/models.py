import datetime

from django.db import models


# Create your models here.
class Locations(models.Model):
    location_name = models.CharField('ชื่อสถานที่',max_length=50)
    class Meta:
        # managed = False
        verbose_name="รายการตำแหน่งห้องเรียน"
        verbose_name_plural="ข้อมูลตำแหน่งห้องเรียน"
    def __str__(self):
        return self.location_name

class Classrooms(models.Model):
    room_name = models.CharField('ชื่อห้อง',max_length=50,primary_key=True,)
    # room_location = models.CharField('เรียนที่',max_length=50)
    room_location = models.ForeignKey(Locations,on_delete=models.PROTECT, verbose_name="เรียนที่",)
    room_stream=models.CharField('ชื่อช่องในการถ่ายทอด',max_length=200)
    room_order=models.IntegerField(default=0)
    # ('ค่าที่บันทึก','ค่าที่แสดง'),
    STATUS_LIST=(
        ('1','เปิด'),
        ('0','ปิด')
    )
    room_status=models.CharField('สถานะห้องเรียน',max_length=20, choices=STATUS_LIST, default='1')
    # Only set added_by during the first save.
    added_by = models.CharField( max_length=50,blank=True)
    room_comment=models.TextField(blank = True)
    created_at=models.CharField( max_length=50,blank=True)
    updated_at=models.CharField( max_length=50,blank=True)
    # รหัสลับสำหรับอาจารย์ — ว่างเปล่า = ปิดใช้งานแชทอาจารย์
    chat_pin = models.CharField('รหัสอาจารย์ (Chat PIN)', max_length=20,
                                blank=True, default='',
                                help_text='ตั้งรหัสลับให้อาจารย์พิมพ์เพื่อแสดง badge "อาจารย์" ในแชท '
                                          '(ว่างเปล่า = ไม่เปิดฟีเจอร์นี้)')
    chat_open = models.BooleanField('เปิดให้นักศึกษาแชท', default=False,
                                    help_text='ถ้าปิด → เฉพาะอาจารย์เท่านั้นที่พิมพ์ได้')

    class Meta:
        verbose_name="รายการห้องเรียน"
        verbose_name_plural="ข้อมูลห้องเรียน"

    def __str__(self):
        return self.room_name

class ClassScheduleCenter(models.Model):
    course_no        = models.CharField('รหัสวิชา', max_length=100)
    section          = models.CharField('ตอนเรียน (Section)', max_length=10,
                                        blank=True, default='',
                                        help_text='เช่น 01, 02, A, B — ว่างได้ถ้าไม่มี section')
    course_name_thai = models.CharField('ชื่อวิชา TH', max_length=255, blank=True, default='-')
    course_name_eng  = models.CharField('ชื่อวิชา EN', max_length=255, blank=True, default='-')
    instructor       = models.CharField('อาจารย์ผู้สอน', max_length=255, blank=True, default='-')
    DAY_LIST=(
        ('1','Monday'),
        ('2','Tuesday'),
        ('3','Wednesday'),
        ('4','Thursday'),
        ('5','Friday'),
        ('6','Saturday'),
        ('7','Sunday')
    )
    # COLOR_CHOICES = (
    #     ('green','GREEN'),
    #     ('blue', 'BLUE'),
    #     ('red','RED'),
    #     ('orange','ORANGE'),
    #     ('black','BLACK'),
    # )
    course_day=models.CharField('วันที่เรียน',max_length=20, choices=DAY_LIST, default='Monday')
    time_start=models.CharField('เริ่มเรียน (00:00)',max_length=20)
    time_end=models.CharField('สิ้นสุด (00:00)',max_length=20)
    room_name = models.ForeignKey(Classrooms,on_delete=models.PROTECT, verbose_name="ห้องเรียน",)
    # Only set added_by during the first save.
    added_by = models.CharField( max_length=50,blank=True)
    created_at=models.CharField( max_length=50,blank=True)
    updated_at=models.CharField( max_length=50,blank=True)
    closed_date   = models.DateField('ปิดคอร์สตั้งแต่วันที่', null=True, blank=True,
                                     help_text='ถ้ากำหนด → วันนั้นและหลังจากนั้นจะแสดง "ปิดคอร์สแล้ว"')
    closed_reason = models.CharField('เหตุผลที่ปิดคอร์ส', max_length=200, blank=True, default='')

    class Meta:
        verbose_name        = 'รายการวิชาเรียน'
        verbose_name_plural = 'ข้อมูลวิชาเรียน'
        ordering            = ('time_start',)
        unique_together     = ('course_no', 'section', 'room_name', 'course_day', 'time_start')

    def __str__(self):
        if self.section:
            return f'{self.course_no} (Sec {self.section})'
        return self.course_no


class ClassCancellation(models.Model):
    schedule    = models.ForeignKey(ClassScheduleCenter, on_delete=models.CASCADE,
                                    verbose_name='วิชา', related_name='cancellations')
    cancel_date = models.DateField('วันที่งดบรรยาย')
    reason      = models.CharField('เหตุผล', max_length=200, blank=True, default='',
                                   help_text='เช่น อาจารย์ติดภารกิจ, ป่วย, ไปสัมมนา')
    created_by  = models.CharField(max_length=50, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'งดบรรยาย'
        verbose_name_plural = 'งดบรรยาย'
        ordering            = ['-cancel_date']
        unique_together     = ('schedule', 'cancel_date')

    def __str__(self):
        return f'{self.schedule} — งด {self.cancel_date}'


class LogSubjectInRoom(models.Model):
    course_no = models.CharField('รหัสวิชา',max_length=30,)
    room_location = models.ForeignKey(Locations,on_delete=models.PROTECT, verbose_name="เรียนที่",)
    user_ip=models.CharField( max_length=100,blank=True)
    created_at=models.CharField( max_length=50,blank=True)

    def __str__(self):
        return self.course_no


class Count(models.Model):
    # Define your fields to match the columns in the existing table
    room_name = models.CharField(max_length=10,primary_key=True)
    sessions_cupertino = models.CharField(max_length=5)
    sessions_total=models.CharField(max_length=5)
    updated=models.CharField(max_length=50)
    
    class Meta:
        managed = False  # This tells Django not to manage the table creation
        db_table = 'live_count'  

class ChatMessage(models.Model):
    room       = models.ForeignKey(Classrooms, on_delete=models.CASCADE,
                                   related_name='chat_messages', verbose_name='ห้องเรียน')
    sender     = models.CharField('ชื่อผู้ส่ง', max_length=80)
    is_teacher = models.BooleanField('อาจารย์', default=False)
    message     = models.TextField('ข้อความ (แสดงผล)', max_length=500)
    message_raw = models.TextField('ข้อความต้นฉบับ', max_length=500, blank=True, default='',
                                   help_text='เก็บข้อความก่อน censor — ว่างเปล่าหมายความว่าไม่มีคำหยาบ')
    created_at  = models.DateTimeField('เวลา', auto_now_add=True)
    sender_ip   = models.GenericIPAddressField('IP ผู้ส่ง', blank=True, null=True)
    active_course = models.CharField('วิชาที่กำลังสอน', max_length=30, blank=True, default='')

    class Meta:
        verbose_name        = 'ข้อความแชท'
        verbose_name_plural = 'ข้อความแชทในห้องเรียน'
        ordering            = ('created_at',)
        indexes             = [models.Index(fields=['room', 'created_at'])]

    def __str__(self):
        prefix = '[อาจารย์] ' if self.is_teacher else ''
        return '{}{} — {}: {}'.format(prefix, self.room_id, self.sender, self.message[:40])


class HolidayDate(models.Model):
    TYPE_HOLIDAY   = 'holiday'
    TYPE_SEMESTER  = 'semester'
    TYPE_MAINTAIN  = 'maintain'
    TYPE_GENERAL   = 'general'
    BANNER_TYPES = [
        (TYPE_HOLIDAY,  '🎌 วันหยุดราชการ'),
        (TYPE_SEMESTER, '🎓 ปิดภาคการศึกษา'),
        (TYPE_MAINTAIN, '🔧 แจ้งซ่อมบำรุง'),
        (TYPE_GENERAL,  '📢 ประกาศทั่วไป'),
    ]

    banner_type = models.CharField('ประเภท', max_length=20,
                                   choices=BANNER_TYPES, default=TYPE_HOLIDAY)
    date_start  = models.DateField('วันเริ่มต้น')
    date_end    = models.DateField('วันสิ้นสุด',
                                   help_text='ถ้าเป็นวันเดียวให้ใส่วันเดียวกับวันเริ่มต้น')
    name        = models.CharField('ชื่อ / หัวข้อ', max_length=100)
    note        = models.CharField('หมายเหตุ', max_length=200, blank=True,
                                   help_text='เช่น ไม่มีการเรียนการสอน / งดถ่ายทอดสด')

    class Meta:
        verbose_name        = 'ประกาศ / แบนเนอร์'
        verbose_name_plural = 'ประกาศ / แบนเนอร์'
        ordering            = ['date_start']

    def __str__(self):
        if self.date_start == self.date_end:
            return f'{self.date_start.strftime("%d/%m/%Y")} — {self.name}'
        return f'{self.date_start.strftime("%d/%m/%Y")} ถึง {self.date_end.strftime("%d/%m/%Y")} — {self.name}'


class BannedStudent(models.Model):
    std_code   = models.CharField('รหัสนักศึกษา', max_length=20, unique=True)
    banned_at  = models.DateTimeField('เวลาที่ถูก ban', auto_now_add=True)
    ban_reason = models.TextField('เหตุผล', blank=True, default='ใช้ถ้อยคำไม่เหมาะสมในระบบแชท')

    class Meta:
        verbose_name        = 'นักศึกษาที่ถูกระงับแชท'
        verbose_name_plural = 'รายชื่อนักศึกษาที่ถูกระงับแชท'

    def __str__(self):
        return self.std_code


class LiveClassroom(models.Model):
    room_name = models.CharField(max_length=50, primary_key=True)
    room_stream = models.CharField(max_length=200)
    room_order = models.IntegerField()
    room_status = models.CharField(max_length=20)  # ใช้ค่า '1' สำหรับถ่ายทอดสด
    updated_at = models.CharField(max_length=50)
    class Meta:
        managed = False  # This tells Django not to manage the table creation
        db_table = 'live_classrooms'  