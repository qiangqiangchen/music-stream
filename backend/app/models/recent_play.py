"""Recent play model."""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class RecentPlay(SQLModel, table=True):
    __tablename__ = "recent_plays"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    track_id: int = Field(foreign_key="tracks.id", index=True)
    played_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    position_ms: Optional[int] = None  # 播放到的位置