"""Lyric schemas."""
from typing import Optional, List
from pydantic import BaseModel
from app.models.lyric import LyricType, LyricSource


class LyricLine(BaseModel):
    time_ms: Optional[int] = None
    text: str


class LyricResponse(BaseModel):
    track_id: int
    type: LyricType
    source: LyricSource
    lrc_text: Optional[str] = None
    lines: List[LyricLine] = []
    offset_ms: int = 0


class LyricOffsetRequest(BaseModel):
    offset_ms: int