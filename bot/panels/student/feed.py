import os
import html
import logging
from typing import List, Dict, Any, Tuple
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.core.callbacks import StudentJobAction, JobCarouselCallback
from bot.config import settings
from bot.core.i18n import get_i18n, get_button_variants
from bot.db.connection import db
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.students_repo import StudentsRepo
from bot.db.repositories.jobs_repo import JobsRepo
from bot.db.repositories.applications_repo import ApplicationsRepo
from bot.services.matching import calculate_match_score, find_near_matches, is_night_job

logger = logging.getLogger(__name__)
router = Router()

DEFAULT_IMAGE_PATH = "bot/assets/imkon_logo.png"


class JobSearchStates(StatesGroup):
    search_query = State()


def deduplicate_jobs(jobs_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Nom, korxona va ish vaqti bo'yicha dublikat vakansiyalarni tozalaydi."""
    seen = set()
    unique = []
    for j in jobs_list:
        title = str(j.get("title", "")).strip().lower()
        comp = str(j.get("company_name", "")).strip().lower()
        start = str(j.get("start_time", "")).strip()
        key = (title, comp, start)
        if key not in seen:
            seen.add(key)
            unique.append(j)
    return unique


def get_filter_keyboard(active: str = "all", lang: str = "uz", back_page: int = 0, back_job_id: int = 0) -> InlineKeyboardMarkup:
    """Mos ishlar va amaliyotlar bo'limidagi tezkor filtrlar klaviaturasi."""
    if lang == "ru":
        btn_jobs = f"{'🔘' if active == 'jobs' else '⚪'} 💼 Вакансии"
        btn_intern = f"{'🔘' if active in ['internships', 'state'] else '⚪'} 🏛 Практика"
        btn_grants = f"{'🔘' if active == 'grants' else '⚪'} 🎓 Гранты"
        btn_all = f"{'🔘' if active == 'all' else '⚪'} 📋 Все"
        btn_search = "🔍 Поиск по ключевым словам"
        btn_back = "⬅️ Назад к вакансии"
        btn_menu = "🔙 Главное меню"
    elif lang == "en":
        btn_jobs = f"{'🔘' if active == 'jobs' else '⚪'} 💼 Paid Jobs"
        btn_intern = f"{'🔘' if active in ['internships', 'state'] else '⚪'} 🏛 Internships"
        btn_grants = f"{'🔘' if active == 'grants' else '⚪'} 🎓 Grants"
        btn_all = f"{'🔘' if active == 'all' else '⚪'} 📋 All"
        btn_search = "🔍 Search by keyword"
        btn_back = "⬅️ Back to job"
        btn_menu = "🔙 Main Menu"
    else:
        btn_jobs = f"{'🔘' if active == 'jobs' else '⚪'} 💼 Pullik ishlar"
        btn_intern = f"{'🔘' if active in ['internships', 'state'] else '⚪'} 🏛 Amaliyotlar"
        btn_grants = f"{'🔘' if active == 'grants' else '⚪'} 🎓 Kontrakt granti"
        btn_all = f"{'🔘' if active == 'all' else '⚪'} 📋 Barchasi"
        btn_search = "🔍 Kalit so'z bilan qidirish"
        btn_back = "⬅️ Orqaga (Vakansiyaga)"
        btn_menu = "🔙 Asosiy menyu"

    rows = [
        [
            InlineKeyboardButton(text=btn_jobs, callback_data="filter_jobs_jobs"),
            InlineKeyboardButton(text=btn_intern, callback_data="filter_jobs_internships"),
        ],
        [
            InlineKeyboardButton(text=btn_grants, callback_data="filter_jobs_grants"),
            InlineKeyboardButton(text=btn_all, callback_data="filter_jobs_all"),
        ],
        [
            InlineKeyboardButton(text=btn_search, callback_data="filter_jobs_search"),
        ]
    ]

    if back_job_id > 0:
        rows.append([
            InlineKeyboardButton(
                text=btn_back,
                callback_data=JobCarouselCallback(section=active, page=back_page, action="nav", job_id=back_job_id).pack()
            ),
            InlineKeyboardButton(text=btn_menu, callback_data="close_carousel")
        ])
    else:
        rows.append([
            InlineKeyboardButton(text=btn_menu, callback_data="close_carousel")
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ============================================================================
# 1. BOT ASOSIY MENYU TUGMALARI
# ============================================================================

@router.message(F.text.in_(get_button_variants("BTN_STUDENT_JOBS")))
async def show_student_paid_jobs(msg: Message):
    """1. PULLIK BO'SH ISH O'RINLARI (ALOHIDA TUGMA)"""
    await show_filtered_carousel(msg, section="jobs", page=0, is_edit=False)


@router.message(F.text.in_(get_button_variants("BTN_STUDENT_INTERNSHIPS")))
async def show_student_internships(msg: Message):
    """2. DAVLAT VA KASBIY AMALIYOTLAR (ALOHIDA TUGMA)"""
    await show_filtered_carousel(msg, section="internships", page=0, is_edit=False)


@router.message(F.text.in_(get_button_variants("BTN_STUDENT_MATCHES")))
async def show_student_matches(msg: Message):
    """3. BARCHA MOS TAKLIFLAR"""
    await show_filtered_carousel(msg, section="all", page=0, is_edit=False)


@router.message(F.text.in_(get_button_variants("BTN_STUDENT_GRANTS")))
async def show_tuition_grants(msg: Message):
    """4. KONTRAKT GRANTLARI BO'LIMI"""
    await show_filtered_carousel(msg, section="grants", page=0, is_edit=False)


@router.callback_query(F.data.startswith("filter_jobs_"))
async def process_filter_jobs(call: CallbackQuery, state: FSMContext):
    """Filtr chiplari bosilganda"""
    filter_type = call.data.replace("filter_jobs_", "")
    
    if filter_type == "search":
        await call.answer()
        await state.set_state(JobSearchStates.search_query)
        lang = await UsersRepo.get_user_lang(call.from_user.id)
        if lang == "ru":
            prompt = "🔍 Введите ключевое слово для поиска вакансий (например: *Hostel, Bunyod, Mittivoy, Dispetcher, Omon School, Inson*):"
        elif lang == "en":
            prompt = "🔍 Enter a keyword to search jobs (e.g. *Hostel, Bunyod, Mittivoy, Dispatcher, Omon School, Inson*):"
        else:
            prompt = "🔍 Qidirmoqchi bo'lgan so'zni kiriting (Masalan: *Hostel, Bunyod, Mittivoy, Dispetcher, Omon School, Inson, Ingliz tili*):"
        await call.message.answer(prompt, parse_mode="Markdown")
        return

    await call.answer("Yangilanmoqda...")
    await show_filtered_carousel(call, section=filter_type, page=0, is_edit=True)


@router.message(JobSearchStates.search_query, F.text)
async def process_search_query(msg: Message, state: FSMContext):
    """Kalit so'z bo'yicha qidiruv"""
    await state.clear()
    query = msg.text.strip().lower()
    await show_filtered_carousel(msg, section="search", page=0, is_edit=False, search_query=query)


# ============================================================================
# 2. FILTRLANGAN VAKANSIYALARNI YIG'ISH VA CAROUSELGA UZATISH
# ============================================================================

async def get_filtered_matched_jobs(
    user_id: int, section: str, search_query: str = ""
) -> Tuple[List[Tuple[Dict[str, Any], float, List[str]]], bool, str]:
    """
    Talaba uchun tozalangan va 'Oltin Uchburchak' bo'yicha saralangan ishlarni qaytaradi.
    Qaytaradi: (matched_jobs, is_near_match, error_or_lock_message)
    """
    lang = await UsersRepo.get_user_lang(user_id)
    student = await StudentsRepo.get_by_tg_id(user_id)
    if not student:
        return [], False, "register_required"

    # Sessiya qulfi tekshiruvi
    from datetime import date
    today = date.today()
    exam_from = student.get("exam_from")
    exam_to = student.get("exam_to")
    if exam_from and exam_to:
        try:
            ef = date.fromisoformat(str(exam_from)) if isinstance(exam_from, str) else exam_from
            et = date.fromisoformat(str(exam_to)) if isinstance(exam_to, str) else exam_to
            if ef <= today <= et:
                lock_msg = (
                    f"🔒 <b>Sessiya va Imtihon qulfi faol ({exam_from} – {exam_to})!</b>\n\n"
                    f"Sizning OTM mas'ul <b>Tyutoringiz</b> tomonidan sessiya qulfi o'rnatilgan.\n"
                    f"Imtihonlar davrida talabalarning akademik o'zlashtirishini ta'minlash uchun ish qidirish va yangi ishlarga ariza topshirish vaqtincha to'xtatilgan.\n\n"
                    f"Sessiya tugashi bilan yoki tyutoringiz qulfni ochganda barcha vakansiyalar qayta ochiladi!"
                )
                return [], False, lock_msg
        except Exception:
            pass

    # Bazadan barcha ochiq ishlarni olamiz va dublikatlarni tozalaymiz
    raw_jobs = await JobsRepo.get_open_jobs()
    all_jobs = deduplicate_jobs(raw_jobs)

    candidate_jobs = []
    for j in all_jobs:
        if section == "jobs" and j.get("listing_type") == "state_internship":
            continue
        if section in ["internships", "state"] and j.get("listing_type") != "state_internship":
            continue
        if section == "grants" and (j.get("listing_type") != "tuition_grant_job" and j.get("tuition_coverage_percent", 0) <= 0):
            continue

        if section == "search" and search_query:
            searchable = (
                str(j.get("title", "")) + " " +
                str(j.get("company_name", "")) + " " +
                str(j.get("category", "")) + " " +
                " ".join(j.get("target_majors") or []) + " " +
                " ".join(j.get("duties") or [])
            ).lower()
            if search_query not in searchable:
                continue

        candidate_jobs.append(j)

    matched_jobs = []
    for j in candidate_jobs:
        is_eligible, score, reasons = calculate_match_score(student, j)
        if is_eligible:
            matched_jobs.append((j, score, reasons))

    matched_jobs.sort(key=lambda x: x[1], reverse=True)

    if not matched_jobs:
        near_matches = find_near_matches(student, candidate_jobs)
        return near_matches, True, ""

    return matched_jobs, False, ""


# ============================================================================
# 3. YAGONA CAROUSEL KO'RINISHI (PAGINATSIYA VA SHU JOYDA EDIT BO'LISHI)
# ============================================================================

async def show_filtered_carousel(
    event,
    section: str = "all",
    page: int = 0,
    is_edit: bool = False,
    search_query: str = "",
):
    """
    Vakansiyalarni bitta xabarda paginatsiya bilan (Carousel) ko'rsatadi.
    Tugmalar bosilganda xabar yangilanadi (edit), yangi xabar tashlanmaydi!
    """
    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id
    msg = event.message if is_callback else event
    lang = await UsersRepo.get_user_lang(user_id)
    t = get_i18n(lang)

    matched_jobs, is_near, lock_or_err = await get_filtered_matched_jobs(user_id, section, search_query)

    if lock_or_err == "register_required":
        await (msg.edit_text if is_edit else msg.answer)(t.MSG_PLEASE_REGISTER, parse_mode="HTML")
        return

    if lock_or_err:
        await (msg.edit_text if is_edit else msg.answer)(lock_or_err, parse_mode="HTML")
        return

    if not matched_jobs:
        empty_text = (
            "🔍 <b>Ushbu toifa bo'yicha hozircha vakansiyalar topilmadi.</b>\n"
            "Boshqa toifani tanlab ko'ring yoki bildirishnomalarni yoqing:"
        )
        kb = get_filter_keyboard(section, lang)
        if is_edit and is_callback:
            try:
                await msg.edit_text(empty_text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await msg.answer(empty_text, reply_markup=kb, parse_mode="HTML")
        else:
            await msg.answer(empty_text, reply_markup=kb, parse_mode="HTML")
        return

    total = len(matched_jobs)
    page = max(0, min(page, total - 1))
    job, score, reasons = matched_jobs[page]

    # Talabaning ushbu ishga arizasi borligini tekshirish
    student = await StudentsRepo.get_by_tg_id(user_id)
    already_applied = False
    if student:
        existing = await db.fetchval(
            "SELECT id FROM applications WHERE job_id = $1 AND student_id = $2",
            job["id"], student["id"]
        )
        already_applied = bool(existing)

    # To'lov va imtiyoz ma'lumotlari
    if job.get("listing_type") == "tuition_grant_job" or job.get("tuition_coverage_percent", 0) > 0:
        pay_info = f"🎓 <b>100% Kontrakt to'lab beriladi!</b>"
    elif job.get("listing_type") == "state_internship":
        pay_amount = job.get("pay_amount", 0)
        pay_info = f"🏛 <b>Rasmiy Davlat Amaliyoti</b> ({pay_amount:,} so'm)" if pay_amount > 0 else "🏛 <b>Rasmiy Davlat Amaliyoti (Tasdiq kundaligi)</b>"
    else:
        pay_info = f"💰 <b>{job.get('pay_amount', 0):,} so'm</b> ({job.get('pay_timing')})"

    # Tungi smena va TTJ ogohlantirishi
    night_warning = ""
    if is_night_job(job):
        night_warning = (
            "\n⚠️ <b>Tungi smena ogohlantirishi:</b> "
            "<i>Agar TTJ (yotoqxona)da yashasangiz, 22:00 dan keyin eshiklar yopilishi sababli ushbu smenani OTM ma'muriyati bilan kelishib oling!</i>\n"
        )

    # Bo'lim nomi
    section_titles = {
        "jobs": "💼 Bo'sh ish o'rinlari (Pullik ishlar)",
        "internships": "🏛 Davlat & Kasbiy Amaliyotlar",
        "state": "🏛 Davlat Amaliyotlari",
        "grants": "🎓 100% Kontrakt Grantlari",
        "all": "🎯 Barcha Mos Takliflar",
        "search": f"🔍 Qidiruv natijalari ('{html.escape(search_query)}')"
    }
    sec_title = section_titles.get(section, "Mos takliflar")
    prefix = "⚡ <b>[Deyarli mos]</b> " if is_near else "🎯 "

    reasons_text = "\n".join([f"  • {html.escape(str(r))}" for r in reasons[:3]])

    card_text = (
        f"{prefix}<b>{sec_title} ({page + 1}/{total}):</b>\n\n"
        f"💼 <b>{html.escape(str(job.get('title')))}</b> (Moslik: <b>{score}%</b>)\n"
        f"🏢 <b>Tashkilot:</b> {html.escape(str(job.get('company_name')))}\n"
        f"📍 <b>Manzil:</b> {html.escape(str(job.get('address')))}\n"
        f"⏰ <b>Vaqt:</b> {job.get('start_time', '')} – {job.get('end_time', '')}\n"
        f"{pay_info}\n"
        f"{night_warning}\n"
        f"💡 <b>Nega sizga mos:</b>\n{reasons_text}\n"
    )

    # =========================================================================
    # KLAVIATURA TUZISH:
    # 1-qator: [⬅️ Oldingi]  [ 1 / 16 ]  [ Keyingi ➡️ ]
    # 2-qator: [✅ Ariza berish / topshirilgan]  [ℹ️ Batafsil]
    # 3-qator: [📋 Toifalar]  [🔍 Qidirish]
    # =========================================================================
    keyboard_buttons = []

    # 1-qator: Paginatsiya
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=JobCarouselCallback(section=section, page=page - 1, action="nav", job_id=job["id"]).pack()
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"📄 {page + 1} / {total}",
            callback_data="noop_indicator"
        )
    )
    if page < total - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Keyingi ➡️",
                callback_data=JobCarouselCallback(section=section, page=page + 1, action="nav", job_id=job["id"]).pack()
            )
        )
    keyboard_buttons.append(nav_row)

    # 2-qator: Ariza va Batafsil
    if already_applied:
        btn_apply = InlineKeyboardButton(text="✅ Ariza topshirilgan", callback_data="already_applied_info")
    else:
        btn_apply = InlineKeyboardButton(
            text="✅ Ariza topshirish",
            callback_data=JobCarouselCallback(section=section, page=page, action="apply", job_id=job["id"]).pack()
        )
    btn_details = InlineKeyboardButton(
        text="ℹ️ Batafsil",
        callback_data=JobCarouselCallback(section=section, page=page, action="view", job_id=job["id"]).pack()
    )
    keyboard_buttons.append([btn_apply, btn_details])

    # 3-qator: Toifalar va Qidiruv
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="📋 Toifalar",
            callback_data=JobCarouselCallback(section=section, page=page, action="menu", job_id=job["id"]).pack()
        ),
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="filter_jobs_search"),
    ])

    # 4-qator: Asosiy menyuga qaytish
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_carousel")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    # Rasm tayyorlash
    img_path = job.get("image_path") or DEFAULT_IMAGE_PATH
    if not os.path.exists(img_path):
        img_path = DEFAULT_IMAGE_PATH

    # Xabarni yangilash (EDIT) yoki yangi yuborish
    is_photo_msg = bool(getattr(msg, "photo", None))
    if is_photo_msg and len(card_text) > 1020:
        card_text = card_text[:1015] + "..."

    if is_edit and is_callback:
        try:
            if is_photo_msg:
                await msg.edit_caption(caption=card_text, reply_markup=kb, parse_mode="HTML")
            else:
                await msg.edit_text(text=card_text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Carousel edit fallback: {e}")
            try:
                if is_photo_msg:
                    await msg.edit_media(
                        media=InputMediaPhoto(media=FSInputFile(img_path), caption=card_text[:1020], parse_mode="HTML"),
                        reply_markup=kb
                    )
            except Exception as e2:
                logger.warning(f"Carousel edit xatosi: {e2}")
    else:
        # Yangi xabar yuborish — FAQAT BITTA XABAR YUBORILADI!
        try:
            if os.path.exists(img_path) and len(card_text) <= 1024:
                photo = FSInputFile(img_path)
                await msg.answer_photo(photo=photo, caption=card_text, reply_markup=kb, parse_mode="HTML")
            else:
                await msg.answer(card_text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Rasm yuborishda xatolik: {e}, oddiy xabar yuboriladi.")
            await msg.answer(card_text, reply_markup=kb, parse_mode="HTML")


# ============================================================================
# 4. CAROUSEL CALLBACKLARI (NAVIGATSIYA, VIEW, BACK, APPLY)
# ============================================================================

@router.callback_query(F.data == "noop_indicator")
async def process_noop(call: CallbackQuery):
    """Indikator bosilganda oddiy axborot"""
    await call.answer("Vakansiyalar orasida navigatsiya qilish uchun ⬅️ va ➡️ tugmalaridan foydalaning.")


@router.callback_query(F.data == "already_applied_info")
async def process_already_applied_info(call: CallbackQuery):
    await call.answer("Siz ushbu vakansiyaga allaqachon ariza topshirgansiz! 'Mening arizalarim' bo'limida holatni ko'rishingiz mumkin.", show_alert=True)


@router.callback_query(JobCarouselCallback.filter(F.action == "nav"))
async def process_carousel_navigation(call: CallbackQuery, callback_data: JobCarouselCallback):
    """⬅️ Oldingi yoki Keyingi ➡️ bosilganda shu joyda o'zgaradi"""
    await call.answer()
    await show_filtered_carousel(call, section=callback_data.section, page=callback_data.page, is_edit=True)


@router.callback_query(JobCarouselCallback.filter(F.action == "menu"))
async def process_carousel_menu(call: CallbackQuery, callback_data: JobCarouselCallback):
    """📋 Toifalar tugmasi bosilganda filtr menyusini chiqarish"""
    await call.answer()
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    text = "🔘 <b>Qaysi yo'nalishdagi takliflarni ko'rmoqchisiz?</b>\nQuyidagi toifalardan birini tanlang:"
    kb = get_filter_keyboard(callback_data.section, lang, back_page=callback_data.page, back_job_id=callback_data.job_id)
    try:
        await call.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await call.message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "close_carousel")
async def process_close_carousel(call: CallbackQuery):
    """Karuselni yopish va asosiy menyuga qaytish"""
    await call.answer("Asosiy menyu")
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    from bot.core.keyboards import get_student_main_keyboard
    kb = get_student_main_keyboard(lang)
    try:
        await call.message.delete()
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await call.message.answer(
        "🏠 <b>Asosiy menyuga qaytdingiz.</b>\nQuyidagi tugmalar orqali kerakli bo'limni tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )


# ============================================================================
# 5. BATAFSIL KO'RISH (VIEW JOB DETAILS) — SHU JOYDA EDIT BO'LADI!
# ============================================================================

def format_job_details(job: Dict[str, Any], max_len: int = 1000) -> str:
    """Telegram photo caption (1024 char) chegarasiga 100% mos ixcham va to'liq ma'lumot."""
    org_type_labels = {
        "state_agency": "🏛 Davlat organi",
        "commercial": "🏢 Tijorat korxonasi",
        "ngo": "🌐 NNT / Xalqaro"
    }
    org_type_str = org_type_labels.get(job.get("org_type"), "🏢 Tashkilot")

    if job.get("listing_type") == "tuition_grant_job" or job.get("tuition_coverage_percent", 0) > 0:
        pay_str = f"🎓 <b>100% Kontrakt to'lanadi!</b> ({job.get('work_obligation_years', 1)} yil staj)"
    elif job.get("listing_type") == "state_internship":
        pay_amount = job.get("pay_amount", 0)
        pay_str = f"🏛 <b>Davlat amaliyoti</b> ({pay_amount:,} so'm)" if pay_amount > 0 else "🏛 <b>Davlat amaliyoti (Tasdiq kundaligi)</b>"
    else:
        pay_str = f"💰 <b>{job.get('pay_amount', 0):,} so'm</b> ({job.get('pay_timing')})"

    majors_list = job.get("target_majors") or []
    majors_str = ", ".join([html.escape(str(m)) for m in majors_list[:3]]) if majors_list else "Barcha yo'nalishlar"
    if len(majors_list) > 3:
        majors_str += "..."

    phone_info = f"\n📞 <b>Aloqa:</b> <code>{html.escape(str(job.get('contact_phone')))}</code>" if job.get("contact_phone") else ""

    header = (
        f"📋 <b>{html.escape(str(job.get('title')))} — Batafsil:</b>\n\n"
        f"🏢 <b>Tashkilot:</b> {html.escape(str(job.get('company_name')))} ({org_type_str})\n"
        f"📍 <b>Manzil:</b> {html.escape(str(job.get('address')))}\n"
        f"⏰ <b>Ish vaqti:</b> {job.get('start_time', '')} – {job.get('end_time', '')}\n"
        f"💵 <b>To'lov:</b> {pay_str}\n"
        f"🎓 <b>Yo'nalishlar:</b> {majors_str}\n"
        f"📚 <b>Kurs:</b> {job.get('min_course_required', 1)}-kurs+{phone_info}\n"
    )

    duties_list = job.get("duties") or []
    perks_list = job.get("perks") or []

    duties_part = ""
    if duties_list:
        d_items = "\n".join([f"  • {html.escape(str(d))}" for d in duties_list[:3]])
        duties_part = f"\n🛠 <b>Vazifalar:</b>\n{d_items}\n"

    perks_part = ""
    if perks_list:
        p_items = "\n".join([f"  ✨ {html.escape(str(p))}" for p in perks_list[:3]])
        perks_part = f"\n🎁 <b>Imtiyozlar:</b>\n{p_items}\n"

    full_text = header + duties_part + perks_part

    if len(full_text) > max_len:
        excess = len(full_text) - max_len + 10
        if len(perks_part) > excess:
            perks_part = perks_part[:-excess] + "...\n"
            full_text = header + duties_part + perks_part
        elif len(duties_part) > excess:
            duties_part = duties_part[:-excess] + "...\n"
            full_text = header + duties_part
        else:
            full_text = full_text[:max_len - 5] + "..."

    return full_text


@router.callback_query(JobCarouselCallback.filter(F.action == "view"))
@router.callback_query(StudentJobAction.filter(F.action == "view"))
async def process_view_job_details(call: CallbackQuery, callback_data: Any):
    """
    Vakansiya tafsilotlarini o'sha xabarning o'zida tahrirlab (edit qilib) ko'rsatadi!
    HTML parse mode va 1000 belgilik cheklov orqali hech qachon xatolik yuz bermaydi.
    """
    await call.answer()
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    job_id = callback_data.job_id
    page = getattr(callback_data, "page", 0)
    section = getattr(callback_data, "section", "all")

    job = await JobsRepo.get_by_id(job_id)
    if not job:
        await call.answer("Vakansiya topilmadi.", show_alert=True)
        return

    details_text = format_job_details(job, max_len=1000)
    map_url = f"https://maps.google.com/?q={job.get('lat')},{job.get('lon')}" if job.get("lat") and job.get("lon") else None

    # Allaqachon ariza berilganmi?
    student = await StudentsRepo.get_by_tg_id(call.from_user.id)
    already_applied = False
    if student:
        existing = await db.fetchval(
            "SELECT id FROM applications WHERE job_id = $1 AND student_id = $2",
            job["id"], student["id"]
        )
        already_applied = bool(existing)

    buttons = []
    
    # Ariza tugmasi
    if already_applied:
        apply_btn = InlineKeyboardButton(text="✅ Ariza topshirilgan", callback_data="already_applied_info")
    else:
        apply_btn = InlineKeyboardButton(
            text="✅ Ariza topshirish",
            callback_data=JobCarouselCallback(section=section, page=page, action="apply", job_id=job["id"]).pack()
        )

    # 1-qator: Orqaga qaytish va Ariza berish
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Ro'yxatga qaytish",
            callback_data=JobCarouselCallback(section=section, page=page, action="back", job_id=job["id"]).pack()
        ),
        apply_btn
    ])

    if map_url:
        buttons.append([InlineKeyboardButton(text="🗺 Xaritada ko'rish (Google Maps)", url=map_url)])

    buttons.append([
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_carousel")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Shu xabarni tahrirlaymiz
    is_photo_msg = bool(getattr(call.message, "photo", None))
    try:
        if is_photo_msg:
            await call.message.edit_caption(caption=details_text, reply_markup=kb, parse_mode="HTML")
        else:
            await call.message.edit_text(text=details_text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"View details edit error: {e}")
        try:
            await call.message.answer(details_text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


@router.callback_query(JobCarouselCallback.filter(F.action == "back"))
async def process_back_to_carousel(call: CallbackQuery, callback_data: JobCarouselCallback):
    """Batafsil oynasidan ro'yxatga qaytish — xuddi o'sha sahifaga qaytadi"""
    await call.answer()
    await show_filtered_carousel(call, section=callback_data.section, page=callback_data.page, is_edit=True)


# ============================================================================
# 6. ARIZA TOPSHIRISH (APPLY) — SHU JOYDA STATUS YANGILANADI
# ============================================================================

@router.callback_query(JobCarouselCallback.filter(F.action == "apply"))
@router.callback_query(StudentJobAction.filter(F.action == "apply"))
async def process_apply(call: CallbackQuery, callback_data: Any):
    """
    Ariza topshirish:
    Sessiya qulfi tekshiriladi, ariza yoziladi, Telegram push ketadi,
    va xabardagi tugma [✅ Ariza topshirilgan] ga aylanadi.
    """
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    student = await StudentsRepo.get_by_tg_id(call.from_user.id)
    if not student:
        await call.answer("Avval ro'yxatdan o'ting!", show_alert=True)
        return

    job_id = callback_data.job_id
    page = getattr(callback_data, "page", 0)
    section = getattr(callback_data, "section", "all")

    job = await JobsRepo.get_by_id(job_id)
    if not job:
        await call.answer("Vakansiya topilmadi.", show_alert=True)
        return

    # 1. Sessiya / Imtihon qulfi tekshiruvi (OTM Tyutori cheklovi)
    from datetime import date
    today = date.today()
    exam_from = student.get("exam_from")
    exam_to = student.get("exam_to")
    if exam_from and exam_to:
        try:
            ef = date.fromisoformat(str(exam_from)) if isinstance(exam_from, str) else exam_from
            et = date.fromisoformat(str(exam_to)) if isinstance(exam_to, str) else exam_to
            if ef <= today <= et:
                lock_alert = (
                    f"🔒 DIQQAT: Sizda {exam_from} dan {exam_to} gacha sessiya va imtihon qulfi faol!\n\n"
                    f"OTM Tyutoringiz tomonidan sessiya qulfi o'rnatilganligi sababli, "
                    f"bu davrda yangi ishlarga ariza topshirish vaqtincha bloklangan."
                )
                await call.answer(lock_alert, show_alert=True)
                return
        except Exception as e:
            logger.warning(f"Exam lock check error in process_apply: {e}")

    # 2. Allaqachon ariza berilganligini tekshirish
    existing_app = await db.fetchrow(
        "SELECT id, status FROM applications WHERE job_id = $1 AND student_id = $2",
        job["id"], student["id"]
    )
    if existing_app:
        await call.answer("Siz ushbu vakansiyaga allaqachon ariza yuborgansiz!", show_alert=True)
        return

    # 3. Yosh himoyasi tekshiruvi (Mehnat kodeksi 411-modda)
    if student.get("age", 19) < 18 and (is_night_job(job) or job.get("min_age", 16) >= 18):
        await call.answer("Kechirasiz, 18 yoshgacha bo'lgan talabalarga tungi va 18+ ishlar taqiqlangan.", show_alert=True)
        return

    # 4. Kontrakt granti uchun GPA tekshiruvi
    min_gpa = float(job.get("min_gpa_required") or 0.0)
    student_gpa = float(student.get("gpa_score") or 0.0)
    if min_gpa > 0.0 and student_gpa < min_gpa:
        await call.answer(f"GPA yetarli emas ({student_gpa} < {min_gpa}).", show_alert=True)
        return

    # 5. Arizani bazada yaratish
    app_id = await ApplicationsRepo.create_application(
        job_id=job["id"],
        student_id=student["id"],
        match_score=95.0,
    )

    await call.answer("🎉 Arizangiz muvaffaqiyatli qabul qilindi!", show_alert=True)

    # 6. Shu xabardagi tugmani yangilash ([✅ Ariza topshirilgan] ga o'tkazish)
    try:
        current_kb = call.message.reply_markup
        if current_kb and current_kb.inline_keyboard:
            new_rows = []
            for row in current_kb.inline_keyboard:
                new_row = []
                for btn in row:
                    if btn.callback_data and (":apply:" in btn.callback_data or (btn.callback_data.startswith("jcar:") and ":apply:" in btn.callback_data)):
                        new_row.append(InlineKeyboardButton(text="✅ Ariza topshirilgan", callback_data="already_applied_info"))
                    else:
                        new_row.append(btn)
                new_rows.append(new_row)
            await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_rows))
    except Exception as e:
        logger.debug(f"Reply markup edit xatosi: {e}")

    # 7. Tasdiq xabari yuborish
    reply_text = (
        f"🎉 <b>Arizangiz muvaffaqiyatli yuborildi!</b>\n\n"
        f"🏢 <b>Tashkilot:</b> {html.escape(str(job.get('company_name')))}\n"
        f"📋 <b>Vakansiya:</b> {html.escape(str(job.get('title')))}\n\n"
        f"Ish beruvchi kadrlar bo'limi nomzodingizni ko'rib chiqmoqda. Natija chiqishi bilan bot orqali sizga bildirishnoma boradi."
    )
    await call.message.reply(reply_text, parse_mode="HTML")

    # 8. Ish beruvchiga zudlik bilan Telegram orqali bildirishnoma yuborish
    try:
        emp_tg = await db.fetchval(
            "SELECT u.tg_id FROM employers e JOIN users u ON e.user_id = u.id WHERE e.id = $1",
            job.get("employer_id")
        )
        if emp_tg:
            await call.bot.send_message(
                emp_tg,
                f"📩 <b>Yangi Nomzod arizasi kelib tushdi!</b>\n\n"
                f"💼 <b>Vakansiya:</b> {html.escape(str(job.get('title')))}\n"
                f"👤 <b>Talaba:</b> {html.escape(str(student.get('full_name')))}\n"
                f"🎓 <b>Yo'nalish:</b> {html.escape(str(student.get('major')))} ({student.get('course')}-kurs)\n"
                f"⭐ <b>GPA:</b> {student.get('gpa_score')}\n\n"
                f"<i>Nomzodni ko'rib chiqish uchun botdagi '📥 Yangi arizalar (Inbox)' bo'limiga kiring.</i>",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.debug(f"Notify employer failed: {e}")

    # 9. Adminlarga bildirishnoma
    try:
        for admin_id in settings.ADMIN_IDS:
            await call.bot.send_message(
                admin_id,
                f"📢 <b>Yangi ariza:</b>\n"
                f"Talaba: <b>{html.escape(str(student.get('full_name')))}</b>\n"
                f"Vakansiya: <b>{html.escape(str(job.get('title')))}</b> ({html.escape(str(job.get('company_name')))})",
                parse_mode="HTML"
            )
    except Exception:
        pass


# ============================================================================
# 7. BILDIRISHNOMALARGA OBUNA BO'LISH
# ============================================================================

@router.callback_query(F.data == "notify_me_subscription")
async def process_notify_me(call: CallbackQuery):
    alert_txt = "Bildirishnomalarga obuna bo'ldingiz! Sizga mos yangi ish chiqishi bilan bot zudlik bilan xabar yuboradi."
    await call.answer(alert_txt, show_alert=True)
    await call.message.reply(f"🔔 <b>{alert_txt}</b>", parse_mode="HTML")
