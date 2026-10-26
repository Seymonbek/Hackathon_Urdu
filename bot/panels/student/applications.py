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
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    apps = await ApplicationsRepo.get_by_student(student["id"])
    if not apps:
        await msg.answer(t.MSG_NO_APPS_YET)
        return

    if lang == "ru":
        status_labels = {
            "pending": "⏳ На рассмотрении",
            "accepted": "✅ Принят",
            "rejected": "❌ Отклонён",
            "done": "🏁 Завершено",
            "no_show": "⚠️ Неявка (штраф)",
        }
        text = "📋 **История ваших заявок:**\n\n"
    elif lang == "en":
        status_labels = {
            "pending": "⏳ Under review",
            "accepted": "✅ Accepted",
            "rejected": "❌ Rejected",
            "done": "🏁 Completed",
            "no_show": "⚠️ No-show (penalty)",
        }
        text = "📋 **Your Application History:**\n\n"
    else:
        status_labels = {
            "pending": "⏳ Ko'rib chiqilmoqda",
            "accepted": "✅ Qabul qilindi",
            "rejected": "❌ Rad etildi",
            "done": "🏁 Bajarildi",
            "no_show": "⚠️ Kelmagan (jarima)",
        }
        text = "📋 **Sizning arizalaringiz tarixi:**\n\n"

    for a in apps[:10]:
        st = status_labels.get(a.get("status"), a.get("status"))
        pay_info = f"{a.get('pay_amount', 0):,} so'm" if a.get("pay_amount", 0) > 0 else ("Практика" if lang == "ru" else ("Internship" if lang == "en" else "Amaliyot"))
        text += (
            f"• **{a.get('job_title')}** ({a.get('company_name')})\n"
            f"  Status: **{st}** | Pay: {pay_info}\n\n"
        )

    await msg.answer(text, parse_mode="Markdown")


@router.message(F.text.in_(get_button_variants("BTN_STUDENT_ACTIVE")))
async def show_active_job(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    student = await StudentsRepo.get_by_tg_id(msg.from_user.id)
    if not student:
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    active_app = await ApplicationsRepo.get_active_by_student(student["id"])
    if not active_app:
        no_job_text = (
            "🔍 **Sizda hozircha faol ish yoki amaliyot mavjud emas.**\n\n"
            "O'zingizga qulay grafikdagi bo'sh ish o'rinlarini yoki mutaxassisligingiz bo'yicha davlat amaliyotlarini tanlang:"
        ) if lang == "uz" else (
            "🔍 **У вас пока нет активной работы или практики.**\n\n"
            "Выберите подходящие вакансии с гибким графиком или гос. практику:"
        ) if lang == "ru" else (
            "🔍 **You currently have no active job or internship.**\n\n"
            "Explore matching vacancies or state internships:"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="💼 Mos bo'sh ish o'rinlari", callback_data="filter_jobs_jobs"),
                    InlineKeyboardButton(text="🏛 Davlat amaliyotlari", callback_data="filter_jobs_internships"),
                ]
            ]
        )
        await msg.answer(no_job_text, reply_markup=kb, parse_mode="Markdown")
        return

    if lang == "ru":
        text = (
            f"💼 **Текущая работа / Практика:**\n\n"
            f"🏢 **Организация:** {active_app.get('company_name')}\n"
            f"💼 **Позиция:** {active_app.get('job_title')}\n"
            f"📍 **Адрес:** {active_app.get('address')}\n"
            f"📞 **Контакт:** {active_app.get('contact_phone')}\n"
            f"⏰ **Время:** {active_app.get('start_time', '')} – {active_app.get('end_time', '')}\n\n"
            f"После окончания смены нажмите кнопку ниже:"
        )
        btn_finish = "✅ Завершил сегодняшнюю смену"
    elif lang == "en":
        text = (
            f"💼 **Current Job / Internship:**\n\n"
            f"🏢 **Organization:** {active_app.get('company_name')}\n"
            f"💼 **Position:** {active_app.get('job_title')}\n"
            f"📍 **Address:** {active_app.get('address')}\n"
            f"📞 **Contact:** {active_app.get('contact_phone')}\n"
            f"⏰ **Time:** {active_app.get('start_time', '')} – {active_app.get('end_time', '')}\n\n"
            f"Once your shift is finished, press the button below:"
        )
        btn_finish = "✅ Finished today's shift"
    else:
        text = (
            f"💼 **Faol Ish / Amaliyotingiz:**\n\n"
            f"🏢 **Tashkilot:** {active_app.get('company_name')}\n"
            f"💼 **Vazifa:** {active_app.get('job_title')}\n"
            f"📍 **Manzil:** {active_app.get('address')}\n"
            f"📞 **Bog'lanish:** {active_app.get('contact_phone')}\n"
            f"⏰ **Vaqt:** {active_app.get('start_time', '')} – {active_app.get('end_time', '')}\n\n"
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
            ]
        ]
    )

    await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(StudentConfirmAction.filter(F.action == "finish_job"))
async def process_finish_job(call: CallbackQuery, callback_data: StudentConfirmAction):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    await ApplicationsRepo.update_status(callback_data.app_id, "done")
    
    alert = "Smena yakunlandi!" if lang == "uz" else ("Смена завершена!" if lang == "ru" else "Shift finished!")
    await call.answer(alert, show_alert=True)
    
    if lang == "ru":
        msg_text = "✅ **Сегодняшняя смена успешно сдана!** Ожидается подтверждение работодателя."
    elif lang == "en":
        msg_text = "✅ **Today's shift successfully submitted!** Awaiting employer confirmation."
    else:
        msg_text = "✅ **Bugungi ish muvaffaqiyatli topshirildi!** Ish beruvchi tasdiqlagach, baholash ochiladi."

    await call.message.edit_text(msg_text, parse_mode="Markdown")


@router.callback_query(StudentConfirmAction.filter(F.action == "accept_offer"))
async def process_accept_offer(call: CallbackQuery, callback_data: StudentConfirmAction):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    await ApplicationsRepo.update_status(callback_data.app_id, "accepted")
    
    alert = "Tabriklaymiz! Ish tasdiqlandi." if lang == "uz" else ("Поздравляем! Работа подтверждена." if lang == "ru" else "Congratulations! Confirmed.")
    await call.answer(alert, show_alert=True)
    
    if lang == "ru":
        msg_text = "✅ **Вы приняты на данное место!** В разделе 'Текущая работа' доступны контакты и адрес."
    elif lang == "en":
        msg_text = "✅ **You are accepted!** Check 'Current Job' section for location and contact details."
    else:
        msg_text = "✅ **Siz ushbu o'ringa qabul qilindingiz!** 'Joriy ish' bo'limi orqali manzil va mas'ul bilan bog'lanishingiz mumkin."

    await call.message.edit_text(msg_text, parse_mode="Markdown")
