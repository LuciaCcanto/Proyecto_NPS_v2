from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "WILEY TECNOLOGY"
    APP_SECRET_KEY: str = "dev-secret-key-change-in-production"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str = "sqlite+aiosqlite:///./nps_platform.db"

    JWT_SECRET_KEY: str = "dev-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 500

    GOOGLE_REVIEW_URL: str = "https://g.page/r/your-business/review"
    TRUSTPILOT_URL: str = "https://www.trustpilot.com/review/yourbusiness.com"

    WHATSAPP_WEBHOOK_SECRET: str = "change-this"
    EMAIL_WEBHOOK_SECRET: str = "change-this"


@lru_cache
def get_settings() -> Settings:
    return Settings()
