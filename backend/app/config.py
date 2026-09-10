from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema Barbearia API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://barbearia:barbearia@localhost:5432/barbearia"
    frontend_origin: str = "http://localhost:5173"
    barbershop_timezone: str = "America/Fortaleza"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
