import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.core.constants import UserRole
from bot.core.i18n import get_i18n, get_button_variants
from bot.core.keyboards import (
    get_location_request_keyboard,
    get_contact_request_keyboard,
    get_radius_keyboard,
    get_student_main_keyboard,
    get_cancel_keyboard,
)
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.students_repo import StudentsRepo
from bot.services.admin_notifier import notify_admin_new_student

router = Router()


class StudentRegistrationStates(StatesGroup):
    full_name = State()
    phone = State()
    region = State()
    university = State()
    course = State()
    major = State()
    location = State()
    radius = State()


# 1. Talaba ro'yxatdan o'tishni boshlash
@router.callback_query(F.data == "role_student")
async def start_student_registration(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    t = get_i18n(lang)

    user_id = await UsersRepo.create_user(call.from_user.id, UserRole.STUDENT.value, lang)
    await state.update_data(user_id=user_id, lang=lang)
    await state.set_state(StudentRegistrationStates.full_name)
    await call.message.answer(t.MSG_REG_STUDENT_NAME, reply_markup=get_cancel_keyboard(lang), parse_mode="Markdown")


# 2. Ism familiya qabul qilish -> Telefon raqam so'rash
@router.message(StudentRegistrationStates.full_name, F.text)
async def process_full_name(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    if msg.text in get_button_variants("BTN_CANCEL"):
        await state.clear()
        cancel_txt = "Bekor qilindi." if lang == "uz" else ("Отменено." if lang == "ru" else "Cancelled.")
        await msg.answer(cancel_txt, reply_markup=ReplyKeyboardRemove())
        return

    await state.update_data(full_name=msg.text.strip())
    await state.set_state(StudentRegistrationStates.phone)
    await msg.answer(
        t.MSG_REG_STUDENT_PHONE,
        reply_markup=get_contact_request_keyboard(lang),
        parse_mode="Markdown"
    )


# 3. Telefon raqam qabul qilish -> Istiqomat hududini so'rash
@router.message(StudentRegistrationStates.phone, F.contact)
@router.message(StudentRegistrationStates.phone, F.text)
async def process_phone(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    if msg.text in get_button_variants("BTN_CANCEL"):
        await state.clear()
        cancel_txt = "Bekor qilindi." if lang == "uz" else ("Отменено." if lang == "ru" else "Cancelled.")
        await msg.answer(cancel_txt, reply_markup=ReplyKeyboardRemove())
        return

    phone = msg.contact.phone_number if msg.contact else msg.text.strip()
    await state.update_data(phone_number=phone)
    await state.set_state(StudentRegistrationStates.region)

    if lang == "ru":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏛 г. Ургенч", callback_data="reg_Urganch shahri"),
                 InlineKeyboardButton(text="🕌 г. Хива", callback_data="reg_Xiva shahri")],
                [InlineKeyboardButton(text="🏙 г. Ташкент", callback_data="reg_Toshkent shahri"),
                 InlineKeyboardButton(text="✍️ Другой регион (ввести)", callback_data="reg_manual")],
            ]
        )
    elif lang == "en":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏛 Urgench city", callback_data="reg_Urganch shahri"),
                 InlineKeyboardButton(text="🕌 Khiva city", callback_data="reg_Xiva shahri")],
                [InlineKeyboardButton(text="🏙 Tashkent city", callback_data="reg_Toshkent shahri"),
                 InlineKeyboardButton(text="✍️ Other region (type)", callback_data="reg_manual")],
            ]
        )
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏛 Urganch shahri", callback_data="reg_Urganch shahri"),
                 InlineKeyboardButton(text="🕌 Xiva shahri", callback_data="reg_Xiva shahri")],
                [InlineKeyboardButton(text="🏙 Toshkent shahri", callback_data="reg_Toshkent shahri"),
                 InlineKeyboardButton(text="✍️ Boshqa hudud (qo'lda yozish)", callback_data="reg_manual")],
            ]
        )

    await msg.answer(t.MSG_REG_STUDENT_REGION, reply_markup=kb, parse_mode="Markdown")


# 4. Hudud qabul qilish (Tugma yoki matn) -> OTM (Universitet) so'rash
@router.callback_query(StudentRegistrationStates.region, F.data.startswith("reg_"))
async def process_region_callback(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    choice = call.data.replace("reg_", "")
    await call.answer()

    if choice == "manual":
        prompt = "Hozir yashayotgan tuman yoki shahringiz nomini yozing:" if lang == "uz" else ("Введите название вашего района или города проживания:" if lang == "ru" else "Type your residing district or city:")
        await call.message.answer(prompt)
        return

    await state.update_data(region=choice)
    await state.set_state(StudentRegistrationStates.university)
    await ask_university(call.message, lang, t)


@router.message(StudentRegistrationStates.region, F.text)
async def process_region_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    await state.update_data(region=msg.text.strip())
    await state.set_state(StudentRegistrationStates.university)
    await ask_university(msg, lang, t)


async def ask_university(message: Message, lang: str, t):
    if lang == "ru":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏛 УрГУ (Ургенч)", callback_data="otm_Urganch Davlat Universiteti (UrDU)")],
                [InlineKeyboardButton(text="💻 ТУИТ Ургенчский филиал", callback_data="otm_TATU Urganch filiali")],
                [InlineKeyboardButton(text="🏥 ТМА Ургенчский филиал", callback_data="otm_TMA Urganch filiali")],
                [InlineKeyboardButton(text="🌾 ТашГАУ филиал", callback_data="otm_ToshDAU Urganch filiali")],
                [InlineKeyboardButton(text="✍️ Другой ВУЗ (ввести вручную)", callback_data="otm_manual")],
            ]
        )
    elif lang == "en":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏛 Urgench State Univ (UrDU)", callback_data="otm_Urganch Davlat Universiteti (UrDU)")],
                [InlineKeyboardButton(text="💻 TUIT Urgench Branch", callback_data="otm_TATU Urganch filiali")],
                [InlineKeyboardButton(text="🏥 TMA Urgench Branch", callback_data="otm_TMA Urganch filiali")],
                [InlineKeyboardButton(text="🌾 TSAU Urgench Branch", callback_data="otm_ToshDAU Urganch filiali")],
                [InlineKeyboardButton(text="✍️ Other University (type)", callback_data="otm_manual")],
            ]
        )
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏛 UrDU (Urganch Davlat Universiteti)", callback_data="otm_Urganch Davlat Universiteti (UrDU)")],
                [InlineKeyboardButton(text="💻 TATU Urganch filiali", callback_data="otm_TATU Urganch filiali")],
                [InlineKeyboardButton(text="🏥 TMA Urganch filiali", callback_data="otm_TMA Urganch filiali")],
                [InlineKeyboardButton(text="🌾 ToshDAU Urganch filiali", callback_data="otm_ToshDAU Urganch filiali")],
                [InlineKeyboardButton(text="✍️ Boshqa OTM (qo'lda yozish)", callback_data="otm_manual")],
            ]
        )
    await message.answer(t.MSG_REG_STUDENT_UNIVERSITY, reply_markup=kb, parse_mode="Markdown")


# 5. Universitet qabul qilish (Tugma yoki matn) -> Kurs / Bosqich tanlash (1 2 3 4 va Magistratura 1 2)
@router.callback_query(StudentRegistrationStates.university, F.data.startswith("otm_"))
async def process_university_callback(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    choice = call.data.replace("otm_", "")
    await call.answer()

    if choice == "manual":
        prompt = "Tahsil olayotgan OTM (Universitet / Institut) nomini yozing:" if lang == "uz" else ("Напишите название вашего ВУЗа:" if lang == "ru" else "Type your University or Institute name:")
        await call.message.answer(prompt)
        return

    await state.update_data(university=choice)
    await state.set_state(StudentRegistrationStates.course)
    await ask_course(call.message, lang, t)


@router.message(StudentRegistrationStates.university, F.text)
async def process_university_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    await state.update_data(university=msg.text.strip())
    await state.set_state(StudentRegistrationStates.course)
    await ask_course(msg, lang, t)


async def ask_course(message: Message, lang: str, t):
    if lang == "ru":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="1-й курс", callback_data="course_1"),
                    InlineKeyboardButton(text="2-й курс", callback_data="course_2"),
                    InlineKeyboardButton(text="3-й курс", callback_data="course_3"),
                    InlineKeyboardButton(text="4-й курс", callback_data="course_4"),
                ],
                [
                    InlineKeyboardButton(text="🎓 Магистратура 1-й курс", callback_data="course_mag_1"),
                    InlineKeyboardButton(text="🎓 Магистратура 2-й курс", callback_data="course_mag_2"),
                ]
            ]
        )
    elif lang == "en":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="1st Year", callback_data="course_1"),
                    InlineKeyboardButton(text="2nd Year", callback_data="course_2"),
                    InlineKeyboardButton(text="3rd Year", callback_data="course_3"),
                    InlineKeyboardButton(text="4th Year", callback_data="course_4"),
                ],
                [
                    InlineKeyboardButton(text="🎓 Master's Year 1", callback_data="course_mag_1"),
                    InlineKeyboardButton(text="🎓 Master's Year 2", callback_data="course_mag_2"),
                ]
            ]
        )
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="1-kurs", callback_data="course_1"),
                    InlineKeyboardButton(text="2-kurs", callback_data="course_2"),
                    InlineKeyboardButton(text="3-kurs", callback_data="course_3"),
                    InlineKeyboardButton(text="4-kurs", callback_data="course_4"),
                ],
                [
                    InlineKeyboardButton(text="🎓 Magistratura 1-kurs", callback_data="course_mag_1"),
                    InlineKeyboardButton(text="🎓 Magistratura 2-kurs", callback_data="course_mag_2"),
                ]
            ]
        )
    await message.answer(t.MSG_REG_STUDENT_COURSE, reply_markup=kb, parse_mode="Markdown")


# 6. Kurs qabul qilish -> Mutaxassislik (Major) so'rash
@router.callback_query(StudentRegistrationStates.course, F.data.startswith("course_"))
async def process_course(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    raw_val = call.data.replace("course_", "")
    await call.answer()

    if raw_val == "mag_1":
        course_num = 5
        label = "Magistratura 1-kurs" if lang == "uz" else ("Магистратура 1-й курс" if lang == "ru" else "Master's Year 1")
    elif raw_val == "mag_2":
        course_num = 6
        label = "Magistratura 2-kurs" if lang == "uz" else ("Магистратура 2-й курс" if lang == "ru" else "Master's Year 2")
    else:
        course_num = int(raw_val)
        label = f"{course_num}-kurs" if lang == "uz" else (f"{course_num}-й курс" if lang == "ru" else f"Year {course_num}")

    await state.update_data(course=course_num, course_label=label)
    await state.set_state(StudentRegistrationStates.major)
    await call.message.answer(t.MSG_REG_STUDENT_MAJOR, parse_mode="Markdown")


# 7. Mutaxassislik qabul qilish -> Yashash joyi (TTJ / Ijara kvartira) lokatsiyasini so'rash
@router.message(StudentRegistrationStates.major, F.text)
async def process_major(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    await state.update_data(major=msg.text.strip())
    await state.set_state(StudentRegistrationStates.location)
    await msg.answer(
        t.MSG_REG_STUDENT_LOCATION,
        reply_markup=get_location_request_keyboard(lang),
        parse_mode="Markdown"
    )


# 8. Lokatsiya qabul qilish -> Qidiruv radiusini tanlash
@router.message(StudentRegistrationStates.location, F.location)
async def process_location(msg: Message, state: FSMContext):
    lat = msg.location.latitude
    lon = msg.location.longitude
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    loc_name = "Talaba yashash joyi (TTJ / Kvartira)"
    await state.update_data(lat=lat, lon=lon, location_name=loc_name)
    await state.set_state(StudentRegistrationStates.radius)
    await msg.answer(t.MSG_REG_STUDENT_RADIUS, reply_markup=get_radius_keyboard(), parse_mode="Markdown")


@router.message(StudentRegistrationStates.location, F.text)
async def process_location_text_or_skip(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    loc_name = msg.text.strip() if msg.text else "Urganch shahri"
    await state.update_data(lat=41.5500, lon=60.6300, location_name=loc_name)
    await state.set_state(StudentRegistrationStates.radius)
    await msg.answer(t.MSG_REG_STUDENT_RADIUS, reply_markup=get_radius_keyboard(), parse_mode="Markdown")


# 9. Radius tanlash -> Bazaga saqlash va Adminga zudlik bilan bildirishnoma yuborish
@router.callback_query(StudentRegistrationStates.radius, F.data.startswith("radius_"))
async def process_radius(call: CallbackQuery, state: FSMContext, bot: Bot):
    radius = float(call.data.split("_")[1])
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)
    await call.answer()

    student_id = await StudentsRepo.create_or_update(
        user_id=data["user_id"],
        full_name=data["full_name"],
        phone_number=data.get("phone_number", ""),
        region=data.get("region", "Urganch"),
        university=data.get("university", "Urganch Davlat Universiteti"),
        course=data.get("course", 1),
        course_label=data.get("course_label", "1-kurs"),
        faculty=data.get("university", "OTM"),
        major=data.get("major", "Umumiy"),
        location_lat=data.get("lat", 41.5500),
        location_lon=data.get("lon", 60.6300),
        location_name=data.get("location_name", "TTJ / Kvartira"),
        max_distance_km=radius,
        is_contract=True,
        yearly_tuition_amount=12000000,
        gpa_score=4.5,
    )

    # 1. Adminga yangi talaba ro'yxatdan to'liq o'tganligi haqida zudlik bilan bildirishnoma
    student_record = await StudentsRepo.get_by_user_id(data["user_id"])
    if student_record:
        student_record["tg_id"] = call.from_user.id
        asyncio.create_task(notify_admin_new_student(bot, student_record))

    await state.clear()
    await call.message.answer(
        t.MSG_REG_STUDENT_SUCCESS,
        reply_markup=get_student_main_keyboard(lang),
        parse_mode="Markdown"
    )
