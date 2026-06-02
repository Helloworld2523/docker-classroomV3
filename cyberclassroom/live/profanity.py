"""
ตรวจจับและกรองคำหยาบภาษาไทย/อังกฤษ
- censor_message(text) → ข้อความที่แทนคำหยาบด้วย ***
- has_profanity(text)  → True ถ้าพบคำหยาบ
"""

import re

# ─── รายการคำหยาบ ──────────────────────────────────────────────────────────────
# แต่ละรายการคือ regex pattern (ไม่ต้องใส่ \b เพราะภาษาไทยไม่มี word boundary)
_PATTERNS = [
    # ─── ไทย ───────────────────────────────────────────────────────────────────
    r'ควย',
    r'ควาย',
    r'หี',
    r'สัตว์',        # ใช้ด่ากัน เช่น "แม่งสัตว์"
    r'เย็ด',
    r'เหี้ย',
    r'ไอ้เหี้ย',
    r'มึง',
    r'กู',
    r'แม่ง',
    r'ไอ้สัตว์',
    r'อีสัตว์',
    r'ระยำ',
    r'ชาติชั่ว',
    r'อีดอก',
    r'อีหน้าหี',
    r'หน้าหี',
    r'ไอ้บ้า',
    r'อีบ้า',
    r'ไอ้โง่',
    r'อีโง่',
    r'ไอ้ควาย',
    r'อีควาย',
    r'ตอแหล',
    # ─── อังกฤษ ────────────────────────────────────────────────────────────────
    r'\bfuck\b',
    r'\bshit\b',
    r'\bass\b',
    r'\bbitch\b',
    r'\bcunt\b',
    r'\bdick\b',
    r'\bpussy\b',
    r'\bwhore\b',
    r'\bfucker\b',
    r'\bfucking\b',
    r'\bbullshit\b',
    r'\bwtf\b',
]

# compile ครั้งเดียวตอน import
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def censor_message(text: str) -> str:
    """แทนคำหยาบทุกคำด้วย *** แล้ว return ข้อความที่กรองแล้ว"""
    for pattern in _COMPILED:
        text = pattern.sub('***', text)
    return text


def has_profanity(text: str) -> bool:
    """True ถ้าพบคำหยาบอย่างน้อย 1 คำ"""
    return any(p.search(text) for p in _COMPILED)
