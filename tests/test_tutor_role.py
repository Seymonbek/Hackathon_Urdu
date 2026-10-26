import asyncio
import unittest
from datetime import date, timedelta

from bot.core.constants import UserRole
from bot.core.keyboards import (
    get_tutor_main_keyboard,
    get_admin_main_keyboard,
    get_admin_role_switch_keyboard,
)
from bot.db.connection import db
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.tutors_repo import TutorsRepo
from bot.services.matching import calculate_match_score


class TestTutorRoleAndExamLock(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await db.connect()
        await self._cleanup()

    async def asyncTearDown(self):
        await self._cleanup()
        await db.disconnect()

    async def _cleanup(self):
        await db.execute("DELETE FROM students WHERE user_id IN (SELECT id FROM users WHERE tg_id >= 888000 AND tg_id < 889000)")
        await db.execute("DELETE FROM tutors WHERE user_id IN (SELECT id FROM users WHERE tg_id >= 888000 AND tg_id < 889000)")
        await db.execute("DELETE FROM users WHERE tg_id >= 888000 AND tg_id < 889000")

    async def test_keyboards_have_tutor_buttons(self):
        """Tyutor va Admin klaviaturalarida barcha kerakli tugmalar mavjudligini tekshirish."""
        tutor_kb = get_tutor_main_keyboard("uz")
        button_texts = [btn.text for row in tutor_kb.keyboard for btn in row]
        self.assertIn("👥 Mening talabalarim", button_texts)
        self.assertIn("🔒 Sessiya / Imtihon qulfi", button_texts)
        self.assertIn("📜 Talabalar bandligi & Ish joylari", button_texts)
        self.assertIn("👤 Tyutor profili", button_texts)

        admin_kb = get_admin_main_keyboard("uz")
        admin_btn_texts = [btn.text for row in admin_kb.keyboard for btn in row]
        self.assertIn("🧑‍🏫 Tyutorlar boshqaruvi", admin_btn_texts)

        role_switch_kb = get_admin_role_switch_keyboard("uz")
        switch_texts = [btn.text for row in role_switch_kb.inline_keyboard for btn in row]
        self.assertTrue(any("Tyutor" in t for t in switch_texts))

    async def test_tutor_creation_and_student_query(self):
        """Tyutor yaratish va biriktirilgan talabalarning ish joyi ko'rinishini tekshirish."""
        # 1. Tyutor yaratish
        u_id = await UsersRepo.create_user(tg_id=888001, role=UserRole.TUTOR.value, lang="uz")
        tutor_id = await TutorsRepo.create_or_update(
            user_id=u_id,
            full_name="Zafar Ergashev",
            university="Urganch Davlat Universiteti (UrDU)",
            faculty="Raqamli texnologiyalar",
            group_name="Dasturiy injiniring 211",
            phone_number="+998901112233"
        )
        self.assertIsNotNone(tutor_id)

        tutor = await TutorsRepo.get_by_tg_id(888001)
        self.assertIsNotNone(tutor)
        self.assertEqual(tutor["full_name"], "Zafar Ergashev")

        # 2. Talaba yaratish va tyutorga biriktirish
        stu_u_id = await UsersRepo.create_user(tg_id=888002, role=UserRole.STUDENT.value, lang="uz")
        await db.execute(
            """
            INSERT INTO students (user_id, full_name, faculty, major, course, gpa_score, tutor_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            stu_u_id, "Shahzod Bekchanov", "Raqamli texnologiyalar", "Dasturiy injiniring", 3, 4.6, tutor_id
        )

        students = await TutorsRepo.get_tutor_students(tutor_id)
        self.assertTrue(len(students) >= 1)
        target_student = next(s for s in students if s["full_name"] == "Shahzod Bekchanov")
        self.assertEqual(target_student["course"], 3)

    async def test_exam_lock_enforcement_in_matching(self):
        """Sessiya qulfi yoqilganda ishlar bloklanishi va ochilganda qayta faollashishini tekshirish."""
        today = date.today()
        exam_from = str(today)
        exam_to = str(today + timedelta(days=20))

        # 1. Tyutor va talaba yaratish
        u_tutor = await UsersRepo.create_user(tg_id=888003, role=UserRole.TUTOR.value, lang="uz")
        tutor_id = await TutorsRepo.create_or_update(
            user_id=u_tutor,
            full_name="Dilshod Matyoqubov",
            university="UrDU",
            faculty="Filologiya",
            group_name="Ingliz tili 201",
        )

        stu_u_id = await UsersRepo.create_user(tg_id=888004, role=UserRole.STUDENT.value, lang="uz")
        await db.execute(
            """
            INSERT INTO students (user_id, full_name, faculty, major, course, gpa_score, tutor_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            stu_u_id, "Nodira Rahimova", "Filologiya", "Ingliz tili", 2, 4.8, tutor_id
        )

        # 2. Tyutor butun guruhga sessiya qulfi o'rnatadi
        await TutorsRepo.set_exam_lock(tutor_id, exam_from, exam_to)

        student = await db.fetchrow("SELECT * FROM students WHERE user_id = $1", stu_u_id)
        self.assertEqual(student["exam_from"], exam_from)
        self.assertEqual(student["exam_to"], exam_to)

        mock_job = {
            "id": 999,
            "title": "Ingliz tili repetitori",
            "listing_type": "paid_job",
            "category": "education",
            "work_format": "offline_shift",
            "status": "open",
            "target_majors": ["Ingliz tili", "Filologiya"],
            "min_course_required": 1,
            "min_gpa_required": 0.0,
            "start_time": "15:00",
            "end_time": "18:00",
            "lat": 41.55,
            "lon": 60.63,
        }

        # 3. Matching algoritmini tekshirish -> Qulf sababli rad etilishi kerak!
        is_eligible, score, reasons = calculate_match_score(dict(student), mock_job)
        self.assertFalse(is_eligible, "Sessiya paytida talabaga ish taklif qilinmasligi kerak")
        self.assertIn("Talabada sessiya/imtihon pauzasi yoqilgan", reasons)

        # 4. Tyutor sessiya qulfini ochadi
        await TutorsRepo.clear_exam_lock(tutor_id)

        student_unlocked = await db.fetchrow("SELECT * FROM students WHERE user_id = $1", stu_u_id)
        self.assertIsNone(student_unlocked["exam_from"])
        self.assertIsNone(student_unlocked["exam_to"])

        # Qulf ochilgach, ish yana mos kelishi kerak
        is_eligible_after, score_after, reasons_after = calculate_match_score(dict(student_unlocked), mock_job)
        self.assertTrue(is_eligible_after, "Sessiya qulfi ochilgach ish mos kelishi kerak")
        self.assertTrue(score_after > 0)


if __name__ == "__main__":
    unittest.main()
