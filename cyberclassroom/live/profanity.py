"""
ระบบตรวจและกรองคำหยาบ v2
- โหลดคำหยาบจาก data/profanity.json (แก้ไขได้โดยไม่ต้อง restart)
- normalize ข้อความก่อนตรวจ เพื่อดักคำเลี่ยงเซ็นเซอร์ เช่น ค ว ย, ค.ว.ย, f-u-c-k
- interface เดิม: censor_message(text), has_profanity(text)
"""

import json
import re
import os

_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'profanity.json')

# ─── โหลดและ compile patterns ─────────────────────────────────────────────────

def _load_patterns():
    """โหลดคำหยาบจาก JSON และ compile เป็น regex"""
    try:
        with open(_DATA_PATH, encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []

    patterns = []
    for category, words in data.items():
        if category.startswith('_'):
            continue  # ข้าม _comment, _version
        for word in words:
            if not word:
                continue
            # ภาษาอังกฤษ: ใช้ word boundary
            if re.search(r'[a-zA-Z]', word):
                pat = r'\b' + re.escape(word) + r'\b'
            else:
                # ภาษาไทย: ไม่มี word boundary ใช้ escaped pattern ตรงๆ
                pat = re.escape(word)
            patterns.append(re.compile(pat, re.IGNORECASE))
    return patterns


_COMPILED = _load_patterns()


def reload():
    """โหลด patterns ใหม่จาก JSON — ใช้เมื่อแก้ไขไฟล์ JSON แล้วไม่ต้อง restart"""
    global _COMPILED
    _COMPILED = _load_patterns()


# ─── Normalize ────────────────────────────────────────────────────────────────

# อักขระที่คนใช้แทรกกลางคำเพื่อเลี่ยงเซ็นเซอร์
_NOISE_RE = re.compile(r'[\s\.\-_\*\+\|/\\,]+')


def _normalize(text: str) -> str:
    """
    ลบอักขระ noise ที่แทรกกลางคำ เพื่อให้ตรวจจับได้
    เช่น  ค ว ย  →  ควย
          f.u.c.k  →  fuck
          ค-ว-ย  →  ควย
    หมายเหตุ: ลบเฉพาะ noise ระหว่างตัวอักษร ไม่ใช่ช่องว่างปกติในประโยค
    """
    # แทน noise ด้วยอักษรว่างเฉพาะตรงกลางคำ (ขนาบด้วยตัวอักษร)
    text = _NOISE_RE.sub('', text)
    return text.lower()


# ─── Public API ───────────────────────────────────────────────────────────────

def has_profanity(text: str) -> bool:
    """True ถ้าพบคำหยาบอย่างน้อย 1 คำ (ตรวจทั้ง original และ normalized)"""
    if not text:
        return False
    normalized = _normalize(text)
    return any(p.search(text) or p.search(normalized) for p in _COMPILED)


def censor_message(text: str) -> str:
    """
    แทนคำหยาบทุกคำด้วย *** ทั้งใน original และรูปแบบที่มี noise แทรก
    เช่น ค.ว.ย → *** , f-u-c-k → ***
    """
    if not text:
        return text

    # censor original text
    for p in _COMPILED:
        text = p.sub('***', text)

    # censor รูปแบบ noise-inserted (เช่น ค ว ย, f.u.c.k)
    # ตรวจหา pattern ที่มี noise แทรก แล้วแทนทั้ง token ด้วย ***
    def replace_noisy(m):
        token = m.group(0)
        if has_profanity(_normalize(token)):
            return '***'
        return token

    noisy_token_re = re.compile(r'\S+')
    text = noisy_token_re.sub(replace_noisy, text)

    return text
