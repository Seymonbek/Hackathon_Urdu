from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    BOT_TOKEN: str = Field(default="DUMMY_BOT_TOKEN_REPLACE_ME")
    BOT_NAME: str = Field(default="Imkon")
    ADMIN_IDS: List[int] = Field(default_factory=lambda: [123456789])

    # Database
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="imkon_db")
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="postgres_secret_password")
    DATABASE_URL: Optional[str] = None
    
    # SQLite fallback (agar PostgreSQL ulanmasa yoki mahalliy test uchun)
    USE_SQLITE_FALLBACK: bool = Field(default=True)
    SQLITE_PATH: str = Field(default="imkon.db")

    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = Field(default="eu-central-1")
    AWS_S3_BUCKET: str = Field(default="imkon-storage")

    # Business Rules
    DEFAULT_LANGUAGE: str = "uz"
    TIMEZONE: str = "Asia/Tashkent"
    QUIET_HOURS_START: int = 22
    QUIET_HOURS_END: int = 8
    NOTIFICATION_THRESHOLD_SCORE: int = 75

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            parts = [p.strip() for p in v.split(",") if p.strip()]
            return [int(p) for p in parts if p.isdigit()]
        elif isinstance(v, (int, float)):
            return [int(v)]
        return v

    @property
    def postgres_dsn(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
