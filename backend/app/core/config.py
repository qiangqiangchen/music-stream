"""Application configuration."""
from typing import Optional

from loguru import logger
from pydantic_settings import BaseSettings  # 修正导入
from pathlib import Path


class Settings(BaseSettings):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info(f"JWT_SECRET (first 10 chars): {self.JWT_SECRET[:10]}...")

    # Application
    APP_NAME: str = "Music Stream"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MEDIA_DIR: Path = BASE_DIR / "media"
    DATA_DIR: Path = BASE_DIR / "data"
    CACHE_DIR: Path = DATA_DIR / "cache"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # Security
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # Features
    ALLOW_REGISTRATION: bool = True
    ALLOW_DOWNLOAD: bool = True

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5500"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外的环境变量


settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
