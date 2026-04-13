"""Test login functionality."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import verify_password, get_password_hash
from sqlalchemy import select

async def test_login():
    """Test if admin user exists and password works."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()

        if not user:
            print("Admin user not found!")
            return

        print(f"Found user: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Is active: {user.is_active}")
        print(f"Password hash: {user.password_hash[:20]}...")

        # Test password
        test_password = "admin123"
        is_valid = verify_password(test_password, user.password_hash)
        print(f"\nPassword '{test_password}' is valid: {is_valid}")

        if not is_valid:
            # Reset password
            print("\nResetting admin password...")
            user.password_hash = get_password_hash("admin123")
            await db.commit()
            print("Password reset to: admin123")

if __name__ == "__main__":
    asyncio.run(test_login())