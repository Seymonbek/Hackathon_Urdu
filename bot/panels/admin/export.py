import csv
import io
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from bot.core.i18n import get_button_variants
from bot.db.repositories.users_repo import UsersRepo
from bot.db.connection import db

router = Router()


@router.message(F.text.in_(get_button_variants("BTN_ADM_EXPORT")))
async def export_data_to_csv(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    wait_txt = "⏳ Baza ma'lumotlari tahlil qilinmoqda va CSV hisobot shakllantirilmoqda..." if lang == "uz" else ("⏳ Формируется CSV отчёт из базы данных..." if lang == "ru" else "⏳ Generating CSV export report from database...")
    await msg.answer(wait_txt)

    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Talabalar hisoboti
    writer.writerow(["--- TALABALAR BANDLIGI VA AMALIYOTI STATISTIKASI ---"])
    writer.writerow(["ID", "Ism", "Fakultet", "Mutaxassislik", "Kurs", "GPA", "Kontrakt/Grant", "Kontrakt Summasi", "Ishonch Balli", "Manzil"])

    students = await db.fetch("SELECT * FROM students ORDER BY id ASC")
    for s in students:
        is_cnt = "Kontrakt" if s.get("is_contract") else "Grant"
        writer.writerow([
            s.get("id"), s.get("full_name"), s.get("faculty"), s.get("major"),
            s.get("course"), s.get("gpa_score"), is_cnt, s.get("yearly_tuition_amount"),
            s.get("trust_score"), s.get("location_name")
        ])

    writer.writerow([])
    # 2. Tashkilotlar va Davlat organlari
    writer.writerow(["--- TASHKILOTLAR VA DAVLAT ORGANLARI ---"])
    writer.writerow(["ID", "Tashkilot Nomi", "Tashkilot Turi", "Soha", "Manzil", "Telefon", "Mas'ul", "Tasdiqlangan", "Reyting"])
    employers = await db.fetch("SELECT * FROM employers ORDER BY id ASC")
    for e in employers:
        writer.writerow([
            e.get("id"), e.get("company_name"), e.get("org_type"), e.get("category"),
            e.get("address"), e.get("contact_phone"), e.get("contact_person"),
            "Ha" if e.get("is_verified") else "Yo'q", e.get("rating")
        ])

    writer.writerow([])
    # 3. Vakansiyalar va Amaliyot Kvotalari
    writer.writerow(["--- VAKANSIYALAR VA AMALIYOT KVOTALARI ---"])
    writer.writerow(["ID", "Nomi", "Turi", "Soha", "Format", "O'rinlar", "To'ldirilgan", "To'lov", "Kontrakt Qoplash %", "Holati"])
    jobs = await db.fetch("SELECT * FROM jobs ORDER BY id ASC")
    for j in jobs:
        writer.writerow([
            j.get("id"), j.get("title"), j.get("listing_type"), j.get("category"),
            j.get("work_format"), j.get("slots_needed"), j.get("filled_count"),
            j.get("pay_amount"), f"{j.get('tuition_coverage_percent')}%", j.get("status")
        ])

    csv_data = output.getvalue().encode("utf-8-sig")
    document = BufferedInputFile(csv_data, filename="imkon_hisobot_hakamlarga.csv")

    caption = (
        "📤 **Imkon — To'liq Baza Eksporti (CSV)**\n\n"
        "Ushbu faylda barcha talabalar, davlat amaliyotlari, korxonalar va bandlik natijalari to'liq jamlangan. "
        "Excel dasturida to'g'ridan-to'g'ri ochiladi."
    )
    if lang == "ru":
        caption = (
            "📤 **Imkon — Полный экспорт базы (CSV)**\n\n"
            "Файл содержит полные данные по студентам, гос. практике, организациям и результатам занятости."
        )
    elif lang == "en":
        caption = (
            "📤 **Imkon — Complete Database Export (CSV)**\n\n"
            "Contains comprehensive data on students, state internships, organizations, and employment metrics."
        )

    await msg.answer_document(
        document=document,
        caption=caption
    )
