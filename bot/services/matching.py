from typing import Dict, Any, Tuple, List, Optional
from datetime import date
from bot.services.geo import calculate_distance
from bot.services.schedule import has_time_conflict


# 1. MUTAXASSISLIK VA SOHA KLASTERLARI (SEMANTIC TAXONOMY)
MAJOR_CLUSTERS = {
    "it": [
        "it", "dastur", "komp", "software", "dasturchi", "axborot", "kiber",
        "web", "veb", "frontend", "backend", "fullstack", "python", "java",
        "sun'iy intellekt", "ai", "data", "ma'lumot", "tizim", "developer", "informatika", "computer"
    ],
    "law": [
        "yurid", "huquq", "advokat", "sud", "adliya", "prokuror", "tergov",
        "qonun", "kriminologiya", "davlat va huquq", "xalqaro huquq", "notariat", "law"
    ],
    "medical": [
        "davo", "tibb", "shifo", "pediatr", "hamshira", "stomatolog", "tish",
        "farmats", "dorishunos", "klinika", "vrach", "terapevt", "akusher", "tibbiy"
    ],
    "finance": [
        "iqtisod", "moliya", "bank", "buxgalter", "audit", "soliq", "menej",
        "marketing", "biznes", "savdo", "logistika", "invest", "hisob", "finance", "kassa"
    ],
    "languages": [
        "filolog", "til", "ingliz", "rus", "arab", "nemis", "fransuz", "turk",
        "xitoy", "koreys", "tarjima", "lingvist", "adabiyot", "o'zbek tili", "english"
    ],
    "pedagogy": [
        "pedagog", "o'qituvchi", "maktab", "boshlang'ich", "bog'cha", "tarbiya",
        "metodist", "ta'lim", "psixolog", "matematika", "fizika", "tarix", "biologiya", "kimyo"
    ],
    "media": [
        "smm", "jurnalist", "media", "dizayn", "design", "grafik", "video",
        "montaj", "kopirayt", "pr", "fotograf", "kontent"
    ],
    "general": [
        "umumiy", "barchasi", "har qanday", "ixtiyoriy", "all", "barcha", "talaba", "xizmat ko'rsatish"
    ]
}


def get_clusters_for_text(text: str) -> set:
    """Matn yoki mutaxassislik nomi qaysi klasterlarga tegishli ekanligini aniqlaydi."""
    found = set()
    t_clean = text.lower().strip()
    if not t_clean:
        return found

    for cluster_name, keywords in MAJOR_CLUSTERS.items():
        if any(kw in t_clean for kw in keywords):
            found.add(cluster_name)
    return found


def match_major_compatibility(student_major: str, target_majors: List[str], job_category: str) -> Tuple[bool, float, str]:
    """
    Talaba mutaxassisligi va vakansiya talabi o'rtasidagi moslikni tekshiradi.
    Qaytaradi: (is_matched: bool, score: float, reason: str)
    """
    s_maj = (student_major or "").lower().strip()
    
    # 1. Agar vakansiya barcha talabalarga ochiq bo'lsa
    if not target_majors or any(g in " ".join(target_majors).lower() for g in ["umumiy", "barcha", "har qanday", "ixtiyoriy", "all"]):
        return True, 25.0, "🎯 Barcha talabalar uchun ochiq vakansiya (+25)"

    # 2. To'g'ridan-to'g'ri so'z va matn mosligi (Exact or substring)
    clean_targets = [t.lower().strip() for t in target_majors if t]
    for tm in clean_targets:
        if tm in s_maj or s_maj in tm:
            return True, 25.0, "🎯 OTM mutaxassisligingizga to'g'ridan-to'g'ri mos (+25)"

    # 3. Semantik klasterlar mosligi
    student_clusters = get_clusters_for_text(s_maj)
    job_text = " ".join(clean_targets) + " " + (job_category or "")
    job_clusters = get_clusters_for_text(job_text)

    # Agar "general" bo'lsa yoki klasterlar kesishsa
    shared = student_clusters.intersection(job_clusters)
    if shared:
        return True, 25.0, "🎯 Yo'nalishingiz va sohangizga klaster bo'yicha to'liq mos (+25)"

    # 4. Mos kelmagan holatda boshlang'ich 10 ball
    return False, 10.0, "💡 Qiziqish doirangizga mos qo'shimcha soha (+10)"


def is_night_job(job: Dict[str, Any]) -> bool:
    """Ish tungi smenaga to'g'ri kelishini tekshiradi (21:00 dan keyin)."""
    if job.get("is_night_shift"):
        return True
    if str(job.get("work_format", "")) in ["hospital_night_shift", "night_shift"]:
        return True

    start_time = str(job.get("start_time") or "")
    end_time = str(job.get("end_time") or "")
    
    for t in [start_time, end_time]:
        if t and any(h in t for h in ["21:", "22:", "23:", "00:", "01:", "02:", "03:", "04:", "05:"]):
            return True
    return False


def calculate_match_score(student: Dict[str, Any], job: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Talaba va vakansiya/amaliyot mosligini 'Oltin Uchburchak' (3 ta vektor) asosida hisoblaydi:
      1. Mutaxassislik va Qiziqishlar (35 ball)
      2. Lokatsiya va Masofa (25 ball)
      3. Dars jadvali va Bo'sh vaqt (25 ball)
      + Imtiyoz: Kontrakt to'lovi / Davlat amaliyoti sertifikati (15 ball)
    Jami: 0 - 100 ball.
    """
    reasons: List[str] = []

    # ==========================================
    # 1. QATTIQ FILTRLAR (HARD FILTERS)
    # ==========================================

    # Status tekshiruvi
    if job.get("status") != "open":
        return False, 0.0, ["Vakansiya ochiq emas"]

    # Sessiya / Imtihon pauza rejimi tekshiruvi
    today = date.today()
    exam_from = student.get("exam_from")
    exam_to = student.get("exam_to")
    if exam_from and exam_to:
        try:
            if isinstance(exam_from, str):
                exam_from = date.fromisoformat(exam_from)
            if isinstance(exam_to, str):
                exam_to = date.fromisoformat(exam_to)
            if exam_from <= today <= exam_to:
                return False, 0.0, ["Talabada sessiya/imtihon pauzasi yoqilgan"]
        except Exception:
            pass

    # 1. YOSH HIMOYASI (O'zbekiston Mehnat kodeksi 411-moddasi)
    # 18 yoshgacha bo'lgan talabalarga tungi ishlar va 18+ talab qilingan ishlar qat'iyan taqiqlanadi
    student_age = student.get("age", 19)
    if student.get("course", 1) == 1 and student.get("is_underage"):
        student_age = 17

    min_age = job.get("min_age", 16)
    night_shift = is_night_job(job)

    if student_age < 18 and (night_shift or min_age >= 18):
        return False, 0.0, ["18 yoshgacha bo'lgan talabalarga tungi va 18+ ishlar qonunan taqiqlangan"]

    # Kurs talabi
    min_course = job.get("min_course_required", 1)
    if student.get("course", 1) < min_course:
        return False, 0.0, [f"Minimal {min_course}-kurs talab etiladi"]

    # GPA talabi (Kontrakt to'lab beriladigan grantlar uchun)
    min_gpa = float(job.get("min_gpa_required") or 0.0)
    student_gpa = float(student.get("gpa_score") or 0.0)
    if min_gpa > 0.0 and student_gpa < min_gpa:
        return False, 0.0, [f"Minimal GPA {min_gpa} talab etiladi (Sizda: {student_gpa})"]

    # Masofa va lokatsiya tekshiruvi
    work_format = job.get("work_format", "offline_shift")
    is_remote = (work_format == "remote_task")
    dist_km = 0.0

    if not is_remote:
        dist_km = calculate_distance(
            student.get("location_lat"), student.get("location_lon"),
            job.get("lat"), job.get("lon")
        )
        max_dist = float(student.get("max_distance_km") or 5.0)
        # Agar talaba va ish koordinatasi mavjud bo'lsa va shahar/viloyatdan tashqarida bo'lsa (> 35 km)
        if student.get("location_lat") and job.get("lat") and dist_km > 35.0:
            return False, 0.0, [f"Boshqa viloyat/shaharda joylashgan ({dist_km:.1f} km)"]

    # Dars jadvali to'qnashuvi
    if not is_remote:
        day_name = "mon"
        if job.get("job_date"):
            try:
                j_date = date.fromisoformat(str(job["job_date"]))
                day_name = j_date.strftime("%a").lower()
            except Exception:
                pass

        sched_busy = student.get("schedule_busy") or {}
        if isinstance(sched_busy, str):
            try:
                import json
                sched_busy = json.loads(sched_busy)
            except Exception:
                sched_busy = {}

        has_conflict = has_time_conflict(
            student_schedule=sched_busy,
            day_name=day_name,
            job_start=job.get("start_time"),
            job_end=job.get("end_time"),
            buffer_min=student.get("buffer_min", 45),
        )
        if has_conflict:
            return False, 0.0, ["Dars jadvali bilan to'qnashuv bor"]

    # ==========================================
    # 2. YUMSHOQ MOSLIK BALLI (0 - 100)
    # ==========================================
    total_score = 0.0

    # 1. Mutaxassislik va Qiziqishlar (35 ball)
    target_majors = job.get("target_majors") or []
    student_major = str(student.get("major") or "")
    job_category = str(job.get("category") or "")

    is_maj_match, maj_score, maj_reason = match_major_compatibility(student_major, target_majors, job_category)
    total_score += maj_score
    reasons.append(maj_reason)

    student_interests = [str(i).lower() for i in (student.get("interests") or [])]
    job_desc = (str(job.get("title", "")) + " " + job_category).lower()
    if any(i in job_desc for i in student_interests if i):
        total_score += 10.0
        reasons.append("Shaxsiy qiziqishingizga mos (+10)")
    else:
        # Standart kasbiy o'sish qiziqishi
        total_score += 5.0

    # 2. Lokatsiya va Masofa (25 ball)
    if is_remote:
        total_score += 25.0
        reasons.append("🌐 Masofaviy ish (Istalgan joydan erkin ishlash) (+25)")
    else:
        max_dist = float(student.get("max_distance_km") or 5.0)
        if dist_km <= 1.5:
            total_score += 25.0
            reasons.append(f"📍 TTJ/Kvartirangizga juda yaqin: {dist_km:.1f} km (+25)")
        elif dist_km <= 3.5:
            total_score += 20.0
            reasons.append(f"📍 Qulay masofa: {dist_km:.1f} km (+20)")
        elif dist_km <= max_dist:
            total_score += 15.0
            reasons.append(f"📍 Qidiruv radiusingizda: {dist_km:.1f} km (+15)")
        elif dist_km <= max_dist * 2.0:
            total_score += 10.0
            reasons.append(f"📍 Shahar ichidagi masofa: {dist_km:.1f} km (+10)")
        else:
            total_score += 5.0
            reasons.append(f"📍 Masofa: {dist_km:.1f} km (+5)")

    # 3. Qulay Vaqt va Darsga Moslik (25 ball)
    if is_remote:
        total_score += 25.0
        reasons.append("⏰ Erkin grafik (Darsdan keyingi mustaqil rejim) (+25)")
    else:
        total_score += 25.0
        reasons.append("⏰ Darsdan keyingi qulay smena (+25)")

    # 4. Kontrakt Granti / Davlat Organi / To'lov (15 ball)
    listing_type = job.get("listing_type")
    tuition_cov = job.get("tuition_coverage_percent", 0)

    if listing_type == "tuition_grant_job" or tuition_cov > 0:
        total_score += 15.0
        reasons.append(f"🎓 Yillik kontrakt {tuition_cov}% to'lab beriladi! (+15)")
    elif listing_type == "state_internship":
        total_score += 15.0
        reasons.append("🏛 Rasmiy davlat organi amaliyoti va tasdiq (+15)")
    else:
        pay = job.get("pay_amount", 0)
        if pay > 0:
            total_score += 15.0
            reasons.append("💰 Kafolatlangan smena to'lovi (+15)")
        else:
            total_score += 10.0

    return True, min(100.0, round(total_score, 1)), reasons


def find_near_matches(student: Dict[str, Any], jobs: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], float, List[str]]]:
    """
    Agar 100% to'liq mos ish topilmasa, yo'nalishi yoki shartlari qisman mos keladigan
    'Deyarli mos' (Near Match: 60% - 79%) ishlarni saralab beradi.
    """
    near_matches = []
    student_major = str(student.get("major") or "").lower()

    for job in jobs:
        if job.get("status") != "open":
            continue
        
        # 18 yoshdan kichik bo'lsa, tungi ishlar hatto deyarli mosda ham ko'rinmaydi
        if student.get("age", 19) < 18 and is_night_job(job):
            continue

        score = 55.0
        reasons = []

        # Mutaxassislik yoki klaster
        target_majors = job.get("target_majors") or []
        is_match, _, _ = match_major_compatibility(student_major, target_majors, job.get("category", ""))
        if is_match:
            score += 20.0
            reasons.append("Mutaxassislik yoki sohasi mos keladi")
        else:
            reasons.append("Qo'shimcha soha bo'yicha talabalar uchun ochiq")

        # Masofa yoki masofaviy
        if job.get("work_format") == "remote_task":
            score += 10.0
            reasons.append("Masofaviy ishlash imkoniyati")

        # Maosh yoki grant
        if job.get("listing_type") == "tuition_grant_job":
            score += 10.0
            reasons.append("Yillik kontrakt to'lab berish imtiyozi bor")
        elif job.get("pay_amount", 0) > 0:
            score += 10.0
            reasons.append("Qulay to'lov taklif etiladi")

        reasons.append("Vaqt yoki oraliq masofa qisman mos keladi (Deyarli mos)")
        near_matches.append((job, min(90.0, round(score, 1)), reasons))

    near_matches.sort(key=lambda x: x[1], reverse=True)
    return near_matches[:4]
