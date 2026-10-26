from typing import Optional, Dict, Any, List
from bot.db.connection import db


class InternshipRepo:
    @staticmethod
    async def add_log(
        application_id: int,
        student_id: int,
        visit_date: str,
        hours_spent: float,
        tasks_performed: str,
    ) -> int:
        if db.is_postgres:
            query = """
                INSERT INTO internship_logs (application_id, student_id, visit_date, hours_spent, tasks_performed)
                VALUES ($1, $2, $3, $4, $5) RETURNING id
            """
            return await db.fetchval(query, application_id, student_id, visit_date, hours_spent, tasks_performed)
        else:
            query = """
                INSERT INTO internship_logs (application_id, student_id, visit_date, hours_spent, tasks_performed)
                VALUES ($1, $2, $3, $4, $5)
            """
            await db.execute(query, application_id, student_id, visit_date, hours_spent, tasks_performed)
            return await db.fetchval("SELECT last_insert_rowid()")

    @staticmethod
    async def get_logs_by_student(student_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT il.*, j.title as internship_title, e.company_name
            FROM internship_logs il
            JOIN applications a ON il.application_id = a.id
            JOIN jobs j ON a.job_id = j.id
            JOIN employers e ON j.employer_id = e.id
            WHERE il.student_id = $1
            ORDER BY il.visit_date DESC
        """
        return await db.fetch(query, student_id)

    @staticmethod
    async def get_logs_by_application(application_id: int) -> List[Dict[str, Any]]:
        query = "SELECT * FROM internship_logs WHERE application_id = $1 ORDER BY visit_date ASC"
        return await db.fetch(query, application_id)

    @staticmethod
    async def verify_log(log_id: int, mentor_score: int, mentor_feedback: str):
        query = """
            UPDATE internship_logs
            SET mentor_score = $1, mentor_feedback = $2, verified_by_mentor = TRUE
            WHERE id = $3
        """
        await db.execute(query, mentor_score, mentor_feedback, log_id)

    @staticmethod
    async def get_total_hours(student_id: int) -> float:
        val = await db.fetchval(
            "SELECT COALESCE(SUM(hours_spent), 0.0) FROM internship_logs WHERE student_id = $1 AND verified_by_mentor = TRUE",
            student_id
        )
        return float(val or 0.0)
