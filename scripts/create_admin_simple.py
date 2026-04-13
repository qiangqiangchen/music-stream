"""Create admin user with simple password hash."""
import asyncio
import sys
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from app.core.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from sqlalchemy import select
from loguru import logger


def simple_hash(password: str) -> str:
    """Simple password hash for testing."""
    return hashlib.sha256(password.encode()).hexdigest()


async def create_admin():
    """Create admin user if not exists."""

    # First ensure tables exist
    logger.info("Ensuring database tables exist...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check if admin exists
        result = await db.execute(select(User).where(User.role == UserRole.ADMIN))
        admin = result.scalar_one_or_none()

        if admin:
            logger.info(f"Admin user already exists: {admin.username}")
            # Update password for existing admin
            admin.password_hash = simple_hash("admin123")
            await db.commit()
            logger.info("Admin password updated to: admin123")
            return

        # Create admin user
        admin = User(
            email="admin@example.com",
            username="admin",
            display_name="Administrator",
            password_hash=simple_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True
        )

        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        logger.success("Admin user created successfully!")
        logger.info("Username: admin")
        logger.info("Password: admin123")
        logger.warning("Please change the password after first login!")


if __name__ == "__main__":
    asyncio.run(create_admin())