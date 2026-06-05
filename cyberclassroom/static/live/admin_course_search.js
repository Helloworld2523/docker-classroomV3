/**
 * Course Search Popup สำหรับ Admin — ClassScheduleCenter
 */

var _CSM = {
    SEARCH_URL: '/admin-api/course-search/',
    modal: null,
    input: null,
    tbody: null,
    statusEl: null,
};

function csmOpenModal() {
    _csmBuildModal();
    _CSM.modal.style.display = 'flex';
    _CSM.input.value = '';
    _CSM.tbody.innerHTML = '';
    _CSM.statusEl.textContent = '';
    _csmFetch('');
    setTimeout(function () { _CSM.input.focus(); }, 100);
}

function _csmCloseModal() {
    if (_CSM.modal) _CSM.modal.style.display = 'none';
}

function _csmBuildModal() {
    if (document.getElementById('courseSearchModal')) return;

    var m = document.createElement('div');
    m.id = 'courseSearchModal';
    m.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:99999;align-items:center;justify-content:center;';
    m.innerHTML = [
        '<div style="background:#fff;border-radius:12px;width:90%;max-width:680px;max-height:80vh;display:flex;flex-direction:column;box-shadow:0 8px 40px rgba(0,0,0,0.25);overflow:hidden;">',
          '<div style="background:#1d4ed8;color:#fff;padding:1rem 1.25rem;display:flex;align-items:center;justify-content:space-between;">',
            '<span style="font-weight:700;font-size:1rem;">🔍 ค้นหารายวิชาจาก RU</span>',
            '<button id="csmCloseBtn" style="background:none;border:none;color:#fff;font-size:1.4rem;cursor:pointer;line-height:1;">×</button>',
          '</div>',
          '<div style="padding:0.85rem 1.25rem;border-bottom:1px solid #e5e7eb;">',
            '<input id="csmSearchInput" type="text" placeholder="พิมพ์รหัสหรือชื่อวิชา..." style="width:100%;padding:0.5rem 0.75rem;border:1px solid #d1d5db;border-radius:8px;font-size:0.9rem;outline:none;box-sizing:border-box;">',
            '<div id="csmStatus" style="font-size:0.78rem;color:#6b7280;margin-top:0.4rem;"></div>',
          '</div>',
          '<div style="overflow-y:auto;flex:1;">',
            '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">',
              '<thead><tr style="background:#f9fafb;position:sticky;top:0;">',
                '<th style="padding:0.6rem 1rem;text-align:left;border-bottom:1px solid #e5e7eb;">รหัสวิชา</th>',
                '<th style="padding:0.6rem 1rem;text-align:left;border-bottom:1px solid #e5e7eb;">ชื่อวิชา</th>',
                '<th style="padding:0.6rem 0.75rem;text-align:center;border-bottom:1px solid #e5e7eb;">Sec</th>',
                '<th style="padding:0.6rem 0.75rem;text-align:center;border-bottom:1px solid #e5e7eb;">หน่วยกิต</th>',
                '<th style="padding:0.6rem 0.75rem;border-bottom:1px solid #e5e7eb;"></th>',
              '</tr></thead>',
              '<tbody id="csmTbody"></tbody>',
            '</table>',
          '</div>',
        '</div>',
    ].join('');

    document.body.appendChild(m);
    _CSM.modal   = m;
    _CSM.input   = document.getElementById('csmSearchInput');
    _CSM.tbody   = document.getElementById('csmTbody');
    _CSM.statusEl = document.getElementById('csmStatus');

    document.getElementById('csmCloseBtn').onclick = _csmCloseModal;
    m.onclick = function (e) { if (e.target === m) _csmCloseModal(); };

    var timer;
    _CSM.input.addEventListener('input', function () {
        clearTimeout(timer);
        timer = setTimeout(function () { _csmFetch(_CSM.input.value.trim()); }, 350);
    });
}

function _csmFetch(q) {
    _CSM.statusEl.textContent = 'กำลังโหลด...';
    _CSM.tbody.innerHTML = '';
    var url = _CSM.SEARCH_URL + (q ? '?q=' + encodeURIComponent(q) : '');
    fetch(url, { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.error) { _CSM.statusEl.textContent = '⚠ ' + data.error; return; }
            _csmRender(data.courses || []);
            _CSM.statusEl.textContent = 'พบ ' + (data.courses || []).length + ' รายการ';
        })
        .catch(function () { _CSM.statusEl.textContent = '⚠ เชื่อมต่อไม่ได้'; });
}

function _csmRender(courses) {
    _CSM.tbody.innerHTML = '';
    if (!courses.length) {
        _CSM.tbody.innerHTML = '<tr><td colspan="5" style="padding:1.5rem;text-align:center;color:#9ca3af;">ไม่พบรายวิชา</td></tr>';
        return;
    }
    courses.forEach(function (c) {
        var tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #f3f4f6';
        tr.onmouseover = function () { tr.style.background = '#eff6ff'; };
        tr.onmouseout  = function () { tr.style.background = ''; };
        tr.innerHTML = [
            '<td style="padding:0.55rem 1rem;font-weight:600;color:#1e3a8a;">' + _csmEsc(c.course_no) + '</td>',
            '<td style="padding:0.55rem 1rem;">' + _csmEsc(c.course_name) + '</td>',
            '<td style="padding:0.55rem 0.75rem;text-align:center;">' + _csmEsc(c.section) + '</td>',
            '<td style="padding:0.55rem 0.75rem;text-align:center;">' + _csmEsc(c.credit) + '</td>',
            '<td style="padding:0.55rem 0.75rem;text-align:center;"><button type="button" style="background:#1d4ed8;color:#fff;border:none;border-radius:6px;padding:0.3rem 0.75rem;font-size:0.8rem;cursor:pointer;">โหลด</button></td>',
        ].join('');
        tr.querySelector('button').onclick = function () { _csmSelect(c); };
        _CSM.tbody.appendChild(tr);
    });
}

function _csmSelect(c) {
    var noField = document.querySelector('textarea[name="course_no"]') || document.querySelector('#id_course_no');
    if (noField) {
        var cur = noField.value.trim();
        noField.value = cur ? cur + ', ' + c.course_no : c.course_no;
    }
    var thField = document.querySelector('input[name="course_name_thai"]') || document.querySelector('#id_course_name_thai');
    if (thField && (!thField.value || thField.value === '-')) {
        thField.value = c.course_name;
    }
    var secField = document.querySelector('select[name="section"]') || document.querySelector('#id_section');
    if (secField && c.section) {
        for (var i = 0; i < secField.options.length; i++) {
            if (secField.options[i].value === c.section) { secField.selectedIndex = i; break; }
        }
    }
    _csmCloseModal();
}

function _csmEsc(s) {
    var d = document.createElement('div');
    d.textContent = String(s || '');
    return d.innerHTML;
}
