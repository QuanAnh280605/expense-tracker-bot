from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    telegram_bot_token: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    db_path: str = ""
    reminder_hour: int = 22
    reminder_minute: int = 0

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("db_path", mode="after")
    @classmethod
    def resolve_db_path(cls, v: str) -> str:
        app_data = Path("/app/data")
        # Khi chạy trong Docker container có mount volume /app/data
        if app_data.is_dir():
            if not v or not Path(v).is_absolute() or v in ("expense_tracker.db", "/app/expense_tracker.db"):
                filename = Path(v).name if v and v != "/app/expense_tracker.db" else "expense_tracker.db"
                return (app_data / filename).as_posix()
            return v

        # Môi trường local development
        if not v or v == "expense_tracker.db":
            return str(BASE_DIR / "expense_tracker.db")
        if not Path(v).is_absolute():
            return str(BASE_DIR / v)
        return v

settings = Settings()
