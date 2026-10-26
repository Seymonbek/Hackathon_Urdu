import logging
import html
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import settings
from bot.core.callbacks import AdminVerifyAction

logger = logging.getLogger(__name__)


async def notify_admin_new_student(bot: Bot, student: dict):
    """Yangi talaba ro'yxatdan to'liq o'tganida adminga chiroyli va to'liq ma'lumotli bildirishnoma yuboradi."""
    tg_id = student.get("tg_id") or student.get("user_id")
    full_name = html.escape(str(student.get("full_name", "Noma'lum")))
    phone = html.escape(str(student.get("phone_number", "Ko'rsatilmagan")))
    region = html.escape(str(student.get("region", "Ko'rsatilmagan")))
    university = html.escape(str(student.get("university", student.get("faculty", "OTM"))))
    major = html.escape(str(student.get("major", "Noma'lum")))
    course_label = html.escape(str(student.get("course_label", f"{student.get('course', 1)}-kurs")))
    
    loc_name = html.escape(str(student.get("location_name", "TTJ / Kvartira")))
    lat = student.get("location_lat")
    lon = student.get("location_lon")
    loc_link = f"<a href=\"https://maps.google.com/?q={lat},{lon}\">Xaritada ko'rish 🗺</a>" if lat and lon else ""
    radius = student.get("max_distance_km", 5.0)

    user_link = f"<a href=\"tg://user?id={tg_id}\">Profil ochish</a>" if tg_id else "Mavjud emas"

    text = (
        f"🎓 <b>YANGI TALABA TO'LIQ RO'YXATDAN O'TDI!</b>\n\n"
        f"👤 <b>Ism familiya:</b> {full_name}\n"
        f"📱 <b>Telefon:</b> <code>{phone}</code>\n"
        f"🔗 <b>Telegram:</b> {user_link} (ID: <code>{tg_id}</code>)\n"
        f"🏙 <b>Istiqomat hududi:</b> {region}\n"
        f"🏛 <b>OTM (Universitet):</b> {university}\n"
        f"📚 <b>Bosqich / Kurs:</b> <b>{course_label}</b>\n"
        f"🎓 <b>Mutaxassisligi:</b> {major}\n"
        f"📍 <b>Yashash joyi (TTJ/Kvartira):</b> {loc_name} {loc_link}\n"
        f"🎯 <b>Qidiruv radiusi:</b> {radius} km\n\n"
        f"⚡ <i>Tizim talabaning yashash joyi atrofidagi eng yaqin ishlar va amaliyotlarni avtomatik qidirishni boshladi.</i>"
    )

    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            logger.info(f"Adminga ({admin_id}) yangi talaba ({full_name}) haqida xabar muvaffaqiyatli yetkazildi.")
        except Exception as e:
            logger.warning(f"Adminga ({admin_id}) xabar yuborishda xatolik: {e}")


async def notify_admin_new_employer(bot: Bot, emp: dict, emp_id: int):
    """Yangi korxona yoki davlat organi ro'yxatdan o'tganida adminga tasdiqlash tugmalari bilan zudlik bilan bildirishnoma yuboradi."""
    tg_id = emp.get("tg_id") or emp.get("user_id")
    company_name = html.escape(str(emp.get("company_name", "Noma'lum")))
    org_type = emp.get("org_type", "")
    org_label = "🏛 Davlat Organi / Sud / Shifoxona" if org_type == "state_agency" else "🏢 Tijoriy Korxona / IT / Biznes"
    
    category = html.escape(str(emp.get("category", "Umumiy")))
    address = html.escape(str(emp.get("address", "Urganch")))
    phone = html.escape(str(emp.get("contact_phone", "Ko'rsatilmagan")))
    contact_person = html.escape(str(emp.get("contact_person", "Noma'lum")))
    user_link = f"<a href=\"tg://user?id={tg_id}\">Telegram orqali bog'lanish</a>" if tg_id else "Mavjud emas"

    text = (
        f"🏢 <b>YANGI TASHKILOT RO'YXATDAN O'TDI!</b>\n\n"
        f"🏛 <b>Nomi:</b> <b>{company_name}</b>\n"
        f"📌 <b>Turi:</b> {org_label}\n"
        f"📂 <b>Soha:</b> {category}\n"
        f"📍 <b>Manzil:</b> {address}\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"👤 <b>Mas'ul shaxs:</b> {contact_person} ({user_link})\n\n"
        f"Tashkilotga rasmiy tasdiq belgisini (✔️) berishni tasdiqlaysizmi?"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash (✔️)",
                    callback_data=AdminVerifyAction(target="employer", action="approve", id=emp_id).pack(),
                ),
                InlineKeyboardButton(
                    text="🚫 Rad etish",
                    callback_data=AdminVerifyAction(target="employer", action="reject", id=emp_id).pack(),
                ),
            ]
        ]
    )

    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=kb,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            logger.info(f"Adminga ({admin_id}) yangi tashkilot ({company_name}) haqida xabar muvaffaqiyatli yetkazildi.")
        except Exception as e:
            logger.warning(f"Adminga ({admin_id}) tashkilot xabari yuborishda xatolik: {e}")
