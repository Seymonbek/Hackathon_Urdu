from datetime import datetime, time
from typing import Dict, List, Optional, Any


# UrDU va OTM standart para vaqtlari (juftliklar)
PARA_SLOTS = {
    1: ("08:30", "10:00"),
    2: ("10:10", "11:40"),
    3: ("12:00", "13:30"),
    4: ("13:40", "15:10"),
    5: ("15:30", "17:00"),
}


def time_to_minutes(t_str: str) -> int:
    try:
        parts = t_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0


def has_time_conflict(
    student_schedule: Dict[str, Any],
    day_name: str,
    job_start: Optional[str],
    job_end: Optional[str],
    buffer_min: int = 45,
) -> bool:
    """
    Talabaning dars soatlari va vakansiya vaqti o'rtasida to'qnashuv borligini tekshiradi.
    To'qnashuv bo'lsa True, bo'sh bo'lsa False qaytaradi.
    """
    if not job_start or not job_end:
        return False  # Erkin grafik yoki masofaviy bo'lsa to'qnashuv yo'q

    if isinstance(student_schedule, str):
        try:
            import json
            student_schedule = json.loads(student_schedule)
        except Exception:
            student_schedule = {}
    elif not isinstance(student_schedule, dict):
        student_schedule = {}

    day_key = day_name.lower()[:3]  # mon, tue, wed...
    busy_list = student_schedule.get(day_key, [])
    if not busy_list:
        return False  # Shu kuni talaba butunlay bo'sh

    j_start = time_to_minutes(job_start) - buffer_min
    j_end = time_to_minutes(job_end) + buffer_min

    for item in busy_list:
        # Item para raqami (masalan 1, 2) yoki vaqt oraliq ("10:00-11:30") bo'lishi mumkin
        if isinstance(item, int) and item in PARA_SLOTS:
            b_start_str, b_end_str = PARA_SLOTS[item]
            b_start = time_to_minutes(b_start_str)
            b_end = time_to_minutes(b_end_str)
        elif isinstance(item, str) and "-" in item:
            parts = item.split("-")
            b_start = time_to_minutes(parts[0])
            b_end = time_to_minutes(parts[1])
        else:
            continue

        # Oraliqlar kesishishini tekshirish: max(start1, start2) < min(end1, end2)
        if max(j_start, b_start) < min(j_end, b_end):
            return True  # Qat'iy to'qnashuv topildi!

    return False
