"""Favorites endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.core.database import get_db
from app.models.favorite import Favorite
from app.models.track import Track
from app.models.user import User
from app.api.deps import get_current_active_user
from loguru import logger

router = APIRouter()


@router.get("")
async def get_favorites(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get user's favorite tracks."""

    # 查询收藏的歌曲
    result = await db.execute(
        select(Favorite, Track).join(
            Track, Favorite.track_id == Track.id
        ).where(
            and_(
                Favorite.user_id == current_user.id,
                Track.is_valid == True
            )
        ).order_by(Favorite.created_at.desc())
    )

    favorites = []
    for fav, track in result:
        favorites.append({
            "id": track.id,
            "title": track.title,
            "artist": track.artist,
            "album": track.album,
            "duration": track.duration,
            "format": track.format,
            "favorited_at": fav.created_at.isoformat()
        })

    return favorites


@router.get("/check/{track_id}")
async def check_favorite(
        track_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Check if track is favorited."""

    result = await db.execute(
        select(Favorite).where(
            and_(
                Favorite.user_id == current_user.id,
                Favorite.track_id == track_id
            )
        )
    )
    favorite = result.scalar_one_or_none()

    return {"is_favorited": favorite is not None}


@router.post("/{track_id}")
async def add_favorite(
        track_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Add track to favorites."""

    # 验证歌曲存在
    track_result = await db.execute(
        select(Track).where(Track.id == track_id, Track.is_valid == True)
    )
    track = track_result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # 检查是否已收藏
    existing = await db.execute(
        select(Favorite).where(
            and_(
                Favorite.user_id == current_user.id,
                Favorite.track_id == track_id
            )
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Already favorited"}

    # 添加收藏
    favorite = Favorite(user_id=current_user.id, track_id=track_id)
    db.add(favorite)
    await db.commit()

    logger.info(f"User {current_user.username} favorited track {track_id}")

    return {"message": "Added to favorites"}


@router.delete("/{track_id}")
async def remove_favorite(
        track_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Remove track from favorites."""

    await db.execute(
        delete(Favorite).where(
            and_(
                Favorite.user_id == current_user.id,
                Favorite.track_id == track_id
            )
        )
    )
    await db.commit()

    logger.info(f"User {current_user.username} unfavorited track {track_id}")

    return {"message": "Removed from favorites"}