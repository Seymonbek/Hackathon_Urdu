import asyncio
import sys
import unittest
from bot.core.i18n import get_i18n, get_button_variants, uz, ru, en
from bot.services.admin_notifier import notify_admin_new_student, notify_admin_new_employer
from bot.db.connection import db
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.students_repo import StudentsRepo
from bot.db.repositories.employers_repo import EmployersRepo

# Windows console encoding fix
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


class TestI18nAndAdminNotification(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await db.connect()

    async def asyncTearDown(self):
        await db.disconnect()

    def test_multilingual_dictionary_keys(self):
        """Barcha 3 tildagi asosiy kalitlar to'liq mavjudligini tekshirish."""
        for key in [
            "BTN_STUDENT_MATCHES", "BTN_STUDENT_GRANTS", "BTN_STUDENT_ACTIVE", "BTN_STUDENT_APPS",
            "BTN_EMP_POST_JOB", "BTN_EMP_INBOX", "BTN_EMP_ACTIVE",
            "BTN_ADM_DASHBOARD", "BTN_ADM_VERIFY", "BTN_ADM_EXPORT", "BTN_ADM_SWITCH_ROLE",
            "MSG_WELCOME", "MSG_REG_STUDENT_SUCCESS", "MSG_REG_EMP_NAME"
        ]:
            self.assertTrue(hasattr(uz, key), f"uz missing {key}")
            self.assertTrue(hasattr(ru, key), f"ru missing {key}")
            self.assertTrue(hasattr(en, key), f"en missing {key}")

            uz_val = getattr(uz, key)
            ru_val = getattr(ru, key)
            en_val = getattr(en, key)

            self.assertNotEqual(uz_val, ru_val, f"{key} uz and ru should be translated")
            self.assertNotEqual(uz_val, en_val, f"{key} uz and en should be translated")

    def test_button_variants_helper(self):
        """get_button_variants 3 ta tildagi variantlarni qaytarishi kerak."""
        variants = get_button_variants("BTN_STUDENT_MATCHES")
        self.assertEqual(len(variants), 3)
        self.assertIn(uz.BTN_STUDENT_MATCHES, variants)
        self.assertIn(ru.BTN_STUDENT_MATCHES, variants)
        self.assertIn(en.BTN_STUDENT_MATCHES, variants)

    async def test_user_language_persistence(self):
        """Foydalanuvchi tanlagan til bazada to'g'ri saqlanishi kerak."""
        test_tg_id = 999111222
        await UsersRepo.update_lang(test_tg_id, "ru")
        lang = await UsersRepo.get_user_lang(test_tg_id)
        self.assertEqual(lang, "ru")

        # Ingliz tiliga o'zgartirish
        await UsersRepo.update_lang(test_tg_id, "en")
        lang = await UsersRepo.get_user_lang(test_tg_id)
        self.assertEqual(lang, "en")

    async def test_admin_notification_data_structure(self):
        """Adminga yuboriladigan bildirishnoma ma'lumotlari to'liq va to'g'ri bo'lishi kerak."""
        test_user_id = await UsersRepo.create_user(888444333, "student", "uz")
        student_id = await StudentsRepo.create_or_update(
            user_id=test_user_id,
            full_name="Jamshid Aliyev",
            phone_number="+998901234567",
            region="Urganch shahri",
            university="Urganch Davlat Universiteti (UrDU)",
            faculty="Fizika-matematika",
            major="Dasturiy injiniring",
            course=3,
            course_label="3-kurs",
            is_contract=True,
            yearly_tuition_amount=14000000,
            gpa_score=4.8,
            location_lat=41.55,
            location_lon=60.63,
            location_name="Urganch, TTJ 2-bino",
            max_distance_km=3.0
        )
        student_record = await StudentsRepo.get_by_user_id(test_user_id)
        self.assertIsNotNone(student_record)
        self.assertEqual(student_record["full_name"], "Jamshid Aliyev")
        self.assertEqual(student_record["phone_number"], "+998901234567")
        self.assertEqual(student_record["region"], "Urganch shahri")
        self.assertEqual(student_record["university"], "Urganch Davlat Universiteti (UrDU)")
        self.assertEqual(student_record["course_label"], "3-kurs")
        self.assertEqual(student_record["major"], "Dasturiy injiniring")


if __name__ == "__main__":
    unittest.main()
