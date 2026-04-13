"""Analytics endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.event import Event
from app.api.deps import get_current_active_user
from app.models.user import User
from loguru import logger

router = APIRouter()


class EventCreate(BaseModel):
    type: str
    track_id: Optional[int] = None
    pos_ms: Optional[int] = None
    session_id: str


@router.post("/events")
async def create_event(
        event_data: EventCreate,
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Record an analytics event."""

    # 记录事件
    event = Event(
        user_id=current_user.id,
        track_id=event_data.track_id,
        type=event_data.type,
        pos_ms=event_data.pos_ms,
        session_id=event_data.session_id,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None
    )

    db.add(event)

    # 当事件类型为 play_start 时，记录最近播放
    if event_data.type == 'play_start' and event_data.track_id:
        from app.models.recent_play import RecentPlay

        # 记录新的播放
        recent = RecentPlay(
            user_id=current_user.id,
            track_id=event_data.track_id,
            position_ms=event_data.pos_ms
        )
        db.add(recent)
        logger.debug(f"Recent play recorded: user={current_user.id}, track={event_data.track_id}")

    await db.commit()

    # 异步清理超过 30 天的最近播放记录（在 commit 之后）
    if event_data.type == 'play_start' and event_data.track_id:
        try:
            from app.models.recent_play import RecentPlay
            from datetime import datetime, timedelta
            from sqlalchemy import delete

            cutoff = datetime.utcnow() - timedelta(days=30)
            await db.execute(
                delete(RecentPlay).where(
                    RecentPlay.user_id == current_user.id,
                    RecentPlay.played_at < cutoff
                )
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to cleanup old recent plays: {e}")

    logger.debug(f"Event recorded: {event_data.type} for track {event_data.track_id}")

    return {"status": "ok"}