from typing import Optional, Dict, Any, List
from bot.db.connection import db


class ApplicationsRepo:
    @staticmethod
    async def create_application(
        job_id: int,
        student_id: int,
        match_score: float,
        is_backup: bool = False,
        backup_rank: int = 0,
    ) -> int:
        if db.is_postgres:
            query = """
                INSERT INTO applications (job_id, student_id, match_score, is_backup, backup_rank, status)
                VALUES ($1, $2, $3, $4, $5, 'pending')
                ON CONFLICT (job_id, student_id) DO UPDATE SET match_score = $3
                RETURNING id
            """
            return await db.fetchval(query, job_id, student_id, match_score, is_backup, backup_rank)
        else:
            query = """
                INSERT OR REPLACE INTO applications (job_id, student_id, match_score, is_backup, backup_rank, status)
                VALUES ($1, $2, $3, $4, $5, 'pending')
            """
            await db.execute(query, job_id, student_id, match_score, is_backup, backup_rank)
            return await db.fetchval("SELECT last_insert_rowid()")

    @staticmethod
    async def get_by_id(app_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT a.*, j.title as job_title, j.employer_id, j.pay_amount, j.start_time, j.end_time,
                   s.full_name as student_name, s.major as student_major, s.course as student_course,
                   s.gpa_score as student_gpa, u.tg_id as student_tg_id,
                   e.company_name, e.contact_phone as employer_phone, e.address as employer_address
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            JOIN students s ON a.student_id = s.id
            JOIN users u ON s.user_id = u.id
            JOIN employers e ON j.employer_id = e.id
            WHERE a.id = $1
        """
        return await db.fetchrow(query, app_id)

    @staticmethod
    async def get_by_job(job_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT a.*, s.full_name, s.major, s.course, s.gpa_score, s.trust_score, s.location_name
            FROM applications a
            JOIN students s ON a.student_id = s.id
            WHERE a.job_id = $1
            ORDER BY a.match_score DESC, a.created_at ASC
        """
        return await db.fetch(query, job_id)

    @staticmethod
    async def get_by_student(student_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT a.*, j.title as job_title, j.listing_type, j.pay_amount, j.pay_unit,
                   e.company_name, e.category, e.address
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            JOIN employers e ON j.employer_id = e.id
            WHERE a.student_id = $1
            ORDER BY a.created_at DESC
        """
        return await db.fetch(query, student_id)

    @staticmethod
    async def get_active_by_student(student_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT a.*, j.title as job_title, j.listing_type, j.pay_amount, j.pay_unit,
                   j.start_time, j.end_time, j.job_date, j.duties,
                   e.company_name, e.contact_phone, e.address, e.lat as emp_lat, e.lon as emp_lon
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            JOIN employers e ON j.employer_id = e.id
            WHERE a.student_id = $1 AND a.status = 'accepted'
            LIMIT 1
        """
        return await db.fetchrow(query, student_id)

    @staticmethod
    async def update_status(app_id: int, status: str, reject_reason: Optional[str] = None):
        if status == 'accepted':
            await db.execute(
                "UPDATE applications SET status = $1, employer_confirmed_at = CURRENT_TIMESTAMP WHERE id = $2",
                status, app_id
            )
        else:
            await db.execute(
                "UPDATE applications SET status = $1, reject_reason = $2 WHERE id = $3",
                status, reject_reason, app_id
            )

    @staticmethod
    async def get_next_backup_candidate(job_id: int) -> Optional[Dict[str, Any]]:
        """Asosiy talaba kelmaganda navbatdagi eng mos zaxira nomzodni oladi."""
        query = """
            SELECT a.*, s.full_name, u.tg_id as student_tg_id, j.title as job_title
            FROM applications a
            JOIN students s ON a.student_id = s.id
            JOIN users u ON s.user_id = u.id
            JOIN jobs j ON a.job_id = j.id
            WHERE a.job_id = $1 AND a.status = 'pending' AND a.is_backup = TRUE
            ORDER BY a.backup_rank ASC, a.match_score DESC
            LIMIT 1
        """
        return await db.fetchrow(query, job_id)
