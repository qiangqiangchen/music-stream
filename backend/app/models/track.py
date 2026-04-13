"""Track model."""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Track(SQLModel, table=True):
    __tablename__ = "tracks"

    id: Optional[int] = Field(default=None, primary_key=True)
    path: str = Field(unique=True, index=True)
    title: str = Field(index=True)
    album: Optional[str] = Field(default=None, index=True)
    album_artist: Optional[str] = Field(default=None, index=True)
    artist: Optional[str] = Field(default=None, index=True)
    genre: Optional[str] = Field(default=None, index=True)
    year: Optional[int] = None
    disc: Optional[int] = None
    track_no: Optional[int] = None
    duration: Optional[float] = None  # seconds
    bitrate: Optional[int] = None  # bps
    sample_rate: Optional[int] = None  # Hz
    format: Optional[str] = None  # mp3, flac, etc.
    size: Optional[int] = None  # bytes
    mime_type: Optional[str] = None
    has_embedded_cover: bool = Field(default=False)
    lyrics_offset_ms: int = Field(default=0)
    last_modified_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    checksum: Optional[str] = None
    is_valid: bool = Field(default=True, index=True)