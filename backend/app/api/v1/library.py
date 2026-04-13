"""Library management endpoints."""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.scanner import MediaScanner
from app.api.deps import get_current_admin_user
from app.models.user import User

router = APIRouter()


@router.post("/scan")
async def scan_library(
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Scan media library for new/updated files (admin only)."""
    scanner = MediaScanner(db)

    # Run scan in background
    background_tasks.add_task(scanner.scan_directory)

    return {"message": "Scan started"}