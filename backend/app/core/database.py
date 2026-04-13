"""Database configuration and session management."""
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from app.core.config import settings
import os

# Convert SQLite URL to async version
database_url = settings.DATABASE_URL
if database_url.startswith("sqlite:///"):
    # Windows 路径处理
    db_path = database_url.replace("sqlite:///", "")
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    database_url = f"sqlite+aiosqlite:///{db_path}"

async_engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    future=True
)

# Session factory
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Sync engine for Alembic
sync_database_url = settings.DATABASE_URL.replace("+aiosqlite", "")
sync_engine = create_engine(
    sync_database_url,
    echo=settings.DEBUG
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)