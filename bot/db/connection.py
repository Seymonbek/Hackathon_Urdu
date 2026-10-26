import os
import json
import logging
from typing import Any, List, Optional, Dict
import asyncpg
import aiosqlite
from bot.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.is_postgres: bool = False
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.sqlite_conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        # 1. Avval PostgreSQL'ga ulanishga harakat qilamiz
        try:
            logger.info(f"PostgreSQL bazasiga ulanilmoqda: {settings.DB_HOST}:{settings.DB_PORT} ({settings.DB_NAME})...")
            self.pg_pool = await asyncpg.create_pool(
                dsn=settings.postgres_dsn,
                min_size=2,
                max_size=10,
                timeout=5.0,
            )
            self.is_postgres = True
            logger.info("✅ PostgreSQL bazasiga muvaffaqiyatli ulanildi (Production/AWS mode)!")
            await self._init_postgres_schema()
            return
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL'ga ulanib bo'lmadi: {e}")

        # 2. Agar PostgreSQL bo'lmasa va SQLite fallback yoqilgan bo'lsa
        if settings.USE_SQLITE_FALLBACK:
            logger.info(f"Lokal SQLite rejimiga o'tilmoqda: {settings.SQLITE_PATH}...")
            self.sqlite_conn = await aiosqlite.connect(settings.SQLITE_PATH)
            self.sqlite_conn.row_factory = aiosqlite.Row
            await self.sqlite_conn.execute("PRAGMA foreign_keys = ON;")
            await self.sqlite_conn.execute("PRAGMA journal_mode = WAL;")
            self.is_postgres = False
            logger.info("✅ SQLite bazasiga ulanildi (Local Development mode)!")
            await self._init_sqlite_schema()
        else:
            raise RuntimeError("PostgreSQL'ga ulanib bo'lmadi va SQLite fallback o'chirilgan.")

    async def _init_postgres_schema(self):
        schema_path = os.path.join(os.path.dirname(__file__), "schema_pg.sql")
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                sql = f.read()
            async with self.pg_pool.acquire() as conn:
                await conn.execute(sql)
                for col, col_type in [
                    ("phone_number", "VARCHAR(30)"),
                    ("region", "VARCHAR(150)"),
                    ("university", "VARCHAR(255)"),
                    ("course_label", "VARCHAR(50)"),
                ]:
                    try:
                        await conn.execute(f"ALTER TABLE students ADD COLUMN IF NOT EXISTS {col} {col_type};")
                    except Exception:
                        pass
            logger.info("✅ PostgreSQL jadvallari va turlari tekshirildi/yaratildi.")

    async def _init_sqlite_schema(self):
        schema_path = os.path.join(os.path.dirname(__file__), "schema_sqlite.sql")
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                sql = f.read()
            await self.sqlite_conn.executescript(sql)
            # Yangi maydonlar migratsiyasi
            for col, col_type in [
                ("phone_number", "TEXT"),
                ("region", "TEXT"),
                ("university", "TEXT"),
                ("course_label", "TEXT"),
            ]:
                try:
                    await self.sqlite_conn.execute(f"ALTER TABLE students ADD COLUMN {col} {col_type};")
                except Exception:
                    pass
            try:
                await self.sqlite_conn.execute("ALTER TABLE jobs ADD COLUMN image_path TEXT DEFAULT 'bot/assets/imkon_logo.png';")
            except Exception:
                pass
            try:
                await self.sqlite_conn.execute("""
                    CREATE TABLE IF NOT EXISTS tutors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                        full_name TEXT NOT NULL,
                        university TEXT NOT NULL,
                        faculty TEXT NOT NULL,
                        group_name TEXT,
                        phone_number TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                await self.sqlite_conn.execute("ALTER TABLE students ADD COLUMN tutor_id INTEGER;")
            except Exception:
                pass
            await self.sqlite_conn.commit()
            logger.info("✅ SQLite jadvallari yaratildi.")

    async def disconnect(self):
        if self.pg_pool:
            await self.pg_pool.close()
            logger.info("PostgreSQL ulanishi yopildi.")
        if self.sqlite_conn:
            await self.sqlite_conn.close()
            logger.info("SQLite ulanishi yopildi.")

    def _convert_query(self, query: str) -> str:
        """PostgreSQL ($1, $2) parametrlarini SQLite (?) ga aylantiradi agar SQLite bo'lsa."""
        if self.is_postgres:
            return query
        # PostgreSQL $1, $2 larni ? ga aylantirish
        import re
        return re.sub(r'\$\d+', '?', query)

    def _serialize_args(self, args: tuple) -> list:
        if self.is_postgres:
            # PostgreSQL'da dict/list kelsa json.dumps qilish
            new_args = []
            for a in args:
                if isinstance(a, (dict, list)):
                    new_args.append(json.dumps(a))
                else:
                    new_args.append(a)
            return new_args
        else:
            # SQLite uchun dict/list kelsa json.dumps qilish
            new_args = []
            for a in args:
                if isinstance(a, (dict, list)):
                    new_args.append(json.dumps(a))
                else:
                    new_args.append(a)
            return new_args

    async def execute(self, query: str, *args) -> str:
        q = self._convert_query(query)
        params = self._serialize_args(args)
        if self.is_postgres:
            async with self.pg_pool.acquire() as conn:
                return await conn.execute(q, *params)
        else:
            cursor = await self.sqlite_conn.execute(q, params)
            await self.sqlite_conn.commit()
            return str(cursor.rowcount)

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        q = self._convert_query(query)
        params = self._serialize_args(args)
        if self.is_postgres:
            async with self.pg_pool.acquire() as conn:
                records = await conn.fetch(q, *params)
                return [dict(r) for r in records]
        else:
            cursor = await self.sqlite_conn.execute(q, params)
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        q = self._convert_query(query)
        params = self._serialize_args(args)
        if self.is_postgres:
            async with self.pg_pool.acquire() as conn:
                record = await conn.fetchrow(q, *params)
                return dict(record) if record else None
        else:
            cursor = await self.sqlite_conn.execute(q, params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchval(self, query: str, *args) -> Any:
        q = self._convert_query(query)
        params = self._serialize_args(args)
        if self.is_postgres:
            async with self.pg_pool.acquire() as conn:
                return await conn.fetchval(q, *params)
        else:
            cursor = await self.sqlite_conn.execute(q, params)
            row = await cursor.fetchone()
            return row[0] if row else None


db = DatabaseManager()
