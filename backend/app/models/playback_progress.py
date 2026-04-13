"""Playback progress model."""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class PlaybackProgress(SQLModel, table=True):
    __tablename__ = "playback_progress"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    track_id: int = Field(foreign_key="tracks.id", index=True)
    position_ms: int = Field(default=0)  # 播放到的毫秒数
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        unique_together = ["user_id", "track_id"]