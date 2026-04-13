"""Login attempt model for security."""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class LoginAttempt(SQLModel, table=True):
    __tablename__ = "login_attempts"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    ip: str = Field(index=True)
    success: bool = Field(default=False)
    attempted_at: datetime = Field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None