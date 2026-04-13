"""Track schemas."""
from typing import Optional
from pydantic import BaseModel


class TrackBase(BaseModel):
    title: str
    album: Optional[str] = None
    album_artist: Optional[str] = None
    artist: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[int] = None
    track_no: Optional[int] = None
    duration: Optional[float] = None


class TrackResponse(TrackBase):
    id: int
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    format: Optional[str] = None
    size: Optional[int] = None
    has_embedded_cover: bool
    is_valid: bool

    class Config:
        from_attributes = True


class TrackListResponse(BaseModel):
    items: list[TrackResponse]
    total: int
    page: int
    page_size: int
    total_pages: int