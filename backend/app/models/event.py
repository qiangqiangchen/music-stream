"""Event model for analytics."""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
import enum

class EventType(str, enum.Enum):
    PLAY_START = "play_start"
    PLAY_END = "play_end"
    PAUSE = "pause"
    SEEK = "seek"
    HEARTBEAT = "heartbeat"
    DOWNLOAD = "download"

class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    track_id: Optional[int] = Field(default=None, foreign_key="tracks.id", index=True)
    type: str = Field(index=True)  # 改为 str 类型
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    pos_ms: Optional[int] = None
    session_id: Optional[str] = Field(default=None, index=True)
    user_agent: Optional[str] = None
    ip: Optional[str] = None