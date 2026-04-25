"""Centralized config — all secrets come from env vars, never hardcoded."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # AI provider
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # Optional database connections for live analysis
    db_postgres_uri: Optional[str] = None
    db_mysql_uri: Optional[str] = None
    db_sqlserver_uri: Optional[str] = None
    db_oracle_uri: Optional[str] = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
