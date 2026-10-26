from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from bot.core.i18n import get_i18n


def get_language_choice_keyboard() -> InlineKeyboardMarkup:
    """Tillar tanlovi klaviaturasi (3 ta til)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
            ]
        ]
    )


def get_role_choice_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Rol tanlash klaviaturasi."""
    t = get_i18n(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t.BTN_ROLE_STUDENT, callback_data="role_student"),
            ],
            [
                InlineKeyboardButton(text=t.BTN_ROLE_EMPLOYER, callback_data="role_employer"),
            ],
        ]
    )


def get_student_main_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Talabaning asosiy menyu klaviaturasi (Amaliyot va Ishlar alohida ajratilgan)."""
    t = get_i18n(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_STUDENT_JOBS), KeyboardButton(text=t.BTN_STUDENT_INTERNSHIPS)],
            [KeyboardButton(text=t.BTN_STUDENT_GRANTS), KeyboardButton(text=t.BTN_STUDENT_ACTIVE)],
            [KeyboardButton(text=t.BTN_STUDENT_APPS), KeyboardButton(text=t.BTN_STUDENT_PROFILE)],
        ],
        resize_keyboard=True,
    )


def get_employer_main_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Ish beruvchi / Davlat organi asosiy klaviaturasi."""
    t = get_i18n(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_EMP_POST_JOB), KeyboardButton(text=t.BTN_EMP_MY_JOBS)],
            [KeyboardButton(text=t.BTN_EMP_INBOX), KeyboardButton(text=t.BTN_EMP_GRANTS)],
            [KeyboardButton(text=t.BTN_EMP_ACTIVE), KeyboardButton(text=t.BTN_EMP_INTERNSHIP_EVAL)],
            [KeyboardButton(text=t.BTN_EMP_PROFILE), KeyboardButton(text=t.BTN_SETTINGS_LANG)],
        ],
        resize_keyboard=True,
    )


def get_tutor_main_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Tyutor boshqaruv klaviaturasi."""
    t = get_i18n(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_TUTOR_STUDENTS), KeyboardButton(text=t.BTN_TUTOR_EXAM_LOCK)],
            [KeyboardButton(text=t.BTN_TUTOR_EMPLOYMENT), KeyboardButton(text=t.BTN_TUTOR_PROFILE)],
            [KeyboardButton(text=t.BTN_SETTINGS_LANG)],
        ],
        resize_keyboard=True,
    )


def get_admin_main_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Super-Admin boshqaruv klaviaturasi."""
    t = get_i18n(lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_ADM_DASHBOARD), KeyboardButton(text=t.BTN_ADM_VERIFY)],
            [KeyboardButton(text=t.BTN_ADM_SPONSORSHIP), KeyboardButton(text=t.BTN_ADM_JOBS)],
            [KeyboardButton(text=t.BTN_ADM_STUDENTS), KeyboardButton(text=t.BTN_ADM_TUTORS)],
            [KeyboardButton(text=t.BTN_ADM_EXPORT), KeyboardButton(text=t.BTN_ADM_SWITCH_ROLE)],
            [KeyboardButton(text=t.BTN_SETTINGS_LANG)],
        ],
        resize_keyboard=True,
    )


def get_admin_role_switch_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Admin uchun rollarni sinash va almashtirish klaviaturasi."""
    if lang == "ru":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎓 Протестировать как Студент", callback_data="switch_to_student")],
                [InlineKeyboardButton(text="🏢 Протестировать как Работодатель", callback_data="switch_to_employer")],
                [InlineKeyboardButton(text="🧑‍🏫 Протестировать как Тьютор", callback_data="switch_to_tutor")],
                [InlineKeyboardButton(text="👑 Вернуться в панель Администратора", callback_data="switch_to_admin")],
            ]
        )
    elif lang == "en":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎓 Test as Student", callback_data="switch_to_student")],
                [InlineKeyboardButton(text="🏢 Test as Employer", callback_data="switch_to_employer")],
                [InlineKeyboardButton(text="🧑‍🏫 Test as Tutor", callback_data="switch_to_tutor")],
                [InlineKeyboardButton(text="👑 Return to Admin Panel", callback_data="switch_to_admin")],
            ]
        )
    else:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎓 Talaba sifatida sinash", callback_data="switch_to_student")],
                [InlineKeyboardButton(text="🏢 Ish beruvchi sifatida sinash", callback_data="switch_to_employer")],
                [InlineKeyboardButton(text="🧑‍🏫 Tyutor sifatida sinash", callback_data="switch_to_tutor")],
                [InlineKeyboardButton(text="👑 Admin panelga qaytish", callback_data="switch_to_admin")],
            ]
        )


def get_location_request_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    t = get_i18n(lang)
    loc_btn_text = "📍 Hozirgi joylashuvimni yuborish"
    if lang == "ru":
        loc_btn_text = "📍 Отправить мою геопозицию"
    elif lang == "en":
        loc_btn_text = "📍 Send my current location"

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=loc_btn_text, request_location=True)],
            [KeyboardButton(text=t.BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_contact_request_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    t = get_i18n(lang)
    contact_btn_text = "📱 Telefon raqamimni ulashish"
    if lang == "ru":
        contact_btn_text = "📱 Поделиться номером телефона"
    elif lang == "en":
        contact_btn_text = "📱 Share phone number"

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=contact_btn_text, request_contact=True)],
            [KeyboardButton(text=t.BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_cancel_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    t = get_i18n(lang)
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.BTN_CANCEL)]],
        resize_keyboard=True,
    )


def get_radius_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚶 1.5 km", callback_data="radius_1.5"),
                InlineKeyboardButton(text="🚲 3.0 km", callback_data="radius_3.0"),
            ],
            [
                InlineKeyboardButton(text="🚌 5.0 km", callback_data="radius_5.0"),
                InlineKeyboardButton(text="🌐 Remote / Global", callback_data="radius_15.0"),
            ],
        ]
    )
