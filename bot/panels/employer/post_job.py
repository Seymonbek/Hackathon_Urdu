import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.core.constants import ListingType, WorkFormat
from bot.core.i18n import get_i18n, get_button_variants
from bot.core.keyboards import get_employer_main_keyboard, get_cancel_keyboard
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo
from bot.db.repositories.jobs_repo import JobsRepo
from bot.services.smart_notifier import notify_matching_students_about_job

router = Router()


class PostJobStates(StatesGroup):
    title = State()
    listing_type = State()
    work_format = State()
    target_major = State()
    times = State()
    pay_or_grant = State()
    slots = State()


@router.message(F.text.in_(get_button_variants("BTN_EMP_POST_JOB")))
async def start_post_job(msg: Message, state: FSMContext):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    emp = await EmployersRepo.get_by_tg_id(msg.from_user.id)
    if not emp:
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    await state.update_data(employer_id=emp["id"], employer_category=emp["category"], lang=lang)
    await state.set_state(PostJobStates.title)

    if lang == "ru":
        prompt = (
            "📝 **Размещение новой вакансии / практики:**\n\n"
            "Введите название вакансии или практики:\n*(Например: Помощник секретаря суда или Преподаватель английского)*"
        )
    elif lang == "en":
        prompt = (
            "📝 **Post Job / Internship Quota:**\n\n"
            "Enter vacancy or internship title:\n*(E.g.: Court Clerk Assistant or English Teacher)*"
        )
    else:
        prompt = (
            "📝 **Yangi e'lon / Kvota joylash:**\n\n"
            "Vakansiya yoki amaliyot nomini kiriting:\n*(Masalan: Sud majlisi kotibi yordamchisi yoki Ingliz tili o'qituvchisi)*"
        )

    await msg.answer(prompt, reply_markup=get_cancel_keyboard(lang), parse_mode="Markdown")


@router.message(PostJobStates.title, F.text)
async def process_job_title(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    if msg.text in get_button_variants("BTN_CANCEL"):
        await state.clear()
        cancel_txt = "Bekor qilindi." if lang == "uz" else ("Отменено." if lang == "ru" else "Cancelled.")
        await msg.answer(cancel_txt, reply_markup=get_employer_main_keyboard(lang))
        return

    await state.update_data(title=msg.text.strip())
    await state.set_state(PostJobStates.listing_type)

    if lang == "ru":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💼 Коммерческая подработка", callback_data="type_paid_job")],
                [InlineKeyboardButton(text="🏛 Гос. практика / Стажировка", callback_data="type_state_internship")],
                [InlineKeyboardButton(text="🎓 Грант на оплату контракта", callback_data="type_tuition_grant_job")],
            ]
        )
        await msg.answer("Выберите тип публикации:", reply_markup=kb)
    elif lang == "en":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💼 Commercial part-time job", callback_data="type_paid_job")],
                [InlineKeyboardButton(text="🏛 State internship / Practicum", callback_data="type_state_internship")],
                [InlineKeyboardButton(text="🎓 Tuition sponsorship grant", callback_data="type_tuition_grant_job")],
            ]
        )
        await msg.answer("Select listing type:", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💼 Tijoriy part-time ish", callback_data="type_paid_job")],
                [InlineKeyboardButton(text="🏛 Davlat amaliyoti / Stajirovka", callback_data="type_state_internship")],
                [InlineKeyboardButton(text="🎓 Kontrakt to'lab beriladigan grant", callback_data="type_tuition_grant_job")],
            ]
        )
        await msg.answer("E'lon turini tanlang:", reply_markup=kb)


@router.callback_query(PostJobStates.listing_type, F.data.startswith("type_"))
async def process_listing_type(call: CallbackQuery, state: FSMContext):
    listing_type = call.data.replace("type_", "")
    await state.update_data(listing_type=listing_type)
    await call.answer()
    await state.set_state(PostJobStates.work_format)

    data = await state.get_data()
    lang = data.get("lang", "uz")

    if lang == "ru":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏢 Офлайн смена (После учёбы)", callback_data="fmt_offline_shift")],
                [InlineKeyboardButton(text="🌙 Ночная смена (После 22:00, 18+)", callback_data="fmt_night_shift")],
                [InlineKeyboardButton(text="💻 Удаленно / Онлайн (Remote)", callback_data="fmt_remote_task")],
                [InlineKeyboardButton(text="⚡️ 1-дневное мероприятие / Gig", callback_data="fmt_one_day_gig")],
            ]
        )
        await call.message.answer("Выберите формат работы:", reply_markup=kb)
    elif lang == "en":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏢 Offline Shift (After classes)", callback_data="fmt_offline_shift")],
                [InlineKeyboardButton(text="🌙 Night Shift (After 22:00, 18+)", callback_data="fmt_night_shift")],
                [InlineKeyboardButton(text="💻 Remote / Online task", callback_data="fmt_remote_task")],
                [InlineKeyboardButton(text="⚡️ 1-day event gig", callback_data="fmt_one_day_gig")],
            ]
        )
        await call.message.answer("Select work format:", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏢 Oflayn smena (Darsdan keyin)", callback_data="fmt_offline_shift")],
                [InlineKeyboardButton(text="🌙 Tungi smena (22:00 dan keyin, 18+)", callback_data="fmt_night_shift")],
                [InlineKeyboardButton(text="💻 Masofaviy / Onlayn (Remote)", callback_data="fmt_remote_task")],
                [InlineKeyboardButton(text="⚡️ 1 kunlik tadbir / Tadbirlar", callback_data="fmt_one_day_gig")],
            ]
        )
        await call.message.answer("Ish yoki amaliyot formatini tanlang:", reply_markup=kb)


@router.callback_query(PostJobStates.work_format, F.data.startswith("fmt_"))
async def process_work_format(call: CallbackQuery, state: FSMContext):
    raw_fmt = call.data.replace("fmt_", "")
    is_night = (raw_fmt == "night_shift")
    work_format = "offline_shift" if is_night else raw_fmt
    min_age = 18 if is_night else 16

    await state.update_data(work_format=work_format, is_night_shift=is_night, min_age=min_age)
    await call.answer()
    await state.set_state(PostJobStates.target_major)

    data = await state.get_data()
    lang = data.get("lang", "uz")

    if is_night:
        night_notice = "🌙 **Tungi smena tanlandi:** Mehnat kodeksi 411-moddasiga ko'ra faqat 18 yoshdan oshgan talabalar ko'ra oladi va TTJ tartib-qoidasi ogohlantiriladi.\n\n"
        if lang == "ru":
            night_notice = "🌙 **Выбрана ночная смена:** По ст. 411 ТК вакансия видна только совершеннолетним студентам (18+).\n\n"
        elif lang == "en":
            night_notice = "🌙 **Night shift selected:** Visible only to adult students (18+) per Labor Code Art. 411.\n\n"
        await call.message.answer(night_notice, parse_mode="Markdown")
    await call.answer()
    await state.set_state(PostJobStates.target_major)

    data = await state.get_data()
    lang = data.get("lang", "uz")

    prompt = (
        "Qaysi OTM mutaxassisligi talabalarini qabul qilasiz?\n*(Masalan: Yurisprudensiya, Davolash ishi, Filologiya yoki Hammasi)*"
        if lang == "uz"
        else (
            "Студентов каких направлений вы принимаете?\n*(Например: Юриспруденция, Лечебное дело, Любое)*"
            if lang == "ru"
            else "Which university majors do you accept?\n*(E.g.: Jurisprudence, Medicine, Any)*"
        )
    )
    await call.message.answer(prompt)


@router.message(PostJobStates.target_major, F.text)
async def process_target_major(msg: Message, state: FSMContext):
    majors = [m.strip() for m in msg.text.split(",") if m.strip()]
    await state.update_data(target_majors=majors)
    await state.set_state(PostJobStates.times)

    data = await state.get_data()
    lang = data.get("lang", "uz")

    prompt = (
        "⏰ Ish / amaliyot soatlarini kiriting (boshlanish va tugash):\n*(Masalan: 14:30 - 18:00)*"
        if lang == "uz"
        else (
            "⏰ Укажите часы работы / практики:\n*(Например: 14:30 - 18:00)*"
            if lang == "ru"
            else "⏰ Enter working / internship hours:\n*(E.g.: 14:30 - 18:00)*"
        )
    )
    await msg.answer(prompt)


@router.message(PostJobStates.times, F.text)
async def process_job_times(msg: Message, state: FSMContext):
    parts = msg.text.split("-")
    start_time = parts[0].strip() if len(parts) >= 1 else "14:00"
    end_time = parts[1].strip() if len(parts) >= 2 else "18:00"

    await state.update_data(start_time=start_time, end_time=end_time)
    data = await state.get_data()
    lang = data.get("lang", "uz")

    await state.set_state(PostJobStates.pay_or_grant)
    if data["listing_type"] == "tuition_grant_job":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎓 100% Kontrakt to'lanadi", callback_data="cov_100")],
                [InlineKeyboardButton(text="🎓 50% Kontrakt to'lanadi", callback_data="cov_50")],
            ]
        )
        prompt = "Iqtidorli kadrga to'lab beriladigan kontrakt ulushini tanlang:" if lang == "uz" else ("Выберите долю оплаты контракта:" if lang == "ru" else "Select tuition coverage share:")
        await msg.answer(prompt, reply_markup=kb)
    elif data["listing_type"] == "state_internship":
        await state.update_data(pay_amount=0, tuition_coverage=0)
        await state.set_state(PostJobStates.slots)
        prompt = "Nechta amaliyotchi talaba qabul qilasiz? (Kvota soni, masalan: 3):" if lang == "uz" else ("Сколько практикантов вы принимаете? (Квота мест, например: 3):" if lang == "ru" else "How many interns will you accept? (Quota, e.g.: 3):")
        await msg.answer(prompt)
    else:
        prompt = "To'lov miqdorini kiriting (so'mda, masalan: 150000 / smena):" if lang == "uz" else ("Введите размер оплаты (в сумах, например: 150000):" if lang == "ru" else "Enter payment amount (in UZS, e.g.: 150000):")
        await msg.answer(prompt)


@router.callback_query(PostJobStates.pay_or_grant, F.data.startswith("cov_"))
async def process_tuition_coverage(call: CallbackQuery, state: FSMContext):
    coverage = int(call.data.replace("cov_", ""))
    await state.update_data(tuition_coverage=coverage, pay_amount=0)
    await call.answer()
    await state.set_state(PostJobStates.slots)

    data = await state.get_data()
    lang = data.get("lang", "uz")
    prompt = "Nechta iqtidorli kadr qabul qilasiz? (Bo'sh o'rinlar soni):" if lang == "uz" else ("Сколько мест предоставляется?:" if lang == "ru" else "How many talent quota slots?:")
    await call.message.answer(prompt)


@router.message(PostJobStates.pay_or_grant, F.text)
async def process_pay_amount(msg: Message, state: FSMContext):
    try:
        pay = int(msg.text.replace(" ", "").replace(",", "").replace(".", ""))
    except ValueError:
        pay = 100000
    await state.update_data(pay_amount=pay, tuition_coverage=0)
    await state.set_state(PostJobStates.slots)

    data = await state.get_data()
    lang = data.get("lang", "uz")
    prompt = "Nechta talaba qabul qilasiz? (Bo'sh o'rinlar soni, masalan: 2):" if lang == "uz" else ("Сколько мест требуется? (Например: 2):" if lang == "ru" else "How many candidates needed? (E.g.: 2):")
    await msg.answer(prompt)


@router.message(PostJobStates.slots, F.text)
async def process_slots(msg: Message, state: FSMContext, bot: Bot):
    try:
        slots = int(msg.text.strip())
    except ValueError:
        slots = 1

    data = await state.get_data()
    lang = data.get("lang", "uz")
    from datetime import date

    job_id = await JobsRepo.create_job(
        employer_id=data["employer_id"],
        title=data["title"],
        listing_type=data["listing_type"],
        category=data["employer_category"],
        work_format=data["work_format"],
        slots_needed=slots,
        target_majors=data["target_majors"],
        duties=["Amaliyot va vazifalarni o'z vaqtida bajarish"],
        start_time=data.get("start_time", "14:00"),
        end_time=data.get("end_time", "18:00"),
        pay_amount=data.get("pay_amount", 0),
        tuition_coverage_percent=data.get("tuition_coverage", 0),
        work_obligation_years=1 if data.get("tuition_coverage", 0) > 0 else 0,
        job_date=str(date.today()),
        lat=41.5500,
        lon=60.6300,
        status="open",
    )

    await state.clear()
    
    if lang == "ru":
        reply = (
            f"✅ **Объявление успешно опубликовано!**\n\n"
            f"🎯 Алгоритм подбора активирован: подходящим студентам отправляются персональные уведомления."
        )
    elif lang == "en":
        reply = (
            f"✅ **Job successfully posted!**\n\n"
            f"🎯 Matching engine running: personalized alerts are being dispatched to matching students."
        )
    else:
        reply = (
            f"✅ **E'lon muvaffaqiyatli joylandi!**\n\n"
            f"🎯 'Oltin Uchburchak' algoritmi ishga tushdi: mos keladigan barcha talabalarga shaxsiy bildirishnoma yuborilmoqda."
        )

    await msg.answer(reply, reply_markup=get_employer_main_keyboard(lang), parse_mode="Markdown")

    # Fondagi xizmat: Mos talabalarga bir zumda shaxsiy push yuborish
    created_job = await JobsRepo.get_by_id(job_id)
    if created_job:
        asyncio.create_task(notify_matching_students_about_job(bot, created_job))
