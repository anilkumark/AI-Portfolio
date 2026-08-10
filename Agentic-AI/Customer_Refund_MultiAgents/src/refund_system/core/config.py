"""Centralized, validated application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int

    openai_api_key: str
    reviewer_email: str
    api_base_url: str = "http://localhost:8000"


settings = Settings()
