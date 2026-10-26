import logging
from bot.db.connection import db
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo
from bot.db.repositories.jobs_repo import JobsRepo

logger = logging.getLogger(__name__)


async def seed_initial_data(force: bool = False):
    """
    Foydalanuvchi taqdim etgan va rasmdagi 100% REAL Urganch/Xorazm e'lonlarini kiritadi.
    Eski soxta e'lonlar butunlay o'chiriladi.
    """
    if force:
        logger.info("Eski soxta e'lonlar tozalanmoqda...")
        await db.execute("DELETE FROM applications")
        await db.execute("DELETE FROM jobs")
        await db.execute("DELETE FROM employers")
        await db.execute("DELETE FROM users WHERE role = 'employer'")

    # Demo Tyutor mavjudligini tekshirish va yaratish
    try:
        tutors_count = await db.fetchval("SELECT COUNT(*) FROM tutors") or 0
        if tutors_count == 0:
            u_tutor = await UsersRepo.create_user(tg_id=990099, role="tutor", lang="uz")
            await db.execute(
                """
                INSERT INTO tutors (user_id, full_name, university, faculty, group_name, phone_number)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                u_tutor,
                "Alisher Boboyev",
                "Urganch Davlat Universiteti (UrDU)",
                "Raqamli texnologiyalar va sun'iy intellekt",
                "Dasturiy injiniring 211-guruh",
                "+998901234567"
            )
            await db.execute("UPDATE students SET tutor_id = (SELECT id FROM tutors LIMIT 1) WHERE tutor_id IS NULL")
            logger.info("✅ Demo Tyutor va talabalar biriktiruvi muvaffaqiyatli yaratildi.")
    except Exception as e:
        logger.warning(f"Tyutor seed qilishda ogohlantirish: {e}")

    count = await db.fetchval("SELECT COUNT(*) FROM jobs")
    if not force and count and count > 0:
        return

    logger.info("100% REAL Urganch/Xorazm e'lonlari kiritilmoqda...")

    from datetime import date
    today_str = str(date.today())

    # ==========================================
    # 1. MEHMON UYI OILAVIY HOSTELI
    # ==========================================
    u1 = await UsersRepo.create_user(tg_id=990001, role="employer")
    e1 = await EmployersRepo.create_or_update(
        user_id=u1,
        company_name="Mehmon uyi oilaviy hosteli",
        org_type="commercial",
        category="hospitality",
        address="Urganch sh., Turon bank ro'parasi (Mo'ljal: Baby Saltanat ofisi)",
        district="Urganch",
        contact_phone="+998701236369, +998770906369",
        contact_person="Mehmon uyi ma'muriyati",
        lat=41.5510,
        lon=60.6320,
    )
    await EmployersRepo.verify_employer(e1, True)

    await JobsRepo.create_job(
        employer_id=e1,
        title="Hostel Boshqaruvchisi (Faqat qizlar, 20-35 yosh)",
        listing_type="paid_job",
        category="general",
        work_format="offline_shift",
        slots_needed=2,
        target_majors=["Umumiy", "Barcha yo'nalishlar", "Menejment", "Turizm"],
        min_course_required=1,
        duties=["Mehmonlarni qabul qilish va ro'yxatga olish", "Xonalar holatini nazorat qilish", "Mas'uliyatli va chaqqon bo'lish"],
        job_date=today_str,
        start_time="08:00",
        end_time="18:00",
        pay_amount=100000,
        pay_unit="per_shift",
        pay_timing="daily",
        pay_method="cash",
        perks=["Kunlik 100 000 so'mdan boshlanadi", "Suhbat asosida ishga olinadi", "Qulay sharoitlar"],
        lat=41.5510,
        lon=60.6320,
        image_path="bot/assets/imkon_logo.png",
    )

    await JobsRepo.create_job(
        employer_id=e1,
        title="Hostel Tozalovchi xodimi (Faqat ayol-qizlar)",
        listing_type="paid_job",
        category="general",
        work_format="offline_shift",
        slots_needed=2,
        target_majors=["Umumiy", "Barcha yo'nalishlar"],
        min_course_required=1,
        duties=["Xonalarni ozoda saqlash", "Choyshablarni almashtirish", "Chaqqon va mas'uliyatli ishlash"],
        job_date=today_str,
        start_time="08:00",
        end_time="18:00",
        pay_amount=100000,
        pay_unit="per_shift",
        pay_timing="daily",
        pay_method="cash",
        perks=["Kunlik 100 000 so'm", "Qulay kunlik to'lov", "Do'stona jamoa"],
        lat=41.5510,
        lon=60.6320,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 2. "BUNYOD" GAMBURG 1-FILIALI
    # ==========================================
    u2 = await UsersRepo.create_user(tg_id=990002, role="employer")
    e2 = await EmployersRepo.create_or_update(
        user_id=u2,
        company_name='"Bunyod" gamburg 1-filiali',
        org_type="commercial",
        category="catering",
        address="Urganch shahri, Mo'ljal: Nadmes, 5-avtobus ko'prigi",
        district="Urganch",
        contact_phone="+998957714881",
        contact_person="Bunyod Gamburg HR",
        lat=41.5495,
        lon=60.6340,
    )
    await EmployersRepo.verify_employer(e2, True)

    await JobsRepo.create_job(
        employer_id=e2,
        title="Ofitsiant (Faqat qizlar, Kunduzgi va Kechki smena)",
        listing_type="paid_job",
        category="catering",
        work_format="offline_shift",
        slots_needed=3,
        target_majors=["Umumiy", "Barcha yo'nalishlar"],
        min_course_required=1,
        duties=["Mijozlarga xushmuomala xizmat ko'rsatish", "Buyurtmalarni tez va ozoda yetkazish", "Tashqi ko'rinish ozodaligiga rioya qilish"],
        job_date=today_str,
        start_time="14:00",
        end_time="21:00",
        pay_amount=110000,
        pay_unit="per_shift",
        pay_timing="daily",
        pay_method="cash",
        perks=["Kunlik 110 000 so'mdan boshlanadi", "Yaxshi ishlasa oylik oshib boradi", "Tushlik ishxona hisobidan"],
        lat=41.5495,
        lon=60.6340,
        image_path="bot/assets/imkon_logo.png",
    )

    await JobsRepo.create_job(
        employer_id=e2,
        title="Tozalik xodimi (Kechki smena)",
        listing_type="paid_job",
        category="catering",
        work_format="offline_shift",
        slots_needed=2,
        target_majors=["Umumiy", "Barcha yo'nalishlar"],
        min_course_required=1,
        duties=["Zal va oshxona tozaligini ta'minlash", "Idish-tovoqlarni tozalash", "Mas'uliyatli va chaqqon ishlash"],
        job_date=today_str,
        start_time="17:00",
        end_time="22:00",
        pay_amount=110000,
        pay_unit="per_shift",
        pay_timing="daily",
        pay_method="cash",
        perks=["Kunlik 110 000 so'mdan boshlanadi", "Yaxshi ishlasa oylik oshadi", "Kechki qulay smena"],
        lat=41.5495,
        lon=60.6340,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 3. "BABY SALTANAT" MEDIA VA TUG'RUQXONA LOYIHASI
    # ==========================================
    u3 = await UsersRepo.create_user(tg_id=990003, role="employer")
    e3 = await EmployersRepo.create_or_update(
        user_id=u3,
        company_name='"Baby Saltanat" jamoasi',
        org_type="commercial",
        category="media",
        address="Urganch sh., Turon bank ro'parasi (Baby Saltanat ofisi)",
        district="Urganch",
        contact_phone="+998701236369, +998770906369",
        contact_person="Baby Saltanat rahbariyati",
        lat=41.5510,
        lon=60.6320,
    )
    await EmployersRepo.verify_employer(e3, True)

    await JobsRepo.create_job(
        employer_id=e3,
        title="Foto-video operator (Tug'ruqxonalardagi faoliyat, Faqat qizlar)",
        listing_type="paid_job",
        category="media",
        work_format="offline_shift",
        slots_needed=2,
        target_majors=["Media", "Jurnalistika", "Dizayn", "Umumiy", "Barcha yo'nalishlar"],
        min_course_required=1,
        duties=["Chaqaloqlar va onalarni professional foto-video tasvirga olish", "Kreativ kadrlar tayyorlash", "20-35 yosh qizlar"],
        job_date=today_str,
        start_time="08:00",
        end_time="18:00",
        pay_amount=100000,
        pay_unit="per_shift",
        pay_timing="daily",
        pay_method="cash",
        perks=["Kunlik 100 000 so'mdan boshlanadi", "Zamonaviy kamera va jihozlar beriladi", "Professional tajriba"],
        lat=41.5510,
        lon=60.6320,
        image_path="bot/assets/imkon_logo.png",
    )

    await JobsRepo.create_job(
        employer_id=e3,
        title="Reklama menejeri (Faqat qizlar, 20-35 yosh)",
        listing_type="paid_job",
        category="media",
        work_format="offline_shift",
        slots_needed=2,
        target_majors=["Marketing", "SMM", "Iqtisodiyot", "Media", "Umumiy"],
        min_course_required=1,
        duties=["Mijozlar bilan muzokaralar olib borish", "Xizmatlar paketini taklif qilish va reklama qilish", "Mas'uliyatli va chaqqon muloqot"],
        job_date=today_str,
        start_time="08:00",
        end_time="18:00",
        pay_amount=100000,
        pay_unit="per_shift",
        pay_timing="daily",
        pay_method="cash",
        perks=["Kunlik 100 000 so'mdan boshlanadi", "Bonus va sotuv foizlari", "Suhbat asosida qabul"],
        lat=41.5510,
        lon=60.6320,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 4. "MITTIVOY" URGANCH MEDIAPARK FILIALI
    # ==========================================
    u4 = await UsersRepo.create_user(tg_id=990004, role="employer")
    e4 = await EmployersRepo.create_or_update(
        user_id=u4,
        company_name='"MITTIVOY" Urganch Mediapark Filiali',
        org_type="commercial",
        category="retail",
        address="Urganch shahri, Al-Xorazmiy ko'chasi (Media Park bozori yonida)",
        district="Urganch",
        contact_phone="@Diyora_mittivoyHR / @Mittivoy_jbot",
        contact_person="Diyora (HR Menejer)",
        lat=41.5540,
        lon=60.6270,
    )
    await EmployersRepo.verify_employer(e4, True)

    await JobsRepo.create_job(
        employer_id=e4,
        title="Sotuvchi-konsultant (3-smena: 14:00 - 23:00, 6/1)",
        listing_type="paid_job",
        category="retail",
        work_format="offline_shift",
        slots_needed=3,
        target_majors=["Umumiy", "Barcha yo'nalishlar", "Savdo", "Iqtisodiyot"],
        min_course_required=1,
        duties=["Mijozlarga tovarlar bo'yicha maslahat berish", "Jamoada do'stona ishlash", "Muloqot qobiliyati va jiddiy yondashuv"],
        job_date=today_str,
        start_time="14:00",
        end_time="23:00",
        pay_amount=3500000,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="card",
        perks=["Oylik: 3 000 000 – 4 500 000 so'm", "Tushlik ishxona hisobidan", "Zamonaviy Mediapark filiali", "Rasmiy staj"],
        lat=41.5540,
        lon=60.6270,
        image_path="bot/assets/imkon_logo.png",
    )

    await JobsRepo.create_job(
        employer_id=e4,
        title="Xavfsizlik xodimi (2-smena: 12:00 - 21:00, 6/1)",
        listing_type="paid_job",
        category="retail",
        work_format="offline_shift",
        slots_needed=2,
        target_majors=["Umumiy", "Barcha yo'nalishlar"],
        min_course_required=1,
        duties=["Do'konda tartib va xavfsizlikni nazorat qilish", "Kirish-chiqish nazorati", "Hushyorlik va faollik"],
        job_date=today_str,
        start_time="12:00",
        end_time="21:00",
        pay_amount=3500000,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="card",
        perks=["Oylik: 3 200 000 – 4 200 000 so'm", "Tushlik ishxona hisobidan", "Qulay 2-smena"],
        lat=41.5540,
        lon=60.6270,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 5. "THE UNITED TEAM" XALQARO LOGISTIKA KOMPANIYASI
    # ==========================================
    u5 = await UsersRepo.create_user(tg_id=990005, role="employer")
    e5 = await EmployersRepo.create_or_update(
        user_id=u5,
        company_name='"The United Team" Logistika Kompaniyasi',
        org_type="commercial",
        category="logistics",
        address="Urganch shahri, IT Park",
        district="Urganch",
        contact_phone="+998919188308 (@HRXodimAgency)",
        contact_person="United Team HR",
        lat=41.5505,
        lon=60.6295,
    )
    await EmployersRepo.verify_employer(e5, True)

    await JobsRepo.create_job(
        employer_id=e5,
        title="Logistika Dispetcheri (O'qitish + Ish, 25 ta bo'sh o'rin)",
        listing_type="paid_job",
        category="logistics",
        work_format="offline_shift",
        slots_needed=25,
        target_majors=["Xorijiy tillar", "Ingliz tili", "Filologiya", "Logistika", "IT", "Barcha yo'nalishlar"],
        min_course_required=1,
        duties=["AQSH/Yevropa yuk tashuvlari logistikasi", "Haydovchilar bilan ingliz tilida muloqot", "Yuk hujjatlarini monitoring qilish"],
        job_date=today_str,
        start_time="17:00",
        end_time="03:00",
        pay_amount=3800000,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="card",
        perks=[
            "20 kunlik BEPUL logistika o'qitish",
            "Kafolatlangan ish va birinchi oylik $300+ (AQSH dollari)",
            "Coffeebreak zona va shinam IT Park ofisi",
            "Kuchli bonus tizimi",
            "Ingliz tili (IELTS 6.0+) talab etiladi"
        ],
        lat=41.5505,
        lon=60.6295,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 6. HDP O'QUV MARKAZI VA "OMON SCHOOL"
    # ==========================================
    u6 = await UsersRepo.create_user(tg_id=990006, role="employer")
    e6 = await EmployersRepo.create_or_update(
        user_id=u6,
        company_name='HDP O\'quv Markazi va "Omon School"',
        org_type="commercial",
        category="education",
        address="Urganch shahar, UrDU (Universitet) ro'parasi",
        district="Urganch",
        contact_phone="+998880398959 (@hdp_omonschool_hr)",
        contact_person="Omon School HR",
        lat=41.5420,
        lon=60.6310,
    )
    await EmployersRepo.verify_employer(e6, True)

    await JobsRepo.create_job(
        employer_id=e6,
        title="Call Operator (Yigit va qizlar, 14:00 - 19:30 smena)",
        listing_type="paid_job",
        category="education",
        work_format="offline_shift",
        slots_needed=4,
        target_majors=["Umumiy", "Barcha yo'nalishlar", "Filologiya", "Pedagogika"],
        min_course_required=1,
        duties=["Mijozlar qo'ng'iroqlariga javob berish", "Kurslar haqida aniq ma'lumot berish", "Nutqi ravon va chaqqon ishlash"],
        job_date=today_str,
        start_time="14:00",
        end_time="19:30",
        pay_amount=4000000,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="card",
        perks=[
            "Maosh: 4 000 000 so'm va undan yuqori",
            "UrDU talabalari uchun universitet ro'parasidagi qulay joylashuv",
            "Doimiy va barqaror ish",
            "O'z ustida ishlash va rivojlanish imkoni",
            "Ariza: https://forms.gle/EbWuKEQJeCqU5GA17"
        ],
        lat=41.5420,
        lon=60.6310,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 7. HDP O'QUV MARKAZI (XIVA VA BOG'OT FILIALLARI)
    # ==========================================
    u7 = await UsersRepo.create_user(tg_id=990007, role="employer")
    e7 = await EmployersRepo.create_or_update(
        user_id=u7,
        company_name="HDP O'quv Markazi (Xiva va Bog'ot)",
        org_type="commercial",
        category="education",
        address="Xiva shahri va Bog'ot tumani filiallari",
        district="Xiva",
        contact_phone="+998995649941 (@HR_Hulkar)",
        contact_person="Hulkar (HR Menejer)",
        lat=41.3780,
        lon=60.3630,
    )
    await EmployersRepo.verify_employer(e7, True)

    await JobsRepo.create_job(
        employer_id=e7,
        title="Ingliz tili asosiy va yordamchi o'qituvchisi (IELTS 7 / C1)",
        listing_type="paid_job",
        category="education",
        work_format="offline_shift",
        slots_needed=3,
        target_majors=["Filologiya", "Ingliz tili", "Xorijiy tillar", "Pedagogika"],
        min_course_required=2,
        duties=["O'quvchilarga interaktiv dars o'tish", "O'zlashtirish ko'rsatkichlarini kuzatish", "IELTS / General English tayyorgarligi"],
        job_date=today_str,
        start_time="14:30",
        end_time="18:30",
        pay_amount=3500000,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="card",
        perks=[
            "Barqaror va o'z vaqtida to'lanadigan maosh (Suhbatda kelishiladi)",
            "Kuchli professional jamoa",
            "Ariza: https://forms.gle/HvkqpQ2XDjBiLS436",
            "Dars jadvali asosida moslashuvchan rejim"
        ],
        lat=41.3780,
        lon=60.3630,
        image_path="bot/assets/imkon_logo.png",
    )

    await JobsRepo.create_job(
        employer_id=e7,
        title="Matematika fani asosiy o'qituvchisi (Sertifikat B+ yoki A+)",
        listing_type="paid_job",
        category="education",
        work_format="offline_shift",
        slots_needed=2,
        target_majors=["Matematika", "Fizika", "Pedagogika", "Axborot texnologiyalari"],
        min_course_required=2,
        duties=["Dars jarayonini qiziqarli tashkil etish", "O'quvchilar bilan individual ishlash", "Milliy va xalqaro sertifikatlarga tayyorlash"],
        job_date=today_str,
        start_time="15:00",
        end_time="19:00",
        pay_amount=3500000,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="card",
        perks=[
            "Zamonaviy va qulay ish muhiti",
            "Suhbat asosida yuqori maosh",
            "Ariza: https://forms.gle/HvkqpQ2XDjBiLS436"
        ],
        lat=41.3780,
        lon=60.3630,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 8. IJTIMOIY HIMOYA MILLIY AGENTLIGI (RASMIY DAVLAT E'LONI - 2-RASM)
    # ==========================================
    u8 = await UsersRepo.create_user(tg_id=990008, role="employer")
    e8 = await EmployersRepo.create_or_update(
        user_id=u8,
        company_name="Ijtimoiy himoya milliy agentligining Xorazm viloyati boshqarmasi",
        org_type="state_agency",
        category="court_law",
        address="Xorazm viloyati, Urganch shahri, G'.G'ulom ko'chasi, 1/4-uy",
        district="Urganch",
        contact_phone="+998622277400 (ichki raqam 2215)",
        contact_person="Kadrlar bo'limi (Vakansiya ID: 158188)",
        lat=41.5560,
        lon=60.6260,
        offers_tuition_sponsorship=True,
    )
    await EmployersRepo.verify_employer(e8, True)

    await JobsRepo.create_job(
        employer_id=e8,
        title="Qo'shko'pir tumani 'Inson' markazi Kompleks ijtimoiy xizmat ko'rsatuvchi xodimi",
        listing_type="state_internship",
        category="court_law",
        work_format="offline_shift",
        slots_needed=5,
        target_majors=["Ijtimoiy ish", "Tibbiy-ijtimoiy ish", "Yurisprudensiya", "Huquqshunoslik", "Psixologiya", "Davlat-huquqiy faoliyat"],
        min_course_required=3,
        min_gpa_required=0.0,
        duties=[
            "Mahallada ijtimoiy himoyaga muhtoj aholi qatlami bilan ishlash",
            "Ijtimoiy-maishiy xizmatlar ko'rsatish monitoringi",
            "Davlat fuqarolik xizmatchisi vazifalarini bajarish"
        ],
        job_date=today_str,
        start_time="09:00",
        end_time="18:00",
        pay_amount=5440000,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="card",
        tuition_coverage_percent=100,
        work_obligation_years=1,
        perks=[
            "Kafolatlangan oylik maosh: 5 440 000,00 UZS",
            "Davlat fuqarolik xizmatchisi maqomi va rasmiy staj",
            "Ijtimoiy himoya agentligining rasmiy OTM amaliyoti va sertifikati",
            "100% yillik kontrakt to'lab berish imtiyozi"
        ],
        lat=41.5560,
        lon=60.6260,
        image_path="bot/assets/inson_gov_vacancy.png",
    )

    # ==========================================
    # 9. AMERIKA LOGISTIKA BROKERLIGI (CAR HAULING)
    # ==========================================
    u9 = await UsersRepo.create_user(tg_id=990009, role="employer")
    e9 = await EmployersRepo.create_or_update(
        user_id=u9,
        company_name="Franky RC Hauling (AQSH Logistika Brokerligi)",
        org_type="commercial",
        category="logistics",
        address="Urganch shahar, UrDU (Universitet) ro'parasi",
        district="Urganch",
        contact_phone="+998501701774 (@FrankyRCHauling)",
        contact_person="Franky HR",
        lat=41.5420,
        lon=60.6310,
    )
    await EmployersRepo.verify_employer(e9, True)

    await JobsRepo.create_job(
        employer_id=e9,
        title="AQSH Logistika Brokeri (Car Hauling, 1 oy bepul trening)",
        listing_type="paid_job",
        category="logistics",
        work_format="offline_shift",
        slots_needed=10,
        target_majors=["Xorijiy tillar", "Ingliz tili", "Filologiya", "Logistika", "Iqtisodiyot", "Barcha yo'nalishlar"],
        min_course_required=1,
        duties=[
            "Amerika Logistika bozorida Car Hauling brokerligi",
            "AQSH mijozlari va haydovchilari bilan ingliz tilida muzokara (B2 daraja)",
            "Amerika vaqtiga moslashib ishlash (17:30 - 04:00)"
        ],
        job_date=today_str,
        start_time="17:30",
        end_time="04:00",
        pay_amount=4000000,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="card",
        perks=[
            "Oylik maosh: $300 dan $1500 gacha (AQSH dollari)",
            "1 oy davomida BEPUL trening orqali ish o'rgatiladi va kafolatlangan ish",
            "Barcha ish jihozlari kompaniya tomonidan ta'minlanadi",
            "Ish staji yuritilishi / bonus / o'sish imkoniyati",
            "UrDU ro'parasidagi zamonaviy sharoit va qulay lokatsiya",
            "Aloqa: @FrankyRCHauling | Tel: +998501701774"
        ],
        lat=41.5420,
        lon=60.6310,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 10. IT PARK XORAZM FILIALI (IT YO'NALISHI)
    # ==========================================
    u10 = await UsersRepo.create_user(tg_id=990010, role="employer")
    e10 = await EmployersRepo.create_or_update(
        user_id=u10,
        company_name="IT Park Xorazm filiali",
        org_type="state_agency",
        category="it",
        address="Urganch shahri, Al-Xorazmiy ko'chasi",
        district="Urganch",
        contact_phone="+998622230010",
        contact_person="IT Park HR (@itpark_xorazm_hr)",
        lat=41.5530,
        lon=60.6295,
    )
    await EmployersRepo.verify_employer(e10, True)

    await JobsRepo.create_job(
        employer_id=e10,
        title="Stajyor Dasturchi va Dizayner (IT Park Xorazm filiali)",
        listing_type="state_internship",
        category="it",
        work_format="offline_shift",
        slots_needed=15,
        target_majors=["Dasturiy injiniring", "Kompyuter injiniringi", "Axborot xavfsizligi", "Sun'iy intellekt", "Amaliy matematika", "IT", "Dizayn", "Barcha yo'nalishlar"],
        min_course_required=1,
        duties=[
            "Frontend/Backend dasturlash yoki Grafik/UI-UX dizayn loyihalarida ishtirok etish",
            "Texnik topshiriqlar bilan ishlash va mantiqiy fikrlash asosida IT mahsulot yaratish",
            "Zamonaviy IT tendensiyalari va texnologiyalarni o'rganish",
            "Jamoada ishlash va real startap loyihalarni ishlab chiqish"
        ],
        job_date=today_str,
        start_time="14:00",
        end_time="18:00",
        pay_amount=0,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="cash",
        perks=[
            "Real startap va xalqaro IT loyihalarda ishtirok etish",
            "Kuchli va professional Senior dasturchilardan mentorlik (ustoz-shogird tizimi)",
            "Zamonaviy va qulay IT-ofis muhiti (Coworking, yuqori tezlikdagi internet)",
            "Loyiha muvaffaqiyatli yakunlansa, IT Park rezident kompaniyalariga doimiy pullik ishga joylashish kafolati",
            "Amaliyot yakunida xalqaro namunadagi Sertifikat va tavsiyanoma",
            "Dars jadvali asosida moslashuvchan grafik (Darsdan bo'sh vaqtda)",
            "Aloqa: @itpark_xorazm_hr | Urganch sh., Al-Xorazmiy ko'chasi"
        ],
        lat=41.5530,
        lon=60.6295,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 11. URGANCH SHAHAR TIBBIYOT BIRLASHMASI (TIBBIYOT YO'NALISHI)
    # ==========================================
    u11 = await UsersRepo.create_user(tg_id=990011, role="employer")
    e11 = await EmployersRepo.create_or_update(
        user_id=u11,
        company_name="Urganch shahar Tibbiyot Birlashmasi (Markaziy shifoxona)",
        org_type="state_agency",
        category="medical",
        address="Urganch shahri, Markaziy shifoxona majmuasi",
        district="Urganch",
        contact_phone="+998622285103",
        contact_person="Tibbiyot birlashmasi HR (@tibbiyot_birlashmasi_hr)",
        lat=41.5600,
        lon=60.6200,
    )
    await EmployersRepo.verify_employer(e11, True)

    await JobsRepo.create_job(
        employer_id=e11,
        title="Stajyor Shifokor va Hamshira (Urganch Markaziy Shifoxonasi)",
        listing_type="state_internship",
        category="medical",
        work_format="offline_shift",
        slots_needed=20,
        target_majors=["Davolash ishi", "Pediatriya", "Tibbiyot", "Oliy hamshiralik", "Stomatologiya", "Hamshiralik ishi", "Farmatsiya"],
        min_course_required=2,
        duties=[
            "Birlamchi tibbiy yordam va diagnostika asoslarini amaliy qo'llash",
            "Bemorlar bilan xushmuomala muloqot, empatiya va tibbiy parvarish",
            "Tibbiy hujjatlar va zamonaviy tibbiy uskunalar bilan ishlash ko'nikmasi",
            "Shifoxona bo'limlarida (terapiya, xirurgiya, kardiologiya) assistentlik qilish"
        ],
        job_date=today_str,
        start_time="08:30",
        end_time="13:30",
        pay_amount=0,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="cash",
        perks=[
            "Malakali shifokorlar va professorlar nazorati ostida real tibbiy amaliyot",
            "Shifoxona bo'limlari (terapiya, xirurgiya, kardiologiya) ish jarayoni bilan tanishish",
            "Tungi navbatchilik va shoshilinch tibbiy yordam ko'rsatish amaliyoti",
            "Uch mahal issiq ovqat va maxsus tibbiy forma (xalat) bilan ta'minlash",
            "Kelajakda shifoxona shtatiga pullik ishga kirish uchun rasmiy tavsiyanoma (Xarakteristika)",
            "Dars jadvali asosida moslashuvchan smena grafigi",
            "Aloqa: @tibbiyot_birlashmasi_hr | Urganch shahri"
        ],
        lat=41.5600,
        lon=60.6200,
        image_path="bot/assets/imkon_logo.png",
    )

    # ==========================================
    # 12. KAPITALBANK ATB URGANCH FILIALI (BANK/MOLIYA YO'NALISHI)
    # ==========================================
    u12 = await UsersRepo.create_user(tg_id=990012, role="employer")
    e12 = await EmployersRepo.create_or_update(
        user_id=u12,
        company_name="Kapitalbank ATB Urganch filiali",
        org_type="commercial",
        category="office",
        address="Urganch shahri, Al-Xorazmiy ko'chasi, 29-uy",
        district="Urganch",
        contact_phone="+998712001515",
        contact_person="Kapitalbank HR (@kapitalbank_hr_urganch)",
        lat=41.5525,
        lon=60.6315,
    )
    await EmployersRepo.verify_employer(e12, True)

    await JobsRepo.create_job(
        employer_id=e12,
        title="Stajyor Iqtisodchi va Bankir (Kapitalbank Urganch filiali)",
        listing_type="state_internship",
        category="office",
        work_format="offline_shift",
        slots_needed=8,
        target_majors=["Iqtisodiyot", "Moliya", "Bank ishi", "Buxgalteriya", "Audit", "Biznes boshqaruvi", "Statistika", "Barcha yo'nalishlar"],
        min_course_required=2,
        duties=[
            "Bank operatsiyalari, kreditlash va chakana xizmatlar ko'rsatish tizimini amalda o'rganish",
            "Mijozlarga bank mahsulotlari bo'yicha maslahat berishda qatnashish",
            "Microsoft Excel dasturida moliyaviy hisobotlar va tahlillar yuritish",
            "Hujjatlar aylanmasi va bank korporativ tizimlarida ishlash"
        ],
        job_date=today_str,
        start_time="13:00",
        end_time="17:00",
        pay_amount=0,
        pay_unit="monthly",
        pay_timing="monthly",
        pay_method="cash",
        perks=[
            "Bankning eng kuchli mutaxassislaridan darsdan tashqari bepul treninglar va korporativ ta'lim",
            "Zamonaviy va nufuzli bank muhitida ishlash imkoniyati",
            "Tekin tushlik (obed) va bank hisobidan transport xizmati",
            "Amaliyotni a'lo bahoga tugatgan talabalarni bankka rasmiy pullik ishga qabul qilish (Job Offer)",
            "Dars jadvaliga moslab o'zgartirilishi mumkin bo'lgan 5/2 grafik (13:00 - 17:00)",
            "Aloqa: @kapitalbank_hr_urganch | Urganch shahri"
        ],
        lat=41.5525,
        lon=60.6315,
        image_path="bot/assets/imkon_logo.png",
    )

    logger.info("✅ Barcha 100% REAL Urganch/Xorazm e'lonlari muvaffaqiyatli kiritildi!")
