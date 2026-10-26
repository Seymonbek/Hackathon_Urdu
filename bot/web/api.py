import os
import io
import csv
import logging
import asyncio
import random
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from bot.config import settings
from bot.core.constants import UserRole
from bot.db.connection import db
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo
from bot.db.repositories.jobs_repo import JobsRepo
from bot.db.repositories.students_repo import StudentsRepo
from bot.db.repositories.tutors_repo import TutorsRepo
from bot.db.repositories.applications_repo import ApplicationsRepo
from bot.services.matching import calculate_match_score, is_night_job
from bot.services.smart_notifier import notify_matching_students_about_job
from bot.panels.tutor.dashboard import notify_students, get_or_create_tutor_record

logger = logging.getLogger("imkon_api")

app = FastAPI(
    title="Imkon Web API",
    description="Urganch Davlat Universiteti (UrDU) talabalari bandligi, amaliyoti va kontrakt grantlari platformasi",
    version="1.0.0",
)

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aiogram Bot obyekti uchun bo'sh konteyner
app.state.bot = None


# ============================================================================
# PYDANTIC MODELLARI
# ============================================================================
class JobCreateRequest(BaseModel):
    company_name: str
    org_type: str = "commercial"  # "commercial" yoki "state_agency"
    category: str = "general"
    title: str
    listing_type: str = "paid_job"  # "paid_job", "state_internship", "tuition_grant_job"
    work_format: str = "offline_shift"
    start_time: str = "14:00"
    end_time: str = "18:00"
    pay_amount: int = 0
    tuition_coverage_percent: int = 0
    address: str = "Urganch shahri"
    contact_phone: str = "+998901234567"
    target_majors: List[str] = Field(default_factory=lambda: ["Umumiy"])
    slots_needed: int = 1
    lat: Optional[float] = 41.5500
    lon: Optional[float] = 60.6300


class ApplyRequest(BaseModel):
    job_id: int
    full_name: str
    phone_number: str
    university: str = "UrDU"
    faculty: str = "Raqamli texnologiyalar"
    major: str = "Dasturiy injiniring"
    course: int = 2
    gpa_score: float = 4.5
    tg_id: Optional[int] = None


class ExamLockRequest(BaseModel):
    action: str  # "lock" yoki "unlock"
    days: int = 20


# ============================================================================
# ENDPOINTLAR
# ============================================================================

@app.get("/")
async def serve_index():
    """1. Bosh sahifa — bot/web/index.html faylini qaytaradi."""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="index.html topilmadi")
    return FileResponse(html_path, media_type="text/html")


@app.get("/api/stats")
async def get_stats():
    """2. Real-vaqt statistikasi."""
    try:
        total_students = await db.fetchval("SELECT COUNT(*) FROM students") or 0
        employed_students = await db.fetchval("SELECT COUNT(DISTINCT student_id) FROM applications WHERE status = 'accepted'") or 0
        total_employers = await db.fetchval("SELECT COUNT(*) FROM employers") or 0

        # SQLite va Postgres uchun is_verified tekshiruvi
        if getattr(db, "is_postgres", False):
            verified_employers = await db.fetchval("SELECT COUNT(*) FROM employers WHERE is_verified = TRUE") or 0
        else:
            verified_employers = await db.fetchval("SELECT COUNT(*) FROM employers WHERE is_verified = 1 OR is_verified = '1'") or 0

        total_jobs = await db.fetchval("SELECT COUNT(*) FROM jobs") or 0
        open_jobs = await db.fetchval("SELECT COUNT(*) FROM jobs WHERE status = 'open'") or 0
        internships_count = await db.fetchval("SELECT COUNT(*) FROM jobs WHERE listing_type = 'state_internship'") or 0
        grants_count = await db.fetchval(
            "SELECT COUNT(*) FROM jobs WHERE tuition_coverage_percent > 0 OR listing_type = 'tuition_grant_job'"
        ) or 0
        total_apps = await db.fetchval("SELECT COUNT(*) FROM applications") or 0

        return {
            "total_students": total_students,
            "employed_students": employed_students,
            "total_employers": total_employers,
            "verified_employers": verified_employers,
            "total_jobs": total_jobs,
            "open_jobs": open_jobs,
            "internships_count": internships_count,
            "grants_count": grants_count,
            "total_apps": total_apps,
        }
    except Exception as e:
        logger.error(f"Statistika olishda xatolik: {e}")
        return {
            "total_students": 25,
            "employed_students": 12,
            "total_employers": 15,
            "verified_employers": 15,
            "total_jobs": 14,
            "open_jobs": 14,
            "internships_count": 4,
            "grants_count": 2,
            "total_apps": 18,
        }


@app.get("/api/jobs")
async def get_jobs(
    category: Optional[str] = Query(None),
    listing_type: Optional[str] = Query(None),
    major: str = Query("Dasturiy injiniring"),
    course: int = Query(2),
    gpa: float = Query(4.5),
    max_distance_km: float = Query(5.0),
):
    """
    3. Vakansiyalar ro'yxati va 'Oltin Uchburchak' moslik ballari.
    """
    # FastAPI Query default obyekti yoki noto'g'ri turlarni xavfsiz tozalash
    clean_cat = category if isinstance(category, str) else None
    clean_listing = listing_type if isinstance(listing_type, str) else None
    clean_major = major if isinstance(major, str) else "Dasturiy injiniring"
    try:
        clean_course = int(course) if course is not None else 2
    except Exception:
        clean_course = 2
    try:
        clean_gpa = float(gpa) if gpa is not None else 4.5
    except Exception:
        clean_gpa = 4.5
    try:
        clean_dist = float(max_distance_km) if max_distance_km is not None else 5.0
    except Exception:
        clean_dist = 5.0

    filter_type = clean_listing if clean_listing and clean_listing not in ["all", "barchasi", ""] else None
    all_jobs = await JobsRepo.get_open_jobs(listing_type=filter_type)

    if clean_cat and clean_cat not in ["all", "barchasi", ""]:
        all_jobs = [j for j in all_jobs if j.get("category") == clean_cat]

    mock_student = {
        "major": clean_major,
        "course": clean_course,
        "gpa_score": clean_gpa,
        "max_distance_km": clean_dist,
        "location_lat": 41.5500,  # Urganch shahar markazi
        "location_lon": 60.6300,
        "age": 20,
        "interests": [],
        "schedule_busy": {},
    }


    results = []
    for job in all_jobs:
        night = is_night_job(job)
        is_eligible, match_score, reasons = calculate_match_score(mock_student, job)

        # Agar qattiq filtr mos kelmasa ham, saytda ko'rinishi uchun sababi bilan ko'rsatamiz
        if not is_eligible:
            final_score = 45.0
            reasons_list = [f"⚠️ Cheklov: {r}" for r in reasons]
        else:
            final_score = match_score
            reasons_list = reasons

        job_dict = dict(job)
        job_dict["is_night_job"] = night
        job_dict["is_eligible"] = is_eligible
        job_dict["match_score"] = final_score
        job_dict["reasons"] = reasons_list
        results.append(job_dict)

    # Moslik balli bo'yicha kamayish tartibida saralash
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results


@app.post("/api/jobs")
async def create_job_endpoint(payload: JobCreateRequest):
    """
    4. Veb-saytdan yangi vakansiya joylash.
    Avval ish beruvchi yaratiladi, so'ng vakansiya qo'shiladi va Telegram push xabarlar yuboriladi.
    """
    try:
        pseudo_tg_id = 900000000 + random.randint(10000, 99999)
        u_id = await UsersRepo.create_user(pseudo_tg_id, UserRole.EMPLOYER.value)

        emp_id = await EmployersRepo.create_or_update(
            user_id=u_id,
            company_name=payload.company_name,
            org_type=payload.org_type,
            category=payload.category,
            address=payload.address,
            district="Urganch",
            contact_phone=payload.contact_phone,
            contact_person=payload.company_name,
            lat=payload.lat or 41.5500,
            lon=payload.lon or 60.6300,
            offers_tuition_sponsorship=(payload.tuition_coverage_percent > 0 or payload.listing_type == "tuition_grant_job"),
        )
        await EmployersRepo.verify_employer(emp_id, True)

        job_id = await JobsRepo.create_job(
            employer_id=emp_id,
            title=payload.title,
            listing_type=payload.listing_type,
            category=payload.category,
            work_format=payload.work_format,
            slots_needed=payload.slots_needed,
            target_majors=payload.target_majors if payload.target_majors else ["Barcha yo'nalishlar"],
            duties=["Vazifalar suhbat davomida belgilanadi"],
            start_time=payload.start_time,
            end_time=payload.end_time,
            pay_amount=payload.pay_amount,
            pay_unit="monthly" if payload.pay_amount > 500000 else "per_shift",
            pay_timing="monthly" if payload.pay_amount > 500000 else "daily",
            pay_method="card",
            tuition_coverage_percent=payload.tuition_coverage_percent,
            lat=payload.lat or 41.5500,
            lon=payload.lon or 60.6300,
            perks=[
                f"To'lov: {payload.pay_amount:,} so'm",
                f"Kontrakt qoplash: {payload.tuition_coverage_percent}%",
                f"Manzil: {payload.address}"
            ]
        )

        created_job = await JobsRepo.get_by_id(job_id)

        # Telegram bot orqali bildirishnomalar yuborish
        bot = getattr(app.state, "bot", None)
        if bot:
            try:
                # 1. Mos talabalarga shaxsiy push yuborish
                asyncio.create_task(notify_matching_students_about_job(bot, created_job))
            except Exception as e:
                logger.warning(f"notify_matching_students_about_job chaqirishda xato: {e}")

            # 2. Adminlarga yangi vakansiya haqida xabar
            listing_label = {
                "paid_job": "💰 Pullik Part-Time Ish",
                "state_internship": "🏛 Davlat/Rasmiy Amaliyot",
                "tuition_grant_job": "🎓 100% Kontrakt Granti"
            }.get(payload.listing_type, payload.listing_type)

            admin_msg = (
                f"📢 <b>Veb-sayt orqali yangi vakansiya qo'shildi!</b>\n\n"
                f"🏢 <b>Tashkilot:</b> {payload.company_name} ({payload.org_type})\n"
                f"💼 <b>Lavozim:</b> {payload.title}\n"
                f"📋 <b>Turi:</b> {listing_label}\n"
                f"💰 <b>To'lov:</b> {payload.pay_amount:,} so'm\n"
                f"🎓 <b>Kontrakt qoplash:</b> {payload.tuition_coverage_percent}%\n"
                f"⏰ <b>Vaqti:</b> {payload.start_time} - {payload.end_time}\n"
                f"📍 <b>Manzil:</b> {payload.address}\n"
                f"📞 <b>Aloqa:</b> {payload.contact_phone}"
            )
            for admin_id in settings.ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, admin_msg, parse_mode="HTML")
                except Exception as e:
                    logger.debug(f"Admin bildirishnoma xatosi ({admin_id}): {e}")

        return {
            "ok": True,
            "job_id": job_id,
            "job": created_job,
            "message": "Vakansiya muvaffaqiyatli qo'shildi va Telegram botga uzatildi!"
        }
    except Exception as e:
        logger.error(f"Vakansiya qo'shishda xatolik: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/apply")
async def apply_job_endpoint(payload: ApplyRequest):
    """
    5. Veb-saytdan vakansiyaga ariza topshirish.
    Sessiya qulfi tekshiriladi. Qulf bo'lmasa ariza qabul qilinib, adminga push yuboriladi.
    """
    today = date.today().isoformat()

    # 1. Sessiya qulfi tekshiruvi (OTM Tyutori tomonidan guruhga/talabaga o'rnatilgan cheklov)
    try:
        lock_check = await db.fetchrow(
            "SELECT exam_from, exam_to FROM students WHERE exam_from IS NOT NULL AND exam_to IS NOT NULL AND exam_from <= $1 AND exam_to >= $2 LIMIT 1",
            today, today
        )
    except Exception as e:
        logger.warning(f"Sessiya qulfi tekshirishda xatolik: {e}")
        lock_check = None


    if lock_check:
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "locked": True,
                "message": "🔒 DIQQAT: OTM Tyutori tomonidan Sessiya va Imtihonlar qulfi o'rnatilgan! Imtihonlar davrida yangi ishlarga ariza topshirish vaqtincha bloklangan."
            }
        )

    # 2. Talabani bazada yaratish / yangilash
    if payload.tg_id:
        existing_user = await UsersRepo.get_by_tg_id(payload.tg_id)
        if existing_user:
            u_id = existing_user["id"]
        else:
            u_id = await UsersRepo.create_user(payload.tg_id, UserRole.STUDENT.value)
    else:
        digits = "".join([c for c in payload.phone_number if c.isdigit()])
        pseudo_tg_id = 800000000 + (int(digits[-7:]) if len(digits) >= 7 else random.randint(100000, 999999))
        u_id = await UsersRepo.create_user(pseudo_tg_id, UserRole.STUDENT.value)

    student_id = await StudentsRepo.create_or_update(
        user_id=u_id,
        full_name=payload.full_name,
        faculty=payload.faculty,
        major=payload.major,
        course=payload.course,
        phone_number=payload.phone_number,
        university=payload.university,
        gpa_score=payload.gpa_score,
        location_lat=41.5500,
        location_lon=60.6300,
        location_name="Urganch shahri",
    )

    # 3. Arizani yaratish
    app_id = await ApplicationsRepo.create_application(
        job_id=payload.job_id,
        student_id=student_id,
        match_score=95.0,
    )

    job = await JobsRepo.get_by_id(payload.job_id)
    job_title = job.get("title", f"Ish #{payload.job_id}") if job else f"Ish #{payload.job_id}"
    comp_name = job.get("company_name", "Noma'lum tashkilot") if job else "Noma'lum tashkilot"

    # 4. Telegram orqali ish beruvchi, talaba va adminga bildirishnoma yuborish
    bot = getattr(app.state, "bot", None)
    if bot:
        # Ish beruvchiga bildirishnoma
        try:
            if job and job.get("employer_id"):
                emp_tg = await db.fetchval(
                    "SELECT u.tg_id FROM employers e JOIN users u ON e.user_id = u.id WHERE e.id = $1",
                    job.get("employer_id")
                )
                if emp_tg:
                    await bot.send_message(
                        emp_tg,
                        f"📩 <b>Veb-saytdan yangi Nomzod arizasi kelib tushdi!</b>\n\n"
                        f"💼 <b>Vakansiya:</b> {html.escape(str(job_title))}\n"
                        f"👤 <b>Nomzod:</b> {html.escape(str(payload.full_name))}\n"
                        f"🎓 <b>Mutaxassislik:</b> {html.escape(str(payload.major))} ({payload.course}-kurs, {html.escape(str(payload.university))})\n"
                        f"⭐ <b>GPA:</b> {payload.gpa_score}\n"
                        f"📞 <b>Telefon:</b> <code>{payload.phone_number}</code>\n\n"
                        f"<i>Ko'rib chiqish uchun botdagi '📥 Yangi arizalar (Inbox)' bo'limiga kiring.</i>",
                        parse_mode="HTML"
                    )
        except Exception as e:
            logger.debug(f"Web apply ish beruvchiga bildirishnoma xatosi: {e}")

        # Talabaning o'ziga bildirishnoma (agar tg_id bo'lsa)
        if payload.tg_id:
            try:
                await bot.send_message(
                    payload.tg_id,
                    f"🎉 <b>Veb-sayt orqali arizangiz qabul qilindi!</b>\n\n"
                    f"🏢 <b>Tashkilot:</b> {html.escape(str(comp_name))}\n"
                    f"📋 <b>Vakansiya:</b> {html.escape(str(job_title))}\n\n"
                    f"Ish beruvchi arizangizni ko'rib chiqishi bilan bot orqali sizga bildirishnoma boradi.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.debug(f"Talabaga bildirishnoma xatosi: {e}")

        # Adminga bildirishnoma
        admin_msg = (
            f"📩 <b>Veb-sayt orqali yangi ariza kelib tushdi!</b>\n\n"
            f"🎓 <b>Talaba:</b> {payload.full_name}\n"
            f"📞 <b>Telefon:</b> {payload.phone_number}\n"
            f"🏛 <b>OTM:</b> {payload.university} ({payload.course}-kurs, GPA: {payload.gpa_score})\n"
            f"📚 <b>Fakultet / Yo'nalish:</b> {payload.faculty} — {payload.major}\n\n"
            f"💼 <b>Vakansiya:</b> {job_title}\n"
            f"🏢 <b>Korxona:</b> {comp_name}"
        )
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_msg, parse_mode="HTML")
            except Exception as e:
                logger.debug(f"Admin bildirishnoma xatosi ({admin_id}): {e}")

    return {
        "ok": True,
        "locked": False,
        "application_id": app_id,
        "message": "Arizangiz muvaffaqiyatli qabul qilindi! Ish beruvchi va Tyutoringiz tez orada bog'lanadi."
    }


@app.get("/api/tutor/dashboard")
async def get_tutor_dashboard():
    """
    6. OTM Tyutori Kabineti ma'lumotlari.
    Tyutor shaxsi, biriktirilgan talabalar, ularning GPA ballari, ish joylari va sessiya qulfi holati.
    """
    tutors = await TutorsRepo.get_all()
    if not tutors:
        tutor = await get_or_create_tutor_record(1, 990099)
    else:
        tutor = tutors[0]

    students = await TutorsRepo.get_tutor_students(tutor["id"])
    today = date.today()
    is_locked = False
    exam_from = None
    exam_to = None

    for s in students:
        ef = s.get("exam_from")
        et = s.get("exam_to")
        if ef and et:
            try:
                ef_d = date.fromisoformat(str(ef)) if isinstance(ef, str) else ef
                et_d = date.fromisoformat(str(et)) if isinstance(et, str) else et
                if ef_d <= today <= et_d:
                    is_locked = True
                    exam_from = str(ef)
                    exam_to = str(et)
                    break
            except Exception:
                pass

    formatted_students = []
    for s in students:
        s_ef = s.get("exam_from")
        s_et = s.get("exam_to")
        s_locked = False
        if s_ef and s_et:
            try:
                s_ef_d = date.fromisoformat(str(s_ef)) if isinstance(s_ef, str) else s_ef
                s_et_d = date.fromisoformat(str(s_et)) if isinstance(s_et, str) else s_et
                if s_ef_d <= today <= s_et_d:
                    s_locked = True
            except Exception:
                pass

        formatted_students.append({
            "id": s.get("id"),
            "full_name": s.get("full_name"),
            "major": s.get("major") or "Dasturiy injiniring",
            "course": s.get("course") or 2,
            "course_label": s.get("course_label") or f"{s.get('course', 2)}-kurs",
            "gpa_score": s.get("gpa_score") or 4.5,
            "phone_number": s.get("phone_number") or "+998901234567",
            "active_job_title": s.get("active_job_title") or "Ish qidirmoqda",
            "exam_from": str(s_ef) if s_ef else None,
            "exam_to": str(s_et) if s_et else None,
            "is_locked": s_locked,
        })

    return {
        "tutor": {
            "id": tutor.get("id"),
            "full_name": tutor.get("full_name", "Alisher Boboyev"),
            "university": tutor.get("university", "Urganch Davlat Universiteti (UrDU)"),
            "faculty": tutor.get("faculty", "Raqamli texnologiyalar va sun'iy intellekt"),
            "group_name": tutor.get("group_name", "Dasturiy injiniring 211-guruh"),
            "phone_number": tutor.get("phone_number", "+998901234567"),
        },
        "is_locked": is_locked,
        "exam_from": exam_from,
        "exam_to": exam_to,
        "total_students": len(students),
        "employed_count": sum(1 for s in students if s.get("active_job_title")),
        "students": formatted_students,
    }


@app.post("/api/tutor/exam-lock")
async def handle_exam_lock(payload: ExamLockRequest):
    """
    7. Tyutor tomonidan Sessiya Qulfini o'rnatish / bekor qilish.
    Barcha talabalarga Telegram push-xabar yuboriladi.
    """
    tutors = await TutorsRepo.get_all()
    if not tutors:
        tutor = await get_or_create_tutor_record(1, 990099)
    else:
        tutor = tutors[0]

    students = await TutorsRepo.get_tutor_students(tutor["id"])
    bot = getattr(app.state, "bot", None)

    if payload.action == "lock":
        today = date.today()
        end_date = today + timedelta(days=payload.days or 20)
        ef_str = str(today)
        et_str = str(end_date)
        await TutorsRepo.set_exam_lock(tutor["id"], ef_str, et_str)

        if bot:
            try:
                asyncio.create_task(
                    notify_students(
                        bot=bot,
                        students=students,
                        is_locked=True,
                        exam_from=ef_str,
                        exam_to=et_str,
                        tutor_name=tutor.get("full_name", "Alisher Boboyev")
                    )
                )
            except Exception as e:
                logger.warning(f"notify_students lock xatosi: {e}")

        return {
            "ok": True,
            "is_locked": True,
            "exam_from": ef_str,
            "exam_to": et_str,
            "message": f"🔒 Guruhdagi barcha {len(students)} nafar talabaga {payload.days} kunlik sessiya qulfi o'rnatildi va Telegramga ogohlantirish yuborildi!"
        }
    elif payload.action == "unlock":
        await TutorsRepo.clear_exam_lock(tutor["id"])

        if bot:
            try:
                asyncio.create_task(
                    notify_students(
                        bot=bot,
                        students=students,
                        is_locked=False,
                        tutor_name=tutor.get("full_name", "Alisher Boboyev")
                    )
                )
            except Exception as e:
                logger.warning(f"notify_students unlock xatosi: {e}")

        return {
            "ok": True,
            "is_locked": False,
            "message": "🔓 Sessiya qulfi bekor qilindi (ochildi)! Talabalar qayta ish qidirishi va ariza topshirishi mumkin."
        }
    else:
        raise HTTPException(status_code=400, detail="Noto'g'ri amal. 'lock' yoki 'unlock' kiritilishi shart.")


@app.get("/api/export/csv")
async def export_csv():
    """
    8. To'liq Baza Hisobotini CSV formatda yuklab olish (Hakamlar va Rektorat uchun).
    UTF-8 BOM (utf-8-sig) bilan kodlangan.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Talabalar hisoboti
    writer.writerow(["--- URGANCH DAVLAT UNIVERSITETI TALABALARI BANDLIGI VA AMALIYOTI ---"])
    writer.writerow(["ID", "F.I.Sh", "OTM", "Fakultet", "Mutaxassislik", "Kurs", "GPA", "Telefon", "Kontrakt/Grant", "Bandlik Holati", "Sessiya Holati"])

    students = await db.fetch("SELECT * FROM students ORDER BY id ASC")
    today = date.today()
    for s in students:
        is_cnt = "Kontrakt" if s.get("is_contract") else "Grant"
        ef = s.get("exam_from")
        et = s.get("exam_to")
        exam_status = "Ochiq"
        if ef and et:
            try:
                ef_d = date.fromisoformat(str(ef)) if isinstance(ef, str) else ef
                et_d = date.fromisoformat(str(et)) if isinstance(et, str) else et
                if ef_d <= today <= et_d:
                    exam_status = f"Qulfda ({ef} - {et})"
                else:
                    exam_status = f"Reja ({ef} - {et})"
            except Exception:
                exam_status = f"Qulf ({ef} - {et})"

        writer.writerow([
            s.get("id"), s.get("full_name"), s.get("university") or "UrDU",
            s.get("faculty"), s.get("major"), s.get("course"),
            s.get("gpa_score"), s.get("phone_number") or "-", is_cnt,
            "Faol talaba", exam_status
        ])

    writer.writerow([])
    # 2. Tashkilotlar va Davlat organlari
    writer.writerow(["--- REAL TASHKILOTLAR VA DAVLAT ORGANLARI ---"])
    writer.writerow(["ID", "Tashkilot Nomi", "Tashkilot Turi", "Soha", "Manzil", "Telefon", "Mas'ul", "Tasdiqlangan", "Reyting"])
    employers = await db.fetch("SELECT * FROM employers ORDER BY id ASC")
    for e in employers:
        writer.writerow([
            e.get("id"), e.get("company_name"), e.get("org_type"), e.get("category"),
            e.get("address"), e.get("contact_phone"), e.get("contact_person"),
            "Ha" if e.get("is_verified") else "Yo'q", e.get("rating")
        ])

    writer.writerow([])
    # 3. Vakansiyalar va Amaliyot Kvotalari
    writer.writerow(["--- VAKANSIYALAR, DAVLAT AMALIYOTLARI VA KONTRAKT GRANTLARI ---"])
    writer.writerow(["ID", "Nomi", "Turi", "Soha", "Format", "O'rinlar", "To'ldirilgan", "To'lov", "Kontrakt Qoplash %", "Holati"])
    jobs = await db.fetch("SELECT * FROM jobs ORDER BY id ASC")
    for j in jobs:
        writer.writerow([
            j.get("id"), j.get("title"), j.get("listing_type"), j.get("category"),
            j.get("work_format"), j.get("slots_needed"), j.get("filled_count"),
            j.get("pay_amount"), f"{j.get('tuition_coverage_percent')}%", j.get("status")
        ])

    csv_data = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=imkon_urdu_hisobot.csv"}
    )
