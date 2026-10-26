from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.core.callbacks import EmployerAppAction
from bot.core.i18n import get_i18n, get_button_variants
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo
from bot.db.repositories.jobs_repo import JobsRepo
from bot.db.repositories.applications_repo import ApplicationsRepo
from bot.services.backup_manager import BackupManager

router = Router()


@router.message(F.text.in_(get_button_variants("BTN_EMP_ACTIVE")))
@router.message(F.text.in_(get_button_variants("BTN_EMP_INTERNSHIP_EVAL")))
async def show_active_workers(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    t = get_i18n(lang)

    emp = await EmployersRepo.get_by_tg_id(msg.from_user.id)
    if not emp:
        await msg.answer(t.MSG_PLEASE_REGISTER)
        return

    my_jobs = await JobsRepo.get_by_employer(emp["id"])
    has_active = False

    for job in my_jobs:
        apps = await ApplicationsRepo.get_by_job(job["id"])
        accepted_apps = [a for a in apps if a.get("status") in ["accepted", "done"]]
        if accepted_apps:
            has_active = True
            for a in accepted_apps:
                status_note = "✅ Xodim smenani tugatganini bildirdi" if a.get("status") == "done" else "🕒 Ish/Amaliyot jarayonida"
                if lang == "ru":
                    status_note = "✅ Работник сообщил о сдаче смены" if a.get("status") == "done" else "🕒 В процессе работы/практики"
                    title = "📅 **Сотрудники / Практиканты на сегодня:**"
                    btn_confirm = "✅ Подтвердить работу"
                    btn_noshow = "⚠️ Не явился (No-show)"
                elif lang == "en":
                    status_note = "✅ Worker submitted shift completion" if a.get("status") == "done" else "🕒 In progress"
                    title = "📅 **Today's Workers / Interns:**"
                    btn_confirm = "✅ Confirm work done"
                    btn_noshow = "⚠️ No-show (penalty)"
                else:
                    title = "📅 **Bugungi xodim / amaliyotchi:**"
                    btn_confirm = "✅ Ishni tasdiqlash"
                    btn_noshow = "⚠️ Kelmadi (No-show)"

                text = (
                    f"{title}\n\n"
                    f"💼 Vazifa: **{job.get('title')}**\n"
                    f"👤 Talaba: **{a.get('full_name')}** ({a.get('major')})\n"
                    f"Holati: {status_note}\n"
                )

                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=btn_confirm,
                                callback_data=EmployerAppAction(action="finish", app_id=a["id"]).pack(),
                            ),
                            InlineKeyboardButton(
                                text=btn_noshow,
                                callback_data=EmployerAppAction(action="no_show", app_id=a["id"]).pack(),
                            ),
                        ]
                    ]
                )
                await msg.answer(text, reply_markup=kb, parse_mode="Markdown")

    if not has_active:
        await msg.answer(t.MSG_NO_ACTIVE_WORKERS)


@router.callback_query(EmployerAppAction.filter(F.action == "no_show"))
async def process_no_show(call: CallbackQuery, callback_data: EmployerAppAction, bot: Bot):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    app = await ApplicationsRepo.get_by_id(callback_data.app_id)
    if not app:
        await call.answer("Ariza topilmadi.", show_alert=True)
        return

    from bot.db.connection import db
    await db.execute("UPDATE students SET trust_score = GREATEST(trust_score - 10, 0) WHERE id = $1", app["student_id"])
    await ApplicationsRepo.update_status(app["id"], "no_show", "Talaba ishga kelmadi")

    alert = "Kelmadi deb belgilandi! Zaxiradagi talabaga avtomatik taklif ketmoqda..." if lang == "uz" else ("Зафиксирована неявка! Приглашение отправлено резерву." if lang == "ru" else "No-show recorded! Backup invite sent.")
    await call.answer(alert, show_alert=True)
    
    reply = (
        f"⚠️ **{app.get('student_name')} kelmadi deb qayd etildi.**\n"
        f"Ishonch ko'rsatkichi -10 ballga kamaytirildi.\n\n"
        f"⚡ **Zaxira zanjiri ishga tushdi:** Eng mos zaxira talabaga taklif yuborildi!"
    )
    await call.message.edit_text(reply)

    # Zaxira zanjirini ishga tushirish
    await BackupManager.handle_candidate_dropout(
        bot=bot,
        job_id=app["job_id"],
        dropped_student_name=app.get("student_name", "Talaba")
    )


@router.callback_query(EmployerAppAction.filter(F.action == "finish"))
async def process_confirm_finish(call: CallbackQuery, callback_data: EmployerAppAction):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    await ApplicationsRepo.update_status(callback_data.app_id, "done")
    alert = "Ish yakunlandi deb tasdiqlandi!" if lang == "uz" else ("Работа успешно подтверждена!" if lang == "ru" else "Work confirmed!")
    await call.answer(alert, show_alert=True)
    await call.message.edit_text("✅ **" + alert + "**")
