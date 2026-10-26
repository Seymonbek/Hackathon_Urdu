import logging
import asyncio
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import settings
from bot.core.callbacks import StudentJobAction
from bot.core.i18n import uz
from bot.db.repositories.students_repo import StudentsRepo
from bot.services.matching import calculate_match_score

logger = logging.getLogger(__name__)


def is_quiet_hour() -> bool:
    current_hour = datetime.now().hour
    start = settings.QUIET_HOURS_START
    end = settings.QUIET_HOURS_END
    if start > end:
        return current_hour >= start or current_hour < end
    return start <= current_hour < end


async def notify_matching_students_about_job(bot: Bot, job: dict):
    """
    Yangi vakansiya chiqqanda 'Oltin Uchburchak' bo'yicha mos talabalarni topib,
    shaxsiy aqlli bildirishnoma yuboruvchi fon xizmati.
    """
    if is_quiet_hour() and not job.get("is_urgent"):
        logger.info("Tinch soatlar (22:00 - 08:00): Bildirishnomalar ertalabga qoldirildi.")
        return

    students = await StudentsRepo.get_all_active_for_matching()
    notified_count = 0

    for s in students:
        is_eligible, score, reasons = calculate_match_score(s, job)
        if is_eligible and score >= settings.NOTIFICATION_THRESHOLD_SCORE:
            tg_id = s.get("tg_id")
            if not tg_id:
                continue

            # Xabar sarlavhasi
            listing_type = job.get("listing_type")
            if listing_type == "tuition_grant_job" or job.get("tuition_coverage_percent", 0) > 0:
                header = uz.NOTIF_GRANT_MATCH_HEADER.format(score=score)
            elif listing_type == "state_internship":
                header = uz.NOTIF_STATE_INTERNSHIP_HEADER.format(score=score)
            else:
                header = uz.NOTIF_JOB_MATCH_HEADER.format(score=score)

            reasons_text = "\n".join([f"✔ {r}" for r in reasons])

            pay_info = f"💰 To'lov: {job.get('pay_amount', 0):,} so'm ({job.get('pay_timing')})"
            if listing_type == "tuition_grant_job":
                pay_info = f"🎓 **Yillik Kontrakt: {job.get('tuition_coverage_percent', 100)}% to'lab beriladi!**"
            elif listing_type == "state_internship":
                pay_info = "📄 **Rasmiy OTM amaliyot kundaligi + Sertifikat**"

            text = (
                f"{header}"
                f"🏢 **Tashkilot:** {job.get('company_name', 'Mavjud')}\n"
                f"💼 **Lavozim:** {job.get('title')}\n"
                f"📍 **Manzil:** {job.get('address', 'Urganch sh.')}\n"
                f"⏰ **Ish vaqti:** {job.get('start_time', '')} – {job.get('end_time', '')}\n"
                f"{pay_info}\n\n"
                f"💡 **Nega sizga mos:**\n{reasons_text}\n"
            )

            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Ariza topshirish",
                            callback_data=StudentJobAction(action="apply", job_id=job["id"]).pack(),
                        ),
                        InlineKeyboardButton(
                            text="ℹ️ Batafsil",
                            callback_data=StudentJobAction(action="view", job_id=job["id"]).pack(),
                        ),
                    ]
                ]
            )

            try:
                await bot.send_message(chat_id=tg_id, text=text, reply_markup=kb, parse_mode="Markdown")
                notified_count += 1
                await asyncio.sleep(0.05)  # Telegram rate-limit himoyasi
            except Exception as e:
                logger.warning(f"Talabaga ({tg_id}) bildirishnoma yuborishda xato: {e}")

    logger.info(f"Vakansiya #{job.get('id')} bo'yicha {notified_count} ta mos talabaga bildirishnoma yuborildi.")
