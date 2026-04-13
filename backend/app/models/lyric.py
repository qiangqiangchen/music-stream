"""Lyric model."""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON
from enum import Enum


class LyricType(str, Enum):
    SYNCED = "synced"
    UNSYNCED = "unsynced"


class LyricSource(str, Enum):
    FILE = "file"
    EMBEDDED = "embedded"


class Lyric(SQLModel, table=True):
    __tablename__ = "lyrics"

    id: Optional[int] = Field(default=None, primary_key=True)
    track_id: int = Field(foreign_key="tracks.id", unique=True, index=True)
    type: LyricType
    source: LyricSource
    lrc_text: Optional[str] = None
    json_payload: list = Field(default=[], sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)