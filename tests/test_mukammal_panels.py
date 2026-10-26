import unittest
from datetime import date, timedelta
from bot.db.connection import db
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.tutors_repo import TutorsRepo
from bot.db.repositories.students_repo import StudentsRepo
from bot.panels.tutor.dashboard import generate_tutor_csv


class TestMukammalPanels(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await db.connect()
        await self._cleanup()

    async def asyncTearDown(self):
        await self._cleanup()
        await db.disconnect()

    async def _cleanup(self):
        await db.execute("DELETE FROM students WHERE user_id IN (SELECT id FROM users WHERE tg_id >= 999000 AND tg_id < 999100)")
        await db.execute("DELETE FROM tutors WHERE user_id IN (SELECT id FROM users WHERE tg_id >= 999000 AND tg_id < 999100)")
        await db.execute("DELETE FROM users WHERE tg_id >= 999000 AND tg_id < 999100")

    async def test_tutor_csv_report_generation(self):
        """Tyutorning guruh CSV hisoboti to'g'ri shakllanishi va UTF-8 BOM mavjudligini tekshirish."""
        mock_tutor = {
            "full_name": "Alisher Qodirov",
            "university": "Urganch Davlat Universiteti (UrDU)",
            "faculty": "Raqamli texnologiyalar",
            "group_name": "Dasturiy injiniring 211",
            "phone_number": "+998901234567"
        }
        mock_students = [
            {
                "full_name": "Sanjar Bek",
                "university": "UrDU",
                "faculty": "Raqamli texnologiyalar",
                "group_name": "211-guruh",
                "course_label": "3-kurs",
                "course": 3,
                "major": "Dasturiy injiniring",
                "phone_number": "+998912345678",
                "gpa_score": 4.75,
                "active_job_title": "Frontend dasturchi (IT Park)",
                "active_company": "IT Park",
                "active_title": "Frontend dasturchi",
                "exam_from": "2026-06-01",
                "exam_to": "2026-06-25",
            },
            {
                "full_name": "Gulnoza Karimova",
                "university": "UrDU",
                "faculty": "Raqamli texnologiyalar",
                "group_name": "211-guruh",
                "course_label": "3-kurs",
                "course": 3,
                "major": "Dasturiy injiniring",
                "phone_number": "+998998887766",
                "gpa_score": 4.2,
                "active_job_title": None,
                "active_company": None,
                "active_title": None,
                "exam_from": None,
                "exam_to": None,
            }
        ]

        csv_bytes = generate_tutor_csv(mock_tutor, mock_students)
        self.assertIsInstance(csv_bytes, bytes)
        self.assertTrue(csv_bytes.startswith(b"\xef\xbb\xbf"), "Excel uchun UTF-8 BOM bilan boshlanishi kerak")

        csv_text = csv_bytes.decode("utf-8-sig")
        self.assertIn("Sanjar Bek", csv_text)
        self.assertIn("Gulnoza Karimova", csv_text)
        self.assertIn("Dasturiy injiniring", csv_text)
        self.assertIn("IT Park", csv_text)
        self.assertIn("Band (Ishlamoqda)", csv_text)
        self.assertIn("Ish qidirmoqda (Band emas)", csv_text)

    async def test_tutor_get_student_by_id_and_individual_lock(self):
        """Tyutor talaba kartasini ochishi va individual sessiya qulfini qo'yish/yechishini tekshirish."""
        # 1. Tyutor va Talaba yaratish
        u_tutor = await UsersRepo.create_user(tg_id=999001, role="tutor", lang="uz")
        t_id = await TutorsRepo.create_or_update(
            user_id=u_tutor,
            full_name="Jamshid Oripov",
            university="UrDU",
            faculty="Iqtisodiyot",
            group_name="Moliya 301",
            phone_number="+998931112233"
        )

        u_stu = await UsersRepo.create_user(tg_id=999002, role="student", lang="uz")
        stu_id = await db.fetchval(
            """
            INSERT INTO students (user_id, full_name, faculty, major, course, gpa_score, tutor_id, phone_number)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            u_stu, "Murodbek Xudoyberganov", "Iqtisodiyot", "Moliya", 3, 4.5, t_id, "+998941234567"
        ) if db.is_postgres else None
        if not stu_id:
            await db.execute(
                """
                INSERT INTO students (user_id, full_name, faculty, major, course, gpa_score, tutor_id, phone_number)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                u_stu, "Murodbek Xudoyberganov", "Iqtisodiyot", "Moliya", 3, 4.5, t_id, "+998941234567"
            )
            stu_id = await db.fetchval("SELECT last_insert_rowid()")

        # 2. get_student_by_id tekshirish
        student_data = await TutorsRepo.get_student_by_id(stu_id)
        self.assertIsNotNone(student_data)
        self.assertEqual(student_data["full_name"], "Murodbek Xudoyberganov")
        self.assertEqual(student_data["phone_number"], "+998941234567")

        # 3. Individual sessiya qulfini yoqish
        await TutorsRepo.set_exam_lock(t_id, "2026-05-10", "2026-05-30", student_id=stu_id)
        locked_stu = await TutorsRepo.get_student_by_id(stu_id)
        self.assertEqual(locked_stu["exam_from"], "2026-05-10")
        self.assertEqual(locked_stu["exam_to"], "2026-05-30")

        # 4. Individual sessiya qulfini yechish
        await TutorsRepo.clear_exam_lock(t_id, student_id=stu_id)
        unlocked_stu = await TutorsRepo.get_student_by_id(stu_id)
        self.assertIsNone(unlocked_stu["exam_from"])
        self.assertIsNone(unlocked_stu["exam_to"])

    async def test_student_gpa_update(self):
        """Talaba o'z GPA balini yangilashi muvaffaqiyatli saqlanishini tekshirish."""
        u_stu = await UsersRepo.create_user(tg_id=999003, role="student", lang="uz")
        await db.execute(
            """
            INSERT INTO students (user_id, full_name, faculty, major, course, gpa_score)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            u_stu, "Kamola Karimova", "Pedagogika", "Boshlang'ich ta'lim", 2, 3.8
        )

        stu = await StudentsRepo.get_by_tg_id(999003)
        self.assertEqual(float(stu["gpa_score"]), 3.8)

        # Yangilash
        await StudentsRepo.update_gpa(stu["id"], 4.85)

        updated_stu = await StudentsRepo.get_by_tg_id(999003)
        self.assertAlmostEqual(float(updated_stu["gpa_score"]), 4.85, places=2)

    async def test_tutor_delete_by_admin(self):
        """Admin tomonidan tyutor o'chirilganda uning talabalari bo'shatilishini tekshirish."""
        u_tutor = await UsersRepo.create_user(tg_id=999004, role="tutor", lang="uz")
        t_id = await TutorsRepo.create_or_update(
            user_id=u_tutor,
            full_name="O'chiriladigan Tyutor",
            university="UrDU",
            faculty="Tarix",
        )

        u_stu = await UsersRepo.create_user(tg_id=999005, role="student", lang="uz")
        await db.execute(
            """
            INSERT INTO students (user_id, full_name, faculty, major, course, tutor_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            u_stu, "Tarixchi Talaba", "Tarix", "Tarix", 1, t_id
        )

        # O'chirishdan oldin talabada tutor_id = t_id
        stu_before = await StudentsRepo.get_by_tg_id(999005)
        self.assertEqual(stu_before["tutor_id"], t_id)

        # Tyutorni o'chirish
        res = await TutorsRepo.delete_tutor(t_id)
        self.assertTrue(res)

        # Talabada tutor_id NULL bo'lishi kerak
        stu_after = await StudentsRepo.get_by_tg_id(999005)
        self.assertIsNone(stu_after["tutor_id"])


if __name__ == "__main__":
    unittest.main()
