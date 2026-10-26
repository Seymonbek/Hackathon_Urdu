from typing import Optional, Dict, Any, List
from bot.db.connection import db


class SponsorshipRepo:
    @staticmethod
    async def create_sponsorship(
        application_id: int,
        student_id: int,
        employer_id: int,
        covered_amount: int,
        obligation_months: int = 12,
        contract_pdf_s3_url: Optional[str] = None,
    ) -> int:
        if db.is_postgres:
            query = """
                INSERT INTO tuition_sponsorships (
                    application_id, student_id, employer_id, covered_amount, obligation_months, contract_pdf_s3_url
                ) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
            """
            return await db.fetchval(
                query, application_id, student_id, employer_id, covered_amount, obligation_months, contract_pdf_s3_url
            )
        else:
            query = """
                INSERT INTO tuition_sponsorships (
                    application_id, student_id, employer_id, covered_amount, obligation_months, contract_pdf_s3_url
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """
            await db.execute(
                query, application_id, student_id, employer_id, covered_amount, obligation_months, contract_pdf_s3_url
            )
            return await db.fetchval("SELECT last_insert_rowid()")

    @staticmethod
    async def get_by_id(spon_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT ts.*, s.full_name as student_name, s.major as student_major, s.gpa_score,
                   e.company_name, e.contact_phone, e.address as employer_address
            FROM tuition_sponsorships ts
            JOIN students s ON ts.student_id = s.id
            JOIN employers e ON ts.employer_id = e.id
            WHERE ts.id = $1
        """
        return await db.fetchrow(query, spon_id)

    @staticmethod
    async def get_by_student(student_id: int) -> List[Dict[str, Any]]:
        query = """
            SELECT ts.*, e.company_name, e.category, e.address
            FROM tuition_sponsorships ts
            JOIN employers e ON ts.employer_id = e.id
            WHERE ts.student_id = $1
            ORDER BY ts.created_at DESC
        """
        return await db.fetch(query, student_id)

    @staticmethod
    async def update_status(spon_id: int, status: str, otm_approved_by: Optional[str] = None):
        if otm_approved_by:
            await db.execute(
                "UPDATE tuition_sponsorships SET status = $1, otm_approved_by = $2, otm_approved_at = CURRENT_TIMESTAMP WHERE id = $3",
                status, otm_approved_by, spon_id
            )
        else:
            await db.execute(
                "UPDATE tuition_sponsorships SET status = $1 WHERE id = $2",
                status, spon_id
            )

    @staticmethod
    async def get_all_pending_otm() -> List[Dict[str, Any]]:
        query = """
            SELECT ts.*, s.full_name as student_name, s.faculty, s.major, s.gpa_score, e.company_name
            FROM tuition_sponsorships ts
            JOIN students s ON ts.student_id = s.id
            JOIN employers e ON ts.employer_id = e.id
            WHERE ts.status = 'student_accepted'
            ORDER BY ts.created_at DESC
        """
        return await db.fetch(query)
