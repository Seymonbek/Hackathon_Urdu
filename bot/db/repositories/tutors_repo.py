from typing import Optional, Dict, Any, List
from bot.db.connection import db


class TutorsRepo:
    @staticmethod
    async def create_or_update(
        user_id: int,
        full_name: str,
        university: str,
        faculty: str,
        group_name: Optional[str] = "",
        phone_number: Optional[str] = "",
    ) -> int:
        existing = await db.fetchrow("SELECT id FROM tutors WHERE user_id = $1", user_id)
        if existing:
            query = """
                UPDATE tutors SET
                    full_name = $1, university = $2, faculty = $3,
                    group_name = $4, phone_number = $5
                WHERE user_id = $6
            """
            await db.execute(query, full_name, university, faculty, group_name, phone_number, user_id)
            return existing["id"]
        else:
            if db.is_postgres:
                query = """
                    INSERT INTO tutors (user_id, full_name, university, faculty, group_name, phone_number)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """
                return await db.fetchval(query, user_id, full_name, university, faculty, group_name, phone_number)
            else:
                query = """
                    INSERT INTO tutors (user_id, full_name, university, faculty, group_name, phone_number)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """
                await db.execute(query, user_id, full_name, university, faculty, group_name, phone_number)
                return await db.fetchval("SELECT last_insert_rowid()")

    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        return await db.fetchrow("SELECT * FROM tutors WHERE user_id = $1", user_id)

    @staticmethod
    async def get_by_tg_id(tg_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT t.*, u.tg_id, u.lang
            FROM tutors t
            JOIN users u ON t.user_id = u.id
            WHERE u.tg_id = $1
        """
        return await db.fetchrow(query, tg_id)

    @staticmethod
    async def get_by_id(tutor_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT t.*, u.tg_id
            FROM tutors t
            JOIN users u ON t.user_id = u.id
            WHERE t.id = $1
        """
        return await db.fetchrow(query, tutor_id)

    @staticmethod
    async def get_all() -> List[Dict[str, Any]]:
        query = """
            SELECT t.*, u.tg_id,
                   (SELECT COUNT(*) FROM students s WHERE s.tutor_id = t.id) as students_count
            FROM tutors t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.id DESC
        """
        return await db.fetch(query)

    @staticmethod
    async def get_tutor_students(tutor_id: int) -> List[Dict[str, Any]]:
        """
        Tyutorga biriktirilgan talabalar ro'yxati va ularning ish/amaliyot holati.
        """
        query = """
            SELECT s.*, u.tg_id,
                   (
                       SELECT j.title || ' (' || e.company_name || ')'
                       FROM applications a
                       JOIN jobs j ON a.job_id = j.id
                       JOIN employers e ON j.employer_id = e.id
                       WHERE a.student_id = s.id AND a.status = 'accepted'
                       LIMIT 1
                   ) as active_job_title
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE s.tutor_id = $1 OR s.tutor_id IS NULL
            ORDER BY s.id DESC
        """
        return await db.fetch(query, tutor_id)

    @staticmethod
    async def assign_student(student_id: int, tutor_id: int) -> bool:
        await db.execute("UPDATE students SET tutor_id = $1 WHERE id = $2", tutor_id, student_id)
        return True

    @staticmethod
    async def set_exam_lock(tutor_id: int, exam_from: str, exam_to: str, student_id: Optional[int] = None) -> int:
        """
        Tyutor tomonidan talabaga yoki butun guruhga sessiya/imtihon qulfi (blokirovkasi) o'rnatish.
        Bu vaqtda talaba ishga ariza topshira olmaydi va barcha takliflar pauzaga tushadi.
        """
        if student_id:
            await db.execute(
                "UPDATE students SET exam_from = $1, exam_to = $2 WHERE id = $3 AND (tutor_id = $4 OR tutor_id IS NULL)",
                exam_from, exam_to, student_id, tutor_id
            )
            return 1
        else:
            res = await db.execute(
                "UPDATE students SET exam_from = $1, exam_to = $2 WHERE tutor_id = $3 OR tutor_id IS NULL",
                exam_from, exam_to, tutor_id
            )
            return int(res) if str(res).isdigit() else 1

    @staticmethod
    async def get_student_by_id(student_id: int) -> Optional[Dict[str, Any]]:
        """Talabaning to'liq ma'lumoti va uning hozirgi ish beruvchisi."""
        query = """
            SELECT s.*, u.tg_id, u.lang,
                   (
                       SELECT j.title || ' (' || e.company_name || ')'
                       FROM applications a
                       JOIN jobs j ON a.job_id = j.id
                       JOIN employers e ON j.employer_id = e.id
                       WHERE a.student_id = s.id AND a.status = 'accepted'
                       LIMIT 1
                   ) as active_job_title,
                   (
                       SELECT e.company_name
                       FROM applications a
                       JOIN jobs j ON a.job_id = j.id
                       JOIN employers e ON j.employer_id = e.id
                       WHERE a.student_id = s.id AND a.status = 'accepted'
                       LIMIT 1
                   ) as active_company,
                   (
                       SELECT j.title
                       FROM applications a
                       JOIN jobs j ON a.job_id = j.id
                       WHERE a.student_id = s.id AND a.status = 'accepted'
                       LIMIT 1
                   ) as active_title,
                   (
                       SELECT e.contact_phone
                       FROM applications a
                       JOIN jobs j ON a.job_id = j.id
                       JOIN employers e ON j.employer_id = e.id
                       WHERE a.student_id = s.id AND a.status = 'accepted'
                       LIMIT 1
                   ) as employer_phone,
                   (
                       SELECT e.address
                       FROM applications a
                       JOIN jobs j ON a.job_id = j.id
                       JOIN employers e ON j.employer_id = e.id
                       WHERE a.student_id = s.id AND a.status = 'accepted'
                       LIMIT 1
                   ) as employer_address
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = $1
        """
        return await db.fetchrow(query, student_id)

    @staticmethod
    async def delete_tutor(tutor_id: int) -> bool:
        """Tyutorni o'chirish va unga biriktirilgan talabalarni bo'shatish."""
        await db.execute("UPDATE students SET tutor_id = NULL WHERE tutor_id = $1", tutor_id)
        await db.execute("DELETE FROM tutors WHERE id = $1", tutor_id)
        return True

    @staticmethod
    async def clear_exam_lock(tutor_id: int, student_id: Optional[int] = None) -> int:
        """Sessiya qulfini ochish."""
        if student_id:
            await db.execute(
                "UPDATE students SET exam_from = NULL, exam_to = NULL WHERE id = $1 AND (tutor_id = $2 OR tutor_id IS NULL)",
                student_id, tutor_id
            )
            return 1
        else:
            res = await db.execute(
                "UPDATE students SET exam_from = NULL, exam_to = NULL WHERE tutor_id = $1 OR tutor_id IS NULL",
                tutor_id
            )
            return int(res) if str(res).isdigit() else 1
