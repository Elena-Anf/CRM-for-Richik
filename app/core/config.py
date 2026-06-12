from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Grooming CRM"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DB_DRIVER: str = "sqlite"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "grooming_crm"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"

    GOOGLE_SERVICE_ACCOUNT_FILE: Optional[str] = None

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_DRIVER == "sqlite":
            return "sqlite+aiosqlite:///./grooming.db"
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
