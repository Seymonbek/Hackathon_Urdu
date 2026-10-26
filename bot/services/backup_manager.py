import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.core.callbacks import StudentConfirmAction
from bot.core.i18n import uz
from bot.db.repositories.applications_repo import ApplicationsRepo
from bot.db.repositories.jobs_repo import JobsRepo

logger = logging.getLogger(__name__)


class BackupManager:
    @staticmethod
    async def handle_candidate_dropout(bot: Bot, job_id: int, dropped_student_name: str):
        """
        Asosiy talaba ishga kelmaganda (no-show) yoki bekor qilganda,
        avtomatik zaxiradagi nomzodga taklif yuboradi.
        """
        job = await JobsRepo.get_by_id(job_id)
        if not job:
            return

        backup = await ApplicationsRepo.get_next_backup_candidate(job_id)
        if not backup:
            logger.info(f"Vakansiya #{job_id} uchun zaxira nomzod topilmadi.")
            return

        student_tg_id = backup.get("student_tg_id")
        if not student_tg_id:
            return

        text = uz.NOTIF_BACKUP_INVITE.format(job_title=job["title"])
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Qabul qilaman",
                        callback_data=StudentConfirmAction(action="accept_offer", app_id=backup["id"]).pack(),
                    ),
                    InlineKeyboardButton(
                        text="❌ Rad etaman",
                        callback_data=StudentConfirmAction(action="cancel_job", app_id=backup["id"]).pack(),
                    ),
                ]
            ]
        )

        try:
            await bot.send_message(chat_id=student_tg_id, text=text, reply_markup=kb, parse_mode="Markdown")
            logger.info(f"Zaxiradagi talabaga ({student_tg_id}) taklif yuborildi.")
        except Exception as e:
            logger.error(f"Zaxira xabarini yuborishda xato: {e}")
