from aiogram import Router, F
from aiogram.types import Message
from bot.core.i18n import get_button_variants, get_i18n
from bot.db.repositories.users_repo import UsersRepo
from bot.db.connection import db

router = Router()


@router.message(F.text.in_(get_button_variants("BTN_ADM_DASHBOARD")))
async def show_admin_dashboard(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    total_students = await db.fetchval("SELECT COUNT(*) FROM students") or 0
    total_employers = await db.fetchval("SELECT COUNT(*) FROM employers") or 0
    verified_employers = await db.fetchval("SELECT COUNT(*) FROM employers WHERE is_verified = TRUE") or 0
    
    total_jobs = await db.fetchval("SELECT COUNT(*) FROM jobs") or 0
    open_jobs = await db.fetchval("SELECT COUNT(*) FROM jobs WHERE status = 'open'") or 0
    internships_count = await db.fetchval("SELECT COUNT(*) FROM jobs WHERE listing_type = 'state_internship'") or 0
    grants_count = await db.fetchval("SELECT COUNT(*) FROM jobs WHERE listing_type = 'tuition_grant_job'") or 0
    
    total_apps = await db.fetchval("SELECT COUNT(*) FROM applications") or 0
    accepted_apps = await db.fetchval("SELECT COUNT(*) FROM applications WHERE status = 'accepted'") or 0
    done_apps = await db.fetchval("SELECT COUNT(*) FROM applications WHERE status = 'done'") or 0

    if lang == "ru":
        text = (
            f"📊 **KASBDOSH — Дашборд управления (В реальном времени)**\n\n"
            f"👥 **Аудитория:**\n"
            f"• Зарегистрировано студентов: **{total_students}**\n"
            f"• Организаций и компаний: **{total_employers}** (Верифицировано: {verified_employers})\n\n"
            f"📋 **Объявления и Квоты:**\n"
            f"• Всего объявлений: **{total_jobs}** (Открыто: {open_jobs})\n"
            f"• 🏛 Гос. практика в госорганах: **{internships_count}**\n"
            f"• 🎓 Гранты с оплатой контракта: **{grants_count}**\n\n"
            f"📈 **Воронка результативности:**\n"
            f"• Подано заявок: **{total_apps}**\n"
            f"• Принято на работу/практику: **{accepted_apps}**\n"
            f"• Успешно завершено: **{done_apps}**\n"
        )
    elif lang == "en":
        text = (
            f"📊 **KASBDOSH — Live Executive Dashboard**\n\n"
            f"👥 **User Base:**\n"
            f"• Registered Students: **{total_students}**\n"
            f"• Registered Organizations: **{total_employers}** (Verified: {verified_employers})\n\n"
            f"📋 **Listings & Quotas:**\n"
            f"• Total Listings: **{total_jobs}** (Active: {open_jobs})\n"
            f"• 🏛 Official State Internships: **{internships_count}**\n"
            f"• 🎓 Tuition Sponsorship Grants: **{grants_count}**\n\n"
            f"📈 **Employment Pipeline:**\n"
            f"• Total Applications: **{total_apps}**\n"
            f"• Candidates Accepted: **{accepted_apps}**\n"
            f"• Completed Engagements: **{done_apps}**\n"
        )
    else:
        text = (
            f"📊 **KASBDOSH — Boshqaruv Dashboardi (Real-Vaqt)**\n\n"
            f"👥 **Auditoriya:**\n"
            f"• Ro'yxatdan o'tgan talabalar: **{total_students} ta**\n"
            f"• Tashkilot va korxonalar: **{total_employers} ta** (Tasdiqlangan: {verified_employers})\n\n"
            f"📋 **E'lonlar va Kvotalar:**\n"
            f"• Jami e'lonlar: **{total_jobs} ta** (Faol ochiq: {open_jobs})\n"
            f"• 🏛 Davlat amaliyotlari: **{internships_count} ta**\n"
            f"• 🎓 Kontrakt to'lab berish grantlari: **{grants_count} ta**\n\n"
            f"📈 **Bandlik va Natijadorlik Voronkasi:**\n"
            f"• Yuborilgan arizalar: **{total_apps} ta**\n"
            f"• Qabul qilinganlar: **{accepted_apps} ta**\n"
            f"• Muvaffaqiyatli yakunlanganlar: **{done_apps} ta**\n"
        )

    await msg.answer(text, parse_mode="Markdown")
