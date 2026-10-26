import html
import logging
from typing import List, Tuple, Dict, Any
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.core.callbacks import EmployerAppAction, EmployerActiveNav
from bot.core.i18n import get_i18n, get_button_variants
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo
from bot.db.repositories.jobs_repo import JobsRepo
from bot.db.repositories.applications_repo import ApplicationsRepo
from bot.services.backup_manager import BackupManager

logger = logging.getLogger(__name__)
router = Router()


async def get_employer_active_workers(user_id: int) -> Tuple[str, List[Tuple[Dict[str, Any], Dict[str, Any]]]]:
    emp = await EmployersRepo.get_by_tg_id(user_id)
    if not emp:
        return "not_registered", []

    my_jobs = await JobsRepo.get_by_employer(emp["id"])
    if not my_jobs:
        return "no_jobs", []

    active_list = []
    for job in my_jobs:
        apps = await ApplicationsRepo.get_by_job(job["id"])
        for a in apps:
            if a.get("status") in ["accepted", "done"]:
                active_list.append((job, a))

    return "ok", active_list


async def render_active_workers_carousel(event, page: int = 0, is_edit: bool = False):
    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id
    msg = event.message if is_callback else event
    lang = await UsersRepo.get_user_lang(user_id)
    t = get_i18n(lang)

    status, active_list = await get_employer_active_workers(user_id)

    if status == "not_registered":
        await (msg.edit_text if is_edit else msg.answer)(t.MSG_PLEASE_REGISTER, parse_mode="HTML")
        return
    if status == "no_jobs":
        await (msg.edit_text if is_edit else msg.answer)(t.MSG_NO_JOBS_YET, parse_mode="HTML")
        return

    if not active_list:
        no_workers_text = (
            "🔍 <b>Hozircha faol ishchilar yoki amaliyotchilar mavjud emas.</b>\n\n"
            "Nomzodlar arizasini qabul qilganingizdan so'ng, ular shu yerda ko'rinadi."
        )
        no_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_active_workers")
        ]])
        if is_edit:
            try:
                await msg.edit_text(no_workers_text, reply_markup=no_kb, parse_mode="HTML")
            except Exception:
                await msg.answer(no_workers_text, reply_markup=no_kb, parse_mode="HTML")
        else:
            await msg.answer(no_workers_text, reply_markup=no_kb, parse_mode="HTML")
        return

    total = len(active_list)
    page = max(0, min(page, total - 1))
    job, a = active_list[page]

    status_note = "✅ Xodim bugungi smenani yakunlaganini bildirdi" if a.get("status") == "done" else "🕒 Ish/Amaliyot jarayonida"

    card_text = (
        f"📅 <b>Bugungi xodim / amaliyotchi ({page + 1}/{total}):</b>\n\n"
        f"💼 <b>Vazifa:</b> {html.escape(str(job.get('title')))}\n"
        f"👤 <b>Talaba:</b> {html.escape(str(a.get('full_name')))} ({html.escape(str(a.get('major')))}, {a.get('course')}-kurs)\n"
        f"📞 <b>Telefon:</b> <code>{html.escape(str(a.get('phone_number', 'Mavjud emas')))}</code>\n"
        f"📍 <b>Holati:</b> <i>{status_note}</i>\n"
    )

    buttons = []

    if total > 1:
        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    text="⬅️ Oldingi",
                    callback_data=EmployerActiveNav(page=page - 1, action="nav").pack()
                )
            )
        nav_row.append(
            InlineKeyboardButton(
                text=f"📄 {page + 1} / {total}",
                callback_data=EmployerActiveNav(page=page, action="noop").pack()
            )
        )
        if page < total - 1:
            nav_row.append(
                InlineKeyboardButton(
                    text="Keyingi ➡️",
                    callback_data=EmployerActiveNav(page=page + 1, action="nav").pack()
                )
            )
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(
            text="✅ Ishni tasdiqlash",
            callback_data=EmployerAppAction(action="finish", app_id=a["id"]).pack(),
        ),
        InlineKeyboardButton(
            text="⚠️ Kelmadi (No-show)",
            callback_data=EmployerAppAction(action="no_show", app_id=a["id"]).pack(),
        ),
    ])

    buttons.append([
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_active_workers")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if is_edit and is_callback:
        try:
            await msg.edit_text(card_text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Active workers edit error: {e}")
            await msg.answer(card_text, reply_markup=kb, parse_mode="HTML")
    else:
        await msg.answer(card_text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text.in_(get_button_variants("BTN_EMP_ACTIVE")))
@router.message(F.text.in_(get_button_variants("BTN_EMP_INTERNSHIP_EVAL")))
async def show_active_workers(msg: Message):
    await render_active_workers_carousel(msg, page=0, is_edit=False)


@router.callback_query(EmployerActiveNav.filter(F.action == "nav"))
async def process_active_nav(call: CallbackQuery, callback_data: EmployerActiveNav):
    await call.answer()
    await render_active_workers_carousel(call, page=callback_data.page, is_edit=True)


@router.callback_query(EmployerActiveNav.filter(F.action == "noop"))
async def process_active_noop(call: CallbackQuery):
    await call.answer("Xodimlar orasida navigatsiya qilish uchun ⬅️ va ➡️ tugmalaridan foydalaning.")


@router.callback_query(F.data == "close_active_workers")
async def process_close_active_workers(call: CallbackQuery):
    await call.answer("Asosiy menyu")
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    from bot.core.keyboards import get_employer_main_keyboard
    kb = get_employer_main_keyboard(lang)
    try:
        await call.message.delete()
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await call.message.answer(
        "🏢 <b>Ish beruvchi kabineti:</b>\nQuyidagi tugmalar orqali kerakli bo'limni tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(EmployerAppAction.filter(F.action == "no_show"))
async def process_no_show(call: CallbackQuery, callback_data: EmployerAppAction, bot: Bot):
    app = await ApplicationsRepo.get_by_id(callback_data.app_id)
    if not app:
        await call.answer("Ariza topilmadi.", show_alert=True)
        return

    from bot.db.connection import db
    await db.execute("UPDATE students SET trust_score = GREATEST(trust_score - 10, 0) WHERE id = $1", app["student_id"])
    await ApplicationsRepo.update_status(app["id"], "no_show", "Talaba ishga kelmadi")

    await call.answer("Kelmadi deb belgilandi! Zaxiradagi talabaga taklif yuborilmoqda...", show_alert=True)

    # Zaxira zanjirini ishga tushirish
    await BackupManager.handle_candidate_dropout(
        bot=bot,
        job_id=app["job_id"],
        dropped_student_name=app.get("student_name", "Talaba")
    )

    await render_active_workers_carousel(call, page=0, is_edit=True)


@router.callback_query(EmployerAppAction.filter(F.action == "finish"))
async def process_confirm_finish(call: CallbackQuery, callback_data: EmployerAppAction):
    await ApplicationsRepo.update_status(callback_data.app_id, "done")
    await call.answer("Ish yakunlandi deb tasdiqlandi!", show_alert=True)
    await render_active_workers_carousel(call, page=0, is_edit=True)
