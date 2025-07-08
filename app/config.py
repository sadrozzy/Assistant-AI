from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@host:port/db_name"
    ALEMBIC_DATABASE_URL: str = "postgresql+asyncpg://user:pass@host:port/db_name"
    TELEGRAM_TOKEN: str = "YOUR_TELEGRAM_TOKEN"
    GOOGLE_CLIENT_ID: str = "YOUR_GOOGLE_CLIENT_ID"
    GOOGLE_CLIENT_SECRET: str = "YOUR_GOOGLE_CLIENT_SECRET"

    DEBUG: bool = True


settings = Settings()
