from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.core.callbacks import EmployerAppAction
from bot.core.i18n import get_i18n, get_button_variants
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo
from bot.db.repositories.jobs_repo import JobsRepo
from bot.db.repositories.applications_repo import ApplicationsRepo

router = Router()


@router.message(F.text.in_(get_button_variants("BTN_EMP_INBOX")))
async def show_employer_inbox(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    emp = await EmployersRepo.get_by_tg_id(msg.from_user.id)
    if not emp:
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    my_jobs = await JobsRepo.get_by_employer(emp["id"])
    if not my_jobs:
        await msg.answer(t.MSG_NO_JOBS_YET)
        return

    has_any = False
    for job in my_jobs:
        apps = await ApplicationsRepo.get_by_job(job["id"])
        pending_apps = [a for a in apps if a.get("status") == "pending"]
        if pending_apps:
            has_any = True
            for a in pending_apps[:5]:
                if lang == "ru":
                    text = (
                        f"📩 **Новый Кандидат:**\n"
                        f"💼 Вакансия: **{job.get('title')}**\n"
                        f"👤 Студент: **{a.get('full_name')}**\n"
                        f"🎓 Специальность/Курс: {a.get('major')} ({a.get('course')}-й курс)\n"
                        f"⭐ Балл GPA: **{a.get('gpa_score')}** | Надёжность: {a.get('trust_score')}/100\n"
                        f"🎯 Показатель соответствия: **{a.get('match_score')}%**\n"
                    )
                    btn_accept = "✅ Принять"
                    btn_backup = "⏳ В резерв"
                    btn_reject = "❌ Отклонить"
                elif lang == "en":
                    text = (
                        f"📩 **New Candidate:**\n"
                        f"💼 Vacancy: **{job.get('title')}**\n"
                        f"👤 Student: **{a.get('full_name')}**\n"
                        f"🎓 Major/Year: {a.get('major')} (Year {a.get('course')})\n"
                        f"⭐ GPA Score: **{a.get('gpa_score')}** | Trust: {a.get('trust_score')}/100\n"
                        f"🎯 Matching Score: **{a.get('match_score')}%**\n"
                    )
                    btn_accept = "✅ Accept"
                    btn_backup = "⏳ Reserve"
                    btn_reject = "❌ Reject"
                else:
                    text = (
                        f"📩 **Yangi Nomzod:**\n"
                        f"💼 Vakansiya: **{job.get('title')}**\n"
                        f"👤 Talaba: **{a.get('full_name')}**\n"
                        f"🎓 Fakultet/Kurs: {a.get('major')} ({a.get('course')}-kurs)\n"
                        f"⭐ GPA bahosi: **{a.get('gpa_score')}** | Ishonch: {a.get('trust_score')}/100\n"
                        f"🎯 Moslik ko'rsatkichi: **{a.get('match_score')}%**\n"
                    )
                    btn_accept = "✅ Qabul qilish"
                    btn_backup = "⏳ Zaxiraga olish"
                    btn_reject = "❌ Rad etish"

                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=btn_accept,
                                callback_data=EmployerAppAction(action="accept", app_id=a["id"]).pack(),
                            ),
                            InlineKeyboardButton(
                                text=btn_backup,
                                callback_data=EmployerAppAction(action="backup", app_id=a["id"]).pack(),
                            ),
                            InlineKeyboardButton(
                                text=btn_reject,
                                callback_data=EmployerAppAction(action="reject", app_id=a["id"]).pack(),
                            ),
                        ]
                    ]
                )
                await msg.answer(text, reply_markup=kb, parse_mode="Markdown")

    if not has_any:
        await msg.answer(t.MSG_NO_NEW_APPS)


@router.message(F.text.in_(get_button_variants("BTN_EMP_MY_JOBS")))
async def show_employer_jobs(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    emp = await EmployersRepo.get_by_tg_id(msg.from_user.id)
    if not emp:
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    my_jobs = await JobsRepo.get_by_employer(emp["id"])
    if not my_jobs:
        await msg.answer(t.MSG_NO_JOBS_YET)
        return

    header = "📋 **Sizning e'lonlaringiz:**\n\n" if lang == "uz" else ("📋 **Ваши объявления:**\n\n" if lang == "ru" else "📋 **Your Job Postings:**\n\n")
    for j in my_jobs:
        status_sym = "🟢 Ochiq" if j.get("status") == "open" else "🔒 Yopiq"
        header += (
            f"• **{j.get('title')}** ({status_sym})\n"
            f"  O'rinlar: {j.get('filled_count')}/{j.get('slots_needed')} | Soha: {j.get('category')}\n\n"
        )
    await msg.answer(header, parse_mode="Markdown")


@router.callback_query(EmployerAppAction.filter(F.action == "accept"))
async def process_accept_candidate(call: CallbackQuery, callback_data: EmployerAppAction, bot: Bot):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    app = await ApplicationsRepo.get_by_id(callback_data.app_id)
    if not app:
        await call.answer("Ariza topilmadi.", show_alert=True)
        return

    await ApplicationsRepo.update_status(app["id"], "accepted")
    await JobsRepo.increment_filled_slot(app["job_id"])

    alert = "Nomzod ishga qabul qilindi!" if lang == "uz" else ("Кандидат принят!" if lang == "ru" else "Candidate accepted!")
    await call.answer(alert, show_alert=True)
    
    reply = (
        f"✅ **{app.get('student_name')} qabul qilindi!**\n"
        f"Talabaga qabul qilinganligi va manzil yuborildi."
    )
    if lang == "ru":
        reply = f"✅ **{app.get('student_name')} принят!**\nСтуденту отправлено уведомление."
    elif lang == "en":
        reply = f"✅ **{app.get('student_name')} accepted!**\nStudent has been notified."

    await call.message.edit_text(reply, parse_mode="Markdown")

    # Talabaga bildirishnoma
    student_tg = app.get("student_tg_id")
    if student_tg:
        s_lang = await UsersRepo.get_user_lang(student_tg)
        if s_lang == "ru":
            notif = (
                f"🎉 **Поздравляем! Вы приняты!**\n\n"
                f"🏢 **Организация:** {app.get('company_name')}\n"
                f"💼 **Должность:** {app.get('job_title')}\n"
                f"📍 **Адрес:** {app.get('employer_address')}\n"
                f"📞 **Телефон куратора:** {app.get('employer_phone')}\n\n"
                f"Подробности в разделе 'Текущая работа'."
            )
        elif s_lang == "en":
            notif = (
                f"🎉 **Congratulations! You have been accepted!**\n\n"
                f"🏢 **Organization:** {app.get('company_name')}\n"
                f"💼 **Position:** {app.get('job_title')}\n"
                f"📍 **Address:** {app.get('employer_address')}\n"
                f"📞 **Contact:** {app.get('employer_phone')}\n\n"
                f"Details available in 'Current Job'."
            )
        else:
            notif = (
                f"🎉 **Tabriklaymiz! Siz qabul qilindingiz!**\n\n"
                f"🏢 **Tashkilot:** {app.get('company_name')}\n"
                f"💼 **Lavozim:** {app.get('job_title')}\n"
                f"📍 **Manzil:** {app.get('employer_address')}\n"
                f"📞 **Mas'ul telefon raqami:** {app.get('employer_phone')}\n\n"
                f"Batafsil ma'lumotni 'Joriy ish' bo'limida ko'rishingiz mumkin."
            )
        try:
            await bot.send_message(chat_id=student_tg, text=notif, parse_mode="Markdown")
        except Exception:
            pass


@router.callback_query(EmployerAppAction.filter(F.action == "backup"))
async def process_backup_candidate(call: CallbackQuery, callback_data: EmployerAppAction, bot: Bot):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    app = await ApplicationsRepo.get_by_id(callback_data.app_id)
    if not app:
        await call.answer("Ariza topilmadi.", show_alert=True)
        return

    from bot.db.connection import db
    await db.execute("UPDATE applications SET is_backup = TRUE, backup_rank = 1 WHERE id = $1", app["id"])

    alert = "Talaba zaxiraga belgilandi!" if lang == "uz" else ("Кандидат сохранён в резерв!" if lang == "ru" else "Student added to backup reserve!")
    await call.answer(alert, show_alert=True)
    
    reply = f"⏳ **{app.get('student_name')} Zaxira nomzod sifatida saqlandi.**"
    await call.message.edit_text(reply)

    # Talabaga xabar
    student_tg = app.get("student_tg_id")
    if student_tg:
        try:
            await bot.send_message(
                chat_id=student_tg,
                text=(
                    f"🛟 **Siz '{app.get('job_title')}' vakansiyasi bo'yicha Zaxiraga olindingiz!**\n"
                    f"Agar bo'sh o'rin ochilsa yoki xodim kelmay qolsa, sizga birinchi navbatda taklif keladi."
                )
            )
        except Exception:
            pass


@router.callback_query(EmployerAppAction.filter(F.action == "reject"))
async def process_reject_candidate(call: CallbackQuery, callback_data: EmployerAppAction):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    await ApplicationsRepo.update_status(callback_data.app_id, "rejected", "Boshqa nomzod tanlandi")
    alert = "Nomzod rad etildi." if lang == "uz" else ("Кандидат отклонён." if lang == "ru" else "Candidate rejected.")
    await call.answer(alert, show_alert=True)
    await call.message.edit_text("❌ " + alert)
