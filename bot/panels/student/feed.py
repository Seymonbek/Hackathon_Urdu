import os
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.core.callbacks import StudentJobAction
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


def get_filter_keyboard(active: str = "all", lang: str = "uz") -> InlineKeyboardMarkup:
    """Mos ishlar va amaliyotlar bo'limidagi tezkor filtrlar klaviaturasi."""
    if lang == "ru":
        btn_jobs = f"{'🔘' if active == 'jobs' else '⚪'} 💼 Вакансии"
        btn_intern = f"{'🔘' if active in ['internships', 'state'] else '⚪'} 🏛 Практика"
        btn_grants = f"{'🔘' if active == 'grants' else '⚪'} 🎓 Гранты"
        btn_all = f"{'🔘' if active == 'all' else '⚪'} 📋 Все"
        btn_search = "🔍 Поиск по ключевым словам"
    elif lang == "en":
        btn_jobs = f"{'🔘' if active == 'jobs' else '⚪'} 💼 Paid Jobs"
        btn_intern = f"{'🔘' if active in ['internships', 'state'] else '⚪'} 🏛 Internships"
        btn_grants = f"{'🔘' if active == 'grants' else '⚪'} 🎓 Grants"
        btn_all = f"{'🔘' if active == 'all' else '⚪'} 📋 All"
        btn_search = "🔍 Search by keyword"
    else:
        btn_jobs = f"{'🔘' if active == 'jobs' else '⚪'} 💼 Pullik ishlar"
        btn_intern = f"{'🔘' if active in ['internships', 'state'] else '⚪'} 🏛 Amaliyotlar"
        btn_grants = f"{'🔘' if active == 'grants' else '⚪'} 🎓 Kontrakt granti"
        btn_all = f"{'🔘' if active == 'all' else '⚪'} 📋 Barchasi"
        btn_search = "🔍 Kalit so'z bilan qidirish"

    return InlineKeyboardMarkup(
        inline_keyboard=[
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
    )


# 1. PULLIK BO'SH ISH O'RINLARI (ALOHIDA TUGMA)
@router.message(F.text.in_(get_button_variants("BTN_STUDENT_JOBS")))
async def show_student_paid_jobs(msg: Message):
    await show_filtered_matches(msg, filter_type="jobs")


# 2. DAVLAT VA KASBIY AMALIYOTLAR / STAJIROVKA (ALOHIDA TUGMA)
@router.message(F.text.in_(get_button_variants("BTN_STUDENT_INTERNSHIPS")))
async def show_student_internships(msg: Message):
    await show_filtered_matches(msg, filter_type="internships")


# 3. BARCHA MOS TAKLIFLAR
@router.message(F.text.in_(get_button_variants("BTN_STUDENT_MATCHES")))
async def show_student_matches(msg: Message):
    await show_filtered_matches(msg, filter_type="all")


@router.callback_query(F.data.startswith("filter_jobs_"))
async def process_filter_jobs(call: CallbackQuery, state: FSMContext):
    await call.answer()
    filter_type = call.data.replace("filter_jobs_", "")
    
    if filter_type == "search":
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

    msg = call.message
    await show_filtered_matches(msg, filter_type=filter_type, user_id=call.from_user.id)


@router.message(JobSearchStates.search_query, F.text)
async def process_search_query(msg: Message, state: FSMContext):
    await state.clear()
    query = msg.text.strip().lower()
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    student = await StudentsRepo.get_by_tg_id(msg.from_user.id)
    if not student:
        t = get_i18n(lang)
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    all_jobs = await JobsRepo.get_open_jobs()
    results = []
    for j in all_jobs:
        searchable = (
            str(j.get("title", "")) + " " +
            str(j.get("company_name", "")) + " " +
            str(j.get("category", "")) + " " +
            " ".join(j.get("target_majors") or []) + " " +
            " ".join(j.get("duties") or [])
        ).lower()
        if query in searchable:
            is_eligible, score, reasons = calculate_match_score(student, j)
            results.append((j, score, reasons))

    if not results:
        no_res = f"🔍 *'{msg.text}'* bo'yicha hech qanday vakansiya topilmadi." if lang == "uz" else (f"🔍 По запросу *'{msg.text}'* ничего не найдено." if lang == "ru" else f"🔍 No jobs found matching *'{msg.text}'*.")
        await msg.answer(no_res, reply_markup=get_filter_keyboard("all", lang), parse_mode="Markdown")
        return

    results.sort(key=lambda x: x[1], reverse=True)
    header = f"🔍 *'{msg.text}'* so'rovi bo'yicha topilgan natijalar ({len(results)} ta):" if lang == "uz" else (f"🔍 Результаты по запросу *'{msg.text}'* ({len(results)}):" if lang == "ru" else f"🔍 Search results for *'{msg.text}'* ({len(results)}):")
    await msg.answer(header, parse_mode="Markdown")
    for job, score, reasons in results[:5]:
        await render_job_card(msg, job, score, reasons, lang, is_near_match=False)


async def show_filtered_matches(msg: Message, filter_type: str = "all", user_id: int = None):
    uid = user_id or msg.chat.id
    lang = await UsersRepo.get_user_lang(uid)
    t = get_i18n(lang)

    student = await StudentsRepo.get_by_tg_id(uid)
    if not student:
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    # Sessiya / Imtihon qulfi tekshiruvi (Tyutor tomonidan o'rnatilgan cheklov)
    from datetime import date
    today = date.today()
    exam_from = student.get("exam_from")
    exam_to = student.get("exam_to")
    if exam_from and exam_to:
        try:
            ef = date.fromisoformat(str(exam_from)) if isinstance(exam_from, str) else exam_from
            et = date.fromisoformat(str(exam_to)) if isinstance(exam_to, str) else exam_to
            if ef <= today <= et:
                if lang == "ru":
                    lock_msg = (
                        f"🔒 **Режим сессии и экзаменов активен ({exam_from} – {exam_to})!**\n\n"
                        f"Ваш университетский **Тьютор** установил период сессии.\n"
                        f"В соответствии с правилами OTM, в этот период поиск работы и подача заявок приостановлены (режим строгой паузы), чтобы вы могли успешно сдать экзамены.\n\n"
                        f"Как только сессия завершится или тьютор снимет ограничение, вакансии снова станут доступны!"
                    )
                elif lang == "en":
                    lock_msg = (
                        f"🔒 **Exam Lock Active ({exam_from} – {exam_to})!**\n\n"
                        f"Your university **Tutor** has placed your account under active exam mode.\n"
                        f"Job search and applications are currently locked so you can focus on your academic examinations.\n\n"
                        f"Access will automatically resume when the exam period concludes."
                    )
                else:
                    lock_msg = (
                        f"🔒 **Sessiya va Imtihon qulfi faol ({exam_from} – {exam_to})!**\n\n"
                        f"Sizning OTM mas'ul **Tyutoringiz** tomonidan sessiya davri belgilangan.\n"
                        f"OTM qoidalariga muvofiq, imtihonlar davrida talabalarning akademik o'zlashtirishini ta'minlash uchun ish qidirish va yangi ishlarga ariza topshirish to'xtatilgan (qat'iy qulf/pauza rejimi).\n\n"
                        f"Sessiya tugashi bilan yoki tyutoringiz qulfni ochganda barcha mos vakansiyalar qayta ochiladi!"
                    )
                await msg.answer(lock_msg, parse_mode="Markdown")
                return
        except Exception as e:
            logger.warning(f"Exam lock check error in show_filtered_matches: {e}")

    all_jobs = await JobsRepo.get_open_jobs()
    matched_jobs = []
    candidate_jobs = []

    for j in all_jobs:
        # Bo'limlar bo'yicha qat'iy ajratish (Ishlar va amaliyotlar aralashmasligi uchun)
        if filter_type == "jobs" and j.get("listing_type") == "state_internship":
            continue
        if filter_type in ["internships", "state"] and j.get("listing_type") != "state_internship":
            continue
        if filter_type == "grants" and j.get("listing_type") != "tuition_grant_job":
            continue
        if filter_type == "remote" and j.get("work_format") != "remote_task":
            continue

        candidate_jobs.append(j)
        is_eligible, score, reasons = calculate_match_score(student, j)
        if is_eligible:
            matched_jobs.append((j, score, reasons))

    matched_jobs.sort(key=lambda x: x[1], reverse=True)

    # 1. To'liq mos ishlar topilmagan holat -> "Deyarli mos" ishlarni ko'rsatish
    if not matched_jobs:
        near_matches = find_near_matches(student, candidate_jobs)
        
        no_full_text = (
            "🔔 **Ushbu bo'lim bo'yicha 100% to'liq mos taklif topilmadi.**\n"
            "Lekin yo'nalishingiz va shartlari qisman to'g'ri keladigan **'Deyarli mos'** takliflar mavjud 👇"
        )
        if lang == "ru":
            no_full_text = (
                "🔔 **По данному разделу нет предложений со 100% совпадением.**\n"
                "Но мы подобрали предложения с частичным совпадением (**'Почти подходящие'**) 👇"
            )
        elif lang == "en":
            no_full_text = (
                "🔔 **No 100% matching offers for this section.**\n"
                "Here are partially matching recommendations (**'Near-matches'**) for you 👇"
            )

        btn_notify = "🔔 Mos ish chiqsa xabar bering" if lang == "uz" else ("🔔 Уведомить о новых вакансиях" if lang == "ru" else "🔔 Notify me when new job opens")
        notify_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=btn_notify, callback_data="notify_me_subscription")]]
        )
        await msg.answer(no_full_text, reply_markup=notify_kb, parse_mode="Markdown")

        # Deyarli mos ishlarni chiqarish
        for job, score, reasons in near_matches[:4]:
            await render_job_card(msg, job, score, reasons, lang, is_near_match=True)
        return

    # 2. To'liq mos ishlarni ko'rsatish
    if lang == "ru":
        filter_names = {
            "all": "Все предложения",
            "jobs": "Подходящие вакансии (Оплачиваемая работа)",
            "internships": "Государственная & Проф. практика (Стажировки)",
            "state": "Государственная практика",
            "grants": "Гранты на контракт",
            "remote": "Удалённая работа"
        }
    elif lang == "en":
        filter_names = {
            "all": "All Offers",
            "jobs": "Available Paid Jobs",
            "internships": "State & Career Internships (Traineeships)",
            "state": "State Internships",
            "grants": "Tuition Grants",
            "remote": "Remote Tasks"
        }
    else:
        filter_names = {
            "all": "Barcha takliflar",
            "jobs": "Bo'sh ish o'rinlari (Pullik ishlar)",
            "internships": "Davlat & Kasbiy Amaliyotlar (Stajirovka)",
            "state": "Davlat amaliyotlari",
            "grants": "Kontrakt grantlari",
            "remote": "Masofaviy ishlar"
        }

    f_title = filter_names.get(filter_type, "Mos takliflar")
    header = f"🎯 **{f_title} ({len(matched_jobs)} ta topildi):**\n"

    await msg.answer(header, reply_markup=get_filter_keyboard(filter_type, lang), parse_mode="Markdown")

    for job, score, reasons in matched_jobs[:5]:
        await render_job_card(msg, job, score, reasons, lang, is_near_match=False)


async def render_job_card(msg: Message, job: dict, score: float, reasons: list, lang: str, is_near_match: bool = False):
    reasons_text = " • " + " • ".join(reasons)
    pay_info = f"💰 {job.get('pay_amount', 0):,} so'm ({job.get('pay_timing')})"
    if job.get("listing_type") == "tuition_grant_job":
        pay_info = f"🎓 **Kontrakt: {job.get('tuition_coverage_percent', 100)}% to'lanadi!**"
    elif job.get("listing_type") == "state_internship":
        pay_info = f"🏛 **Davlat amaliyoti / {job.get('pay_amount', 0):,} so'm**"

    # Tungi smena va TTJ ogohlantirishi
    night_warning = ""
    if is_night_job(job):
        if lang == "ru":
            night_warning = "\n⚠️ **Ночная смена:** *Если вы живёте в общежитии (ТТЖ), согласуйте ночную смену с администрацией ВУЗа (после 22:00 вход закрыт).*\n"
        elif lang == "en":
            night_warning = "\n⚠️ **Night Shift Notice:** *If staying in university dormitory, verify with admin as doors close at 22:00.*\n"
        else:
            night_warning = "\n⚠️ **Tungi smena ogohlantirishi:** *Agar TTJ (yotoqxona)da yashasangiz, 22:00 dan keyin eshiklar yopilishi sababli ushbu smenani OTM yoki komendant bilan kelishib oling!*\n"

    tag = "⚡ [Deyarli mos] " if is_near_match else "🎯 "
    if lang == "ru":
        card_text = (
            f"{tag}**{job.get('title')}** (Совпадение: {score}%)\n"
            f"🏢 Организация: {job.get('company_name')}\n"
            f"📍 Адрес: {job.get('address')}\n"
            f"⏰ Время: {job.get('start_time', '')} – {job.get('end_time', '')}\n"
            f"{pay_info}\n"
            f"{night_warning}\n"
            f"💡 **Причина:** {reasons_text}"
        )
        btn_apply = "✅ Подать заявку"
        btn_details = "ℹ️ Подробнее"
    elif lang == "en":
        card_text = (
            f"{tag}**{job.get('title')}** (Match: {score}%)\n"
            f"🏢 Organization: {job.get('company_name')}\n"
            f"📍 Address: {job.get('address')}\n"
            f"⏰ Schedule: {job.get('start_time', '')} – {job.get('end_time', '')}\n"
            f"{pay_info}\n"
            f"{night_warning}\n"
            f"💡 **Reasons:** {reasons_text}"
        )
        btn_apply = "✅ Apply"
        btn_details = "ℹ️ Details"
    else:
        card_text = (
            f"{tag}**{job.get('title')}** (Moslik: {score}%)\n"
            f"🏢 Tashkilot: {job.get('company_name')}\n"
            f"📍 Manzil: {job.get('address')}\n"
            f"⏰ Vaqt: {job.get('start_time', '')} – {job.get('end_time', '')}\n"
            f"{pay_info}\n"
            f"{night_warning}\n"
            f"💡 **Moslik sababi:** {reasons_text}"
        )
        btn_apply = "✅ Ariza berish"
        btn_details = "ℹ️ Batafsil"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=btn_apply,
                    callback_data=StudentJobAction(action="apply", job_id=job["id"]).pack(),
                ),
                InlineKeyboardButton(
                    text=btn_details,
                    callback_data=StudentJobAction(action="view", job_id=job["id"]).pack(),
                ),
            ]
        ]
    )

    # Rasm bilan yuborish (IMKON logotipi yoki rasmiy e'lon rasmi)
    img_path = job.get("image_path") or DEFAULT_IMAGE_PATH
    if not os.path.exists(img_path):
        img_path = DEFAULT_IMAGE_PATH

    try:
        if os.path.exists(img_path):
            photo = FSInputFile(img_path)
            if len(card_text) <= 1024:
                await msg.answer_photo(photo=photo, caption=card_text, reply_markup=kb, parse_mode="Markdown")
            else:
                await msg.answer_photo(photo=photo)
                await msg.answer(card_text, reply_markup=kb, parse_mode="Markdown")
        else:
            await msg.answer(card_text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Rasm yuborishda xatolik: {e}, oddiy xabar yuboriladi.")
        await msg.answer(card_text, reply_markup=kb, parse_mode="Markdown")


# ==========================================
# 3. BATAFSIL KO'RISH (VIEW JOB DETAILS)
# ==========================================
@router.callback_query(StudentJobAction.filter(F.action == "view"))
async def process_view_job_details(call: CallbackQuery, callback_data: StudentJobAction):
    await call.answer()
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    job = await JobsRepo.get_by_id(callback_data.job_id)
    if not job:
        not_found = "Vakansiya topilmadi." if lang == "uz" else ("Вакансия не найдена." if lang == "ru" else "Job not found.")
        await call.message.reply(not_found)
        return

    # Tashkilot turi
    org_type_labels = {
        "state_agency": "🏛 Davlat organi / Muassasasi",
        "commercial": "🏢 Tijorat korxonasi / Kompaniya",
        "ngo": "🌐 NNT / Xalqaro tashkilot"
    }
    org_type_str = org_type_labels.get(job.get("org_type"), "🏢 Tashkilot")

    # To'lov va imtiyoz
    if job.get("listing_type") == "tuition_grant_job":
        pay_str = f"🎓 **100% Yillik kontrakt to'lanadi!** (Majburiyat: {job.get('work_obligation_years', 1)} yil staj)"
    elif job.get("listing_type") == "state_internship":
        pay_str = f"🏛 **Rasmiy davlat xizmati / amaliyoti** (Maosh: {job.get('pay_amount', 0):,} so'm)"
    else:
        pay_str = f"💰 **{job.get('pay_amount', 0):,} so'm** ({job.get('pay_unit')}, {job.get('pay_timing')})"

    # Vazifalar va imtiyozlar ro'yxati
    duties_list = job.get("duties") or []
    duties_str = "\n".join([f"  • {d}" for d in duties_list]) if duties_list else "  • Ish beruvchi ko'rsatmasi bo'yicha"

    perks_list = job.get("perks") or []
    perks_str = "\n".join([f"  ✨ {p}" for p in perks_list]) if perks_list else "  ✨ Qonuniy mehnat sharoitlari"

    majors_list = job.get("target_majors") or []
    majors_str = ", ".join(majors_list) if majors_list else "Barcha yo'nalishlar"

    # Xarita havolasi
    map_url = f"https://maps.google.com/?q={job.get('lat')},{job.get('lon')}" if job.get("lat") and job.get("lon") else None

    # Aloqa ma'lumotlari
    phone_info = f"\n📞 **Aloqa:** {job.get('contact_phone')}" if job.get("contact_phone") else ""

    if lang == "ru":
        details_text = (
            f"📋 **{job.get('title')}**\n\n"
            f"🏢 **Работодатель:** {job.get('company_name')} ({org_type_str})\n"
            f"📍 **Адрес:** {job.get('address')}\n"
            f"⏰ **График:** {job.get('start_time', '')} – {job.get('end_time', '')}\n"
            f"💵 **Оплата / Льгота:** {pay_str}\n"
            f"🎓 **Подходящие специальности:** {majors_str}\n"
            f"📚 **Мин. курс:** {job.get('min_course_required', 1)}-й курс{phone_info}\n\n"
            f"🛠 **Обязанности:**\n{duties_str}\n\n"
            f"🎁 **Преимущества:**\n{perks_str}"
        )
        btn_apply = "✅ Подать заявку"
        btn_map = "🗺 Открыть на карте"
    elif lang == "en":
        details_text = (
            f"📋 **{job.get('title')}**\n\n"
            f"🏢 **Organization:** {job.get('company_name')} ({org_type_str})\n"
            f"📍 **Address:** {job.get('address')}\n"
            f"⏰ **Working Hours:** {job.get('start_time', '')} – {job.get('end_time', '')}\n"
            f"💵 **Compensation / Benefit:** {pay_str}\n"
            f"🎓 **Target Majors:** {majors_str}\n"
            f"📚 **Min Course:** Year {job.get('min_course_required', 1)}{phone_info}\n\n"
            f"🛠 **Duties:**\n{duties_str}\n\n"
            f"🎁 **Perks & Benefits:**\n{perks_str}"
        )
        btn_apply = "✅ Apply"
        btn_map = "🗺 View on Google Maps"
    else:
        details_text = (
            f"📋 **{job.get('title')}**\n\n"
            f"🏢 **Ish beruvchi:** {job.get('company_name')} ({org_type_str})\n"
            f"📍 **Aniq manzil:** {job.get('address')}\n"
            f"⏰ **Ish vaqti:** {job.get('start_time', '')} – {job.get('end_time', '')}\n"
            f"💵 **To'lov / Imtiyoz:** {pay_str}\n"
            f"🎓 **Mos yo'nalishlar:** {majors_str}\n"
            f"📚 **Minimal kurs:** {job.get('min_course_required', 1)}-kurs{phone_info}\n\n"
            f"🛠 **Asosiy vazifalar:**\n{duties_str}\n\n"
            f"🎁 **Qulaylik va imtiyozlar:**\n{perks_str}"
        )
        btn_apply = "✅ Ariza topshirish"
        btn_map = "🗺 Xaritada ko'rish"

    buttons = [
        [InlineKeyboardButton(text=btn_apply, callback_data=StudentJobAction(action="apply", job_id=job["id"]).pack())]
    ]
    if map_url:
        buttons.append([InlineKeyboardButton(text=btn_map, url=map_url)])

    # Rasm bilan yuborish
    img_path = job.get("image_path") or DEFAULT_IMAGE_PATH
    if not os.path.exists(img_path):
        img_path = DEFAULT_IMAGE_PATH

    try:
        if os.path.exists(img_path):
            photo = FSInputFile(img_path)
            if len(details_text) <= 1024:
                await call.message.answer_photo(photo=photo, caption=details_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
            else:
                await call.message.answer_photo(photo=photo)
                await call.message.answer(details_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
        else:
            await call.message.answer(details_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Rasm yuborishda xatolik: {e}")
        await call.message.answer(details_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")


# ==========================================
# 4. ARIZA TOPSHIRISH (APPLY)
# ==========================================
@router.callback_query(StudentJobAction.filter(F.action == "apply"))
async def process_apply(call: CallbackQuery, callback_data: StudentJobAction):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    student = await StudentsRepo.get_by_tg_id(call.from_user.id)
    if not student:
        alert_msg = "Avval ro'yxatdan o'ting!" if lang == "uz" else ("Сначала зарегистрируйтесь!" if lang == "ru" else "Please register first!")
        await call.answer(alert_msg, show_alert=True)
        return

    job = await JobsRepo.get_by_id(callback_data.job_id)
    if not job:
        not_found = "Vakansiya topilmadi." if lang == "uz" else ("Вакансия не найдена." if lang == "ru" else "Job not found.")
        await call.answer(not_found, show_alert=True)
        return

    # Sessiya / Imtihon qulfi tekshiruvi (Tyutor tomonidan o'rnatilgan blokirovka)
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
                    f"Tyutoringiz tomonidan sessiya qulfi o'rnatilganligi sababli, bu davrda yangi ishlarga ariza topshirish va qabul qilish to'xtatilgan (pauza rejimi)."
                ) if lang == "uz" else (
                    f"🔒 ВНИМАНИЕ: С {exam_from} по {exam_to} действует блокировка сессии!\n\n"
                    f"Тьютор установил запрет на подачу заявок на время экзаменов (режим паузы)."
                ) if lang == "ru" else (
                    f"🔒 ATTENTION: Exam lock is active from {exam_from} to {exam_to} by your Tutor. Job applications are locked."
                )
                await call.answer(lock_alert, show_alert=True)
                return
        except Exception as e:
            logger.warning(f"Exam lock check error in process_apply: {e}")

    # Allaqachon ariza berilganligini tekshirish
    existing_app = await db.fetchrow(
        "SELECT id, status FROM applications WHERE job_id = $1 AND student_id = $2",
        job["id"], student["id"]
    )
    if existing_app:
        warn = "Siz ushbu vakansiyaga allaqachon ariza yuborgansiz!" if lang == "uz" else ("Вы уже подали заявку на эту вакансию!" if lang == "ru" else "You have already applied for this job!")
        await call.answer(warn, show_alert=True)
        return

    # Yosh himoyasi tekshiruvi (Mehnat kodeksi 411-modda)
    if student.get("age", 19) < 18 and (is_night_job(job) or job.get("min_age", 16) >= 18):
        warn = "Kechirasiz, 18 yoshgacha bo'lgan talabalar tungi ishlarga qabul qilinmaydi." if lang == "uz" else ("Несовершеннолетние не допускаются к ночным сменам." if lang == "ru" else "Night work prohibited under 18.")
        await call.answer(warn, show_alert=True)
        return

    # Kontrakt granti uchun GPA tekshiruvi
    min_gpa = float(job.get("min_gpa_required") or 0.0)
    student_gpa = float(student.get("gpa_score") or 0.0)
    if min_gpa > 0.0 and student_gpa < min_gpa:
        warn = f"GPA yetarli emas ({student_gpa} < {min_gpa})." if lang == "uz" else (f"Недостаточный GPA ({student_gpa} < {min_gpa})." if lang == "ru" else f"Insufficient GPA ({student_gpa} < {min_gpa}).")
        await call.answer(warn, show_alert=True)
        return

    # Ariza yaratish
    await ApplicationsRepo.create_application(
        job_id=job["id"],
        student_id=student["id"],
        match_score=90.0,
    )

    alert_ok = "✅ Arizangiz qabul qilindi!" if lang == "uz" else ("✅ Заявка принята!" if lang == "ru" else "✅ Application submitted!")
    await call.answer(alert_ok, show_alert=True)

    if lang == "ru":
        reply_text = (
            f"🎉 **Ваша заявка успешно отправлена!**\n\n"
            f"🏢 **Организация:** {job.get('company_name')}\n"
            f"📋 **Вакансия:** {job.get('title')}\n\n"
            f"Работодатель получил ваше резюме и контакты. Как только решение будет принято, бот пришлёт вам уведомление."
        )
    elif lang == "en":
        reply_text = (
            f"🎉 **Your application has been successfully submitted!**\n\n"
            f"🏢 **Organization:** {job.get('company_name')}\n"
            f"📋 **Job:** {job.get('title')}\n\n"
            f"The employer has received your resume and contact info. You will be notified here as soon as an update arrives."
        )
    else:
        reply_text = (
            f"🎉 **Arizangiz muvaffaqiyatli yuborildi!**\n\n"
            f"🏢 **Tashkilot:** {job.get('company_name')}\n"
            f"📋 **Vakansiya:** {job.get('title')}\n\n"
            f"Ish beruvchi kadrlar bo'limi nomzodingizni ko'rib chiqmoqda. Natija chiqishi bilan bot orqali sizga xabar beriladi."
        )

    await call.message.reply(reply_text, parse_mode="Markdown")


# ==========================================
# 5. KONTRAKT GRANTLARI BO'LIMI
# ==========================================
@router.message(F.text.in_(get_button_variants("BTN_STUDENT_GRANTS")))
async def show_tuition_grants(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    student = await StudentsRepo.get_by_tg_id(msg.from_user.id)
    if not student:
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    grant_jobs = await JobsRepo.get_open_jobs(listing_type="tuition_grant_job")
    if not grant_jobs:
        # Agar maxsus listing_type bo'yicha bo'lmasa, kontrakt qoplaydigan barcha ishlarni ko'rsatish
        grant_jobs = await db.fetch("SELECT j.*, e.company_name, e.address FROM jobs j JOIN employers e ON j.employer_id = e.id WHERE j.tuition_coverage_percent > 0 AND j.status = 'open'")

    if not grant_jobs:
        await msg.answer(t.MSG_NO_GRANTS_YET)
        return

    intro = (
        "🎓 **Kontrakt to'lab beriladigan nufuzli davlat va xususiy grantlar:**\n"
        "Ushbu vakansiyalarga qabul qilingan talabalarning yillik to'lov-kontrakti tashkilot tomonidan 100% to'lab beriladi 👇"
    )
    if lang == "ru":
        intro = (
            "🎓 **Вакансии с оплатой годового контракта:**\n"
            "Организация оплачивает 100% контракта студента в обмен на стажировку и работу 👇"
        )
    elif lang == "en":
        intro = (
            "🎓 **Tuition Sponsorship Programs:**\n"
            "Employers offering 100% tuition sponsorship for qualified students 👇"
        )
    await msg.answer(intro, parse_mode="Markdown")

    for job in grant_jobs[:5]:
        is_eligible, score, reasons = calculate_match_score(student, job)
        reasons_text = " • " + " • ".join(reasons)

        if lang == "ru":
            text = (
                f"🎓 **{job.get('title')}** (Совпадение: {score}%)\n"
                f"🏢 Организация: {job.get('company_name')}\n"
                f"📍 Адрес: {job.get('address')}\n"
                f"🎁 **Льгота:** Оплата годового контракта {job.get('tuition_coverage_percent', 100)}%!\n"
                f"📋 **Требование:** Мин. GPA {job.get('min_gpa_required', 4.0)}+ (У вас: {student.get('gpa_score')})\n"
                f"⏳ Отработка: {job.get('work_obligation_years', 1)} год(а)\n\n"
                f"💡 {reasons_text}"
            )
            btn_apply = "📝 Подать заявку на грант"
            btn_details = "ℹ️ Подробнее"
        elif lang == "en":
            text = (
                f"🎓 **{job.get('title')}** (Match: {score}%)\n"
                f"🏢 Organization: {job.get('company_name')}\n"
                f"📍 Address: {job.get('address')}\n"
                f"🎁 **Benefit:** {job.get('tuition_coverage_percent', 100)}% Tuition Sponsorship!\n"
                f"📋 **Requirement:** Min GPA {job.get('min_gpa_required', 4.0)}+ (Yours: {student.get('gpa_score')})\n"
                f"⏳ Service commitment: {job.get('work_obligation_years', 1)} year(s)\n\n"
                f"💡 {reasons_text}"
            )
            btn_apply = "📝 Apply for Tuition Grant"
            btn_details = "ℹ️ Details"
        else:
            text = (
                f"🎓 **{job.get('title')}** (Moslik: {score}%)\n"
                f"🏢 Tashkilot: {job.get('company_name')}\n"
                f"📍 Manzil: {job.get('address')}\n"
                f"🎁 **Imtiyoz:** Yillik to'lov-kontrakt {job.get('tuition_coverage_percent', 100)}% to'lab beriladi!\n"
                f"📋 **Talab:** Minimal GPA {job.get('min_gpa_required', 4.0)}+ (Sizda: {student.get('gpa_score')})\n"
                f"⏳ Ishlab berish majburiyati: {job.get('work_obligation_years', 1)} yil\n\n"
                f"💡 {reasons_text}"
            )
            btn_apply = "📝 Grantga ariza topshirish"
            btn_details = "ℹ️ Batafsil"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=btn_apply,
                        callback_data=StudentJobAction(action="apply", job_id=job["id"]).pack(),
                    ),
                    InlineKeyboardButton(
                        text=btn_details,
                        callback_data=StudentJobAction(action="view", job_id=job["id"]).pack(),
                    ),
                ]
            ]
        )

        img_path = job.get("image_path") or DEFAULT_IMAGE_PATH
        if not os.path.exists(img_path):
            img_path = DEFAULT_IMAGE_PATH

        try:
            if os.path.exists(img_path):
                photo = FSInputFile(img_path)
                if len(text) <= 1024:
                    await msg.answer_photo(photo=photo, caption=text, reply_markup=kb, parse_mode="Markdown")
                else:
                    await msg.answer_photo(photo=photo)
                    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")
            else:
                await msg.answer(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


# ==========================================
# 6. BILDIRISHNOMA OBUNASI (NOTIFY ME)
# ==========================================
@router.callback_query(F.data == "notify_me_subscription")
async def process_notify_me(call: CallbackQuery):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    if lang == "ru":
        alert_txt = "Оповещения включены! Как только появится подходящая вакансия, мы сразу уведомим вас."
    elif lang == "en":
        alert_txt = "Alerts enabled! As soon as a matching job or internship opens, you will get instant notification."
    else:
        alert_txt = "Bildirishnomalarga obuna bo'ldingiz! Sizga mos yangi ish chiqishi bilan bot zudlik bilan xabar yuboradi."

    await call.answer(alert_txt, show_alert=True)
    await call.message.reply(f"🔔 **{alert_txt}**", parse_mode="Markdown")
