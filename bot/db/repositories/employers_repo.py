from typing import Optional, Dict, Any, List
from bot.db.connection import db


class EmployersRepo:
    @staticmethod
    async def get_by_user_id(user_id: int) -> Optional[Dict[str, Any]]:
        return await db.fetchrow("SELECT * FROM employers WHERE user_id = $1", user_id)

    @staticmethod
    async def get_by_tg_id(tg_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT e.*, u.tg_id, u.status as user_status 
            FROM employers e 
            JOIN users u ON e.user_id = u.id 
            WHERE u.tg_id = $1
        """
        return await db.fetchrow(query, tg_id)

    @staticmethod
    async def create_or_update(
        user_id: int,
        company_name: str,
        org_type: str,
        category: str,
        address: str,
        district: str,
        contact_phone: str,
        contact_person: str,
        lat: float = None,
        lon: float = None,
        offers_tuition_sponsorship: bool = False,
    ) -> int:
        existing = await EmployersRepo.get_by_user_id(user_id)
        if existing:
            query = """
                UPDATE employers SET
                    company_name = $1, org_type = $2, category = $3,
                    address = $4, district = $5, contact_phone = $6,
                    contact_person = $7, lat = $8, lon = $9,
                    offers_tuition_sponsorship = $10
                WHERE user_id = $11
            """
            await db.execute(
                query,
                company_name, org_type, category,
                address, district, contact_phone,
                contact_person, lat, lon,
                offers_tuition_sponsorship, user_id
            )
            return existing["id"]
        else:
            if db.is_postgres:
                query = """
                    INSERT INTO employers (
                        user_id, company_name, org_type, category,
                        address, district, contact_phone, contact_person,
                        lat, lon, offers_tuition_sponsorship
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) RETURNING id
                """
                return await db.fetchval(
                    query,
                    user_id, company_name, org_type, category,
                    address, district, contact_phone, contact_person,
                    lat, lon, offers_tuition_sponsorship
                )
            else:
                query = """
                    INSERT INTO employers (
                        user_id, company_name, org_type, category,
                        address, district, contact_phone, contact_person,
                        lat, lon, offers_tuition_sponsorship
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """
                await db.execute(
                    query,
                    user_id, company_name, org_type, category,
                    address, district, contact_phone, contact_person,
                    lat, lon, offers_tuition_sponsorship
                )
                return await db.fetchval("SELECT last_insert_rowid()")

    @staticmethod
    async def verify_employer(employer_id: int, verified: bool = True):
        await db.execute("UPDATE employers SET is_verified = $1 WHERE id = $2", verified, employer_id)

    @staticmethod
    async def get_all_unverified() -> List[Dict[str, Any]]:
        return await db.fetch("SELECT * FROM employers WHERE is_verified = FALSE ORDER BY created_at DESC")

    @staticmethod
    async def get_all() -> List[Dict[str, Any]]:
        return await db.fetch("SELECT * FROM employers ORDER BY created_at DESC")
