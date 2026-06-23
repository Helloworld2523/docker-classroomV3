import datetime
from django import forms
from django.contrib import admin
from django.utils.html import mark_safe
from django.db.models import Case, When, IntegerField

from .models import (
    Classrooms, ClassScheduleCenter, ClassCancellation, Locations,
    LogSubjectInRoom, Count, LiveClassroom, ChatMessage, BannedStudent, HolidayDate,
)
from . import config


# ─── helpers ──────────────────────────────────────────────────────────────────

def _get_server(location_id):
    mapping = {
        1: config.serverMedia68,
        2: config.serverMedia65,
        3: config.serverMedia66,
        4: config.serverMedia68,
        5: config.serverMedia66,
        6: config.serverMedia66,
        7: config.serverMedia66,
        8: config.serverMedia67,
    }
    return mapping.get(location_id, config.serverMedia66)


def _viewer_map():
    """room_name.lower() → int viewer count"""
    return {
        c.room_name.strip().lower(): (
            int(c.sessions_total) if str(c.sessions_total).isdigit() else 0
        )
        for c in Count.objects.all()
    }


def _live_set():
    """set of room_name.lower() that are currently live (room_status='1')"""
    return {
        r.room_name.strip().lower()
        for r in LiveClassroom.objects.filter(room_status='1')
    }


# ─── ClassScheduleCenter Form ────────────────────────────────────────────────

_SECTION_CHOICES = [
    ('', '— ไม่มี section —'),
    ('1','1'), ('2','2'), ('3','3'), ('4','4'), ('5','5'),
    ('6','6'), ('7','7'), ('8','8'), ('9','9'),
    ('A','A'), ('B','B'), ('C','C'), ('D','D'), ('E','E'),
]

_DAY_CHOICES_EN = [
    ('1','Monday'),
    ('2','Tuesday'),
    ('3','Wednesday'),
    ('4','Thursday'),
    ('5','Friday'),
    ('6','Saturday'),
    ('7','Sunday'),
]

class ClassScheduleCenterForm(forms.ModelForm):
    instructor = forms.CharField(max_length=255, required=False, label='อาจารย์ผู้สอน')
    # รหัสวิชา — รองรับหลายรหัสคั่นด้วย , หรือขึ้นบรรทัดใหม่
    course_no  = forms.CharField(
        label='รหัสวิชา',
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'กรอกรหัสวิชาได้หลายรหัส คั่นด้วย , หรือ Enter\nเช่น ENG1111, ENG1110',
            'style': 'font-family:monospace;font-size:0.9rem;',
        }),
        help_text=mark_safe('''
กรอกรหัสเดียว หรือหลายรหัสพร้อมกัน คั่นด้วย , (comma) หรือขึ้นบรรทัดใหม่<br>
<button type="button" onclick="csmOpen()"
style="margin-top:0.5rem;padding:0.4rem 1rem;background:#1d4ed8;color:#fff;
border:none;border-radius:6px;font-size:0.82rem;cursor:pointer;
font-weight:600;box-shadow:0 2px 6px rgba(29,78,216,0.3);">
🔍 ค้นหาวิชาจาก RU</button>
<div id="csmModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:99999;align-items:center;justify-content:center;">
  <div style="background:#fff;border-radius:12px;width:96%;max-width:960px;max-height:88vh;display:flex;flex-direction:column;box-shadow:0 8px 40px rgba(0,0,0,0.25);overflow:hidden;">
    <div style="background:#1d4ed8;color:#fff;padding:0.85rem 1.25rem;display:flex;align-items:center;justify-content:space-between;">
      <span style="font-weight:700;">🔍 ค้นหารายวิชาจาก RU</span>
      <button type="button" onclick="csmClose()" style="background:none;border:none;color:#fff;font-size:1.4rem;cursor:pointer;line-height:1;">×</button>
    </div>
    <!-- ตั้งค่าปีการศึกษา / ภาคเรียน -->
    <div style="padding:0.6rem 1.25rem;background:#eff6ff;border-bottom:1px solid #bfdbfe;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;">
      <label style="font-size:0.82rem;color:#1e40af;font-weight:600;">ปีการศึกษา:
        <select id="csmYear" style="margin-left:0.4rem;padding:0.25rem 0.5rem;border:1px solid #93c5fd;border-radius:6px;font-size:0.82rem;">
          <option value="2568" selected>2568</option>
          <option value="2567">2567</option>
          <option value="2566">2566</option>
          <option value="2569">2569</option>
        </select>
      </label>
      <label style="font-size:0.82rem;color:#1e40af;font-weight:600;">ภาคเรียน:
        <select id="csmSem" style="margin-left:0.4rem;padding:0.25rem 0.5rem;border:1px solid #93c5fd;border-radius:6px;font-size:0.82rem;">
          <option value="1" selected>1</option>
          <option value="2">2</option>
          <option value="3">3 (ฤดูร้อน)</option>
        </select>
      </label>
      <button type="button" onclick="csmFetch(document.getElementById(\'csmQ\').value.trim())"
        style="padding:0.25rem 0.85rem;background:#1d4ed8;color:#fff;border:none;border-radius:6px;font-size:0.8rem;cursor:pointer;">
        โหลดใหม่
      </button>
    </div>
    <div style="padding:0.75rem 1.25rem;border-bottom:1px solid #e5e7eb;">
      <input id="csmQ" type="text" placeholder="พิมพ์รหัสหรือชื่อวิชาเพื่อกรอง..."
        style="width:100%;padding:0.5rem 0.75rem;border:1px solid #d1d5db;border-radius:8px;font-size:0.9rem;outline:none;box-sizing:border-box;">
      <div id="csmStat" style="font-size:0.78rem;color:#6b7280;margin-top:0.4rem;"></div>
    </div>
    <div style="overflow-y:auto;flex:1;">
      <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
        <thead><tr style="background:#f9fafb;position:sticky;top:0;">
          <th style="padding:0.6rem 0.75rem;text-align:left;border-bottom:1px solid #e5e7eb;white-space:nowrap;">รหัสวิชา</th>
          <th style="padding:0.6rem 0.75rem;text-align:left;border-bottom:1px solid #e5e7eb;">ชื่อวิชา</th>
          <th style="padding:0.6rem 0.5rem;text-align:center;border-bottom:1px solid #e5e7eb;">วัน</th>
          <th style="padding:0.6rem 0.5rem;text-align:center;border-bottom:1px solid #e5e7eb;">เวลา</th>
          <th style="padding:0.6rem 0.5rem;text-align:center;border-bottom:1px solid #e5e7eb;">ห้อง</th>
          <th style="padding:0.6rem 0.5rem;text-align:center;border-bottom:1px solid #e5e7eb;">วันสอบ</th>
          <th style="padding:0.6rem 0.5rem;text-align:center;border-bottom:1px solid #e5e7eb;">หน่วยกิต</th>
        </tr></thead>
        <tbody id="csmBody"></tbody>
      </table>
    </div>
  </div>
</div>
<script>
var _csmCache={};var _csmMetaLoaded=false;
function csmOpen(){
  document.getElementById("csmModal").style.display="flex";
  document.getElementById("csmQ").value="";
  document.getElementById("csmBody").innerHTML="";
  document.getElementById("csmStat").textContent="กำลังโหลด...";
  _csmCache={};
  document.getElementById("csmQ").oninput=function(){
    clearTimeout(window._csmT);
    window._csmT=setTimeout(function(){csmFetch(document.getElementById("csmQ").value.trim());},400);
  };
  if(!_csmMetaLoaded){
    /* โหลด meta ก่อน เพื่อ build dropdown ปีการศึกษา */
    fetch("/admin-api/course-search/?meta_only=1",{credentials:"same-origin"})
    .then(function(r){return r.json();})
    .then(function(d){
      _csmBuildYearDropdown(d.meta||{});
      _csmMetaLoaded=true;
      csmFetch("");
      setTimeout(function(){document.getElementById("csmQ").focus();},100);
    })
    .catch(function(){csmFetch("");});
  } else {
    csmFetch("");
    setTimeout(function(){document.getElementById("csmQ").focus();},100);
  }
  document.getElementById("csmYear").onchange=function(){
    localStorage.setItem("csm_year",this.value);_csmCache={};csmFetch(document.getElementById("csmQ").value.trim());
  };
  document.getElementById("csmSem").onchange=function(){
    localStorage.setItem("csm_sem",this.value);_csmCache={};csmFetch(document.getElementById("csmQ").value.trim());
  };
}
function _csmBuildYearDropdown(meta){
  var sel=document.getElementById("csmYear");
  var savedYear=localStorage.getItem("csm_year")||meta.default_year||"2568";
  var savedSem=localStorage.getItem("csm_sem")||meta.default_semester||"1";
  var years=meta.years||[savedYear];
  sel.innerHTML="";
  years.forEach(function(y){
    var o=document.createElement("option");
    o.value=y;o.textContent=y;
    if(y===savedYear)o.selected=true;
    sel.appendChild(o);
  });
  document.getElementById("csmSem").value=savedSem;
}
function csmClose(){document.getElementById("csmModal").style.display="none";}
function csmFetch(q){
  var year=document.getElementById("csmYear").value;
  var sem=document.getElementById("csmSem").value;
  var cacheKey=year+"|"+sem;
  document.getElementById("csmStat").textContent="กำลังโหลด...";
  document.getElementById("csmBody").innerHTML="";
  function render(rows){
    var terms=q?q.toUpperCase().split("_").map(function(t){return t.trim();}).filter(function(t){return t.length>0;}):[];
    var filtered=terms.length?rows.filter(function(c){
      var cn=String(c.course_no||"").toUpperCase();
      var nm=String(c.course_name||"").toUpperCase();
      return terms.some(function(t){return cn.includes(t)||nm.includes(t);});
    }):rows;
    if(terms.length>1){
      filtered=filtered.slice().sort(function(a,b){
        var ai=terms.findIndex(function(t){return String(a.course_no||"").toUpperCase().includes(t);});
        var bi=terms.findIndex(function(t){return String(b.course_no||"").toUpperCase().includes(t);});
        if(ai<0)ai=terms.length;
        if(bi<0)bi=terms.length;
        return ai-bi;
      });
    }
    var display=filtered.slice(0,200);
    var statMsg="พบ "+filtered.length+" รายการ จากทั้งหมด "+rows.length+" รายการ";
    if(filtered.length>200)statMsg+=" (แสดง 200 รายการแรก — พิมพ์เพื่อกรองเพิ่ม)";
    document.getElementById("csmStat").textContent=statMsg;
    var tb=document.getElementById("csmBody");
    tb.innerHTML="";
    if(!filtered.length){
      tb.innerHTML="<tr><td colspan=7 style=\\"padding:1.5rem;text-align:center;color:#9ca3af;\\">ไม่พบรายวิชา</td></tr>";
      return;
    }
    display.forEach(function(c){
      var tr=document.createElement("tr");
      tr.style.borderBottom="1px solid #f3f4f6";
      tr.onmouseover=function(){tr.style.background="#eff6ff";};
      tr.onmouseout=function(){tr.style.background="";};
      var cn=c.course_no||"";
      var nm=c.course_name||"";
      var sec=String(c.section||"");
      var cr=c.credit||"";
      var tp=c.time_period||"";
      var rm=c.course_room||"";
      var ex=c.examdate||"";
      var dy=c.day_name_s||"";
      function esc(s){var d=document.createElement("div");d.textContent=String(s||"");return d.innerHTML;}
      tr.innerHTML=
        "<td style=\\"padding:0.5rem 0.75rem;white-space:nowrap;\\">"+
          "<div style=\\"font-weight:700;color:#1e3a8a;font-size:0.88rem;\\">"+esc(cn)+"</div>"+
          "<button type=\\"button\\" style=\\"margin-top:3px;background:#1d4ed8;color:#fff;border:none;border-radius:5px;padding:0.2rem 0.6rem;font-size:0.75rem;cursor:pointer;width:100%;\\" title=\\"โหลดวิชานี้\\">"+
            "&#8595; โหลด"+
          "</button>"+
        "</td>"+
        "<td style=\\"padding:0.5rem 0.75rem;font-size:0.84rem;\\">"+esc(nm)+"</td>"+
        "<td style=\\"padding:0.5rem;text-align:center;font-size:0.8rem;font-weight:600;color:#1d4ed8;\\">"+esc(dy)+"</td>"+
        "<td style=\\"padding:0.5rem;text-align:center;font-size:0.8rem;white-space:nowrap;\\">"+esc(tp)+"</td>"+
        "<td style=\\"padding:0.5rem;text-align:center;font-size:0.8rem;\\">"+esc(rm)+"</td>"+
        "<td style=\\"padding:0.5rem;text-align:center;font-size:0.8rem;white-space:nowrap;\\">"+esc(ex)+"</td>"+
        "<td style=\\"padding:0.5rem;text-align:center;font-size:0.85rem;\\">"+esc(cr)+"</td>";
      tr.querySelector("button").onclick=function(){
        /* รหัสวิชา — ถ้า search หลาย code (คั่นด้วย _) ให้ใส่ทุก code พร้อมกัน */
        var ta=document.querySelector("textarea[name=course_no]")||document.getElementById("id_course_no");
        if(ta){
          var qRaw=document.getElementById("csmQ").value.trim();
          var qTerms=qRaw.split("_").map(function(t){return t.trim().toUpperCase();}).filter(function(t){return t.length>0;});
          var fillVal=qTerms.length>1?qTerms.join("_"):cn;
          ta.value=fillVal;
        }
        /* ชื่อวิชา TH */
        var th=document.querySelector("input[name=course_name_thai]")||document.getElementById("id_course_name_thai");
        if(th)th.value=nm;
        /* section */
        var secEl=document.querySelector("select[name=section]")||document.getElementById("id_section");
        if(secEl&&sec){for(var i=0;i<secEl.options.length;i++){if(secEl.options[i].value===sec){secEl.selectedIndex=i;break;}}}
        /* เวลา: "0830-1100" → "08:30" / "11:00" */
        if(tp){
          var parts=tp.split("-");
          function toHHMM(t){t=t.trim();if(t.length===4)return t.slice(0,2)+":"+t.slice(2);return t;}
          var tsEl=document.querySelector("input[name=time_start]")||document.getElementById("id_time_start");
          var teEl=document.querySelector("input[name=time_end]")||document.getElementById("id_time_end");
          if(tsEl&&parts[0])tsEl.value=toHHMM(parts[0]);
          if(teEl&&parts[1])teEl.value=toHHMM(parts[1]);
        }
        /* วันที่เรียน: แปลง day_name_s → tick checkbox
           greedy 2-char ก่อน: TH=4 TU=2 SA=6 SU=7 จากนั้น M=1 W=3 F=5 */
        if(dy){
          var _D2=[["TH","4"],["TU","2"],["SA","6"],["SU","7"]];
          var _D1=[["M","1"],["W","3"],["F","5"]];
          var dayMap=[];var s=dy.toUpperCase();var ci=0;
          while(ci<s.length){
            var matched2=false;
            for(var di=0;di<_D2.length;di++){
              if(s.substr(ci,2)===_D2[di][0]){dayMap.push(_D2[di][1]);ci+=2;matched2=true;break;}
            }
            if(!matched2){
              for(var di=0;di<_D1.length;di++){
                if(s[ci]===_D1[di][0]){dayMap.push(_D1[di][1]);break;}
              }
              ci++;
            }
          }
          document.querySelectorAll("input[name=course_day]").forEach(function(cb){
            cb.checked=dayMap.indexOf(cb.value)!==-1;
          });
        }
        /* อาจารย์ผู้สอน */
        var instrEl=document.querySelector("input[name=instructor]")||document.getElementById("id_instructor");
        if(instrEl&&c.instructor)instrEl.value=c.instructor;
        /* ห้องเรียน — FK dropdown, match by value or text */
        var rmEl=document.querySelector("select[name=room_name]")||document.getElementById("id_room_name");
        if(rmEl&&rm){
          var matched=false;
          var rmUp=rm.trim().toUpperCase();
          for(var i=0;i<rmEl.options.length;i++){
            if(rmEl.options[i].value.toUpperCase()===rmUp||rmEl.options[i].text.toUpperCase().includes(rmUp)){
              rmEl.selectedIndex=i;matched=true;break;
            }
          }
          if(!matched)document.getElementById("csmStat").textContent="⚠ ไม่พบห้อง "+rm+" ใน dropdown";
        }
        csmClose();
      };
      tb.appendChild(tr);
    });
  }
  /* ใช้ cache ถ้ามีแล้ว */
  if(_csmCache[cacheKey]){render(_csmCache[cacheKey]);return;}
  var fd=new FormData();
  fd.append("course_year",year);
  fd.append("course_semester",sem);
  var csrf=document.cookie.split(";").map(function(c){return c.trim();}).filter(function(c){return c.startsWith("csrftoken=");}).map(function(c){return c.split("=")[1];})[0]||"";
  fd.append("csrfmiddlewaretoken",csrf);
  fetch("/admin-api/course-search/",{method:"POST",body:fd,credentials:"same-origin"})
  .then(function(r){return r.json();})
  .then(function(d){
    if(d.error){document.getElementById("csmStat").textContent="⚠ "+d.error;return;}
    var rows=d.courses||[];
    _csmCache[cacheKey]=rows;
    render(rows);
  })
  .catch(function(e){document.getElementById("csmStat").textContent="⚠ เชื่อมต่อไม่ได้: "+e;});
}
document.addEventListener("click",function(e){if(e.target===document.getElementById("csmModal"))csmClose();});
/* ── section เปลี่ยน → ต่อท้าย _section ใน course_no ── */
(function(){
  function _syncSec(){
    var ta=document.querySelector("textarea[name=course_no]")||document.getElementById("id_course_no");
    var se=document.querySelector("select[name=section]")||document.getElementById("id_section");
    if(!ta||!se)return;
    var sec=se.value.trim();
    /* ลบ _Sxx หรือ _section เก่าออกก่อน (ถ้ามี) */
    var raw=ta.value.trim().replace(/_S?[0-9A-Ea-e]$/i,"");
    ta.value=sec?raw+"_S"+sec:raw;
  }
  document.addEventListener("change",function(e){
    var el=e.target;
    if(el&&(el.name==="section"||el.id==="id_section"))_syncSec();
  });
})();
</script>
'''),
    )
    section    = forms.ChoiceField(
        choices=_SECTION_CHOICES,
        required=False,
        label='ตอนเรียน (Section)',
        help_text='เลือก section หรือปล่อยว่างถ้าไม่มี',
    )
    course_day = forms.MultipleChoiceField(
        choices=_DAY_CHOICES_EN,
        label='วันที่เรียน',
        widget=forms.CheckboxSelectMultiple,
        help_text='เลือกได้หลายวัน — ระบบจะสร้างแถวแยกให้อัตโนมัติ',
    )
    time_start = forms.TimeField(
        label='เริ่มเรียน',
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        input_formats=['%H:%M'],
        help_text='รูปแบบ HH:MM เช่น 08:30',
    )
    time_end = forms.TimeField(
        label='สิ้นสุด',
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        input_formats=['%H:%M'],
        help_text='รูปแบบ HH:MM เช่น 17:00',
    )

    class Meta:
        model  = ClassScheduleCenter
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Edit mode → รหัสวิชาเป็น text input เดียว และวันเป็น single choice
        if self.instance and self.instance.pk:
            _orig_help = self.fields['course_no'].help_text
            self.fields['course_no'] = forms.CharField(
                label='รหัสวิชา',
                initial=self.instance.course_no,
                help_text=_orig_help,
            )
            self.fields['course_day'] = forms.ChoiceField(
                choices=_DAY_CHOICES_EN,
                label='วันที่เรียน',
                initial=self.instance.course_day,
            )

    def clean_course_no(self):
        raw = self.cleaned_data.get('course_no', '')
        import re
        # แยกเฉพาะ comma และ newline — _ คงไว้เป็นส่วนหนึ่งของ course_no
        codes = [c.strip().upper() for c in re.split(r'[,\n]+', raw) if c.strip()]
        if not codes:
            raise forms.ValidationError('กรุณากรอกรหัสวิชาอย่างน้อย 1 รหัส')
        self._course_codes = codes
        return codes[0]

    def clean_time_start(self):
        t = self.cleaned_data.get('time_start')
        return t.strftime('%H:%M') if t else ''

    def clean_time_end(self):
        t = self.cleaned_data.get('time_end')
        return t.strftime('%H:%M') if t else ''

    def clean_section(self):
        return self.cleaned_data.get('section', '')

    def clean_course_day(self):
        days = self.cleaned_data.get('course_day', [])
        self._selected_days = days if isinstance(days, list) else [days]
        return self._selected_days[0] if self._selected_days else '1'


# ─── ClassScheduleCenter inline ───────────────────────────────────────────────

class ClassScheduleCenterInlineForm(forms.ModelForm):
    section    = forms.ChoiceField(choices=_SECTION_CHOICES, required=False, label='Section')
    course_day = forms.ChoiceField(choices=_DAY_CHOICES_EN, label='วันที่เรียน')
    time_start = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'), input_formats=['%H:%M'])
    time_end   = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'), input_formats=['%H:%M'])
    instructor = forms.CharField(max_length=255, required=False, label='อาจารย์ผู้สอน')

    class Meta:
        model  = ClassScheduleCenter
        fields = '__all__'

    def clean_time_start(self):
        t = self.cleaned_data.get('time_start')
        return t.strftime('%H:%M') if t else ''

    def clean_time_end(self):
        t = self.cleaned_data.get('time_end')
        return t.strftime('%H:%M') if t else ''

    def clean_section(self):
        return self.cleaned_data.get('section', '')


class ClassScheduleCenterInline(admin.TabularInline):
    model  = ClassScheduleCenter
    form   = ClassScheduleCenterInlineForm
    extra  = 0
    fields = ('course_no', 'section', 'course_name_thai', 'instructor',
              'course_day', 'time_start', 'time_end')
    exclude = ['added_by', 'created_at', 'updated_at']
    ordering = ('time_start',)
    show_change_link = True
    verbose_name = "วิชาในห้องนี้"
    verbose_name_plural = "ตารางวิชาในห้อง"


# ─── ClassroomsAdmin ──────────────────────────────────────────────────────────

class ClassroomsAdmin(admin.ModelAdmin):

    # ── list view ─────────────────────────────────────────
    list_display = (
        'mini_player',        # embedded video (muted, autoplay)
        'room_info',          # name + location in one cell
        'live_badge',         # LIVE / offline badge
        'viewer_count_display',
        'room_status_badge',
        'chat_status_badge',  # เปิด/ปิด chat
        'stream_preview_link',
    )
    list_display_links = ('room_info',)
    list_filter        = ('room_location', 'room_status')
    search_fields      = ('room_name', 'room_stream')
    list_per_page      = 20
    # default ordering handled by get_queryset (live-first, viewer-count-desc)

    # ── change/add view ───────────────────────────────────
    readonly_fields = ('live_status_detail', 'viewer_count_detail', 'live_player_embed')
    fieldsets = (
        ('ข้อมูลห้องเรียน', {
            'fields': ('room_name', 'room_location', 'room_stream',
                       'room_order', 'room_status', 'room_comment'),
        }),
        ('💬 แชทในห้องเรียน', {
            'fields': ('chat_pin',),
            'description': (
                'ตั้งรหัสลับให้อาจารย์พิมพ์เพื่อได้รับ badge "อาจารย์" ในหน้าแชท '
                '(ว่างเปล่า = ปิดฟีเจอร์แชท)'
            ),
        }),
        ('📡 สถานะ Live ปัจจุบัน', {
            'fields': ('live_status_detail', 'viewer_count_detail'),
            'classes': ('collapse',),
            'description': 'ข้อมูลแสดงผลแบบ real-time จากระบบ',
        }),
        ('🎬 ดูสดในหน้า Admin', {
            'fields': ('live_player_embed',),
            'classes': ('collapse',),
        }),
    )
    inlines = [ClassScheduleCenterInline]

    class Media:
        css = {'all': ('live/admin_classrooms.css',)}
        js  = ('live/admin_classrooms.js',)

    # ── smart sort: live-first → viewer-count desc ─────────

    def get_queryset(self, request):
        qs = super(ClassroomsAdmin, self).get_queryset(request)

        # Only apply our custom sort when no column-header sort is active
        if request.GET.get('o'):
            return qs

        live_s = _live_set()
        vmap   = _viewer_map()

        # Sort in Python: (0=live,1=offline) then (-viewers)
        rooms = sorted(
            list(qs),
            key=lambda r: (
                0 if r.room_name.strip().lower() in live_s else 1,
                -vmap.get(r.room_name.strip().lower(), 0),
            )
        )

        if not rooms:
            return qs

        # Preserve the Python-sorted order back into a queryset
        pks = [r.pk for r in rooms]
        preserved = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(pks)],
            output_field=IntegerField()
        )
        return qs.annotate(_sort_order=preserved).order_by('_sort_order')

    # ── list columns ──────────────────────────────────────

    def mini_player(self, obj):
        """Embedded HLS player — muted autoplay, 200×113 px"""
        is_live = obj.room_name.strip().lower() in _live_set()

        if not is_live:
            return mark_safe(
                '<div class="admin-mini-player">'
                '<div class="player-offline">&#9679; ออฟไลน์</div>'
                '</div>'
            )

        server  = _get_server(obj.room_location.id if obj.room_location else 0)
        src     = '{}{}/playlist.m3u8'.format(server, obj.room_name.lower())

        return mark_safe(
            '<div class="admin-mini-player">'
            '<span class="player-live-dot">LIVE</span>'
            '<video data-hlssrc="{src}" muted playsinline preload="none"'
            ' style="width:200px;height:113px;background:#000;border-radius:0 0 6px 6px;">'
            '</video>'
            '</div>'.format(src=src)
        )
    mini_player.short_description = '📺 Preview'
    mini_player.allow_tags = True

    def room_info(self, obj):
        location = obj.room_location.location_name if obj.room_location else '—'
        return mark_safe(
            '<strong style="font-size:0.95rem;">{name}</strong>'
            '<br><span style="color:#64748b;font-size:0.78rem;">{loc}</span>'.format(
                name=obj.room_name,
                loc=location,
            )
        )
    room_info.short_description = 'ห้องเรียน'
    room_info.admin_order_field = 'room_name'

    def live_badge(self, obj):
        is_live = obj.room_name.strip().lower() in _live_set()
        if is_live:
            return mark_safe(
                '<span class="admin-badge badge-live">&#9679; LIVE</span>'
            )
        return mark_safe(
            '<span class="admin-badge badge-offline">&#9675; ออฟไลน์</span>'
        )
    live_badge.short_description = 'Live'

    def viewer_count_display(self, obj):
        count = _viewer_map().get(obj.room_name.strip().lower(), 0)
        if count > 0:
            return mark_safe(
                '<span class="admin-badge badge-viewers">{} คน</span>'.format(count)
            )
        return mark_safe('<span style="color:#94a3b8">—</span>')
    viewer_count_display.short_description = '👥 ผู้ชม'

    def room_status_badge(self, obj):
        if obj.room_status == '1':
            return mark_safe('<span class="admin-badge badge-open">เปิด</span>')
        return mark_safe('<span class="admin-badge badge-closed">ปิด</span>')
    room_status_badge.short_description = 'สถานะ'

    def chat_status_badge(self, obj):
        if obj.chat_pin:
            return mark_safe(
                '<span style="background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;'
                'border-radius:6px;padding:2px 10px;font-size:.78rem;font-weight:600;">'
                '💬 เปิด</span>'
            )
        return mark_safe(
            '<span style="background:#f8fafc;color:#94a3b8;border:1px solid #e2e8f0;'
            'border-radius:6px;padding:2px 10px;font-size:.78rem;">'
            '— ปิด</span>'
        )
    chat_status_badge.short_description = 'แชท'

    def stream_preview_link(self, obj):
        url = '/showSubjectInRoom/{}/'.format(obj.room_name)
        return mark_safe(
            '<a href="{}" target="_blank" class="admin-stream-link">'
            '&#9654; ดูสด</a>'.format(url)
        )
    stream_preview_link.short_description = 'ลิงก์'
    stream_preview_link.allow_tags = True

    # ── detail readonly fields ─────────────────────────────

    def live_status_detail(self, obj):
        is_live = obj.room_name.strip().lower() in _live_set()
        if is_live:
            return mark_safe(
                '<span class="admin-badge badge-live" style="font-size:1rem;padding:6px 16px;">'
                '&#9679; กำลังถ่ายทอดสดอยู่</span>'
            )
        return mark_safe(
            '<span class="admin-badge badge-offline" style="font-size:1rem;padding:6px 16px;">'
            '&#9675; ไม่ได้ถ่ายทอดสดในขณะนี้</span>'
        )
    live_status_detail.short_description = 'สถานะ Live ปัจจุบัน'

    def viewer_count_detail(self, obj):
        count = _viewer_map().get(obj.room_name.strip().lower(), 0)
        return mark_safe(
            '<strong style="font-size:1.4rem;color:#3b82f6">{}</strong>'
            '<span style="color:#64748b;margin-left:6px">คน</span>'.format(count)
        )
    viewer_count_detail.short_description = 'จำนวนผู้ชมขณะนี้'

    def live_player_embed(self, obj):
        if not obj.room_location:
            return '—'
        server  = _get_server(obj.room_location.id)
        src     = '{}{}/playlist.m3u8'.format(server, obj.room_name.lower())
        room_id = obj.room_name.replace(' ', '_').replace('/', '_')
        return mark_safe(
            '<div style="max-width:640px;margin:8px 0;">'
            '<video id="adminVid_{rid}" data-hlssrc="{src}"'
            ' style="width:100%;max-width:640px;height:360px;background:#000;border-radius:8px;"'
            ' controls muted autoplay playsinline></video>'
            '<p style="font-size:0.72rem;color:#64748b;margin-top:4px;">📡 {src}</p>'
            '</div>'.format(rid=room_id, src=src)
        )
    live_player_embed.short_description = 'ดูการถ่ายทอดสด (HLS)'

    # ── save hook ─────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        now = datetime.datetime.now()
        if not obj.pk:
            obj.created_at = str(now)
        obj.updated_at = str(now)
        obj.added_by   = request.user.username
        super(ClassroomsAdmin, self).save_model(request, obj, form, change)


admin.site.register(Classrooms, ClassroomsAdmin)


# ─── LiveClassroom — read-only live monitor ───────────────────────────────────

class LiveClassroomAdmin(admin.ModelAdmin):
    list_display  = ('room_name', 'live_status_badge', 'viewer_count_col',
                     'room_stream', 'updated_at')
    list_filter   = ('room_status',)
    search_fields = ('room_name',)
    list_per_page = 30
    ordering      = ('room_order', 'room_name')

    class Media:
        css = {'all': ('live/admin_classrooms.css',)}

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def live_status_badge(self, obj):
        if obj.room_status == '1':
            return mark_safe(
                '<span class="admin-badge badge-live">&#9679; LIVE</span>'
            )
        return mark_safe(
            '<span class="admin-badge badge-offline">&#9675; ออฟไลน์</span>'
        )
    live_status_badge.short_description = 'สถานะ'

    def viewer_count_col(self, obj):
        count = _viewer_map().get(obj.room_name.strip().lower(), 0)
        if count > 0:
            return mark_safe(
                '<span class="admin-badge badge-viewers">{} คน</span>'.format(count)
            )
        return mark_safe('<span style="color:#94a3b8">—</span>')
    viewer_count_col.short_description = '👥 ผู้ชม'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        vmap          = _viewer_map()
        live_rooms    = LiveClassroom.objects.filter(room_status='1')
        total_viewers = sum(
            vmap.get(r.room_name.strip().lower(), 0) for r in live_rooms
        )
        extra_context['live_count']    = live_rooms.count()
        extra_context['total_viewers'] = total_viewers
        return super(LiveClassroomAdmin, self).changelist_view(
            request, extra_context=extra_context
        )

    change_list_template = 'live/admin_live_monitor_list.html'


admin.site.register(LiveClassroom, LiveClassroomAdmin)


# ─── Count — read-only viewer stats ──────────────────────────────────────────

class CountAdmin(admin.ModelAdmin):
    list_display  = ('room_name', 'sessions_total', 'sessions_cupertino', 'updated')
    search_fields = ('room_name',)
    list_per_page = 30
    ordering      = ('-sessions_total',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Count, CountAdmin)


# ─── ClassScheduleCenter ──────────────────────────────────────────────────────

class ClassCancellationInline(admin.TabularInline):
    model   = ClassCancellation
    extra   = 1
    fields  = ('cancel_date', 'reason', 'created_by')
    readonly_fields = ('created_by',)
    verbose_name        = 'งดบรรยาย'
    verbose_name_plural = 'งดบรรยายวันใดบ้าง'

    def save_new_objects(self, formset, commit=True):
        for form in formset.new_objects:
            form.created_by = formset.request.user.username
        return super().save_new_objects(formset, commit)


class ClassScheduleCenterAdmin(admin.ModelAdmin):
    form          = ClassScheduleCenterForm
    list_display  = ('course_no', 'section', 'course_name_thai', 'instructor',
                     'course_day_display', 'time_start', 'time_end', 'room_name')
    list_per_page = 25
    search_fields = ('course_no', 'section', 'room_name__room_name', 'course_name_thai', 'instructor')
    list_filter   = ('course_day', 'room_name')
    exclude       = ('added_by', 'created_at', 'updated_at')
    readonly_fields = ('closed_status_display',)
    change_list_template = 'admin/classschedulecenter_changelist.html'
    inlines = [ClassCancellationInline]

    def closed_status_display(self, obj):
        if not obj.pk:
            return '-'
        import datetime
        today = datetime.date.today()
        if obj.closed_date and today >= obj.closed_date:
            return mark_safe(
                f'<span style="color:#991b1b;font-weight:700;">🔴 ปิดคอร์สแล้ว ตั้งแต่ {obj.closed_date}</span>'
            )
        if obj.closed_date:
            return mark_safe(
                f'<span style="color:#92400e;">🟡 กำหนดปิด {obj.closed_date}</span>'
            )
        return mark_safe('<span style="color:#166534;">🟢 เปิดสอนปกติ</span>')
    closed_status_display.short_description = 'สถานะคอร์ส'

    def get_urls(self):
        from django.urls import path as _path
        urls = super().get_urls()
        custom = [
            _path('clear-by-room/', self.admin_site.admin_view(self.clear_by_room_view),
                  name='live_classschedulecenter_clear_by_room'),
        ]
        return custom + urls

    def clear_by_room_view(self, request):
        from django.shortcuts import render as _render, redirect as _redirect
        from django.contrib import messages as _messages
        from django.db.models import Count as _Count

        # สร้าง summary ต่อห้อง
        rooms = (
            ClassScheduleCenter.objects
            .values('room_name_id')
            .annotate(row_count=_Count('id'), course_count=_Count('course_no', distinct=True))
            .order_by('room_name_id')
        )

        if request.method == 'POST':
            selected = request.POST.getlist('rooms')
            if not selected:
                _messages.warning(request, 'กรุณาเลือกห้องเรียนอย่างน้อย 1 ห้อง')
            else:
                deleted, _ = ClassScheduleCenter.objects.filter(room_name_id__in=selected).delete()
                _messages.success(request, f'ลบข้อมูลตารางเรียน {deleted} แถว จากห้อง: {", ".join(selected)}')
                return _redirect('../')

        context = {
            **self.admin_site.each_context(request),
            'rooms': list(rooms),
            'opts': self.model._meta,
            'title': 'ลบตารางเรียนตามห้องเรียน',
        }
        return _render(request, 'admin/classschedulecenter_clear_by_room.html', context)

    _DAY_NAMES = dict(_DAY_CHOICES_EN)

    def course_day_display(self, obj):
        return self._DAY_NAMES.get(str(obj.course_day), obj.course_day)
    course_day_display.short_description = 'วันที่เรียน'
    course_day_display.admin_order_field = 'course_day'

    def save_model(self, request, obj, form, change):
        now   = datetime.datetime.now()
        days  = getattr(form, '_selected_days', [form.cleaned_data.get('course_day')])
        codes = getattr(form, '_course_codes',  [obj.course_no])

        if change:
            # Edit mode — บันทึกปกติ
            obj.updated_at = str(now)
            obj.added_by   = request.user.username
            super().save_model(request, obj, form, change)
            return

        # Add mode — วน course_code × วัน → สร้างทุก combination
        created_count = 0
        skipped_count = 0
        for code in codes:
            for day in days:
                _, created = ClassScheduleCenter.objects.get_or_create(
                    course_no  = code,
                    section    = obj.section,
                    room_name  = obj.room_name,
                    course_day = day,
                    time_start = obj.time_start,
                    defaults={
                        'course_name_thai': obj.course_name_thai,
                        'course_name_eng':  obj.course_name_eng,
                        'instructor':       obj.instructor,
                        'time_end':         obj.time_end,
                        'added_by':         request.user.username,
                        'created_at':       str(now),
                        'updated_at':       str(now),
                    }
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        total = len(codes) * len(days)
        msg = f'สร้างตารางเรียน {created_count}/{total} รายการ'
        if len(codes) > 1:
            msg += f' | รหัสวิชา: {", ".join(codes)}'
        msg += f' | วัน: {", ".join(self._DAY_NAMES.get(d, d) for d in days)}'
        if skipped_count:
            msg += f' (ข้าม {skipped_count} รายการที่มีอยู่แล้ว)'
        self.message_user(request, msg)


admin.site.register(ClassScheduleCenter, ClassScheduleCenterAdmin)


@admin.register(ClassCancellation)
class ClassCancellationAdmin(admin.ModelAdmin):
    list_display  = ('schedule', 'cancel_date', 'reason', 'created_by', 'created_at')
    list_filter   = ('cancel_date', 'schedule__room_name')
    search_fields = ('schedule__course_no', 'reason')
    date_hierarchy = 'cancel_date'
    ordering      = ('-cancel_date',)

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user.username
        super().save_model(request, obj, form, change)


# ─── Locations ────────────────────────────────────────────────────────────────

class LocationsAdmin(admin.ModelAdmin):
    ordering = ('id',)


admin.site.register(Locations, LocationsAdmin)


# ─── LogSubjectInRoom ─────────────────────────────────────────────────────────

class CreatedAtFilter(admin.SimpleListFilter):
    """กรองตาม created_at (CharField รูปแบบ 'YYYY-MM-DD ...')"""
    title        = 'ช่วงเวลา'
    parameter_name = 'period'

    def lookups(self, request, model_admin):
        return (
            ('today',   'วันนี้'),
            ('week',    '7 วันล่าสุด'),
            ('month',   'เดือนนี้'),
            ('year',    'ปีนี้'),
        )

    def queryset(self, request, queryset):
        import datetime as dt
        now = dt.datetime.now()
        if self.value() == 'today':
            prefix = now.strftime('%Y-%m-%d')
            return queryset.filter(created_at__startswith=prefix)
        if self.value() == 'week':
            days = [(now - dt.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
            from django.db.models import Q
            q = Q()
            for d in days:
                q |= Q(created_at__startswith=d)
            return queryset.filter(q)
        if self.value() == 'month':
            prefix = now.strftime('%Y-%m')
            return queryset.filter(created_at__startswith=prefix)
        if self.value() == 'year':
            prefix = now.strftime('%Y')
            return queryset.filter(created_at__startswith=prefix)
        return queryset


class LogSubjectInRoomAdmin(admin.ModelAdmin):
    list_display         = ('created_at_fmt', 'course_no', 'room_location', 'user_ip')
    list_per_page        = 50
    ordering             = ('-id',)          # PK มี index -> เร็ว
    list_filter          = (CreatedAtFilter, 'room_location')
    search_fields        = ('course_no', 'user_ip')
    list_select_related  = ('room_location',)
    show_full_result_count = False           # ปิด COUNT(*) ทั้งตาราง

    class Media:
        css = {'all': ('live/admin_classrooms.css',)}

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    # -- เพิ่ม URL: /admin/live/logsubjectinroom/analytics-json/ ---------------
    def get_urls(self):
        from django.urls import path
        urls = super(LogSubjectInRoomAdmin, self).get_urls()
        extra = [
            path(
                'analytics-json/',
                self.admin_site.admin_view(self._analytics_json),
                name='live_log_analytics_json',
            ),
        ]
        return extra + urls

    # -- JSON endpoint: ยิง query ที่นี่ ไม่ให้ block changelist ---------------
    def _analytics_json(self, request):
        import datetime as dt
        from django.http import JsonResponse
        from django.core.cache import cache
        from django.db.models import Count as DjCount, Case, When, IntegerField
        from django.db.models.functions import Substr

        now   = dt.datetime.now()
        today = now.strftime('%Y-%m-%d')
        month = now.strftime('%Y-%m')

        CACHE_KEY = 'log_analytics_{}'.format(today)
        CACHE_TTL = 5 * 60

        if request.GET.get('refresh'):
            cache.delete(CACHE_KEY)

        data = cache.get(CACHE_KEY)

        if data is None:
            base = LogSubjectInRoom.objects.all()

            # Q1: วันนี้ + เดือนนี้ ใน 1 query
            stats = base.filter(
                created_at__startswith=month
            ).aggregate(
                month_count=DjCount('id'),
                today_count=DjCount(Case(
                    When(created_at__startswith=today, then=1),
                    output_field=IntegerField(),
                )),
            )

            # Q2: unique IPs วันนี้
            unique_today = (
                base.filter(created_at__startswith=today)
                .values('user_ip').distinct().count()
            )

            # Q3: trend 7 วัน ใน 1 query (Substr + GROUP BY)
            week_start = (now - dt.timedelta(days=6)).strftime('%Y-%m-%d')
            trend_dict = {
                r['day']: r['cnt']
                for r in (
                    base.filter(created_at__gte=week_start)
                    .annotate(day=Substr('created_at', 1, 10))
                    .values('day')
                    .annotate(cnt=DjCount('id'))
                )
            }
            daily_trend = []
            max_v = 1
            for i in range(6, -1, -1):
                d   = (now - dt.timedelta(days=i)).strftime('%Y-%m-%d')
                cnt = trend_dict.get(d, 0)
                daily_trend.append({'date': d[5:], 'count': cnt})
                if cnt > max_v:
                    max_v = cnt
            for item in daily_trend:
                item['pct'] = int(item['count'] * 100 / max_v)

            # Q4: top 10 วิชา เดือนนี้
            top_courses = list(
                base.filter(created_at__startswith=month)
                .values('course_no')
                .annotate(visits=DjCount('id'))
                .order_by('-visits')[:10]
            )
            if top_courses:
                mc = top_courses[0]['visits'] or 1
                for item in top_courses:
                    item['pct'] = int(item['visits'] * 100 / mc)

            # Q5: top 5 สถานที่ เดือนนี้
            top_locations = list(
                base.filter(created_at__startswith=month)
                .values('room_location__location_name')
                .annotate(visits=DjCount('id'))
                .order_by('-visits')[:5]
            )

            data = {
                'today_count'  : stats['today_count']  or 0,
                'month_count'  : stats['month_count']  or 0,
                'unique_today' : unique_today,
                'top_courses'  : top_courses,
                'top_locations': top_locations,
                'daily_trend'  : daily_trend,
                'month_label'  : now.strftime('%B %Y'),
                'today_label'  : today,
                'cached'       : False,
            }
            cache.set(CACHE_KEY, data, CACHE_TTL)
        else:
            data = dict(data)
            data['cached'] = True

        return JsonResponse(data)

    # -- changelist: ไม่ยิง query analytics เลย -- โหลดเร็วทันที -------------
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['analytics_json_url'] = 'analytics-json/'
        return super(LogSubjectInRoomAdmin, self).changelist_view(
            request, extra_context=extra_context
        )

    def created_at_fmt(self, obj):
        val = str(obj.created_at or '').strip()
        return val[:19] if len(val) >= 19 else val
    created_at_fmt.short_description = 'เวลา'
    created_at_fmt.admin_order_field = 'id'

    change_list_template = 'live/admin_log_analytics.html'


admin.site.register(LogSubjectInRoom, LogSubjectInRoomAdmin)


# ─── ChatMessage ──────────────────────────────────────────────────────────────

class ChatMessageAdmin(admin.ModelAdmin):
    list_display    = ('created_at_fmt', 'room', 'course_badge', 'sender_badge', 'message_bubble', 'profanity_badge', 'sender_ip')
    list_filter     = ('is_teacher', 'room')
    search_fields   = ('sender', 'message', 'room__room_name', 'sender_ip')
    ordering        = ('-created_at',)
    list_per_page   = 50
    readonly_fields = ('room', 'sender', 'is_teacher', 'message_full', 'message_raw_display', 'created_at', 'sender_ip')
    date_hierarchy  = 'created_at'
    list_select_related = ('room',)

    class Media:
        css = {'all': ('live/admin_classrooms.css',)}

    def has_add_permission(self, request):
        return False

    def course_badge(self, obj):
        if obj.active_course:
            return mark_safe(
                '<span style="background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe;'
                'border-radius:6px;padding:2px 8px;font-size:.78rem;font-weight:600;">'
                '{}</span>'.format(obj.active_course)
            )
        return mark_safe('<span style="color:#9ca3af;font-size:.78rem;">—</span>')
    course_badge.short_description = 'วิชา'
    course_badge.admin_order_field = 'active_course'

    def created_at_fmt(self, obj):
        from django.conf import settings
        from django.utils.timezone import localtime
        dt = obj.created_at
        if getattr(settings, 'USE_TZ', True) and dt.tzinfo:
            dt = localtime(dt)
        return dt.strftime('%d/%m %H:%M')
    created_at_fmt.short_description = 'เวลา'
    created_at_fmt.admin_order_field = 'created_at'

    def sender_badge(self, obj):
        from django.utils.html import escape
        name = escape(obj.sender)
        if obj.is_teacher:
            return mark_safe(
                '<span style="display:inline-flex;align-items:center;gap:4px;'
                'background:#fef3c7;color:#92400e;border:1px solid #fbbf24;'
                'border-radius:20px;padding:2px 10px;font-size:.8rem;font-weight:600;">'
                '&#9733; {}</span>'.format(name)
            )
        return mark_safe(
            '<span style="display:inline-flex;align-items:center;gap:4px;'
            'background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe;'
            'border-radius:20px;padding:2px 10px;font-size:.8rem;">'
            '&#128100; {}</span>'.format(name)
        )
    sender_badge.short_description = 'ผู้ส่ง'

    def message_bubble(self, obj):
        from django.utils.html import escape
        text = escape(obj.message[:150])
        if obj.is_teacher:
            bg, border, color = '#fffbeb', '#fde68a', '#78350f'
        else:
            bg, border, color = '#f8faff', '#dbeafe', '#1e3a5f'
        return mark_safe(
            '<span style="display:inline-block;background:{};border:1px solid {};'
            'color:{};border-radius:10px;padding:4px 12px;font-size:.85rem;'
            'max-width:420px;word-break:break-word;">{}</span>'.format(
                bg, border, color, text)
        )
    message_bubble.short_description = 'ข้อความ'

    def message_full(self, obj):
        from django.utils.html import escape
        return mark_safe(
            '<div style="background:#f8faff;border:1px solid #dbeafe;border-radius:10px;'
            'padding:12px 16px;font-size:.95rem;white-space:pre-wrap;">{}</div>'.format(
                escape(obj.message))
        )
    message_full.short_description = 'ข้อความ (แสดงผล)'

    def message_raw_display(self, obj):
        from django.utils.html import escape
        if not obj.message_raw:
            return mark_safe('<span style="color:#9ca3af;">—</span>')
        return mark_safe(
            '<div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:10px;'
            'padding:12px 16px;font-size:.95rem;white-space:pre-wrap;color:#be123c;">{}</div>'.format(
                escape(obj.message_raw))
        )
    message_raw_display.short_description = 'ข้อความต้นฉบับ (มีคำหยาบ)'

    def profanity_badge(self, obj):
        if obj.message_raw:
            return mark_safe(
                '<span style="background:#fff1f2;color:#be123c;border:1px solid #fecdd3;'
                'border-radius:6px;padding:2px 8px;font-size:.75rem;font-weight:600;">⚠ มีคำหยาบ</span>'
            )
        return ''
    profanity_badge.short_description = ''

    def get_fields(self, request, obj=None):
        return ('room', 'sender', 'is_teacher', 'message_full', 'message_raw_display', 'created_at', 'sender_ip')

    actions = ['clear_room_chat']

    def clear_room_chat(self, request, queryset):
        rooms = set(queryset.values_list('room_id', flat=True))
        deleted, _ = ChatMessage.objects.filter(room_id__in=rooms).delete()
        self.message_user(request, 'ลบข้อความ {} รายการจาก {} ห้อง'.format(deleted, len(rooms)))
    clear_room_chat.short_description = 'ลบข้อความแชทในห้องที่เลือกทั้งหมด'


admin.site.register(ChatMessage, ChatMessageAdmin)


# ─── BannedStudent ────────────────────────────────────────────────────────────

class BannedStudentAdmin(admin.ModelAdmin):
    list_display    = ('std_code', 'banned_at_fmt', 'ban_reason_short')
    search_fields   = ('std_code', 'ban_reason')
    ordering        = ('-banned_at',)
    readonly_fields = ('banned_at',)
    list_per_page   = 50
    actions         = ['unban_selected']

    def banned_at_fmt(self, obj):
        return obj.banned_at.strftime('%d/%m/%Y %H:%M')
    banned_at_fmt.short_description = 'เวลาที่ถูก ban'
    banned_at_fmt.admin_order_field = 'banned_at'

    def ban_reason_short(self, obj):
        return obj.ban_reason[:80] + ('…' if len(obj.ban_reason) > 80 else '')
    ban_reason_short.short_description = 'เหตุผล'

    def unban_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, 'ปลดแบน {} รหัสนักศึกษา เรียบร้อยแล้ว'.format(count))
    unban_selected.short_description = 'ปลดแบน (unban) รหัสที่เลือก'


admin.site.register(BannedStudent, BannedStudentAdmin)


# ─── HolidayDate (ประกาศ / แบนเนอร์) ─────────────────────────────────────────

class HolidayDateAdmin(admin.ModelAdmin):
    list_display   = ('type_badge', 'date_range_fmt', 'name', 'note', 'status_badge')
    search_fields  = ('name', 'note')
    ordering       = ('date_start',)
    list_per_page  = 50
    date_hierarchy = 'date_start'
    list_filter    = ('banner_type',)

    class Media:
        js = ('live/admin_datepicker_th.js', 'live/admin_course_search.js')

    fieldsets = (
        ('📋 ข้อมูลประกาศ', {
            'fields': ('banner_type', 'name', 'note'),
        }),
        ('📅 ช่วงเวลา', {
            'fields': ('date_start', 'date_end'),
            'description': 'ถ้าเป็นวันเดียวให้ใส่วันเดียวกันทั้งสองช่อง',
        }),
    )

    # สี/ไอคอนตามประเภท
    _TYPE_STYLE = {
        'holiday':  ('🎌', '#78350f', '#fef3c7', '#fbbf24'),
        'semester': ('🎓', '#4c1d95', '#f3e8ff', '#c4b5fd'),
        'maintain': ('🔧', '#78350f', '#fffbeb', '#fcd34d'),
        'general':  ('📢', '#1e3a8a', '#eff6ff', '#93c5fd'),
    }

    def type_badge(self, obj):
        icon, color, bg, border = self._TYPE_STYLE.get(
            obj.banner_type, ('📢', '#1e3a8a', '#eff6ff', '#93c5fd'))
        label = obj.get_banner_type_display()
        return mark_safe(
            f'<span style="background:{bg};color:{color};border:1px solid {border};'
            f'border-radius:6px;padding:2px 10px;font-size:.78rem;font-weight:600;">'
            f'{label}</span>'
        )
    type_badge.short_description = 'ประเภท'

    def date_range_fmt(self, obj):
        if obj.date_start == obj.date_end:
            return obj.date_start.strftime('%d/%m/%Y')
        return f'{obj.date_start.strftime("%d/%m/%Y")} – {obj.date_end.strftime("%d/%m/%Y")}'
    date_range_fmt.short_description = 'ช่วงเวลา'
    date_range_fmt.admin_order_field = 'date_start'

    def status_badge(self, obj):
        from datetime import date
        today = date.today()
        if obj.date_start <= today <= obj.date_end:
            return mark_safe(
                '<span style="background:#fef3c7;color:#92400e;border:1px solid #fbbf24;'
                'border-radius:6px;padding:2px 10px;font-size:.78rem;font-weight:700;">'
                '⚡ แสดงอยู่</span>'
            )
        if obj.date_end < today:
            return mark_safe('<span style="color:#94a3b8;font-size:.78rem;">ผ่านแล้ว</span>')
        return mark_safe(
            '<span style="background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;'
            'border-radius:6px;padding:2px 10px;font-size:.78rem;">กำลังจะมาถึง</span>'
        )
    status_badge.short_description = 'สถานะ'


admin.site.register(HolidayDate, HolidayDateAdmin)
