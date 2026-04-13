"""Initialize database and create tables."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from app.core.database import init_db
from loguru import logger

async def main():
    """Initialize database."""
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database tables created successfully!")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())