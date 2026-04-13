"""Recent plays endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.recent_play import RecentPlay
from app.models.track import Track
from app.models.user import User
from app.api.deps import get_current_active_user
from loguru import logger

from sqlalchemy import select, desc, delete, func
from fastapi import HTTPException


router = APIRouter()


class RecentPlayCreate(BaseModel):
    track_id: int
    position_ms: Optional[int] = None


@router.get("")
async def get_recent_plays(
        limit: int = Query(50, ge=1, le=200),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get user's recently played tracks."""

    # 查询最近播放（去重，保留每个歌曲最新的播放记录）
    subquery = select(
        RecentPlay.track_id,
        func.max(RecentPlay.played_at).label('latest_played')
    ).where(
        RecentPlay.user_id == current_user.id
    ).group_by(RecentPlay.track_id).subquery()

    query = select(
        RecentPlay, Track
    ).join(
        Track, RecentPlay.track_id == Track.id
    ).join(
        subquery,
        (RecentPlay.track_id == subquery.c.track_id) &
        (RecentPlay.played_at == subquery.c.latest_played)
    ).where(
        RecentPlay.user_id == current_user.id,
        Track.is_valid == True
    ).order_by(desc(RecentPlay.played_at)).limit(limit)

    result = await db.execute(query)

    recent_plays = []
    for recent, track in result:
        beijing_time = recent.played_at + timedelta(hours=8)
        recent_plays.append({
            "id": track.id,
            "title": track.title,
            "artist": track.artist,
            "album": track.album,
            "duration": track.duration,
            "format": track.format,
            "played_at": beijing_time.isoformat(),
            "position_ms": recent.position_ms
        })

    return recent_plays


@router.post("")
async def add_recent_play(
        data: RecentPlayCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Record a track play."""

    # 验证歌曲存在
    track_result = await db.execute(
        select(Track).where(Track.id == data.track_id, Track.is_valid == True)
    )
    track = track_result.scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # 创建记录
    recent = RecentPlay(
        user_id=current_user.id,
        track_id=data.track_id,
        position_ms=data.position_ms
    )

    db.add(recent)
    await db.commit()

    # 清理超过 30 天的记录（异步处理，不阻塞响应）
    await cleanup_old_records(db, current_user.id)

    return {"message": "Recorded"}

@router.delete("/clear")
async def clear_recent_plays(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Clear all recent plays."""
    from sqlalchemy import delete

    await db.execute(
        delete(RecentPlay).where(RecentPlay.user_id == current_user.id)
    )
    await db.commit()

    return {"message": "Cleared"}


@router.delete("/{track_id}")
async def remove_from_recent(
        track_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Remove a track from recent plays."""
    from sqlalchemy import delete

    await db.execute(
        delete(RecentPlay).where(
            RecentPlay.user_id == current_user.id,
            RecentPlay.track_id == track_id
        )
    )
    await db.commit()

    return {"message": "Removed"}




async def cleanup_old_records(db: AsyncSession, user_id: int):
    """Delete records older than 30 days."""
    cutoff = datetime.utcnow() - timedelta(days=30)

    await db.execute(
        delete(RecentPlay).where(
            RecentPlay.user_id == user_id,
            RecentPlay.played_at < cutoff
        )
    )
    await db.commit()