import json
from typing import Optional, Dict, Any, List
from bot.db.connection import db


class JobsRepo:
    @staticmethod
    async def create_job(
        employer_id: int,
        title: str,
        listing_type: str,
        category: str,
        work_format: str,
        slots_needed: int,
        target_majors: List[str],
        duties: List[str],
        min_course_required: int = 1,
        min_gpa_required: float = 0.0,
        required_skills: List[str] = None,
        job_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        total_hours: float = 0.0,
        pay_amount: int = 0,
        pay_unit: str = "per_shift",
        pay_method: str = "cash",
        pay_timing: str = "daily",
        tuition_coverage_percent: int = 0,
        work_obligation_years: int = 0,
        perks: List[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        is_urgent: bool = False,
        status: str = "open",
        image_path: Optional[str] = "bot/assets/imkon_logo.png",
    ) -> int:
        target_majors = target_majors or []
        required_skills = required_skills or []
        duties = duties or []
        perks = perks or []
        image_path = image_path or "bot/assets/imkon_logo.png"

        if db.is_postgres:
            query = """
                INSERT INTO jobs (
                    employer_id, title, listing_type, category, work_format,
                    slots_needed, target_majors, min_course_required, min_gpa_required,
                    required_skills, job_date, start_time, end_time, total_hours,
                    pay_amount, pay_unit, pay_method, pay_timing,
                    tuition_coverage_percent, work_obligation_years,
                    duties, perks, lat, lon, is_urgent, status, image_path
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27
                ) RETURNING id
            """
            return await db.fetchval(
                query,
                employer_id, title, listing_type, category, work_format,
                slots_needed, target_majors, min_course_required, min_gpa_required,
                required_skills, job_date, start_time, end_time, total_hours,
                pay_amount, pay_unit, pay_method, pay_timing,
                tuition_coverage_percent, work_obligation_years,
                duties, perks, lat, lon, is_urgent, status, image_path
            )
        else:
            query = """
                INSERT INTO jobs (
                    employer_id, title, listing_type, category, work_format,
                    slots_needed, target_majors, min_course_required, min_gpa_required,
                    required_skills, job_date, start_time, end_time, total_hours,
                    pay_amount, pay_unit, pay_method, pay_timing,
                    tuition_coverage_percent, work_obligation_years,
                    duties, perks, lat, lon, is_urgent, status, image_path
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27
                )
            """
            await db.execute(
                query,
                employer_id, title, listing_type, category, work_format,
                slots_needed, target_majors, min_course_required, min_gpa_required,
                required_skills, job_date, start_time, end_time, total_hours,
                pay_amount, pay_unit, pay_method, pay_timing,
                tuition_coverage_percent, work_obligation_years,
                duties, perks, lat, lon, is_urgent, status, image_path
            )
            return await db.fetchval("SELECT last_insert_rowid()")

    @staticmethod
    async def delete_job(job_id: int) -> bool:
        """E'lonni bazadan butunlay o'chirish."""
        await db.execute("DELETE FROM jobs WHERE id = $1", job_id)
        return True

    @staticmethod
    async def get_by_id(job_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT j.*, e.company_name, e.org_type, e.address, e.contact_phone, e.contact_person, e.rating as employer_rating, e.is_verified
            FROM jobs j
            JOIN employers e ON j.employer_id = e.id
            WHERE j.id = $1
        """
        row = await db.fetchrow(query, job_id)
        if row:
            return JobsRepo._parse_json_fields(row)
        return None

    @staticmethod
    async def get_open_jobs(listing_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if listing_type:
            query = """
                SELECT j.*, e.company_name, e.org_type, e.address, e.rating as employer_rating, e.is_verified, e.district
                FROM jobs j
                JOIN employers e ON j.employer_id = e.id
                WHERE j.status = 'open' AND j.listing_type = $1
                ORDER BY j.is_urgent DESC, j.created_at DESC
            """
            rows = await db.fetch(query, listing_type)
        else:
            query = """
                SELECT j.*, e.company_name, e.org_type, e.address, e.rating as employer_rating, e.is_verified, e.district
                FROM jobs j
                JOIN employers e ON j.employer_id = e.id
                WHERE j.status = 'open'
                ORDER BY j.is_urgent DESC, j.created_at DESC
            """
            rows = await db.fetch(query)

        return [JobsRepo._parse_json_fields(r) for r in rows]

    @staticmethod
    async def get_by_employer(employer_id: int) -> List[Dict[str, Any]]:
        query = "SELECT * FROM jobs WHERE employer_id = $1 ORDER BY created_at DESC"
        rows = await db.fetch(query, employer_id)
        return [JobsRepo._parse_json_fields(r) for r in rows]

    @staticmethod
    async def update_status(job_id: int, status: str):
        await db.execute("UPDATE jobs SET status = $1 WHERE id = $2", status, job_id)

    @staticmethod
    async def increment_filled_slot(job_id: int) -> bool:
        """Poygasiz (atomic) o'rin to'ldirish."""
        job = await JobsRepo.get_by_id(job_id)
        if not job:
            return False
        
        new_filled = job["filled_count"] + 1
        new_status = "filled" if new_filled >= job["slots_needed"] else "open"
        
        await db.execute(
            "UPDATE jobs SET filled_count = $1, status = $2 WHERE id = $3",
            new_filled, new_status, job_id
        )
        return True

    @staticmethod
    def _parse_json_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        d = dict(row)
        for field in ["target_majors", "required_skills", "duties", "perks"]:
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        return d
