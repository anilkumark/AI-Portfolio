"""Centralized, validated application settings."""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings loads .env into `settings` below but never touches real
# os.environ — libraries that read env vars directly (LangChain/LangSmith
# tracing) need this too.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int

    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"


settings = Settings()
