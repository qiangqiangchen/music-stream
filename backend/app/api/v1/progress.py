"""Playback progress endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.playback_progress import PlaybackProgress
from app.models.user import User
from app.api.deps import get_current_active_user
from loguru import logger

router = APIRouter()


class ProgressUpdate(BaseModel):
    position_ms: int


@router.get("/{track_id}")
async def get_progress(
        track_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get saved playback progress for a track."""

    result = await db.execute(
        select(PlaybackProgress).where(
            PlaybackProgress.user_id == current_user.id,
            PlaybackProgress.track_id == track_id
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        return {
            "track_id": track_id,
            "position_ms": progress.position_ms,
            "updated_at": progress.updated_at.isoformat()
        }
    else:
        return {
            "track_id": track_id,
            "position_ms": 0
        }


@router.post("/{track_id}")
async def save_progress(
        track_id: int,
        data: ProgressUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Save playback progress for a track."""

    # 查找现有记录
    result = await db.execute(
        select(PlaybackProgress).where(
            PlaybackProgress.user_id == current_user.id,
            PlaybackProgress.track_id == track_id
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        # 更新现有记录
        progress.position_ms = data.position_ms
        progress.updated_at = datetime.utcnow()
    else:
        # 创建新记录
        progress = PlaybackProgress(
            user_id=current_user.id,
            track_id=track_id,
            position_ms=data.position_ms
        )
        db.add(progress)

    await db.commit()

    return {"message": "Progress saved"}


@router.delete("/{track_id}")
async def clear_progress(
        track_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Clear playback progress for a track."""

    result = await db.execute(
        select(PlaybackProgress).where(
            PlaybackProgress.user_id == current_user.id,
            PlaybackProgress.track_id == track_id
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        await db.delete(progress)
        await db.commit()

    return {"message": "Progress cleared"}