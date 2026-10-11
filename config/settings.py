import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    telegram_bot_token: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    db_path: str = str(BASE_DIR / "expense_tracker.db")
    reminder_hour: int = 22
    reminder_minute: int = 0

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
