"""Favorite model."""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Favorite(SQLModel, table=True):
    __tablename__ = "favorites"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    track_id: int = Field(foreign_key="tracks.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        unique_together = ["user_id", "track_id"]