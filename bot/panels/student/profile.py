import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.core.i18n import get_i18n, get_button_variants
from bot.core.keyboards import get_location_request_keyboard, get_language_choice_keyboard
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.students_repo import StudentsRepo
from bot.db.repositories.applications_repo import ApplicationsRepo
from bot.db.repositories.internship_repo import InternshipRepo

logger = logging.getLogger(__name__)
router = Router()


class ExamModeStates(StatesGroup):
    exam_dates = State()


class StudentGpaStates(StatesGroup):
    enter_gpa = State()


# ==========================================
# 1. TALABA PROFILI ASOSIY KO'RINIShI
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_STUDENT_PROFILE")))
async def show_profile(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    student = await StudentsRepo.get_by_tg_id(msg.from_user.id)
    if not student:
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    phone = student.get("phone_number") or "Kiritilmagan"
    region = student.get("region") or "Urganch shahri"
    university = student.get("university") or student.get("faculty") or "UrDU"
    course_lbl = student.get("course_label") or f"{student.get('course', 1)}-kurs"
    major = student.get("major") or "Umumiy"
    loc_name = student.get("location_name") or "TTJ / Kvartira"
    radius = student.get("max_distance_km", 5.0)

    # Sessiya holati (Tyutor tomonidan boshqariladi)
    if student.get("exam_from"):
        exam_status = f"🔒 Faol ({student.get('exam_from')} – {student.get('exam_to')}) [Tyutor belgilagan]"
        if lang == "ru":
            exam_status = f"🔒 Активен ({student.get('exam_from')} – {student.get('exam_to')}) [Установлен тьютором]"
        elif lang == "en":
            exam_status = f"🔒 Active ({student.get('exam_from')} – {student.get('exam_to')}) [Set by Tutor]"
    else:
        exam_status = "🔓 Ochiq (Sessiya yo'q)"
        if lang == "ru":
            exam_status = "🔓 Открыт (Сессия не установлена)"
        elif lang == "en":
            exam_status = "🔓 Open (No exam lock)"

    if lang == "ru":
        text = (
            f"👤 **Профиль студента:**\n\n"
            f"• **Имя:** {student.get('full_name')}\n"
            f"• **Телефон:** {phone}\n"
            f"• **Регион:** {region}\n"
            f"• **ВУЗ:** {university}\n"
            f"• **Курс:** {course_lbl}\n"
            f"• **Специальность:** {major}\n"
            f"• **Локация жилья (ТТЖ/Квартира):** {loc_name} (Радиус: {radius} км)\n"
            f"• **Режим сессии / Экзамены:** {exam_status}\n\n"
            f"⚙️ **Управление настройками:**"
        )
        btn_resume = "📄 Smart Резюме"
        btn_lang = "🌐 Сменить язык"
        btn_loc = "📍 Обновить жильё (ТТЖ)"
        btn_diary = "📜 Дневник практики"
        btn_exam = "🔒 Режим сессии (Тьютор)"
        btn_resign = "📄 Заявление об уходе (14 дней)"
    elif lang == "en":
        text = (
            f"👤 **Student Profile:**\n\n"
            f"• **Name:** {student.get('full_name')}\n"
            f"• **Phone:** {phone}\n"
            f"• **Region:** {region}\n"
            f"• **University:** {university}\n"
            f"• **Year:** {course_lbl}\n"
            f"• **Major:** {major}\n"
            f"• **Living Location (Dorm/Flat):** {loc_name} (Radius: {radius} km)\n"
            f"• **Exam Lock Status:** {exam_status}\n\n"
            f"⚙️ **Profile Management:**"
        )
        btn_resume = "📄 Smart Resume"
        btn_lang = "🌐 Change Language"
        btn_loc = "📍 Update Living Location"
        btn_diary = "📜 Internship Logbook"
        btn_exam = "🔒 Exam Lock (Tutor)"
        btn_resign = "📄 14-day Resignation Notice"
    else:
        text = (
            f"👤 **Talaba Profili:**\n\n"
            f"• **Ism:** {student.get('full_name')}\n"
            f"• **Telefon:** {phone}\n"
            f"• **Yashash hududi:** {region}\n"
            f"• **OTM:** {university}\n"
            f"• **Bosqich / Kurs:** {course_lbl}\n"
            f"• **Mutaxassislik:** {major}\n"
            f"• **Yashash joyi (TTJ/Kvartira):** {loc_name} (Radius: {radius} km)\n"
            f"• **Sessiya / Imtihon holati:** {exam_status}\n\n"
            f"⚙️ **Profil sozlamalari va imkoniyatlar:**"
        )
        btn_resume = "📄 Smart Rezyume (Ulashish)"
        btn_lang = "🌐 Tilni o'zgartirish"
        btn_loc = "📍 Joylashuvni yangilash"
        btn_diary = "📜 Amaliyot kundaligi"
        btn_exam = "🔒 Sessiya holati (Tyutor)"
        btn_resign = "📄 14 kunlik ariza shabloni"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=btn_resume, callback_data="profile_smart_resume"),
                InlineKeyboardButton(text=btn_loc, callback_data="update_location_prompt"),
            ],
            [
                InlineKeyboardButton(text=btn_diary, callback_data="profile_internship_diary"),
                InlineKeyboardButton(text=btn_exam, callback_data="toggle_exam_mode"),
            ],
            [
                InlineKeyboardButton(text=btn_lang, callback_data="profile_change_lang"),
                InlineKeyboardButton(text=btn_resign, callback_data="profile_resign_template"),
            ]
        ]
    )

    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


# ==========================================
# 2. PROFIL ICHIDAN TILNI O'ZGARTIRISH
# ==========================================
@router.callback_query(F.data == "profile_change_lang")
async def profile_change_lang_handler(call: CallbackQuery):
    await call.answer()
    lang_prompt = "Tilni tanlang / Выберите язык / Please select language:"
    await call.message.answer(lang_prompt, reply_markup=get_language_choice_keyboard())


# ==========================================
# 3. PROFIL ICHIDAN JOYLASHUVNI YANGILASH
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_STUDENT_LOCATION")))
@router.callback_query(F.data == "update_location_prompt")
async def prompt_update_location(event):
    msg = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()

    lang = await UsersRepo.get_user_lang(user_id)
    prompt = (
        "📍 **Yashash joyingizni (TTJ yoki ijara kvartira) yangilash:**\n"
        "Yaqin atrofdagi mos ishlarni aniq topish uchun lokatsiyangizni yuboring:"
    )
    if lang == "ru":
        prompt = (
            "📍 **Обновление локации жилья (ТТЖ или квартира):**\n"
            "Отправьте геопозицию, чтобы находить работу рядом с домом:"
        )
    elif lang == "en":
        prompt = (
            "📍 **Update your residence location (Dorm or flat):**\n"
            "Send your current location to find jobs close to you:"
        )

    await msg.answer(prompt, reply_markup=get_location_request_keyboard(lang), parse_mode="Markdown")


# ==========================================
# 4. SESSIYA / IMTIHON REJIMI (FAQAT TYUTOR TOMONIDAN BOSHQARILADI)
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_STUDENT_EXAM_MODE")))
@router.callback_query(F.data == "toggle_exam_mode")
async def prompt_exam_mode(event, state: FSMContext):
    msg = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()

    lang = await UsersRepo.get_user_lang(user_id)
    student = await StudentsRepo.get_by_tg_id(user_id)
    
    if student and student.get("exam_from") and student.get("exam_to"):
        if lang == "ru":
            info_txt = (
                f"🔒 **Режим сессии активен ({student.get('exam_from')} – {student.get('exam_to')}):**\n\n"
                f"Период сессии установлен вашим **Тьютором**.\n"
                f"В этот период подача заявок на вакансии и приём новых предложений работы заблокированы (режим строгой паузы), чтобы вы могли сосредоточиться на учёбе и экзаменах.\n\n"
                f"ℹ️ *Снять или изменить даты блокировки может только ваш тьютор.*"
            )
        elif lang == "en":
            info_txt = (
                f"🔒 **Exam Lock Active ({student.get('exam_from')} – {student.get('exam_to')}):**\n\n"
                f"This lock was set by your **Tutor**.\n"
                f"During exams, submitting job applications and accepting job offers is paused so you can focus on studies.\n\n"
                f"ℹ️ *Only your university tutor can manage or unlock this period.*"
            )
        else:
            info_txt = (
                f"🔒 **Sessiya va Imtihon qulfi faol ({student.get('exam_from')} – {student.get('exam_to')}):**\n\n"
                f"Ushbu muddat sizning mas'ul **Tyutoringiz** tomonidan belgilangan.\n"
                f"Imtihonlar davrida talabaning o'zlashtirishini ta'minlash maqsadida yangi ishlarga ariza topshirish va yangi ish qabul qilish to'liq bloklangan (pauza rejimi).\n\n"
                f"ℹ️ *Sessiya qulfini faqat OTM tyutori ochishi yoki muddatini o'zgartirishi mumkin.*"
            )
        await msg.answer(
            info_txt,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Profilga qaytish", callback_data="profile_back_to_main")
            ]]),
            parse_mode="Markdown"
        )
    else:
        if lang == "ru":
            info_txt = (
                "🔓 **Режим экзаменов не установлен:**\n\n"
                "В данный момент у вас нет активной сессионной блокировки. Вы можете свободно искать работу и подавать заявки.\n\n"
                "ℹ️ *График сессии устанавливается централизованно вашим тьютором через панель тьютора.*"
            )
        elif lang == "en":
            info_txt = (
                "🔓 **No Exam Lock Active:**\n\n"
                "You currently have no exam lock. You can explore jobs and submit applications freely.\n\n"
                "ℹ️ *Exam mode is strictly managed by your assigned Tutor.*"
            )
        else:
            info_txt = (
                "🔓 **Sessiya qulfi belgilanmagan:**\n\n"
                "Hozirda sizda faol imtihon cheklovi yo'q. Qulay ishlarni qidirishingiz va arizalar topshirishingiz mumkin.\n\n"
                "ℹ️ *Eslatma: Yangi qoidalarga ko'ra, sessiya va imtihonlar muddati faqat OTM tyutori tomonidan belgilanadi va boshqariladi.*"
            )
        await msg.answer(
            info_txt,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Profilga qaytish", callback_data="profile_back_to_main")
            ]]),
            parse_mode="Markdown"
        )


# ==========================================
# 5. 14 KUNLIK ARIZA SHABLONI (MEHNAT KODEKSI 160-MODDA)
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_STUDENT_RESIGN_TEMPLATE")))
@router.callback_query(F.data == "profile_resign_template")
async def show_resignation_template(event):
    msg = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()

    lang = await UsersRepo.get_user_lang(user_id)
    student = await StudentsRepo.get_by_tg_id(user_id)
    name = student.get("full_name", "Talaba") if student else "Talaba"

    from datetime import date, timedelta
    today = date.today()
    resign_date = today + timedelta(days=14)

    active_app = await ApplicationsRepo.get_active_by_student(student["id"]) if student else None
    company = active_app.get("company_name", "[Tashkilot nomi]") if active_app else "[Tashkilot nomi]"

    if lang == "ru":
        template = (
            f"📄 **Шаблон заявления об увольнении по собственному желанию (за 14 дней)**\n"
            f"*(Согласно статье 160 Трудового кодекса Республики Узбекистан)*\n\n"
            f"📌 *Работник обязан письменно предупредить работодателя о прекращении договора за 14 календарных дней.*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Руководителю «{company}»**\n"
            f"**От:** {name}\n\n"
            f"**ЗАЯВЛЕНИЕ**\n\n"
            f"На основании статьи 160 Трудового кодекса Республики Узбекистан прошу расторгнуть заключённый со мной трудовой договор по собственному желанию по истечении 14-дневного срока предупреждения — с **{resign_date.strftime('%d.%m.%Y')} г.**, и произвести со мной полный расчёт.\n\n"
            f"Дата подачи: **{today.strftime('%d.%m.%Y')}**\n"
            f"Подпись: ____________ ({name})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 *Вы можете скопировать этот текст заявления и передать работодателю.*"
        )
    elif lang == "en":
        template = (
            f"📄 **14-day Resignation Notice Template**\n"
            f"*(In accordance with Article 160 of the Labor Code of Uzbekistan)*\n\n"
            f"📌 *An employee must provide a 14-day written notice to terminate employment voluntarily.*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**To the Director of: {company}**\n"
            f"**From Student:** {name}\n\n"
            f"**RESIGNATION NOTICE**\n\n"
            f"Pursuant to Article 160 of the Labor Code of the Republic of Uzbekistan, I hereby submit my notice to terminate my employment agreement voluntarily upon the expiration of the statutory 14-day notice period, effective **{resign_date.strftime('%Y-%m-%d')}**, and request final settlement.\n\n"
            f"Date: **{today.strftime('%Y-%m-%d')}**\n"
            f"Signature: ____________ ({name})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 *You may copy this legal template and submit it to your employer.*"
        )
    else:
        template = (
            f"📄 **14 Kunlik Mehnat Shartnomasini Bekor Qilish Arizasi Shabloni**\n"
            f"*(O'zbekiston Respublikasi Mehnat kodeksining 160-moddasi bo'yicha)*\n\n"
            f"📌 *Xodim o'z xohishiga ko'ra ishdan bo'shash haqida ish beruvchini 14 kun oldin yozma ogohlantirishi shart.*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**\"{company}\" rahbari nomiga**\n"
            f"**Talaba:** {name}dan\n\n"
            f"**ARIZA**\n\n"
            f"O'zbekiston Respublikasi Mehnat kodeksining 160-moddasiga asosan, men bilan tuzilgan mehnat shartnomasini qonunda belgilangan 14 kunlik ogohlantirish muddati tugagach, **{resign_date.strftime('%d.%m.%Y')}** kunidan bekor qilishingizni hamda men bilan to'liq hisob-kitob qilishingizni so'rayman.\n\n"
            f"Ariza topshirilgan sana: **{today.strftime('%d.%m.%Y')}**\n"
            f"Imzo: ____________ ({name})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 *Ushbu tayyor ariza matnidan nusxa olib, ish beruvchingizga topshirishingiz mumkin.*"
        )

    await msg.answer(
        template,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Profilga qaytish", callback_data="profile_back_to_main")
        ]]),
        parse_mode="Markdown"
    )


# ==========================================
# 6. TALABA SMART REZYUMESI (CV CARD)
# ==========================================
@router.callback_query(F.data == "profile_smart_resume")
async def show_smart_resume(call: CallbackQuery):
    await call.answer()
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    student = await StudentsRepo.get_by_tg_id(call.from_user.id)
    if not student:
        await call.message.answer("Talaba profili topilmadi.")
        return

    internship_hours = await InternshipRepo.get_total_hours(student["id"])
    active_app = await ApplicationsRepo.get_active_by_student(student["id"])
    
    if active_app:
        job_display = f"🏢 {active_app.get('company_name')} — {active_app.get('job_title')}"
    else:
        job_display = "🔍 Ish qidiruvchi (Bo'sh ish yoki amaliyotga tayyor)"

    course_val = student.get("course_label") or f"{student.get('course', 1)}-kurs"
    gpa_val = student.get("gpa_score") or 0.0

    resume_text = (
        f"📄 **IMKON — TALABA SMART REZYUMESI**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **F.I.Sh:** {student.get('full_name')}\n"
        f"📱 **Telefon:** `{student.get('phone_number') or 'Kiritilmagan'}`\n"
        f"🏛 **OTM:** {student.get('university') or student.get('faculty')}\n"
        f"📂 **Mutaxassislik:** {student.get('major')} ({course_val})\n"
        f"⭐ **GPA o'zlashtirish:** **{gpa_val} / 5.0**\n"
        f"📍 **Yashash manzili:** {student.get('location_name') or 'Urganch shahri'}\n"
        f"📜 **Amaliyot soatlari:** **{internship_hours} soat** tasdiqlangan\n"
        f"💼 **Faoliyat holati:** {job_display}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛡 *Imkon platformasida verifikatsiyadan o'tgan rasmiy talaba profili.*"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ GPA balini yangilash", callback_data="profile_gpa_prompt"),
                InlineKeyboardButton(text="📍 Joylashuvni yangilash", callback_data="update_location_prompt"),
            ],
            [
                InlineKeyboardButton(text="📜 Amaliyot kundaligi", callback_data="profile_internship_diary"),
                InlineKeyboardButton(text="⬅️ Profilga qaytish", callback_data="profile_back_to_main"),
            ]
        ]
    )

    await call.message.edit_text(resume_text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "profile_back_to_main")
async def process_profile_back(call: CallbackQuery):
    await call.answer()
    await show_profile(call.message)


# ==========================================
# 7. GPA BALINI YANGILASH (FSM)
# ==========================================
@router.callback_query(F.data == "profile_gpa_prompt")
async def prompt_update_gpa(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(StudentGpaStates.enter_gpa)
    prompt = (
        "⭐ **Yangi GPA o'zlashtirish balingizni kiriting:**\n\n"
        "*(Masalan: `4.5` yoki `4.8` yoki `3.9`)*\n\n"
        "💡 *Bu ball sizga kontrakt to'lanadigan grant ishlar va nufuzli davlat amaliyotlariga tavsiya etilishda ustunlik beradi.*"
    )
    await call.message.answer(prompt, parse_mode="Markdown")


@router.message(StudentGpaStates.enter_gpa, F.text)
async def process_gpa_input(msg: Message, state: FSMContext):
    await state.clear()
    student = await StudentsRepo.get_by_tg_id(msg.from_user.id)
    if not student:
        await msg.answer("Talaba topilmadi.")
        return

    text = msg.text.strip().replace(",", ".")
    try:
        gpa_score = float(text)
        if not (1.0 <= gpa_score <= 5.0):
            await msg.answer("⚠️ GPA balli 1.0 va 5.0 oralig'ida bo'lishi kerak. Iltimos, qayta urinib ko'ring.")
            return
    except ValueError:
        await msg.answer("⚠️ Iltimos, faqat son kiriting (Masalan: `4.5`):")
        return

    await StudentsRepo.update_gpa(student["id"], gpa_score)
    res_text = (
        f"✅ **GPA bahoingiz muvaffaqiyatli saqlandi: {gpa_score} ⭐!**\n\n"
        f"Endi e'lonlar lentasida GPA talabiga mos yuqori daromadli ishlar va kontrakt grantlari profilingizga moslashtirildi."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Smart Rezyumeni ko'rish", callback_data="profile_smart_resume")],
        ]
    )
    await msg.answer(res_text, reply_markup=kb, parse_mode="Markdown")
