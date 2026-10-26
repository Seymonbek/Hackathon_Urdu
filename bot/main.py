import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from bot.config import settings
from bot.core.constants import UserRole
from bot.core.i18n import get_i18n, get_button_variants
from bot.core.keyboards import (
    get_language_choice_keyboard,
    get_role_choice_keyboard,
    get_student_main_keyboard,
    get_employer_main_keyboard,
    get_tutor_main_keyboard,
    get_admin_main_keyboard,
    get_admin_role_switch_keyboard,
)
from bot.core.middleware import ThrottlingMiddleware, BlockCheckMiddleware
from bot.db.connection import db
from bot.db.seed import seed_initial_data
from bot.db.repositories.users_repo import UsersRepo
from bot.panels.student.router import router as student_router
from bot.panels.employer.router import router as employer_router
from bot.panels.admin.router import router as admin_router
from bot.panels.tutor.router import tutor_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("kasbdosh_bot")

root_router = Router()


@root_router.message(CommandStart())
async def handle_start(msg: Message):
    user_id = msg.from_user.id
    user = await UsersRepo.get_by_tg_id(user_id)

    # 1. Yangi foydalanuvchi bo'lsa yoki tili tanlanmagan bo'lsa — avval tilni so'raymiz
    if not user or not user.get("lang"):
        welcome_multilang = (
            "Assalomu alaykum! **Kasbdosh / Imkon** tizimiga xush kelibsiz!\n"
            "Добро пожаловать в систему **Kasbdosh / Imkon**!\n"
            "Welcome to **Kasbdosh / Imkon** platform!\n\n"
            "Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please select your language:"
        )
        await msg.answer(welcome_multilang, reply_markup=get_language_choice_keyboard(), parse_mode="Markdown")
        return

    lang = user.get("lang", "uz")
    t = get_i18n(lang)

    # 2. Super-Admin tekshiruvi
    if user_id in settings.ADMIN_IDS:
        if user.get("role") != UserRole.ADMIN.value:
            await UsersRepo.create_user(user_id, UserRole.ADMIN.value, lang)
        await msg.answer(
            t.MSG_ADMIN_WELCOME,
            reply_markup=get_admin_main_keyboard(lang),
            parse_mode="Markdown"
        )
        return

    # 3. Mavjud talaba, ish beruvchi yoki tyutor
    role = user.get("role")
    if role == UserRole.STUDENT.value:
        await msg.answer(
            t.MSG_STUDENT_DASHBOARD_TITLE,
            reply_markup=get_student_main_keyboard(lang),
            parse_mode="Markdown"
        )
    elif role == UserRole.EMPLOYER.value:
        await msg.answer(
            t.MSG_EMPLOYER_DASHBOARD_TITLE,
            reply_markup=get_employer_main_keyboard(lang),
            parse_mode="Markdown"
        )
    elif role == UserRole.TUTOR.value:
        await msg.answer(
            t.MSG_TUTOR_DASHBOARD_TITLE,
            reply_markup=get_tutor_main_keyboard(lang),
            parse_mode="Markdown"
        )
    else:
        await msg.answer(t.MSG_WELCOME, reply_markup=get_role_choice_keyboard(lang), parse_mode="Markdown")


@root_router.message(Command("lang"))
@root_router.message(Command("language"))
@root_router.message(F.text.in_(get_button_variants("BTN_SETTINGS_LANG")))
async def handle_change_language(msg: Message):
    lang_prompt = (
        "Tilni tanlang / Выберите язык / Please select language:"
    )
    await msg.answer(lang_prompt, reply_markup=get_language_choice_keyboard())


@root_router.callback_query(F.data.startswith("set_lang_"))
async def process_set_language(call: CallbackQuery):
    lang = call.data.replace("set_lang_", "")
    user_id = call.from_user.id
    
    await UsersRepo.update_lang(user_id, lang)
    await call.answer("Til saqlandi! / Язык сохранён! / Language saved!")

    t = get_i18n(lang)
    user = await UsersRepo.get_by_tg_id(user_id)
    role = user.get("role") if user else None

    # Admin bo'lsa
    if user_id in settings.ADMIN_IDS and role == UserRole.ADMIN.value:
        await call.message.answer(
            t.MSG_ADMIN_WELCOME,
            reply_markup=get_admin_main_keyboard(lang),
            parse_mode="Markdown"
        )
        return

    # Roliga qarab tegishli menyuni ochish
    if role == UserRole.STUDENT.value:
        await call.message.answer(
            t.MSG_STUDENT_DASHBOARD_TITLE,
            reply_markup=get_student_main_keyboard(lang),
            parse_mode="Markdown"
        )
    elif role == UserRole.EMPLOYER.value:
        await call.message.answer(
            t.MSG_EMPLOYER_DASHBOARD_TITLE,
            reply_markup=get_employer_main_keyboard(lang),
            parse_mode="Markdown"
        )
    elif role == UserRole.TUTOR.value:
        await call.message.answer(
            t.MSG_TUTOR_DASHBOARD_TITLE,
            reply_markup=get_tutor_main_keyboard(lang),
            parse_mode="Markdown"
        )
    else:
        await call.message.answer(
            t.MSG_WELCOME,
            reply_markup=get_role_choice_keyboard(lang),
            parse_mode="Markdown"
        )


@root_router.message(Command("admin"))
async def handle_admin_command(msg: Message):
    user_id = msg.from_user.id
    if user_id not in settings.ADMIN_IDS:
        await msg.answer("Kechirasiz, sizda ushbu buyruqqa kirish huquqi yo'q.")
        return

    lang = await UsersRepo.get_user_lang(user_id)
    t = get_i18n(lang)
    await UsersRepo.create_user(user_id, UserRole.ADMIN.value, lang)
    await msg.answer(
        t.MSG_ADMIN_WELCOME,
        reply_markup=get_admin_main_keyboard(lang),
        parse_mode="Markdown"
    )


@root_router.message(Command("switch_role"))
@root_router.message(F.text.in_(get_button_variants("BTN_ADM_SWITCH_ROLE")))
async def handle_switch_role_prompt(msg: Message):
    user_id = msg.from_user.id
    if user_id not in settings.ADMIN_IDS:
        return

    lang = await UsersRepo.get_user_lang(user_id)
    prompt_text = "🔁 Qaysi rolda tizimni sinab ko'rmoqchisiz?"
    if lang == "ru":
        prompt_text = "🔁 В какой роли вы хотите протестировать систему?"
    elif lang == "en":
        prompt_text = "🔁 Which role would you like to test the system with?"

    await msg.answer(prompt_text, reply_markup=get_admin_role_switch_keyboard(lang))


@root_router.callback_query(F.data.startswith("switch_to_"))
async def process_role_switch(call: CallbackQuery):
    user_id = call.from_user.id
    if user_id not in settings.ADMIN_IDS:
        await call.answer("Ruxsat yo'q!", show_alert=True)
        return

    target_role = call.data.replace("switch_to_", "")
    lang = await UsersRepo.get_user_lang(user_id)
    t = get_i18n(lang)

    if target_role == "student":
        await UsersRepo.create_user(user_id, UserRole.STUDENT.value, lang)
        await call.answer("Talaba rejimiga o'tildi!")
        await call.message.answer(
            "🎓 **Talaba rejimi faollashdi (Test rejimi):**\n"
            "Siz talabalar ko'radigan barcha imkoniyatlarni sinab ko'rishingiz mumkin. "
            "Admin panelga qaytish uchun /admin buyrug'ini yuboring.",
            reply_markup=get_student_main_keyboard(lang),
            parse_mode="Markdown"
        )
    elif target_role == "employer":
        await UsersRepo.create_user(user_id, UserRole.EMPLOYER.value, lang)
        await call.answer("Ish beruvchi rejimiga o'tildi!")
        await call.message.answer(
            "🏢 **Ish beruvchi / Tashkilot rejimi faollashdi (Test rejimi):**\n"
            "Vakansiya va kvotalar joylashingiz mumkin. "
            "Admin panelga qaytish uchun /admin buyrug'ini yuboring.",
            reply_markup=get_employer_main_keyboard(lang),
            parse_mode="Markdown"
        )
    elif target_role == "tutor":
        await UsersRepo.create_user(user_id, UserRole.TUTOR.value, lang)
        await call.answer("Tyutor rejimiga o'tildi!")
        await call.message.answer(
            "🧑‍🏫 **Tyutor boshqaruv kabineti faollashdi (Test rejimi):**\n"
            "Talabalar bandligi, ish joylari va sessiya qulfini boshqarishingiz mumkin. "
            "Admin panelga qaytish uchun /admin buyrug'ini yuboring.",
            reply_markup=get_tutor_main_keyboard(lang),
            parse_mode="Markdown"
        )
    elif target_role == "admin":
        await UsersRepo.create_user(user_id, UserRole.ADMIN.value, lang)
        await call.answer("Admin rejimiga qaytildi!")
        await call.message.answer(
            t.MSG_ADMIN_WELCOME,
            reply_markup=get_admin_main_keyboard(lang),
            parse_mode="Markdown"
        )


async def main():
    logger.info("Kasbdosh bot tizimi ishga tushirilmoqda...")

    # Ma'lumotlar bazasiga ulanish
    await db.connect()

    # Demo ma'lumotlarni kiritish
    await seed_initial_data()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewarelarni ro'yxatdan o'tkazish
    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.message.middleware(BlockCheckMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.3))
    dp.callback_query.middleware(BlockCheckMiddleware())

    # Routerlarni ulash
    dp.include_router(root_router)
    dp.include_router(student_router)
    dp.include_router(employer_router)
    dp.include_router(admin_router)
    dp.include_router(tutor_router)

    try:
        logger.info(f"Bot muvaffaqiyatli ishga tushdi: @{settings.BOT_NAME}")
        # Avvalgi kutilayotgan eskirgan xabarlarni tozalash (drop pending updates)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot ishlashida xatolik yuz berdi: {e}")
    finally:
        await db.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
