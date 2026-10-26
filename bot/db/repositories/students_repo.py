import json
from typing import Optional, Dict, Any, List
from bot.db.connection import db


class StudentsRepo:
    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        row = await db.fetchrow("SELECT * FROM students WHERE user_id = $1", user_id)
        if row:
            return StudentsRepo._parse_json_fields(row)
        return None

    @staticmethod
    async def get_by_tg_id(tg_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT s.*, u.tg_id, u.status as user_status 
            FROM students s 
            JOIN users u ON s.user_id = u.id 
            WHERE u.tg_id = $1
        """
        row = await db.fetchrow(query, tg_id)
        if row:
            return StudentsRepo._parse_json_fields(row)
        return None

    @staticmethod
    async def create_or_update(
        user_id: int,
        full_name: str,
        faculty: str,
        major: str,
        course: int,
        phone_number: str = None,
        region: str = None,
        university: str = None,
        course_label: str = None,
        is_contract: bool = True,
        yearly_tuition_amount: int = 0,
        gpa_score: float = 0.0,
        interests: List[str] = None,
        skills: List[str] = None,
        location_lat: float = None,
        location_lon: float = None,
        location_name: str = None,
        max_distance_km: float = 5.0,
        schedule_busy: Dict = None,
        transport_cost: int = 0,
    ) -> int:
        interests = interests or []
        skills = skills or []
        schedule_busy = schedule_busy or {}

        existing = await StudentsRepo.get_by_user_id(user_id)
        if existing:
            query = """
                UPDATE students SET
                    full_name = $1, faculty = $2, major = $3, course = $4,
                    phone_number = $5, region = $6, university = $7, course_label = $8,
                    is_contract = $9, yearly_tuition_amount = $10, gpa_score = $11,
                    interests = $12, skills = $13, location_lat = $14, location_lon = $15,
                    location_name = $16, max_distance_km = $17, schedule_busy = $18,
                    transport_cost = $19
                WHERE user_id = $20
            """
            await db.execute(
                query,
                full_name, faculty, major, course,
                phone_number, region, university, course_label,
                is_contract, yearly_tuition_amount, gpa_score,
                interests, skills, location_lat, location_lon,
                location_name, max_distance_km, schedule_busy,
                transport_cost, user_id
            )
            return existing["id"]
        else:
            if db.is_postgres:
                query = """
                    INSERT INTO students (
                        user_id, full_name, faculty, major, course,
                        phone_number, region, university, course_label,
                        is_contract, yearly_tuition_amount, gpa_score,
                        interests, skills, location_lat, location_lon,
                        location_name, max_distance_km, schedule_busy, transport_cost
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                    ) RETURNING id
                """
                return await db.fetchval(
                    query,
                    user_id, full_name, faculty, major, course,
                    phone_number, region, university, course_label,
                    is_contract, yearly_tuition_amount, gpa_score,
                    interests, skills, location_lat, location_lon,
                    location_name, max_distance_km, schedule_busy, transport_cost
                )
            else:
                query = """
                    INSERT INTO students (
                        user_id, full_name, faculty, major, course,
                        phone_number, region, university, course_label,
                        is_contract, yearly_tuition_amount, gpa_score,
                        interests, skills, location_lat, location_lon,
                        location_name, max_distance_km, schedule_busy, transport_cost
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                    )
                """
                await db.execute(
                    query,
                    user_id, full_name, faculty, major, course,
                    phone_number, region, university, course_label,
                    is_contract, yearly_tuition_amount, gpa_score,
                    interests, skills, location_lat, location_lon,
                    location_name, max_distance_km, schedule_busy, transport_cost
                )
                return await db.fetchval("SELECT last_insert_rowid()")

    @staticmethod
    async def update_location(student_id: int, lat: float, lon: float, location_name: str, max_distance_km: float):
        await db.execute(
            "UPDATE students SET location_lat = $1, location_lon = $2, location_name = $3, max_distance_km = $4 WHERE id = $5",
            lat, lon, location_name, max_distance_km, student_id
        )

    @staticmethod
    async def update_schedule(student_id: int, schedule_busy: dict):
        await db.execute(
            "UPDATE students SET schedule_busy = $1 WHERE id = $2",
            schedule_busy, student_id
        )

    @staticmethod
    async def update_exam_mode(student_id: int, exam_from: Optional[str], exam_to: Optional[str]):
        await db.execute(
            "UPDATE students SET exam_from = $1, exam_to = $2 WHERE id = $3",
            exam_from, exam_to, student_id
        )

    @staticmethod
    async def update_gpa(student_id: int, gpa_score: float):
        await db.execute(
            "UPDATE students SET gpa_score = $1 WHERE id = $2",
            gpa_score, student_id
        )

    @staticmethod
    async def get_all_active_for_matching() -> List[Dict[str, Any]]:
        query = """
            SELECT s.*, u.tg_id 
            FROM students s 
            JOIN users u ON s.user_id = u.id 
            WHERE u.status = 'active'
        """
        rows = await db.fetch(query)
        return [StudentsRepo._parse_json_fields(r) for r in rows]

    @staticmethod
    def _parse_json_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        d = dict(row)
        for field in ["interests", "skills", "schedule_busy", "work_formats"]:
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        return d
