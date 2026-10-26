from typing import Optional, Dict, Any
from bot.db.connection import db


class UsersRepo:
    @staticmethod
    async def get_by_tg_id(tg_id: int) -> Optional[Dict[str, Any]]:
        return await db.fetchrow(
            "SELECT * FROM users WHERE tg_id = $1", tg_id
        )

    @staticmethod
    async def create_user(tg_id: int, role: str, lang: str = "uz") -> int:
        user = await UsersRepo.get_by_tg_id(tg_id)
        if user:
            await db.execute(
                "UPDATE users SET role = $1, status = 'active', last_seen = CURRENT_TIMESTAMP WHERE tg_id = $2",
                role, tg_id
            )
            return user["id"]
        
        if db.is_postgres:
            return await db.fetchval(
                "INSERT INTO users (tg_id, role, lang) VALUES ($1, $2, $3) RETURNING id",
                tg_id, role, lang
            )
        else:
            await db.execute(
                "INSERT INTO users (tg_id, role, lang) VALUES ($1, $2, $3)",
                tg_id, role, lang
            )
            return await db.fetchval("SELECT last_insert_rowid()")

    @staticmethod
    async def update_status(user_id: int, status: str):
        await db.execute("UPDATE users SET status = $1 WHERE id = $2", status, user_id)

    @staticmethod
    async def update_lang(tg_id: int, lang: str):
        user = await UsersRepo.get_by_tg_id(tg_id)
        if user:
            await db.execute("UPDATE users SET lang = $1 WHERE tg_id = $2", lang, tg_id)
        else:
            if db.is_postgres:
                await db.execute("INSERT INTO users (tg_id, role, lang) VALUES ($1, 'guest', $2)", tg_id, lang)
            else:
                await db.execute("INSERT INTO users (tg_id, role, lang) VALUES ($1, 'guest', $2)", tg_id, lang)

    @staticmethod
    async def get_user_lang(tg_id: int) -> str:
        user = await UsersRepo.get_by_tg_id(tg_id)
        if user and user.get("lang"):
            return user["lang"]
        return "uz"

    @staticmethod
    async def update_last_seen(tg_id: int):
        await db.execute("UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE tg_id = $1", tg_id)
