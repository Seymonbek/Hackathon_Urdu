import asyncio
import io
import sys

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from bot.db.connection import db
from bot.db.seed import seed_initial_data
from bot.web.api import app, JobCreateRequest, ApplyRequest, ExamLockRequest
from bot.web.api import (
    serve_index,
    get_stats,
    get_jobs,
    create_job_endpoint,
    apply_job_endpoint,
    get_tutor_dashboard,
    handle_exam_lock,
    export_csv
)


async def run_tests():
    print("🚀 Web API testlari boshlandi...")
    await db.connect()
    await seed_initial_data()

    # 1. GET / (index.html tekshiruvi)
    print("1. GET / tekshirilmoqda...")
    resp = await serve_index()
    assert resp.status_code == 200
    print("✅ GET / muvaffaqiyatli!")

    # 2. GET /api/stats
    print("2. GET /api/stats tekshirilmoqda...")
    stats = await get_stats()
    assert "total_jobs" in stats
    assert "employed_students" in stats
    assert "internships_count" in stats
    assert "grants_count" in stats
    print(f"✅ GET /api/stats muvaffaqiyatli! Natija: {stats}")

    # 3. GET /api/jobs
    print("3. GET /api/jobs tekshirilmoqda...")
    jobs = await get_jobs(major="Dasturiy injiniring", course=2, gpa=4.5, max_distance_km=5.0)
    assert isinstance(jobs, list)
    assert len(jobs) > 0
    first_job = jobs[0]
    assert "match_score" in first_job
    assert "reasons" in first_job
    assert "is_night_job" in first_job
    print(f"✅ GET /api/jobs muvaffaqiyatli! {len(jobs)} ta vakansiya olindi. Top job: {first_job.get('title')} ({first_job.get('match_score')}%)")

    # 4. POST /api/jobs
    print("4. POST /api/jobs tekshirilmoqda...")
    new_job_payload = JobCreateRequest(
        company_name="Urganch IT Hub Test",
        org_type="commercial",
        category="it",
        title="Python Backend Dasturchi (Stajyor)",
        listing_type="paid_job",
        work_format="offline_shift",
        start_time="14:00",
        end_time="18:00",
        pay_amount=2500000,
        tuition_coverage_percent=50,
        address="Urganch sh., Al-Xorazmiy ko'chasi, 12",
        contact_phone="+998901234567",
        target_majors=["Dasturiy injiniring", "Axborot texnologiyalari"],
        slots_needed=2,
        lat=41.5520,
        lon=60.6310,
    )
    job_resp = await create_job_endpoint(new_job_payload)
    assert job_resp["ok"] is True
    created_job_id = job_resp["job_id"]
    print(f"✅ POST /api/jobs muvaffaqiyatli! Yaratilgan vakansiya ID: {created_job_id}")

    # 5. POST /api/tutor/exam-lock (LOCK qilish)
    print("5. POST /api/tutor/exam-lock ('lock') tekshirilmoqda...")
    lock_resp = await handle_exam_lock(ExamLockRequest(action="lock", days=20))
    assert lock_resp["ok"] is True
    assert lock_resp["is_locked"] is True
    print(f"✅ Sessiya qulfi yoqildi: {lock_resp['message']}")

    # 6. POST /api/apply (Qulf paytida sinab ko'rish - 403 / locked: true bo'lishi kerak)
    print("6. POST /api/apply (Qulf paytida ariza berish) tekshirilmoqda...")
    apply_payload = ApplyRequest(
        job_id=created_job_id,
        full_name="Alisher Navoiy",
        phone_number="+998909876543",
        university="UrDU",
        faculty="Raqamli texnologiyalar",
        major="Dasturiy injiniring",
        course=2,
        gpa_score=4.8,
    )
    blocked_resp = await apply_job_endpoint(apply_payload)
    # blocked_resp JSONResponse status_code=403
    assert blocked_resp.status_code == 403
    print("✅ Sessiya qulfi arizani muvaffaqiyatli blokladi (HTTP 403)!")

    # 7. POST /api/tutor/exam-lock (UNLOCK qilish)
    print("7. POST /api/tutor/exam-lock ('unlock') tekshirilmoqda...")
    unlock_resp = await handle_exam_lock(ExamLockRequest(action="unlock"))
    assert unlock_resp["ok"] is True
    assert unlock_resp["is_locked"] is False
    print(f"✅ Sessiya qulfi ochildi: {unlock_resp['message']}")

    # 8. POST /api/apply (Qulf ochilgach qayta ariza berish)
    print("8. POST /api/apply (Qulf ochilgach) tekshirilmoqda...")
    success_apply = await apply_job_endpoint(apply_payload)
    assert success_apply["ok"] is True
    assert success_apply["locked"] is False
    print(f"✅ Ariza muvaffaqiyatli qabul qilindi! ID: {success_apply['application_id']}")

    # 9. GET /api/tutor/dashboard
    print("9. GET /api/tutor/dashboard tekshirilmoqda...")
    dash = await get_tutor_dashboard()
    assert "tutor" in dash
    assert "students" in dash
    assert len(dash["students"]) > 0
    print(f"✅ GET /api/tutor/dashboard muvaffaqiyatli! Tyutor: {dash['tutor']['full_name']}, Talabalar soni: {len(dash['students'])}")

    # 10. GET /api/export/csv
    print("10. GET /api/export/csv tekshirilmoqda...")
    csv_resp = await export_csv()
    assert csv_resp.status_code == 200
    # Stream content tekshiruvi
    content = b""
    async for chunk in csv_resp.body_iterator:
        content += chunk
    assert b"URGANCH DAVLAT UNIVERSITETI" in content or b"TALABALAR" in content
    print(f"✅ GET /api/export/csv muvaffaqiyatli! CSV hajmi: {len(content)} bayt")

    await db.disconnect()
    print("\n🎉 BARCHA 10 TA TEST 100% MUVAFFAQQYATLI O'TDI!")


if __name__ == "__main__":
    asyncio.run(run_tests())
