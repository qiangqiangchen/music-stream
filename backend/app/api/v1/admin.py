"""Admin analytics endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger  # 添加这行

from app.core.database import get_db
from app.models.track import Track
from app.models.event import Event, EventType
from app.models.user import User
from app.api.deps import get_current_admin_user

router = APIRouter()

@router.get("/stats/overview")
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get system overview statistics."""

    # 总曲目数
    tracks_result = await db.execute(
        select(func.count()).select_from(Track).where(Track.is_valid == True)
    )
    total_tracks = tracks_result.scalar() or 0

    # 总用户数
    users_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)
    )
    total_users = users_result.scalar() or 0

    # 总播放量
    plays_result = await db.execute(
        select(func.count()).select_from(Event).where(Event.type == 'play_start')
    )
    total_plays = plays_result.scalar() or 0

    # 今日播放量
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_plays_result = await db.execute(
        select(func.count()).select_from(Event).where(
            Event.type == 'play_start',
            Event.ts >= today_start
        )
    )
    today_plays = today_plays_result.scalar() or 0

    logger.info(f"Stats: tracks={total_tracks}, users={total_users}, plays={total_plays}, today={today_plays}")

    return {
        "total_tracks": total_tracks,
        "total_users": total_users,
        "total_plays": total_plays,
        "today_plays": today_plays
    }


@router.get("/stats/top-tracks")
async def get_top_tracks(
    period: str = Query("7d", regex="^(1d|7d|30d|all)$"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get top played tracks."""

    # 计算时间范围
    now = datetime.utcnow()
    if period == "1d":
        start_date = now - timedelta(days=1)
    elif period == "7d":
        start_date = now - timedelta(days=7)
    elif period == "30d":
        start_date = now - timedelta(days=30)
    else:
        start_date = datetime(1970, 1, 1)

    # 查询热门曲目
    query = select(
        Track.id,
        Track.title,
        Track.artist,
        Track.album,
        func.count(Event.id).label('play_count')
    ).join(
        Event, Event.track_id == Track.id
    ).where(
        Event.type == 'play_start',
        Event.ts >= start_date,
        Track.is_valid == True
    ).group_by(
        Track.id, Track.title, Track.artist, Track.album
    ).order_by(
        func.count(Event.id).desc()
    ).limit(limit)

    result = await db.execute(query)
    tracks = []
    for row in result:
        tracks.append({
            "id": row.id,
            "title": row.title,
            "artist": row.artist,
            "album": row.album,
            "play_count": row.play_count
        })

    logger.info(f"Top tracks for period {period}: {len(tracks)} results")

    return {
        "period": period,
        "tracks": tracks
    }


@router.get("/stats/listening-trend")
async def get_listening_trend(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get daily listening trend."""

    trend_data = []

    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date + timedelta(days=1), datetime.min.time())

        # 当日播放次数
        plays_result = await db.execute(
            select(func.count()).select_from(Event).where(
                and_(
                    Event.type == 'play_start',
                    Event.ts >= day_start,
                    Event.ts < day_end
                )
            )
        )
        plays = plays_result.scalar() or 0

        # 当日独立用户数
        users_result = await db.execute(
            select(func.count(func.distinct(Event.user_id))).select_from(Event).where(
                and_(
                    Event.type == 'play_start',
                    Event.ts >= day_start,
                    Event.ts < day_end
                )
            )
        )
        unique_users = users_result.scalar() or 0

        trend_data.append({
            "date": date.isoformat(),
            "plays": plays,
            "unique_users": unique_users
        })

    return {
        "days": days,
        "data": list(reversed(trend_data))
    }


@router.get("/stats/recent-activity")
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get recent playback activity."""

    query = select(
        Event.ts,
        Event.type,
        User.username,
        Track.title,
        Track.artist
    ).join(
        User, Event.user_id == User.id
    ).join(
        Track, Event.track_id == Track.id, isouter=True
    ).order_by(
        Event.ts.desc()
    ).limit(limit)

    result = await db.execute(query)
    activities = []
    for row in result:
        activities.append({
            "timestamp": row.ts.isoformat(),
            "type": row.type,
            "username": row.username,
            "track": f"{row.artist} - {row.title}" if row.title else None
        })

    return {
        "activities": activities
    }


@router.get("/security/login-attempts")
async def get_login_attempts(
        limit: int = Query(50, ge=1, le=200),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_admin_user)
):
    """Get recent login attempts (admin only)."""
    from app.models.login_attempt import LoginAttempt

    result = await db.execute(
        select(LoginAttempt).order_by(LoginAttempt.attempted_at.desc()).limit(limit)
    )
    attempts = result.scalars().all()

    return [
        {
            "id": a.id,
            "username": a.username,
            "ip": a.ip,
            "success": a.success,
            "attempted_at": a.attempted_at.isoformat(),
            "user_agent": a.user_agent
        }
        for a in attempts
    ]