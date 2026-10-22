"""Runtime settings, read from environment variables prefixed with SYNCSIGHT_."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SYNCSIGHT_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://syncsight:syncsight@localhost:5433/syncsight"


@lru_cache
def get_settings() -> Settings:
    return Settings()
