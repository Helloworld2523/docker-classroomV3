/**
 * เปลี่ยนชื่อเดือน/วันใน Django admin calendar เป็นภาษาไทย
 */
(function waitForCalendar() {
    if (typeof CalendarNamespace === 'undefined') {
        setTimeout(waitForCalendar, 100);
        return;
    }

    CalendarNamespace.month_names = [
        'มกราคม','กุมภาพันธ์','มีนาคม','เมษายน',
        'พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม',
        'กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'
    ];
    CalendarNamespace.month_names_abbr = [
        'ม.ค.','ก.พ.','มี.ค.','เม.ย.',
        'พ.ค.','มิ.ย.','ก.ค.','ส.ค.',
        'ก.ย.','ต.ค.','พ.ย.','ธ.ค.'
    ];
    CalendarNamespace.day_names_abbr = [
        'อา','จ','อ','พ','พฤ','ศ','ส'
    ];
})();
