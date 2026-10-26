import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.core.callbacks import StudentConfirmAction
from bot.core.i18n import get_i18n, get_button_variants
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.students_repo import StudentsRepo
from bot.db.repositories.applications_repo import ApplicationsRepo

router = Router()


@router.message(F.text.in_(get_button_variants("BTN_STUDENT_APPS")))
async def show_my_applications(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    student = await StudentsRepo.get_by_tg_id(msg.from_user.id)
    if not student:
        await msg.answer(t.MSG_PLEASE_REGISTER, parse_mode="HTML")
        return

    apps = await ApplicationsRepo.get_by_student(student["id"])
    if not apps:
        await msg.answer(t.MSG_NO_APPS_YET, parse_mode="HTML")
        return

    status_labels = {
        "pending": "⏳ Ko'rib chiqilmoqda",
        "accepted": "✅ Qabul qilindi",
        "rejected": "❌ Rad etildi",
        "done": "🏁 Bajarildi",
        "no_show": "⚠️ Kelmagan (jarima)",
    }
    text = "📋 <b>Sizning arizalaringiz tarixi:</b>\n\n"

    for a in apps[:10]:
        st = status_labels.get(a.get("status"), a.get("status"))
        pay_info = f"{a.get('pay_amount', 0):,} so'm" if a.get("pay_amount", 0) > 0 else "Amaliyot / Stajirovka"
        text += (
            f"• <b>{html.escape(str(a.get('job_title')))}</b> ({html.escape(str(a.get('company_name')))}):\n"
            f"  Holati: <b>{st}</b> | To'lov: {pay_info}\n\n"
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💼 Bo'sh ish o'rinlari", callback_data="filter_jobs_jobs"),
        InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_carousel")
    ]])
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(F.text.in_(get_button_variants("BTN_STUDENT_ACTIVE")))
async def show_active_job(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    student = await StudentsRepo.get_by_tg_id(msg.from_user.id)
    if not student:
        await msg.answer(t.MSG_PLEASE_REGISTER, parse_mode="HTML")
        return

    active_app = await ApplicationsRepo.get_active_by_student(student["id"])
    if not active_app:
        no_job_text = (
            "🔍 <b>Sizda hozircha faol ish yoki amaliyot mavjud emas.</b>\n\n"
            "O'zingizga qulay grafikdagi bo'sh ish o'rinlarini yoki mutaxassisligingiz bo'yicha davlat amaliyotlarini tanlang:"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="💼 Mos bo'sh ish o'rinlari", callback_data="filter_jobs_jobs"),
                    InlineKeyboardButton(text="🏛 Davlat amaliyotlari", callback_data="filter_jobs_internships"),
                ],
                [
                    InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_carousel"),
                ]
            ]
        )
        await msg.answer(no_job_text, reply_markup=kb, parse_mode="HTML")
        return

    text = (
        f"💼 <b>Faol Ish / Amaliyotingiz:</b>\n\n"
        f"🏢 <b>Tashkilot:</b> {html.escape(str(active_app.get('company_name')))}\n"
        f"💼 <b>Vazifa:</b> {html.escape(str(active_app.get('job_title')))}\n"
        f"📍 <b>Manzil:</b> {html.escape(str(active_app.get('address')))}\n"
        f"📞 <b>Bog'lanish:</b> <code>{html.escape(str(active_app.get('contact_phone', '')))}</code>\n"
        f"⏰ <b>Vaqt:</b> {active_app.get('start_time', '')} – {active_app.get('end_time', '')}\n\n"
        f"Ish yoki amaliyot kunini yakunlagach, quyidagi tugmani bosing:"
    )
    btn_finish = "✅ Bugungi smenani tugatdim"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=btn_finish,
                    callback_data=StudentConfirmAction(action="finish_job", app_id=active_app["id"]).pack(),
                )
            ],
            [
                InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_carousel")
            ]
        ]
    )

    await msg.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(StudentConfirmAction.filter(F.action == "finish_job"))
async def process_finish_job(call: CallbackQuery, callback_data: StudentConfirmAction):
    await ApplicationsRepo.update_status(callback_data.app_id, "done")
    await call.answer("Smena yakunlandi!", show_alert=True)
    msg_text = "✅ <b>Bugungi ish muvaffaqiyatli topshirildi!</b> Ish beruvchi tasdiqlagach, baholash ochiladi."
    await call.message.edit_text(msg_text, parse_mode="HTML")


@router.callback_query(StudentConfirmAction.filter(F.action == "accept_offer"))
async def process_accept_offer(call: CallbackQuery, callback_data: StudentConfirmAction):
    await ApplicationsRepo.update_status(callback_data.app_id, "accepted")
    await call.answer("Tabriklaymiz! Ish tasdiqlandi.", show_alert=True)
    msg_text = "✅ <b>Siz ushbu o'ringa qabul qilindingiz!</b> 'Joriy ish' bo'limi orqali manzil va mas'ul bilan bog'lanishingiz mumkin."
    await call.message.edit_text(msg_text, parse_mode="HTML")
