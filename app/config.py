from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    GEMINI_API_KEY: str = "your_gemini_api_key"
    GEMINI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    ASSEMBLYAI_API_KEY: str = "ASSEMBLYAI_API_KEY"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@host:port/db_name"
    ALEMBIC_DATABASE_URL: str = "postgresql+asyncpg://user:pass@host:port/db_name"
    TELEGRAM_TOKEN: str = "YOUR_TELEGRAM_TOKEN"
    GOOGLE_CLIENT_ID: str = "YOUR_GOOGLE_CLIENT_ID"
    GOOGLE_CLIENT_SECRET: str = "YOUR_GOOGLE_CLIENT_SECRET"
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    ai: AISettings = AISettings()


settings = Settings()
