import html
import logging
from typing import List, Tuple, Dict, Any
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.core.callbacks import EmployerAppAction, EmployerInboxNav
from bot.core.i18n import get_i18n, get_button_variants
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo
from bot.db.repositories.jobs_repo import JobsRepo
from bot.db.repositories.applications_repo import ApplicationsRepo

logger = logging.getLogger(__name__)
router = Router()


async def get_employer_pending_apps(user_id: int) -> Tuple[str, List[Tuple[Dict[str, Any], Dict[str, Any]]]]:
    """Ish beruvchining barcha vakansiyalariga kelgan pending arizalarini yig'adi."""
    emp = await EmployersRepo.get_by_tg_id(user_id)
    if not emp:
        return "not_registered", []

    my_jobs = await JobsRepo.get_by_employer(emp["id"])
    if not my_jobs:
        return "no_jobs", []

    pending_list = []
    for job in my_jobs:
        apps = await ApplicationsRepo.get_by_job(job["id"])
        for a in apps:
            if a.get("status") == "pending":
                pending_list.append((job, a))

    return "ok", pending_list


async def render_inbox_carousel(event, page: int = 0, is_edit: bool = False):
    """Yangi arizalarni bitta xabarda paginatsiya orqali ko'rsatadi."""
    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id
    msg = event.message if is_callback else event
    lang = await UsersRepo.get_user_lang(user_id)
    t = get_i18n(lang)

    status, pending_list = await get_employer_pending_apps(user_id)

    if status == "not_registered":
        await (msg.edit_text if is_edit else msg.answer)(t.MSG_PLEASE_REGISTER, parse_mode="HTML")
        return
    if status == "no_jobs":
        await (msg.edit_text if is_edit else msg.answer)(t.MSG_NO_JOBS_YET, parse_mode="HTML")
        return

    if not pending_list:
        no_apps_text = (
            "📭 <b>Hozircha yangi arizalar mavjud emas.</b>\n\n"
            "Talabalar sizning vakansiyangizga ariza topshirishi bilan bot orqali bildirishnoma olasiz."
        )
        no_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_employer_inbox")
        ]])
        if is_edit:
            try:
                await msg.edit_text(no_apps_text, reply_markup=no_kb, parse_mode="HTML")
            except Exception:
                await msg.answer(no_apps_text, reply_markup=no_kb, parse_mode="HTML")
        else:
            await msg.answer(no_apps_text, reply_markup=no_kb, parse_mode="HTML")
        return

    total = len(pending_list)
    page = max(0, min(page, total - 1))
    job, a = pending_list[page]

    # Nomzod kartasi matni
    card_text = (
        f"📩 <b>Yangi Nomzod ({page + 1}/{total}):</b>\n\n"
        f"💼 <b>Vakansiya:</b> {html.escape(str(job.get('title')))}\n"
        f"👤 <b>Talaba:</b> {html.escape(str(a.get('full_name')))}\n"
        f"🎓 <b>Yo'nalish:</b> {html.escape(str(a.get('major')))} ({a.get('course')}-kurs, {html.escape(str(a.get('university', 'UrDU')))})"
        f"\n⭐ <b>GPA bali:</b> <b>{a.get('gpa_score')}</b> | Ishonch: <b>{a.get('trust_score')}/100</b>\n"
        f"🎯 <b>Moslik:</b> <b>{a.get('match_score')}%</b>\n"
        f"📞 <b>Telefon:</b> <code>{html.escape(str(a.get('phone_number', 'Mavjud emas')))}</code>\n"
    )

    buttons = []

    # 1-qator: Agar 1 tadan ko'p bo'lsa navigatsiya
    if total > 1:
        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    text="⬅️ Oldingi",
                    callback_data=EmployerInboxNav(page=page - 1, action="nav").pack()
                )
            )
        nav_row.append(
            InlineKeyboardButton(
                text=f"📄 {page + 1} / {total}",
                callback_data=EmployerInboxNav(page=page, action="noop").pack()
            )
        )
        if page < total - 1:
            nav_row.append(
                InlineKeyboardButton(
                    text="Keyingi ➡️",
                    callback_data=EmployerInboxNav(page=page + 1, action="nav").pack()
                )
            )
        buttons.append(nav_row)

    # 2-qator: Boshqaruv tugmalari
    buttons.append([
        InlineKeyboardButton(
            text="✅ Qabul qilish",
            callback_data=EmployerAppAction(action="accept", app_id=a["id"]).pack(),
        ),
        InlineKeyboardButton(
            text="⏳ Zaxiraga",
            callback_data=EmployerAppAction(action="backup", app_id=a["id"]).pack(),
        ),
        InlineKeyboardButton(
            text="❌ Rad etish",
            callback_data=EmployerAppAction(action="reject", app_id=a["id"]).pack(),
        ),
    ])

    # 3-qator: Asosiy menyuga qaytish
    buttons.append([
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_employer_inbox")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if is_edit and is_callback:
        try:
            await msg.edit_text(card_text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Inbox edit error: {e}")
            await msg.answer(card_text, reply_markup=kb, parse_mode="HTML")
    else:
        await msg.answer(card_text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text.in_(get_button_variants("BTN_EMP_INBOX")))
async def show_employer_inbox(msg: Message):
    """Ish beruvchi arizalar pochtasi — 1 ta xabarda qulay karusel"""
    await render_inbox_carousel(msg, page=0, is_edit=False)


@router.callback_query(EmployerInboxNav.filter(F.action == "nav"))
async def process_inbox_navigation(call: CallbackQuery, callback_data: EmployerInboxNav):
    await call.answer()
    await render_inbox_carousel(call, page=callback_data.page, is_edit=True)


@router.callback_query(EmployerInboxNav.filter(F.action == "noop"))
async def process_inbox_noop(call: CallbackQuery):
    await call.answer("Nomzodlar orasida navigatsiya qilish uchun ⬅️ va ➡️ tugmalaridan foydalaning.")


@router.callback_query(F.data == "close_employer_inbox")
async def process_close_employer_inbox(call: CallbackQuery):
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


@router.message(F.text.in_(get_button_variants("BTN_EMP_MY_JOBS")))
async def show_employer_jobs(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    emp = await EmployersRepo.get_by_tg_id(msg.from_user.id)
    if not emp:
        await msg.answer(t.MSG_PLEASE_REGISTER, parse_mode="HTML")
        return

    my_jobs = await JobsRepo.get_by_employer(emp["id"])
    if not my_jobs:
        await msg.answer(t.MSG_NO_JOBS_YET, parse_mode="HTML")
        return

    header = "📋 <b>Sizning e'lonlaringiz:</b>\n\n"
    for j in my_jobs:
        status_sym = "🟢 Ochiq" if j.get("status") == "open" else "🔒 Yopiq"
        header += (
            f"• <b>{html.escape(str(j.get('title')))}</b> ({status_sym})\n"
            f"  Bandlik: {j.get('filled_count')}/{j.get('slots_needed')} | Soha: {html.escape(str(j.get('category')))}\n\n"
        )
    await msg.answer(header, parse_mode="HTML")


@router.callback_query(EmployerAppAction.filter(F.action == "accept"))
async def process_accept_candidate(call: CallbackQuery, callback_data: EmployerAppAction, bot: Bot):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    app = await ApplicationsRepo.get_by_id(callback_data.app_id)
    if not app:
        await call.answer("Ariza topilmadi.", show_alert=True)
        return

    await ApplicationsRepo.update_status(app["id"], "accepted")
    await JobsRepo.increment_filled_slot(app["job_id"])

    await call.answer("✅ Nomzod ishga qabul qilindi!", show_alert=True)

    # Talabaga bildirishnoma
    student_tg = app.get("student_tg_id")
    if student_tg:
        s_lang = await UsersRepo.get_user_lang(student_tg)
        notif = (
            f"🎉 <b>Tabriklaymiz! Siz qabul qilindingiz!</b>\n\n"
            f"🏢 <b>Tashkilot:</b> {html.escape(str(app.get('company_name')))}\n"
            f"💼 <b>Lavozim:</b> {html.escape(str(app.get('job_title')))}\n"
            f"📍 <b>Manzil:</b> {html.escape(str(app.get('employer_address')))}\n"
            f"📞 <b>Mas'ul telefon:</b> <code>{html.escape(str(app.get('employer_phone', '')))}</code>\n\n"
            f"Batafsil ma'lumotni '💼 Joriy ish' bo'limida ko'rishingiz mumkin."
        )
        try:
            await bot.send_message(chat_id=student_tg, text=notif, parse_mode="HTML")
        except Exception:
            pass

    # Keyingi nomzodga o'tish yoki xabarni yangilash
    await render_inbox_carousel(call, page=0, is_edit=True)


@router.callback_query(EmployerAppAction.filter(F.action == "backup"))
async def process_backup_candidate(call: CallbackQuery, callback_data: EmployerAppAction, bot: Bot):
    app = await ApplicationsRepo.get_by_id(callback_data.app_id)
    if not app:
        await call.answer("Ariza topilmadi.", show_alert=True)
        return

    from bot.db.connection import db
    await db.execute("UPDATE applications SET is_backup = TRUE, backup_rank = 1 WHERE id = $1", app["id"])
    await call.answer("⏳ Talaba zaxiraga olindi!", show_alert=True)

    # Talabaga xabar
    student_tg = app.get("student_tg_id")
    if student_tg:
        try:
            await bot.send_message(
                chat_id=student_tg,
                text=(
                    f"🛟 <b>Siz '{html.escape(str(app.get('job_title')))}' vakansiyasi bo'yicha Zaxiraga olindingiz!</b>\n"
                    f"Agar yangi o'rin ochilsa, sizga birinchi navbatda taklif keladi."
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

    await render_inbox_carousel(call, page=0, is_edit=True)


@router.callback_query(EmployerAppAction.filter(F.action == "reject"))
async def process_reject_candidate(call: CallbackQuery, callback_data: EmployerAppAction):
    await ApplicationsRepo.update_status(callback_data.app_id, "rejected", "Boshqa nomzod tanlandi")
    await call.answer("❌ Nomzod rad etildi.", show_alert=True)
    await render_inbox_carousel(call, page=0, is_edit=True)
