"""Centralized, validated application settings."""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings loads .env into `settings` below but never touches real
# os.environ — libraries that read env vars directly (LangChain/LangSmith's
# tracing) need this too.
load_dotenv()


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
