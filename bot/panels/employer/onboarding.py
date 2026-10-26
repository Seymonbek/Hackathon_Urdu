from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.core.constants import UserRole, OrgType
from bot.core.i18n import get_i18n
from bot.core.keyboards import get_employer_main_keyboard, get_cancel_keyboard, get_contact_request_keyboard
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo
from bot.services.admin_notifier import notify_admin_new_employer

router = Router()


class EmployerRegistrationStates(StatesGroup):
    company_name = State()
    org_type = State()
    category = State()
    address = State()
    phone = State()
    contact_person = State()


@router.callback_query(F.data == "role_employer")
async def start_employer_registration(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    t = get_i18n(lang)

    user_id = await UsersRepo.create_user(call.from_user.id, UserRole.EMPLOYER.value, lang)
    await state.update_data(user_id=user_id, lang=lang)
    await state.set_state(EmployerRegistrationStates.company_name)
    await call.message.answer(t.MSG_REG_EMP_NAME, reply_markup=get_cancel_keyboard(lang), parse_mode="Markdown")


@router.message(EmployerRegistrationStates.company_name, F.text)
async def process_emp_name(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    if msg.text == t.BTN_CANCEL:
        await state.clear()
        await msg.answer("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        return

    await state.update_data(company_name=msg.text.strip())
    await state.set_state(EmployerRegistrationStates.org_type)

    btn_state = "🏛 Davlat Organi / Sud / Shifoxona" if lang == "uz" else ("🏛 Госорган / Суд / Больница" if lang == "ru" else "🏛 State Agency / Court / Hospital")
    btn_comm = "🏢 Tijoriy Korxona / IT / Do'kon / Kafe" if lang == "uz" else ("🏢 Бизнес / IT / Магазин / Кафе" if lang == "ru" else "🏢 Commercial / IT / Store / Cafe")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=btn_state, callback_data="org_state")],
            [InlineKeyboardButton(text=btn_comm, callback_data="org_comm")],
        ]
    )
    await msg.answer(t.MSG_REG_EMP_ORG_TYPE, reply_markup=kb)


@router.callback_query(EmployerRegistrationStates.org_type, F.data.startswith("org_"))
async def process_org_type(call: CallbackQuery, state: FSMContext):
    org_type = OrgType.STATE_AGENCY.value if call.data == "org_state" else OrgType.COMMERCIAL.value
    await state.update_data(org_type=org_type)
    await call.answer()
    
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    await state.set_state(EmployerRegistrationStates.category)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚖️ Sud / Adliya / Huquq", callback_data="cat_court_law")],
            [InlineKeyboardButton(text="🏥 Shifoxona / Tibbiyot", callback_data="cat_medical")],
            [InlineKeyboardButton(text="📚 Ta'lim / O'quv markazi", callback_data="cat_education")],
            [InlineKeyboardButton(text="💻 IT / Media / SMM", callback_data="cat_it")],
            [InlineKeyboardButton(text="🛍 Savdo / Supermarket", callback_data="cat_retail")],
            [InlineKeyboardButton(text="☕️ Kafe / Umumiy ovqatlanish", callback_data="cat_horeca")],
        ]
    )
    await call.message.answer(t.MSG_REG_EMP_CATEGORY, reply_markup=kb)


@router.callback_query(EmployerRegistrationStates.category, F.data.startswith("cat_"))
async def process_category(call: CallbackQuery, state: FSMContext):
    category = call.data.replace("cat_", "")
    await state.update_data(category=category)
    await call.answer()

    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    await state.set_state(EmployerRegistrationStates.address)
    await call.message.answer(t.MSG_REG_EMP_ADDRESS)


@router.message(EmployerRegistrationStates.address, F.text)
async def process_address(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    await state.update_data(address=msg.text.strip(), district="Urganch")
    await state.set_state(EmployerRegistrationStates.phone)
    await msg.answer(t.MSG_REG_EMP_PHONE, reply_markup=get_contact_request_keyboard(lang))


@router.message(EmployerRegistrationStates.phone, F.contact)
@router.message(EmployerRegistrationStates.phone, F.text)
async def process_phone(msg: Message, state: FSMContext):
    phone = msg.contact.phone_number if msg.contact else msg.text.strip()
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    await state.update_data(phone=phone)
    await state.set_state(EmployerRegistrationStates.contact_person)
    await msg.answer(t.MSG_REG_EMP_PERSON, reply_markup=get_cancel_keyboard(lang))


@router.message(EmployerRegistrationStates.contact_person, F.text)
async def process_contact_person(msg: Message, state: FSMContext, bot: Bot):
    contact_person = msg.text.strip()
    data = await state.get_data()
    lang = data.get("lang", "uz")
    t = get_i18n(lang)

    emp_id = await EmployersRepo.create_or_update(
        user_id=data["user_id"],
        company_name=data["company_name"],
        org_type=data["org_type"],
        category=data["category"],
        address=data["address"],
        district=data.get("district", "Urganch"),
        contact_phone=data["phone"],
        contact_person=contact_person,
        lat=41.5500,
        lon=60.6300,
        offers_tuition_sponsorship=True,
    )

    # Adminga yangi tashkilot haqida tasdiqlash tugmalari bilan zudlik bilan bildirishnoma
    emp_record = await EmployersRepo.get_by_user_id(data["user_id"])
    if emp_record:
        emp_record["tg_id"] = msg.from_user.id
        import asyncio
        asyncio.create_task(notify_admin_new_employer(bot, emp_record, emp_id))

    await state.clear()
    
    success_msg = f"✅ **{data['company_name']} muvaffaqiyatli ro'yxatdan o'tdi!**\n\nEndi yangi vakansiya, amaliyot kvotasi yoki kontrakt to'lab berish e'lonini joylashingiz mumkin."
    if lang == "ru":
        success_msg = f"✅ **{data['company_name']} успешно зарегистрирована!**\n\nТеперь вы можете размещать вакансии, квоты на практику и гранты на оплату контракта."
    elif lang == "en":
        success_msg = f"✅ **{data['company_name']} successfully registered!**\n\nNow you can post vacancies, internship quotas, and tuition sponsorship grants."

    await msg.answer(
        success_msg,
        reply_markup=get_employer_main_keyboard(lang),
        parse_mode="Markdown"
    )
