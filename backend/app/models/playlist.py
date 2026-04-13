"""Playlist models."""
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class Playlist(SQLModel, table=True):
    __tablename__ = "playlists"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_public: bool = Field(default=False)
    cover_track_id: Optional[int] = Field(default=None, foreign_key="tracks.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # 关系
    items: List["PlaylistItem"] = Relationship(back_populates="playlist",
                                               sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class PlaylistItem(SQLModel, table=True):
    __tablename__ = "playlist_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    playlist_id: int = Field(foreign_key="playlists.id", index=True)
    track_id: int = Field(foreign_key="tracks.id")
    position: int = Field(default=0)
    added_at: datetime = Field(default_factory=datetime.utcnow)

    # 关系
    playlist: Optional[Playlist] = Relationship(back_populates="items")
    track: Optional["Track"] = Relationship()