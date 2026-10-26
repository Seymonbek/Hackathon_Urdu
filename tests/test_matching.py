import asyncio
from bot.services.matching import calculate_match_score


def test_matching_algorithm():
    # 1. Sinov talabasi (Yurisprudensiya 3-kurs, GPA 4.5, Urganch markazida)
    student = {
        "id": 1,
        "full_name": "Javohir Aliyev",
        "faculty": "Yuridik",
        "major": "Yurisprudensiya",
        "course": 3,
        "gpa_score": 4.5,
        "interests": ["sud_kotibi", "notariat"],
        "location_lat": 41.5500,
        "location_lon": 60.6300,
        "max_distance_km": 5.0,
        "schedule_busy": {"mon": ["08:30-10:00", "10:10-11:40"]},
        "buffer_min": 45,
    }

    # 2. Mos Sud Vakansiyasi (Dushanba 14:30 - 17:30, masofa 1.2 km)
    matched_job = {
        "id": 101,
        "title": "Sud majlisi kotibi yordamchisi",
        "listing_type": "state_internship",
        "category": "court_law",
        "work_format": "offline_shift",
        "status": "open",
        "target_majors": ["Yurisprudensiya", "Huquqshunoslik"],
        "min_course_required": 2,
        "min_gpa_required": 0.0,
        "start_time": "14:30",
        "end_time": "17:30",
        "lat": 41.5540,
        "lon": 60.6280,
    }

    is_eligible, score, reasons = calculate_match_score(student, matched_job)
    print(f"Test 1 - Mos kelishi: {is_eligible}, Ball: {score}, Sabablar: {reasons}")
    assert is_eligible is True, "Mos ish qabul qilinishi kerak edi"
    assert score >= 85.0, f"Ball 85+ bo'lishi kerak edi, olingan: {score}"

    # 3. To'qnashadigan Ish (Dushanba 10:30 - 13:00 - dars paytida!)
    conflicting_job = dict(matched_job)
    conflicting_job["id"] = 102
    conflicting_job["start_time"] = "10:30"
    conflicting_job["end_time"] = "13:00"

    is_eligible_conf, score_conf, reasons_conf = calculate_match_score(student, conflicting_job)
    print(f"Test 2 - Dars to'qnashuvi: {is_eligible_conf}, Sabab: {reasons_conf}")
    assert is_eligible_conf is False, "Dars bilan to'qnashgan ish rad etilishi kerak edi"

    # 4. Kontrakt to'lab beriladigan grant (GPA talabi bilan)
    grant_job = {
        "id": 103,
        "title": "Adliya maslahatchisi stajori (KONTRAKT GRANTI)",
        "listing_type": "tuition_grant_job",
        "category": "court_law",
        "work_format": "offline_shift",
        "status": "open",
        "target_majors": ["Yurisprudensiya"],
        "min_course_required": 3,
        "min_gpa_required": 4.2,
        "tuition_coverage_percent": 100,
        "start_time": "15:00",
        "end_time": "18:00",
        "lat": 41.5520,
        "lon": 60.6310,
    }

    # 5. Semantik Klaster Mosligi (IT / Dasturchi)
    student_it = {
        "id": 2,
        "full_name": "Sardor IT",
        "faculty": "Kompyuter ilmlari",
        "major": "Dasturiy injiniring",
        "course": 2,
        "gpa_score": 4.0,
        "location_lat": 41.5500,
        "location_lon": 60.6300,
        "max_distance_km": 10.0,
        "schedule_busy": {},
    }
    job_it = {
        "id": 104,
        "title": "Junior Python Dasturchisi",
        "listing_type": "paid_job",
        "category": "it",
        "work_format": "remote_task",
        "status": "open",
        "target_majors": ["IT", "Dasturchi", "Axborot texnologiyalari"],
        "min_course_required": 1,
        "pay_amount": 3500000,
    }
    is_it_match, it_score, it_reasons = calculate_match_score(student_it, job_it)
    print(f"Test 4 - Semantik IT Mosligi: {is_it_match}, Ball: {it_score}, Sabab: {it_reasons}")
    assert is_it_match is True
    assert it_score >= 90.0, f"IT klaster balli 90+ bo'lishi kerak, olingan: {it_score}"

    print("\n✅ BARCHA MOSLIK, KLASTER VA TO'QNASHUV TESTLARI MUVAFFAQIYATLI O'TDI!")


if __name__ == "__main__":
    test_matching_algorithm()
