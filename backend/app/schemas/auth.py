"""Authentication schemas."""
import re
from typing import Optional
from pydantic import BaseModel, EmailStr, validator, ConfigDict, Field
from app.models.user import UserRole
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str
    display_name: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    display_name: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=8, max_length=72)

    @validator('username')
    def username_valid(cls, v):
        # 只允许字母、数字、下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

    @validator('password')
    def password_strength(cls, v):
        # 至少包含一个字母和一个数字
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含至少一个字母')
        if not re.search(r'\d', v):
            raise ValueError('密码必须包含至少一个数字')
        return v

    @validator('display_name')
    def display_name_valid(cls, v):
        if v:
            # 移除危险字符
            v = re.sub(r'[<>"\']', '', v)
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)