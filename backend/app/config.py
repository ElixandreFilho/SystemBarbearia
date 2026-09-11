from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema Barbearia API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://barbearia:barbearia@localhost:5432/barbearia"
    frontend_origin: str = "http://localhost:5173"
    barbershop_timezone: str = "America/Fortaleza"
    jwt_secret_key: str = "development-only-change-me"
    jwt_access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    refresh_cookie_secure: bool = False
    resend_api_key: str | None = None
    resend_from_email: str = "Barbearia <noreply@example.com>"
    app_base_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
