import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://bot_user:bot_password@localhost:5432/bot_db")
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")

    # Настройки API
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://example.ru")
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))

    # Настройки SQLAlchemy
    SQLALCHEMY_DATABASE_URI: str = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
