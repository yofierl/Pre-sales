"""应用配置。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "sqlite:///./data/shouqian.db"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    storage_path: str = "storage"
    project_name: str = "售前知识 Agent"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()