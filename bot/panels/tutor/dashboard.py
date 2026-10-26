import io
import csv
import logging
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.core.i18n import get_button_variants, get_i18n
from bot.core.constants import UserRole
from bot.db.connection import db
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.tutors_repo import TutorsRepo
from bot.db.repositories.internship_repo import InternshipRepo

logger = logging.getLogger(__name__)

router = Router()


class TutorExamStates(StatesGroup):
    enter_dates = State()
    enter_single_dates = State()


async def get_or_create_tutor_record(user_id: int, tg_id: int, lang: str = "uz") -> dict:
    """Tyutor yozuvini oladi yoki test/admin uchun avtomatik bazada yaratadi."""
    tutor = await TutorsRepo.get_by_tg_id(tg_id)
    if not tutor:
        user = await UsersRepo.get_by_tg_id(tg_id)
        u_id = user["id"] if user else 1
        t_id = await TutorsRepo.create_or_update(
            user_id=u_id,
            full_name="Bosh Tyutor",
            university="Urganch Davlat Universiteti (UrDU)",
            faculty="Raqamli texnologiyalar va sun'iy intellekt",
            group_name="Dasturiy injiniring 211-guruh",
            phone_number="+998901234567"
        )
        # Mavjud biriktirilmagan talabalarni avtomatik shu tyutorga biriktirish
        await db.execute("UPDATE students SET tutor_id = $1 WHERE tutor_id IS NULL", t_id)
        tutor = await TutorsRepo.get_by_id(t_id)
    return tutor


async def notify_students(
    bot: Bot,
    students: List[Dict[str, Any]],
    is_locked: bool,
    exam_from: str = "",
    exam_to: str = "",
    tutor_name: str = "OTM Tyutoringiz",
):
    """Sessiya qulfi o'rnatilganda yoki ochilganda barcha talabalarga avtomatik xabar yuborish."""
    for s in students:
        tg_id = s.get("tg_id")
        if not tg_id:
            continue
        try:
            if is_locked:
                text = (
                    f"🔒 **DIQQAT: Sessiya va Imtihonlar Qulfi Faollashdi!**\n\n"
                    f"🏛 OTM Tyutoringiz **{tutor_name}** tomonidan sessiya qulfi o'rnatildi.\n"
                    f"📅 Muddat: **{exam_from}** dan **{exam_to}** gacha\n\n"
                    f"⛔️ **Pauza rejimi:** Ushbu davrda yangi ishlarga ariza topshirish va yangi ish qabul qilish "
                    f"vaqtincha to'xtatildi. Barcha e'tiboringizni imtihonlarga qarating!"
                )
            else:
                text = (
                    f"🔓 **Xushxabar! Sessiya Qulfi Ochildi!**\n\n"
                    f"Tyutoringiz tomonidan sessiya cheklovi bekor qilindi.\n"
                    f"Endi siz yana bo'sh ish o'rinlari va davlat amaliyotlariga bemalol ariza topshirishingiz mumkin."
                )
            await bot.send_message(tg_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.debug(f"Talabaga push bildirishnoma yetib bormadi (tg_id={tg_id}): {e}")


async def notify_single_student(
    bot: Bot,
    student_tg_id: Optional[int],
    is_locked: bool,
    exam_from: str = "",
    exam_to: str = "",
    tutor_name: str = "OTM Tyutoringiz",
):
    """Yakka talabaga sessiya qulfi bildirishnomasi."""
    if not student_tg_id:
        return
    try:
        if is_locked:
            text = (
                f"🔒 **DIQQAT: Sessiya Qulfi Faollashdi!**\n\n"
                f"Tyutoringiz **{tutor_name}** tomonidan hisobingizga sessiya qulfi belgilandi ({exam_from} – {exam_to}).\n"
                f"Yangi ishlarga arizalar topshirish vaqtincha to'xtatildi."
            )
        else:
            text = (
                f"🔓 **Sessiya Qulfi Ochildi!**\n\n"
                f"Tyutoringiz tomonidan hisobingizdagi sessiya cheklovi bekor qilindi. Ish qidirish qayta faollashdi."
            )
        await bot.send_message(student_tg_id, text, parse_mode="Markdown")
    except Exception as e:
        logger.debug(f"Push notification error (tg_id={student_tg_id}): {e}")


def generate_tutor_csv(tutor: dict, students: List[Dict[str, Any]]) -> bytes:
    """Tyutorning guruhi uchun rasmiy CSV/Excel hisobot fayli yaratish."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([f"--- {tutor.get('university', 'OTM')} | {tutor.get('group_name', 'Guruh')} BANDLIK VA AMALIYOT HISOBOTI ---"])
    writer.writerow([f"Tyutor: {tutor.get('full_name')} | Tel: {tutor.get('phone_number')} | Sana: {date.today()}"])
    writer.writerow([])
    writer.writerow([
        "№", "Talaba F.I.Sh", "OTM", "Fakultet / Guruh", "Kurs",
        "Mutaxassislik", "Telefon", "GPA", "Ish Joyi (Korxona)",
        "Lavozim", "Bandlik Holati", "Sessiya Holati"
    ])
    today = date.today()
    for idx, s in enumerate(students, start=1):
        if s.get("active_job_title"):
            emp_status = "Band (Ishlamoqda)"
            job_info = s.get("active_job_title")
        else:
            emp_status = "Ish qidirmoqda (Band emas)"
            job_info = "-"

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
                    exam_status = f"Rejalashtirilgan ({ef} - {et})"
            except Exception:
                exam_status = f"Qulf ({ef} - {et})"

        writer.writerow([
            idx,
            s.get("full_name"),
            s.get("university") or tutor.get("university"),
            f"{s.get('faculty')} ({tutor.get('group_name', '')})",
            s.get("course_label") or f"{s.get('course', 1)}-kurs",
            s.get("major") or s.get("faculty"),
            s.get("phone_number") or "-",
            s.get("gpa_score") or "0.0",
            s.get("active_company") or (job_info.split("(")[1].rstrip(")") if "(" in job_info else "-"),
            s.get("active_title") or (job_info.split("(")[0].strip() if "(" in job_info else "-"),
            emp_status,
            exam_status
        ])
    return output.getvalue().encode("utf-8-sig")


# ==========================================
# 1. MENING TALABALARIM VA ULARNING ISH JOYLARI
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_TUTOR_STUDENTS")))
@router.callback_query(F.data == "tutor_refresh_students")
async def show_tutor_students(event):
    msg = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer("Ma'lumotlar yangilandi!")

    lang = await UsersRepo.get_user_lang(user_id)
    tutor = await get_or_create_tutor_record(user_id, user_id, lang)
    students = await TutorsRepo.get_tutor_students(tutor["id"])

    if not students:
        empty_text = (
            "👥 **Mening talabalarim ro'yxati:**\n\n"
            "Hozircha sizga biriktirilgan talabalar mavjud emas.\n"
            "Talabalar botda ro'yxatdan o'tganda yoki admin tomonidan guruh bo'yicha biriktirilgach shu yerda aks etadi."
        ) if lang == "uz" else (
            "👥 **Список моих студентов:**\n\n"
            "Пока за вами не закреплены студенты."
        ) if lang == "ru" else (
            "👥 **My Students List:**\n\n"
            "No students assigned yet."
        )
        await msg.answer(empty_text)
        return

    employed_count = sum(1 for s in students if s.get("active_job_title"))
    today = date.today()
    locked_count = 0
    for s in students:
        ef, et = s.get("exam_from"), s.get("exam_to")
        if ef and et:
            try:
                ef_d = date.fromisoformat(str(ef)) if isinstance(ef, str) else ef
                et_d = date.fromisoformat(str(et)) if isinstance(et, str) else et
                if ef_d <= today <= et_d:
                    locked_count += 1
            except Exception:
                pass

    text = (
        f"👥 **Guruh talabalari monitoringi ({len(students)} nafar):**\n"
        f"🏛 OTM: **{tutor.get('university')}**\n"
        f"📂 Fakultet / Guruh: **{tutor.get('faculty')}** ({tutor.get('group_name') or 'Barcha guruhlar'})\n"
        f"💼 Band bo'lganlar (ishlayotganlar): **{employed_count} / {len(students)} nafar** ({round(employed_count/len(students)*100, 1)}%)\n"
        f"🔒 Sessiya qulfidagilar: **{locked_count} nafar**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Batafsil ma'lumot va individual qulfni boshqarish uchun talabaning ustiga bosing:*\n\n"
    )

    inline_keyboard = []
    # Talabalar ro'yxatini interaktiv tugmalar ko'rinishida chiqarish
    for idx, s in enumerate(students[:10], start=1):
        if s.get("active_job_title"):
            job_icon = "💼 Band"
            job_status = f"💼 {s.get('active_job_title')}"
        else:
            job_icon = "🔍 Qidirmoqda"
            job_status = "🔍 Ish qidirmoqda"

        ef, et = s.get("exam_from"), s.get("exam_to")
        lock_icon = "🔓"
        if ef and et:
            try:
                ef_d = date.fromisoformat(str(ef)) if isinstance(ef, str) else ef
                et_d = date.fromisoformat(str(et)) if isinstance(et, str) else et
                if ef_d <= today <= et_d:
                    lock_icon = "🔒"
            except Exception:
                pass

        course_str = s.get("course_label") or f"{s.get('course', 1)}-kurs"
        text += (
            f"{idx}. 🎓 **{s.get('full_name')}** ({course_str})\n"
            f"   {job_status} | GPA: **{s.get('gpa_score') or '0.0'}** ⭐ {lock_icon}\n"
        )

        btn_title = f"{idx}. 🎓 {s.get('full_name')[:18]} ({job_icon}) {lock_icon}"
        inline_keyboard.append([
            InlineKeyboardButton(text=btn_title, callback_data=f"tutor_stu_{s['id']}")
        ])

    # Pastki boshqaruv tugmalari
    inline_keyboard.append([
        InlineKeyboardButton(text="📥 Guruh hisoboti (CSV yuklab olish)", callback_data="tutor_export_csv"),
    ])
    inline_keyboard.append([
        InlineKeyboardButton(text="🔒 Sessiya qulfini boshqarish", callback_data="tutor_exam_panel_open"),
        InlineKeyboardButton(text="📊 Bandlik tahlili", callback_data="tutor_employment_details"),
    ])
    inline_keyboard.append([
        InlineKeyboardButton(text="🔄 Ro'yxatni yangilash", callback_data="tutor_refresh_students"),
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    if isinstance(event, CallbackQuery):
        await msg.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


# ==========================================
# 1.1 TALABA ANKETASI VA INDIVIDUAL NAZORAT
# ==========================================
@router.callback_query(F.data.startswith("tutor_stu_") & ~F.data.startswith("tutor_stu_lock_") & ~F.data.startswith("tutor_stu_unlock_") & ~F.data.startswith("tutor_stu_logs_"))
async def process_view_student_dossier(call: CallbackQuery):
    student_id = int(call.data.replace("tutor_stu_", ""))
    student = await TutorsRepo.get_student_by_id(student_id)
    if not student:
        await call.answer("Talaba topilmadi.", show_alert=True)
        return

    await call.answer()
    today = date.today()

    # Amaliyot daftarchasi soatlari
    internship_hours = await InternshipRepo.get_total_hours(student_id)

    # Sessiya qulfi holati
    ef = student.get("exam_from")
    et = student.get("exam_to")
    is_locked = False
    lock_text = "🔓 Ochiq (Sessiya qulfi yo'q)"
    if ef and et:
        try:
            ef_d = date.fromisoformat(str(ef)) if isinstance(ef, str) else ef
            et_d = date.fromisoformat(str(et)) if isinstance(et, str) else et
            if ef_d <= today <= et_d:
                is_locked = True
                lock_text = f"🔒 Faol qulfda ({ef} – {et})"
            else:
                lock_text = f"📅 Rejalashtirilgan ({ef} – {et})"
        except Exception:
            is_locked = True
            lock_text = f"🔒 Faol ({ef} – {et})"

    # Ish joyi
    if student.get("active_job_title"):
        job_info = (
            f"🏢 **Korxona / Tashkilot:** {student.get('active_company') or '-'}\n"
            f"💼 **Lavozim:** {student.get('active_title') or student.get('active_job_title')}\n"
            f"📞 **Ish beruvchi telefoni:** `{student.get('employer_phone') or 'Kiritilmagan'}`\n"
            f"📍 **Ish joyi manzili:** {student.get('employer_address') or 'Urganch'}"
        )
    else:
        job_info = "🔍 **Holati:** Hozirda ish qidirmoqda (Faol ishga kirmagan)"

    contract_info = "To'lov-kontrakt" if student.get("is_contract") else "Davlat granti"
    course_str = student.get("course_label") or f"{student.get('course', 1)}-kurs"
    loc_str = student.get("location_name") or "Urganch shahri"

    dossier_text = (
        f"🎓 **Talaba Monitoring Karti (Dossier):**\n\n"
        f"• **F.I.Sh:** {student.get('full_name')}\n"
        f"• **OTM:** {student.get('university') or 'UrDU'}\n"
        f"• **Fakultet / Yo'nalish:** {student.get('faculty')} — {student.get('major')}\n"
        f"• **Bosqich:** {course_str} ({contract_info})\n"
        f"• **GPA o'zlashtirish:** **{student.get('gpa_score') or '0.0'}** / 5.0 ⭐\n"
        f"• **Telefon:** `{student.get('phone_number') or 'Mavjud emas'}`\n"
        f"• **Yashash joyi:** {loc_str}\n"
        f"• **Amaliyot daftarchasi:** **{internship_hours} soat** tasdiqlangan 📜\n"
        f"• **Sessiya holati:** {lock_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 **BANDLIK MA'LUMOTI:**\n"
        f"{job_info}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
    )

    buttons = []
    if is_locked:
        buttons.append([
            InlineKeyboardButton(text="🔓 Qulfni ochish (Ish qidirishga ruxsat)", callback_data=f"tutor_stu_unlock_{student_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🔒 Sessiya qulfi qo'yish (20 kun)", callback_data=f"tutor_stu_lock_{student_id}")
        ])

    buttons.append([
        InlineKeyboardButton(text="📜 Amaliyot kundaligini ko'rish", callback_data=f"tutor_stu_logs_{student_id}"),
        InlineKeyboardButton(text="⬅️ Talabalar ro'yxati", callback_data="tutor_refresh_students")
    ])

    await call.message.edit_text(dossier_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


# --- 1.2 YAKKA TALABAGA QULF QO'YISH / YECHISH ---
@router.callback_query(F.data.startswith("tutor_stu_lock_"))
async def process_tutor_lock_single_student(call: CallbackQuery, bot: Bot):
    student_id = int(call.data.replace("tutor_stu_lock_", ""))
    tutor = await get_or_create_tutor_record(call.from_user.id, call.from_user.id)
    student = await TutorsRepo.get_student_by_id(student_id)

    today = date.today()
    end_date = today + timedelta(days=20)
    ef_str = str(today)
    et_str = str(end_date)

    await TutorsRepo.set_exam_lock(tutor["id"], ef_str, et_str, student_id=student_id)
    await call.answer("🔒 Sessiya qulfi o'rnatildi!", show_alert=True)

    # Talabaga to'g'ridan-to'g'ri push bildirishnoma
    if student:
        await notify_single_student(
            bot=bot,
            student_tg_id=student.get("tg_id"),
            is_locked=True,
            exam_from=ef_str,
            exam_to=et_str,
            tutor_name=tutor.get("full_name", "Tyutoringiz")
        )

    # Kartaga qaytish
    call.data = f"tutor_stu_{student_id}"
    await process_view_student_dossier(call)


@router.callback_query(F.data.startswith("tutor_stu_unlock_"))
async def process_tutor_unlock_single_student(call: CallbackQuery, bot: Bot):
    student_id = int(call.data.replace("tutor_stu_unlock_", ""))
    tutor = await get_or_create_tutor_record(call.from_user.id, call.from_user.id)
    student = await TutorsRepo.get_student_by_id(student_id)

    await TutorsRepo.clear_exam_lock(tutor["id"], student_id=student_id)
    await call.answer("🔓 Sessiya qulfi ochildi!", show_alert=True)

    # Talabaga push bildirishnoma
    if student:
        await notify_single_student(
            bot=bot,
            student_tg_id=student.get("tg_id"),
            is_locked=False,
            tutor_name=tutor.get("full_name", "Tyutoringiz")
        )

    # Kartaga qaytish
    call.data = f"tutor_stu_{student_id}"
    await process_view_student_dossier(call)


# --- 1.3 TALABA AMALIYOT KUNDALIGI KO'RINIShI ---
@router.callback_query(F.data.startswith("tutor_stu_logs_"))
async def process_view_student_logs(call: CallbackQuery):
    student_id = int(call.data.replace("tutor_stu_logs_", ""))
    student = await TutorsRepo.get_student_by_id(student_id)
    logs = await InternshipRepo.get_logs_by_student(student_id)

    await call.answer()
    name = student.get("full_name", "Talaba") if student else "Talaba"
    text = f"📜 **{name} — Amaliyot Kundaligi Qaydlari:**\n\n"

    if not logs:
        text += "Talaba hozircha amaliyot kundaligiga soatlar yoki vazifalar kiritmagan."
    else:
        for idx, l in enumerate(logs[:7], start=1):
            verified = "✅ Tasdiqlangan" if l.get("verified_by_mentor") else "⏳ Kutilmoqda"
            text += (
                f"{idx}. 📅 Sana: **{l.get('visit_date')}** ({l.get('hours_spent')} soat)\n"
                f"   🏢 {l.get('company_name')} | Holati: {verified}\n"
                f"   📝 Vazifa: _{l.get('tasks_performed', '')}_\n\n"
            )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Talaba kartiga qaytish", callback_data=f"tutor_stu_{student_id}")]
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


# ==========================================
# 1.4 GURUH HISOBOTINI CSV FORMATDA YUKLAB OLISH
# ==========================================
@router.callback_query(F.data == "tutor_export_csv")
async def process_tutor_export_csv(call: CallbackQuery):
    await call.answer("Hisobot tayyorlanmoqda...")
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    tutor = await get_or_create_tutor_record(call.from_user.id, call.from_user.id, lang)
    students = await TutorsRepo.get_tutor_students(tutor["id"])

    csv_bytes = generate_tutor_csv(tutor, students)
    filename = f"bandlik_hisoboti_{tutor.get('group_name', 'guruh')}_{date.today()}.csv".replace(" ", "_")
    document = BufferedInputFile(csv_bytes, filename=filename)

    caption = (
        f"📊 **OTM Tyutori Rasmiy Bandlik Hisoboti (CSV / Excel)**\n\n"
        f"🏛 OTM: **{tutor.get('university')}**\n"
        f"📂 Guruh: **{tutor.get('group_name') or 'Barcha biriktirilgan talabalar'}**\n"
        f"👥 Talabalar soni: **{len(students)} nafar**\n"
        f"📅 Sana: **{date.today()}**\n\n"
        f"Ushbu faylni to'g'ridan-to'g'ri Microsoft Excel dasturida ochib, Dekanat yoki Rektoratga taqdim etishingiz mumkin."
    )

    await call.message.answer_document(document=document, caption=caption, parse_mode="Markdown")


# ==========================================
# 2. SESSIYA / IMTIHON QULFI PANELI
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_TUTOR_EXAM_LOCK")))
@router.callback_query(F.data == "tutor_exam_panel_open")
async def show_tutor_exam_panel(event):
    msg = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()

    lang = await UsersRepo.get_user_lang(user_id)
    tutor = await get_or_create_tutor_record(user_id, user_id, lang)
    students = await TutorsRepo.get_tutor_students(tutor["id"])

    today = date.today()
    locked_students = []
    current_dates = None

    for s in students:
        ef = s.get("exam_from")
        et = s.get("exam_to")
        if ef and et:
            try:
                ef_d = date.fromisoformat(str(ef)) if isinstance(ef, str) else ef
                et_d = date.fromisoformat(str(et)) if isinstance(et, str) else et
                if ef_d <= today <= et_d:
                    locked_students.append(s)
                    current_dates = f"{ef} – {et}"
            except Exception:
                pass

    if locked_students:
        status_text = (
            f"🔒 **STATUS: SESSIYA QULFI FAOL!**\n"
            f"📅 Amaldagi davr: **{current_dates}**\n"
            f"👥 Qulfdagi talabalar soni: **{len(locked_students)} nafar**\n\n"
            f"⛔️ **Qulf rejimi qoidasi:** Hozirda sizning talabalaringiz yangi ishlarga ariza bera olmaydi, "
            f"barcha bo'sh ish takliflari pauzaga olingan va talabalar faqat imtihonlarga tayyorlanmoqda."
        )
    else:
        status_text = (
            f"🔓 **STATUS: SESSIYA QULFI O'CHIRILGAN**\n\n"
            f"Talabalar hozirda ochiq rejimda: ular qulay bo'sh ishlarni qidirishi, "
            f"ariza topshirishi va amaliyot dasturlariga qatnashishi mumkin.\n\n"
            f"💡 *Sessiya yoki imtihonlar boshlanganda quyidagi tugma orqali guruhga qulf o'rnating.*"
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔒 Guruhga sessiya qulfini yoqish", callback_data="tutor_lock_dates_prompt"),
                InlineKeyboardButton(text="⚡ 20 kunlik tezkor qulf", callback_data="tutor_lock_preset_20d"),
            ],
            [
                InlineKeyboardButton(text="🔓 Qulfni ochish (Bekor qilish)", callback_data="tutor_unlock_all"),
            ],
            [
                InlineKeyboardButton(text="📥 Guruh hisoboti (CSV)", callback_data="tutor_export_csv"),
                InlineKeyboardButton(text="👥 Mening talabalarim", callback_data="tutor_refresh_students"),
            ]
        ]
    )

    full_msg = (
        f"📚 **Sessiya va Imtihonlar Boshqaruvi (Eksklyuziv Tyutor Paneli):**\n\n"
        f"OTM: **{tutor.get('university')}** | Guruh: **{tutor.get('group_name') or 'Barcha'}**\n\n"
        f"{status_text}"
    )

    if isinstance(event, CallbackQuery):
        await msg.edit_text(full_msg, reply_markup=kb, parse_mode="Markdown")
    else:
        await msg.answer(full_msg, reply_markup=kb, parse_mode="Markdown")


# --- 2.1 Tezkor 20 kunlik qulf ---
@router.callback_query(F.data == "tutor_lock_preset_20d")
async def process_tutor_lock_preset_20d(call: CallbackQuery, bot: Bot):
    tutor = await get_or_create_tutor_record(call.from_user.id, call.from_user.id)
    students = await TutorsRepo.get_tutor_students(tutor["id"])

    today = date.today()
    end_date = today + timedelta(days=20)
    ef_str = str(today)
    et_str = str(end_date)

    await TutorsRepo.set_exam_lock(tutor["id"], ef_str, et_str)
    await call.answer("✅ 20 kunlik sessiya qulfi yoqildi!", show_alert=True)

    # Barcha talabalarga push bildirishnoma
    await notify_students(
        bot=bot,
        students=students,
        is_locked=True,
        exam_from=ef_str,
        exam_to=et_str,
        tutor_name=tutor.get("full_name", "Tyutoringiz")
    )

    await call.message.edit_text(
        f"🔒 **Sessiya qulfi muvaffaqiyatli o'rnatildi!**\n\n"
        f"📅 Boshlanish sanasi: **{ef_str}**\n"
        f"📅 Tugash sanasi: **{et_str}** (20 kun davomida)\n"
        f"👥 Guruhdagi **{len(students)} nafar talabaga** xabar yuborildi va yangi ishlarga ariza topshirish to'liq pauzaga o'tkazildi.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔓 Qulfni bekor qilish", callback_data="tutor_unlock_all")],
                [InlineKeyboardButton(text="👥 Talabalar holatini ko'rish", callback_data="tutor_refresh_students")]
            ]
        )
    )


# --- 2.2 Qo'lda sana kiritish ---
@router.callback_query(F.data == "tutor_lock_dates_prompt")
async def process_tutor_lock_dates_prompt(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(TutorExamStates.enter_dates)
    prompt = (
        "📅 **Sessiya va imtihonlar sanasi oralig'ini kiriting:**\n\n"
        "Format: `YYYY-MM-DD - YYYY-MM-DD`\n"
        "*(Masalan: `2026-06-01 - 2026-06-25` yoki `2026-05-15 - 2026-06-10`)*\n\n"
        "Shu davr mobaynida talabalar yangi ishlarga ariza bera olmaydi."
    )
    await call.message.answer(prompt, parse_mode="Markdown")


@router.message(TutorExamStates.enter_dates, F.text)
async def process_tutor_dates_input(msg: Message, state: FSMContext, bot: Bot):
    await state.clear()
    tutor = await get_or_create_tutor_record(msg.from_user.id, msg.from_user.id)
    students = await TutorsRepo.get_tutor_students(tutor["id"])
    text = msg.text.strip()

    if "-" in text and len(text.split("-")) >= 4:
        parts = text.split(" - ") if " - " in text else text.split("-")
        if len(parts) == 2:
            ef_str = parts[0].strip()
            et_str = parts[1].strip()
        else:
            ef_str = str(date.today())
            et_str = str(date.today() + timedelta(days=25))
    else:
        ef_str = str(date.today())
        et_str = str(date.today() + timedelta(days=25))

    await TutorsRepo.set_exam_lock(tutor["id"], ef_str, et_str)

    # Barcha talabalarga push bildirishnoma
    await notify_students(
        bot=bot,
        students=students,
        is_locked=True,
        exam_from=ef_str,
        exam_to=et_str,
        tutor_name=tutor.get("full_name", "Tyutoringiz")
    )

    res_txt = (
        f"🔒 **Sessiya qulfi o'rnatildi!**\n\n"
        f"📅 Muddat: **{ef_str}** dan **{et_str}** gacha\n"
        f"🏛 Guruhdagi **{len(students)} nafar talabaga** avtomatik ogohlantirish yuborildi va ariza topshirish to'xtatildi.\n\n"
        f"Imtihonlar tugagach yoki xohlagan paytingizda qulfni ochishingiz mumkin."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Qulfni ochish", callback_data="tutor_unlock_all")],
            [InlineKeyboardButton(text="👥 Talabalarni ko'rish", callback_data="tutor_refresh_students")]
        ]
    )
    await msg.answer(res_txt, reply_markup=kb, parse_mode="Markdown")


# --- 2.3 Sessiya qulfini bekor qilish ---
@router.callback_query(F.data == "tutor_unlock_all")
async def process_tutor_unlock_all(call: CallbackQuery, bot: Bot):
    tutor = await get_or_create_tutor_record(call.from_user.id, call.from_user.id)
    students = await TutorsRepo.get_tutor_students(tutor["id"])

    await TutorsRepo.clear_exam_lock(tutor["id"])
    await call.answer("🔓 Sessiya qulfi ochildi!", show_alert=True)

    # Barcha talabalarga push bildirishnoma
    await notify_students(
        bot=bot,
        students=students,
        is_locked=False,
        tutor_name=tutor.get("full_name", "Tyutoringiz")
    )

    await call.message.edit_text(
        "🔓 **Sessiya qulfi bekor qilindi (Ochildi)!**\n\n"
        f"Guruhdagi **{len(students)} nafar talabaga** xushxabar yuborildi. Ish qidirish va arizalar topshirish qayta faollashtirildi.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔒 Qayta qulf o'rnatish", callback_data="tutor_exam_panel_open")],
                [InlineKeyboardButton(text="👥 Talabalarni ko'rish", callback_data="tutor_refresh_students")]
            ]
        )
    )


# ==========================================
# 3. TALABALAR BANDLIGI VA ISH JOYLARI MONITORINGI
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_TUTOR_EMPLOYMENT")))
@router.callback_query(F.data == "tutor_employment_details")
async def show_tutor_employment(event):
    msg = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()

    lang = await UsersRepo.get_user_lang(user_id)
    tutor = await get_or_create_tutor_record(user_id, user_id, lang)
    students = await TutorsRepo.get_tutor_students(tutor["id"])

    total = len(students)
    employed = [s for s in students if s.get("active_job_title")]
    unemployed = [s for s in students if not s.get("active_job_title")]
    employed_pct = round((len(employed) / total * 100), 1) if total > 0 else 0

    stats_text = (
        f"📊 **Talabalar Bandligi & Ish Joylari Hisoboti:**\n\n"
        f"🏛 OTM: **{tutor.get('university')}**\n"
        f"📂 Guruh: **{tutor.get('group_name') or 'Barcha'}**\n"
        f"👥 Jami biriktirilgan talabalar: **{total} nafar**\n"
        f"💼 Rasmiy ishga joylashganlar: **{len(employed)} nafar ({employed_pct}%)**\n"
        f"🔍 Hozirda ish qidirayotganlar: **{len(unemployed)} nafar**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 **Ishlayotgan talabalar ro'yxati va korxonalari:**\n\n"
    )

    if not employed:
        stats_text += "Hozircha guruhda faol ishga qabul qilingan talabalar mavjud emas."
    else:
        for idx, s in enumerate(employed, start=1):
            phone_val = s.get("phone_number") or "Kiritilmagan"
            course_val = s.get("course_label") or f"{s.get('course', 1)}-kurs"
            stats_text += (
                f"{idx}. 🎓 **{s.get('full_name')}** ({course_val})\n"
                f"   🏢 **Ish joyi:** {s.get('active_job_title')}\n"
                f"   📱 Aloqa: `{phone_val}` | GPA: **{s.get('gpa_score') or '0.0'}** ⭐\n\n"
            )

    stats_text += (
        "\n📌 *Ma'lumotlar real vaqt rejimida ish beruvchilar va talabalar "
        "tomonidan tasdiqlangan arizalar asosida shakllanadi.*"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📥 Guruh hisoboti (CSV yuklab olish)", callback_data="tutor_export_csv")],
            [
                InlineKeyboardButton(text="👥 Barcha talabalar", callback_data="tutor_refresh_students"),
                InlineKeyboardButton(text="🔒 Sessiya paneli", callback_data="tutor_exam_panel_open"),
            ]
        ]
    )

    if isinstance(event, CallbackQuery):
        await msg.edit_text(stats_text, reply_markup=kb, parse_mode="Markdown")
    else:
        await msg.answer(stats_text, reply_markup=kb, parse_mode="Markdown")


# ==========================================
# 4. TYUTOR PROFILI
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_TUTOR_PROFILE")))
async def show_tutor_profile(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    tutor = await get_or_create_tutor_record(msg.from_user.id, msg.from_user.id, lang)
    students = await TutorsRepo.get_tutor_students(tutor["id"])

    today = date.today()
    has_exam_lock = False
    for s in students:
        ef = s.get("exam_from")
        et = s.get("exam_to")
        if ef and et:
            try:
                ef_d = date.fromisoformat(str(ef)) if isinstance(ef, str) else ef
                et_d = date.fromisoformat(str(et)) if isinstance(et, str) else et
                if ef_d <= today <= et_d:
                    has_exam_lock = True
                    break
            except Exception:
                pass

    lock_label = "🔒 Faol (Talabalar ish arizalari bloklangan)" if has_exam_lock else "🔓 Ochiq (Sessiya o'chirilgan)"

    text = (
        f"👤 **Tyutor Shaxsiy Profili:**\n\n"
        f"• **F.I.Sh:** {tutor.get('full_name')}\n"
        f"• **Telegram ID:** `{msg.from_user.id}`\n"
        f"• **OTM:** {tutor.get('university')}\n"
        f"• **Fakultet:** {tutor.get('faculty')}\n"
        f"• **Guruh:** {tutor.get('group_name') or 'Biriktirilgan guruhlar'}\n"
        f"• **Aloqa telefoni:** {tutor.get('phone_number') or 'Kiritilmagan'}\n"
        f"• **Nazoratdagi talabalar:** {len(students)} nafar\n"
        f"• **Joriy sessiya qulfi holati:** {lock_label}\n\n"
        f"⚙️ Boshqaruv amallari:"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Talabalarni ko'rish", callback_data="tutor_refresh_students"),
                InlineKeyboardButton(text="🔒 Sessiya qulfi", callback_data="tutor_exam_panel_open"),
            ],
            [
                InlineKeyboardButton(text="📥 Guruh hisoboti (CSV)", callback_data="tutor_export_csv"),
                InlineKeyboardButton(text="📊 Bandlik tahlili", callback_data="tutor_employment_details"),
            ]
        ]
    )

    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")
