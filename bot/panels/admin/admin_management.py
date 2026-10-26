import io
import csv
import logging
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.core.constants import UserRole
from bot.core.i18n import get_button_variants, get_i18n
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo
from bot.db.repositories.jobs_repo import JobsRepo
from bot.db.repositories.tutors_repo import TutorsRepo
from bot.db.connection import db

logger = logging.getLogger(__name__)
router = Router()


class AdminAddJobStates(StatesGroup):
    company_name = State()
    title = State()
    schedule = State()
    pay = State()
    contact = State()


class AdminAddTutorStates(StatesGroup):
    tg_id = State()
    full_name = State()
    university = State()
    faculty_group = State()
    phone_number = State()


# ==========================================
# 1. TALABALAR VA HISOBOTLAR MONITORINGI
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_ADM_STUDENTS")))
@router.callback_query(F.data == "adm_stu_all")
async def list_students_summary(event):
    msg = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()

    lang = await UsersRepo.get_user_lang(user_id)
    total_students = await db.fetchval("SELECT COUNT(*) FROM students") or 0
    employed_students = await db.fetchval("SELECT COUNT(DISTINCT student_id) FROM applications WHERE status = 'accepted'") or 0
    unemployed_students = max(0, total_students - employed_students)

    students = await db.fetch("""
        SELECT s.*, 
               (
                   SELECT j.title || ' (' || e.company_name || ')'
                   FROM applications a
                   JOIN jobs j ON a.job_id = j.id
                   JOIN employers e ON j.employer_id = e.id
                   WHERE a.student_id = s.id AND a.status = 'accepted'
                   LIMIT 1
               ) as active_job
        FROM students s 
        ORDER BY s.id DESC LIMIT 10
    """)
    if not students:
        empty = "Bazada talabalar mavjud emas." if lang == "uz" else ("В базе нет студентов." if lang == "ru" else "No students found.")
        await msg.answer(empty)
        return

    employed_pct = round(employed_students / total_students * 100, 1) if total_students else 0
    text = (
        f"🎓 **Talabalar Monitoring Boshqaruvi:**\n\n"
        f"• Jami ro'yxatdan o'tgan: **{total_students} nafar**\n"
        f"• Ishga joylashganlar: **{employed_students} nafar ({employed_pct}%)**\n"
        f"• Ish qidirayotganlar: **{unemployed_students} nafar**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 **Oxirgi ro'yxatdan o'tgan talabalar:**\n\n"
    )

    for s in students:
        is_cnt = "Kontrakt" if s.get("is_contract") else "Grant"
        loc_val = s.get("location_name") or "Urganch"
        phone_val = s.get("phone_number") or "Mavjud emas"
        job_tag = f"💼 {s.get('active_job')}" if s.get("active_job") else "🔍 Ish qidirmoqda"
        course_lbl = s.get("course_label") or f"{s.get('course')}-kurs"
        text += (
            f"• **{s.get('full_name')}** ({s.get('faculty')}, {course_lbl})\n"
            f"  {job_tag} | GPA: **{s.get('gpa_score')}** ⭐ | {is_cnt}\n"
            f"  Joylashuv: {loc_val} | Tel: `{phone_val}`\n\n"
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💼 Band talabalar", callback_data="adm_stu_employed"),
                InlineKeyboardButton(text="🔍 Ish qidirayotganlar", callback_data="adm_stu_seeking"),
            ],
            [
                InlineKeyboardButton(text="📥 Baza hisobotini yuklab olish (CSV)", callback_data="adm_stu_export_csv"),
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm_stu_all"),
            ]
        ]
    )
    if isinstance(event, CallbackQuery):
        await msg.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


# --- 1.1 Band talabalar filtri ---
@router.callback_query(F.data == "adm_stu_employed")
async def process_adm_stu_employed(call: CallbackQuery):
    await call.answer()
    students = await db.fetch("""
        SELECT s.*, 
               (
                   SELECT j.title || ' (' || e.company_name || ')'
                   FROM applications a
                   JOIN jobs j ON a.job_id = j.id
                   JOIN employers e ON j.employer_id = e.id
                   WHERE a.student_id = s.id AND a.status = 'accepted'
                   LIMIT 1
               ) as active_job
        FROM students s 
        WHERE s.id IN (SELECT student_id FROM applications WHERE status = 'accepted')
        ORDER BY s.id DESC LIMIT 15
    """)

    text = f"💼 **Band bo'lgan (Ishlayotgan) talabalar ({len(students)} nafar):**\n\n"
    if not students:
        text += "Hozircha faol ishga qabul qilingan talabalar mavjud emas."
    else:
        for idx, s in enumerate(students, start=1):
            course_lbl = s.get("course_label") or f"{s.get('course')}-kurs"
            text += (
                f"{idx}. 🎓 **{s.get('full_name')}** ({course_lbl})\n"
                f"   🏢 **Ish joyi:** {s.get('active_job')}\n"
                f"   📱 Tel: `{s.get('phone_number') or '-'}` | GPA: **{s.get('gpa_score')}** ⭐\n\n"
            )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Ish qidirayotganlar", callback_data="adm_stu_seeking")],
            [InlineKeyboardButton(text="⬅️ Barcha talabalar", callback_data="adm_stu_all")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# --- 1.2 Ish qidirayotgan talabalar filtri ---
@router.callback_query(F.data == "adm_stu_seeking")
async def process_adm_stu_seeking(call: CallbackQuery):
    await call.answer()
    students = await db.fetch("""
        SELECT s.*
        FROM students s 
        WHERE s.id NOT IN (SELECT student_id FROM applications WHERE status = 'accepted')
        ORDER BY s.id DESC LIMIT 15
    """)

    text = f"🔍 **Hozirda ish qidirayotgan talabalar ({len(students)} nafar):**\n\n"
    if not students:
        text += "Barcha talabalar ish bilan ta'minlangan."
    else:
        for idx, s in enumerate(students, start=1):
            course_lbl = s.get("course_label") or f"{s.get('course')}-kurs"
            text += (
                f"{idx}. 🎓 **{s.get('full_name')}** ({s.get('faculty')}, {course_lbl})\n"
                f"   📍 Yashash: {s.get('location_name') or 'Urganch'}\n"
                f"   📱 Tel: `{s.get('phone_number') or '-'}` | GPA: **{s.get('gpa_score')}** ⭐\n\n"
            )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💼 Band talabalar", callback_data="adm_stu_employed")],
            [InlineKeyboardButton(text="⬅️ Barcha talabalar", callback_data="adm_stu_all")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# --- 1.3 CSV Eksport tugmasi ---
@router.callback_query(F.data == "adm_stu_export_csv")
async def process_adm_stu_export_csv(call: CallbackQuery):
    from bot.panels.admin.export import export_data_to_csv
    await export_data_to_csv(call.message)
    await call.answer()


# ==========================================
# 2. VAKANSIYALARNI BOSHQARISH (QO'SHISH VA FILTR BILAN O'CHIRISH)
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_ADM_JOBS")))
async def show_jobs_admin_panel(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    total_jobs = await db.fetchval("SELECT COUNT(*) FROM jobs") or 0
    open_jobs = await db.fetchval("SELECT COUNT(*) FROM jobs WHERE status = 'open'") or 0

    text = (
        f"📋 **E'lonlar va Vakansiyalarni Boshqarish:**\n\n"
        f"• Bazadagi jami e'lonlar: **{total_jobs} ta**\n"
        f"• Faol ochiq e'lonlar: **{open_jobs} ta**\n\n"
        f"Quyidagi amallardan birini tanlang 👇"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Yangi e'lon qo'shish", callback_data="adm_job_add_start"),
                InlineKeyboardButton(text="🗑 E'lonni o'chirish (Filtrlar bilan)", callback_data="adm_job_del_categories"),
            ],
            [
                InlineKeyboardButton(text="📋 Barcha faol e'lonlar ro'yxati", callback_data="adm_job_view_all"),
            ]
        ]
    )

    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


# --- 2.1 Barcha e'lonlar ro'yxati ---
@router.callback_query(F.data == "adm_job_view_all")
async def process_view_all_jobs(call: CallbackQuery):
    await call.answer()
    jobs = await db.fetch(
        "SELECT j.*, e.company_name FROM jobs j JOIN employers e ON j.employer_id = e.id ORDER BY j.id DESC LIMIT 15"
    )
    if not jobs:
        await call.message.answer("Bazada e'lonlar topilmadi.")
        return

    text = "📋 **Bazadagi real e'lonlar ro'yxati:**\n\n"
    for j in jobs:
        pay = f"{j.get('pay_amount', 0):,} so'm" if j.get('pay_amount') else "Kelishiladi"
        text += (
            f"🆔 `{j.get('id')}` • **{j.get('title')}**\n"
            f"  🏢 {j.get('company_name')} | 💰 {pay}\n"
            f"  ⏰ {j.get('start_time', '')} - {j.get('end_time', '')}\n\n"
        )

    await call.message.answer(text, parse_mode="Markdown")


# --- 2.2 E'LON QO'SHISH WIZARD (FSM) ---
@router.callback_query(F.data == "adm_job_add_start")
async def start_add_job_flow(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(AdminAddJobStates.company_name)
    await call.message.answer(
        "➕ **Yangi e'lon qo'shish (1/5):**\n\n"
        "Ish beruvchi korxona/tashkilot nomini kiriting:\n"
        "*(Masalan: 'Mega Texno Urganch' yoki 'Target O'quv Markazi')*",
        parse_mode="Markdown"
    )


@router.message(AdminAddJobStates.company_name, F.text)
async def process_add_company(msg: Message, state: FSMContext):
    await state.update_data(company_name=msg.text.strip())
    await state.set_state(AdminAddJobStates.title)
    await msg.answer(
        "💼 **Lavozim / Kasb nomini kiriting (2/5):**\n"
        "*(Masalan: 'Sotuvchi-konsultant', 'Ofitsiant', 'Ingliz tili o'qituvchisi')*",
        parse_mode="Markdown"
    )


@router.message(AdminAddJobStates.title, F.text)
async def process_add_title(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text.strip())
    await state.set_state(AdminAddJobStates.schedule)
    await msg.answer(
        "⏰ **Ish vaqti va smenasini kiriting (3/5):**\n"
        "*(Masalan: '14:00 - 20:00 (Kechki smena, 6/1)')*",
        parse_mode="Markdown"
    )


@router.message(AdminAddJobStates.schedule, F.text)
async def process_add_schedule(msg: Message, state: FSMContext):
    await state.update_data(schedule=msg.text.strip())
    await state.set_state(AdminAddJobStates.pay)
    await msg.answer(
        "💰 **Oylik yoki kunlik maosh miqdorini kiriting (4/5):**\n"
        "*(Masalan: '3 500 000 so'm' yoki 'Kunlik 120 000 so'm')*",
        parse_mode="Markdown"
    )


@router.message(AdminAddJobStates.pay, F.text)
async def process_add_pay(msg: Message, state: FSMContext):
    # Raqamni ajratib olish
    digits = "".join([c for c in msg.text if c.isdigit()])
    pay_num = int(digits) if digits else 2000000
    await state.update_data(pay_text=msg.text.strip(), pay_amount=pay_num)
    await state.set_state(AdminAddJobStates.contact)
    await msg.answer(
        "📍 **Manzil va Telefon raqamini kiriting (5/5):**\n"
        "*(Masalan: 'Urganch sh., Al-Xorazmiy ko'chasi | Tel: +998901234567')*",
        parse_mode="Markdown"
    )


@router.message(AdminAddJobStates.contact, F.text)
async def process_add_contact(msg: Message, state: FSMContext):
    data = await state.get_data()
    contact_text = msg.text.strip()
    await state.clear()

    # Bazasiga yangi ish beruvchi va ish kiritish
    user_id = await UsersRepo.create_user(tg_id=msg.from_user.id, role="employer")
    employer_id = await EmployersRepo.create_or_update(
        user_id=user_id,
        company_name=data["company_name"],
        org_type="commercial",
        category="general",
        address=contact_text,
        district="Urganch",
        contact_phone=contact_text,
        contact_person="Admin tomonidan qo'shildi",
        lat=41.5510,
        lon=60.6310,
    )

    from datetime import date
    job_id = await JobsRepo.create_job(
        employer_id=employer_id,
        title=data["title"],
        listing_type="paid_job",
        category="general",
        work_format="offline_shift",
        slots_needed=2,
        target_majors=["Umumiy", "Barcha yo'nalishlar"],
        min_course_required=1,
        duties=[f"Grafik: {data['schedule']}", "Mas'uliyatli va chaqqon ishlash"],
        job_date=str(date.today()),
        start_time="14:00",
        end_time="20:00",
        pay_amount=data["pay_amount"],
        pay_unit="per_shift" if "kun" in data.get("pay_text", "").lower() else "monthly",
        pay_timing="daily" if "kun" in data.get("pay_text", "").lower() else "monthly",
        pay_method="cash",
        perks=[data.get("pay_text", ""), contact_text],
        lat=41.5510,
        lon=60.6310,
        image_path="bot/assets/imkon_logo.png",
    )

    await msg.answer(
        f"✅ **Yangi e'lon muvaffaqiyatli bazaga qo'shildi!**\n\n"
        f"🆔 E'lon ID: `{job_id}`\n"
        f"🏢 Tashkilot: **{data['company_name']}**\n"
        f"💼 Lavozim: **{data['title']}**\n"
        f"💰 Maosh: **{data['pay_amount']:,} so'm**\n"
        f"📍 Manzil/Aloqa: {contact_text}\n\n"
        f"Ushbu vakansiya barcha talabalar qidiruvida darhol ko'rinadi!",
        parse_mode="Markdown"
    )


# --- 2.3 FILTRLAR BILAN E'LONLARNI O'CHIRISH (FILTERED DELETE) ---
@router.callback_query(F.data == "adm_job_del_categories")
async def show_delete_filter_categories(call: CallbackQuery):
    await call.answer()
    text = (
        "🗑 **E'lonlarni o'chirish — Soha/Filtrni tanlang:**\n\n"
        "Qaysi yo'nalishdagi e'lonlarni ko'rish va o'chirishni xohlaysiz?"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏛 Davlat amaliyotlari", callback_data="delcat_court_law"),
                InlineKeyboardButton(text="🏨 Mehmonxona va Hostel", callback_data="delcat_hospitality"),
            ],
            [
                InlineKeyboardButton(text="🍔 Gamburg & Umumiy ovqat", callback_data="delcat_catering"),
                InlineKeyboardButton(text="🛍 Savdo & Mediapark", callback_data="delcat_retail"),
            ],
            [
                InlineKeyboardButton(text="🚚 Xalqaro Logistika", callback_data="delcat_logistics"),
                InlineKeyboardButton(text="📚 Ta'lim & O'quv markaz", callback_data="delcat_education"),
            ],
            [
                InlineKeyboardButton(text="📸 Media & Reklama", callback_data="delcat_media"),
                InlineKeyboardButton(text="🔘 Barcha e'lonlar (13 ta)", callback_data="delcat_all"),
            ]
        ]
    )

    await call.message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("delcat_"))
async def process_filtered_job_list_for_deletion(call: CallbackQuery):
    await call.answer()
    category = call.data.replace("delcat_", "")

    if category == "all":
        jobs = await db.fetch(
            "SELECT j.id, j.title, j.pay_amount, e.company_name FROM jobs j JOIN employers e ON j.employer_id = e.id ORDER BY j.id DESC LIMIT 20"
        )
    else:
        jobs = await db.fetch(
            "SELECT j.id, j.title, j.pay_amount, e.company_name FROM jobs j JOIN employers e ON j.employer_id = e.id WHERE j.category = $1 OR e.category = $2 ORDER BY j.id DESC",
            category, category
        )

    if not jobs:
        await call.message.answer("Ushbu filtr bo'yicha e'lonlar topilmadi.")
        return

    text = f"🗑 **Tanlangan toifadagi e'lonlar ({len(jobs)} ta):**\nO'chirmoqchi bo'lgan e'loningiz yonidagi '❌ O'chirish' tugmasini bosing 👇"
    buttons = []
    for j in jobs:
        btn_text = f"❌ O'chirish: #{j['id']} {j['title'][:25]}..."
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"del_confirm_{j['id']}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Boshqa filtrni tanlash", callback_data="adm_job_del_categories")])

    await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


@router.callback_query(F.data.startswith("del_confirm_"))
async def process_confirm_delete(call: CallbackQuery):
    job_id = int(call.data.replace("del_confirm_", ""))
    job = await JobsRepo.get_by_id(job_id)
    if not job:
        await call.answer("E'lon topilmadi.", show_alert=True)
        return

    await call.answer()
    confirm_text = (
        f"⚠️ **E'lonni o'chirishni tasdiqlaysizmi?**\n\n"
        f"🆔 ID: `{job['id']}`\n"
        f"📋 Lavozim: **{job['title']}**\n"
        f"🏢 Tashkilot: {job.get('company_name')}\n\n"
        f"Bu amalni ortga qaytarib bo'lmaydi!"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"del_execute_{job_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm_job_del_categories"),
            ]
        ]
    )
    await call.message.answer(confirm_text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("del_execute_"))
async def process_execute_delete(call: CallbackQuery):
    job_id = int(call.data.replace("del_execute_", ""))
    await JobsRepo.delete_job(job_id)
    await call.answer("✅ E'lon bazadan muvaffaqiyatli o'chirildi!", show_alert=True)
    await call.message.edit_text(
        f"✅ **E'lon (ID: #{job_id}) muvaffaqiyatli o'chirildi!**\n\n"
        f"Talabalar qidiruvidan ushbu e'lon olib tashlandi.",
        parse_mode="Markdown"
    )


# ==========================================
# 3. KONTRAKT VA SHIKOYATLAR MONITORINGI
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_ADM_SPONSORSHIP")))
async def list_sponsorship_summary(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    grants = await db.fetch("SELECT * FROM jobs WHERE listing_type = 'tuition_grant_job' OR tuition_coverage_percent > 0 ORDER BY id DESC")
    
    text = "🎓 **Talabalar Kontraktini Ish Beruvchilar Tomonidan To'lash Monitoringi:**\n\n"
    if not grants:
        text += "Hozircha faol kontrakt grantlari mavjud emas."
    else:
        for g in grants[:5]:
            text += (
                f"• **{g.get('title')}**\n"
                f"  Qoplash: **{g.get('tuition_coverage_percent')}%** | Majburiyat: {g.get('work_obligation_years')} yil\n"
                f"  Min GPA: {g.get('min_gpa_required', 0.0)}\n\n"
            )

    text += (
        "\n📌 *O'zbekiston Respublikasi Soliq kodeksining 378-moddasiga muvofiq, "
        "yuridik shaxslar tomonidan talabalar kontraktini to'lash xarajatlari foyda solig'idan ozod etiladi.*"
    )
    await msg.answer(text, parse_mode="Markdown")


@router.message(F.text.in_(get_button_variants("BTN_ADM_REPORTS")))
async def list_reports_summary(msg: Message):
    text = "⚠️ **Shikoyatlar va Nizolar Monitoringi:**\n\nKutilayotgan shikoyat yoki nizolar mavjud emas. Tizim barqaror ishlamoqda."
    await msg.answer(text, parse_mode="Markdown")


# ==========================================
# 4. TYUTORLARNI BOSHQARISH VA TAYINLASH
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_ADM_TUTORS")))
@router.callback_query(F.data == "adm_tutors_refresh")
async def list_tutors_management(event):
    msg = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()

    lang = await UsersRepo.get_user_lang(user_id)
    tutors = await TutorsRepo.get_all()

    text = (
        f"🧑‍🏫 **OTM Tyutorlari Boshqaruvi:**\n\n"
        f"• Bazadagi jami tyutorlar: **{len(tutors)} nafar**\n\n"
        f"📋 **Mavjud tyutorlar ro'yxati:**\n\n"
    )

    inline_keyboard = []
    if not tutors:
        text += "Hozircha tizimda tyutorlar mavjud emas. Yangi tyutor tayinlash uchun quyidagi tugmani bosing 👇"
    else:
        for idx, t in enumerate(tutors, start=1):
            text += (
                f"{idx}. 🧑‍🏫 **{t.get('full_name')}** (ID: `{t.get('tg_id')}`)\n"
                f"   🏛 OTM: {t.get('university')}\n"
                f"   📂 Fakultet/Guruh: {t.get('faculty')} ({t.get('group_name') or 'Barcha'})\n"
                f"   👥 Biriktirilgan talabalar: **{t.get('students_count', 0)} nafar**\n\n"
            )
            btn_title = f"{idx}. 🧑‍🏫 {t.get('full_name')[:18]} ({t.get('students_count', 0)} talaba)"
            inline_keyboard.append([
                InlineKeyboardButton(text=btn_title, callback_data=f"adm_tutor_detail_{t['id']}")
            ])

    inline_keyboard.append([
        InlineKeyboardButton(text="➕ Yangi tyutor tayinlash", callback_data="adm_tutor_add_start"),
        InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm_tutors_refresh"),
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    if isinstance(event, CallbackQuery):
        await msg.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


# --- 4.1 Tyutor anketasi va boshqaruvi ---
@router.callback_query(F.data.startswith("adm_tutor_detail_"))
async def process_adm_tutor_detail(call: CallbackQuery):
    tutor_id = int(call.data.replace("adm_tutor_detail_", ""))
    tutor = await TutorsRepo.get_by_id(tutor_id)
    if not tutor:
        await call.answer("Tyutor topilmadi.", show_alert=True)
        return

    await call.answer()
    students_count = await db.fetchval("SELECT COUNT(*) FROM students WHERE tutor_id = $1", tutor_id) or 0

    detail_text = (
        f"🧑‍🏫 **Tyutor Boshqaruv Karti:**\n\n"
        f"• **F.I.Sh:** {tutor.get('full_name')}\n"
        f"• **Telegram ID:** `{tutor.get('tg_id')}`\n"
        f"• **OTM:** {tutor.get('university')}\n"
        f"• **Fakultet:** {tutor.get('faculty')}\n"
        f"• **Guruh:** {tutor.get('group_name') or 'Barcha'}\n"
        f"• **Telefon:** `{tutor.get('phone_number') or 'Kiritilmagan'}`\n"
        f"• **Biriktirilgan talabalar:** **{students_count} nafar**\n"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Guruh talabalari ro'yxati", callback_data=f"adm_tutor_students_{tutor_id}")],
            [
                InlineKeyboardButton(text="🗑 Tyutorni o'chirish", callback_data=f"adm_tutor_del_{tutor_id}"),
                InlineKeyboardButton(text="⬅️ Tyutorlar ro'yxati", callback_data="adm_tutors_refresh"),
            ]
        ]
    )
    await call.message.edit_text(detail_text, reply_markup=kb, parse_mode="Markdown")


# --- 4.2 Tyutorga biriktirilgan talabalar ro'yxati ---
@router.callback_query(F.data.startswith("adm_tutor_students_"))
async def process_adm_tutor_students(call: CallbackQuery):
    tutor_id = int(call.data.replace("adm_tutor_students_", ""))
    tutor = await TutorsRepo.get_by_id(tutor_id)
    students = await TutorsRepo.get_tutor_students(tutor_id)

    await call.answer()
    t_name = tutor.get("full_name") if tutor else "Tyutor"
    text = f"👥 **{t_name} — Nazoratidagi talabalar ({len(students)} nafar):**\n\n"

    if not students:
        text += "Ushbu tyutorga biriktirilgan talabalar mavjud emas."
    else:
        for idx, s in enumerate(students[:15], start=1):
            job_str = f"💼 {s.get('active_job_title')}" if s.get("active_job_title") else "🔍 Ish qidirmoqda"
            course_lbl = s.get("course_label") or f"{s.get('course')}-kurs"
            text += (
                f"{idx}. 🎓 **{s.get('full_name')}** ({course_lbl})\n"
                f"   {job_str} | Tel: `{s.get('phone_number') or '-'}`\n\n"
            )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Tyutor kartiga qaytish", callback_data=f"adm_tutor_detail_{tutor_id}")]
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# --- 4.3 Tyutorni o'chirish ---
@router.callback_query(F.data.startswith("adm_tutor_del_"))
async def process_adm_tutor_del(call: CallbackQuery):
    tutor_id = int(call.data.replace("adm_tutor_del_", ""))
    await TutorsRepo.delete_tutor(tutor_id)
    await call.answer("✅ Tyutor o'chirildi va talabalar bo'shatildi!", show_alert=True)
    await list_tutors_management(call)


@router.callback_query(F.data == "adm_tutor_add_start")
async def process_start_add_tutor(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(AdminAddTutorStates.tg_id)
    await call.message.answer(
        "🧑‍🏫 **Yangi Tyutor tayinlash (1/5):**\n\n"
        "Tyutorning **Telegram ID raqami**ni kiriting:\n"
        "*(Masalan: `6956456422` yoki boshqa foydalanuvchining ID raqami)*\n\n"
        "💡 *Telegram ID ni olish uchun tyutordan @userinfobot orqali ID sini yuborishini so'rashingiz mumkin.*",
        parse_mode="Markdown"
    )


@router.message(AdminAddTutorStates.tg_id, F.text)
async def process_tutor_tg_id(msg: Message, state: FSMContext):
    try:
        tg_id = int(msg.text.strip())
    except ValueError:
        await msg.answer("Iltimos, faqat raqamlardan iborat Telegram ID kiriting (Masalan: `6956456422`):")
        return

    await state.update_data(tg_id=tg_id)
    await state.set_state(AdminAddTutorStates.full_name)
    await msg.answer(
        "🧑‍🏫 **Tyutor F.I.Sh (2/5):**\n\n"
        "Tyutorning to'liq ism-familiyasini kiriting:\n*(Masalan: Otabek Rahimov)*",
        parse_mode="Markdown"
    )


@router.message(AdminAddTutorStates.full_name, F.text)
async def process_tutor_full_name(msg: Message, state: FSMContext):
    await state.update_data(full_name=msg.text.strip())
    await state.set_state(AdminAddTutorStates.university)
    await msg.answer(
        "🏛 **OTM Nomi (3/5):**\n\n"
        "Tyutor faoliyat yuritadigan universitet yoki institut nomini kiriting:\n*(Masalan: Urganch Davlat Universiteti (UrDU))*",
        parse_mode="Markdown"
    )


@router.message(AdminAddTutorStates.university, F.text)
async def process_tutor_university(msg: Message, state: FSMContext):
    await state.update_data(university=msg.text.strip())
    await state.set_state(AdminAddTutorStates.faculty_group)
    await msg.answer(
        "📂 **Fakultet va Guruh (4/5):**\n\n"
        "Tyutor mas'ul bo'lgan fakultet va guruh nomini kiriting:\n*(Masalan: Raqamli texnologiyalar, Dasturiy injiniring 211-guruh)*",
        parse_mode="Markdown"
    )


@router.message(AdminAddTutorStates.faculty_group, F.text)
async def process_tutor_faculty_group(msg: Message, state: FSMContext):
    await state.update_data(faculty_group=msg.text.strip())
    await state.set_state(AdminAddTutorStates.phone_number)
    await msg.answer(
        "📱 **Aloqa telefoni (5/5):**\n\n"
        "Tyutorning telefon raqamini kiriting:\n*(Masalan: +998901234567)*",
        parse_mode="Markdown"
    )


@router.message(AdminAddTutorStates.phone_number, F.text)
async def process_tutor_finish(msg: Message, state: FSMContext):
    phone_number = msg.text.strip()
    data = await state.get_data()
    await state.clear()

    tg_id = data["tg_id"]
    full_name = data["full_name"]
    university = data["university"]
    faculty_group = data["faculty_group"]

    # 1. User jadvalida tyutor rolini belgilash
    user = await UsersRepo.get_by_tg_id(tg_id)
    if not user:
        user_id = await UsersRepo.create_user(tg_id, UserRole.TUTOR.value, "uz")
    else:
        user_id = user["id"]
        await UsersRepo.update_role(tg_id, UserRole.TUTOR.value)

    # 2. Tyutorlar jadvaliga kiritish
    tutor_id = await TutorsRepo.create_or_update(
        user_id=user_id,
        full_name=full_name,
        university=university,
        faculty=faculty_group,
        group_name=faculty_group,
        phone_number=phone_number
    )

    # 3. Biriktirilmagan talabalarni avtomatik shu tyutorga biriktirish
    await db.execute("UPDATE students SET tutor_id = $1 WHERE tutor_id IS NULL", tutor_id)
    assigned_count = await db.fetchval("SELECT COUNT(*) FROM students WHERE tutor_id = $1", tutor_id) or 0

    success_text = (
        f"✅ **Yangi Tyutor muvaffaqiyatli tayinlandi!**\n\n"
        f"• **F.I.Sh:** {full_name}\n"
        f"• **Telegram ID:** `{tg_id}`\n"
        f"• **OTM:** {university}\n"
        f"• **Fakultet/Guruh:** {faculty_group}\n"
        f"• **Telefon:** {phone_number}\n"
        f"• **Biriktirilgan talabalar:** {assigned_count} nafar\n\n"
        f"Tyutor botga `/start` yuborganida unga to'g'ridan-to'g'ri Tyutor boshqaruv kabineti va sessiya qulfi paneli ochiladi."
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧑‍🏫 Barcha tyutorlar ro'yxati", callback_data="adm_tutors_refresh")]
        ]
    )
    await msg.answer(success_text, reply_markup=kb, parse_mode="Markdown")
