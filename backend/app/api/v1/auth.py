"""Authentication endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import hashlib

from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token,
    decode_token, get_password_hash, verify_password
)
from app.core.config import settings
from app.models.user import User, UserRole
from app.schemas.auth import (
    UserCreate, UserLogin, TokenResponse,
    RefreshTokenRequest, UserResponse
)
from app.api.deps import get_current_active_user
from app.core.limiter import limiter

from app.models.login_attempt import LoginAttempt

router = APIRouter()


def simple_hash(password: str) -> str:
    """Simple password hash for compatibility."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_simple_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password with fallback."""
    # Try bcrypt/pbkdf2 first
    if verify_password(plain_password, hashed_password):
        return True
    # Try simple hash
    return simple_hash(plain_password) == hashed_password


@router.post("/register", response_model=UserResponse)
@limiter.limit("3/minute")  # 每分钟最多 3 次注册
async def register(
        request: Request,
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    if not settings.ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled"
        )

    # Check if user exists
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) |
            (User.username == user_data.username)
        )
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )

    # Create user
    try:
        password_hash = get_password_hash(user_data.password)
    except:
        password_hash = simple_hash(user_data.password)

    user = User(
        email=user_data.email,
        username=user_data.username,
        display_name=user_data.display_name or user_data.username,
        password_hash=password_hash,
        role=UserRole.USER
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"New user registered: {user.username}")

    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # 每分钟最多 5 次登录尝试
async def login(
        request: Request,
        credentials: UserLogin,
        db: AsyncSession = Depends(get_db)
):
    """Login and get tokens."""
    from app.models.login_attempt import LoginAttempt

    # 记录登录尝试的辅助函数
    async def log_attempt(success: bool):
        attempt = LoginAttempt(
            username=credentials.username,
            ip=request.client.host if request.client else None,
            success=success,
            user_agent=request.headers.get("user-agent")
        )
        db.add(attempt)
        await db.commit()

    # Find user by username
    result = await db.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Login attempt for non-existent user: {credentials.username}")
        await log_attempt(False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Verify password
    if not verify_simple_password(credentials.password, user.password_hash):
        logger.warning(f"Invalid password for user: {credentials.username}")
        await log_attempt(False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if not user.is_active:
        logger.warning(f"Inactive user login attempt: {credentials.username}")
        await log_attempt(False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # 登录成功
    await log_attempt(True)

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # Create tokens
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.info(f"User logged in: {user.username}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
        request: Request,
        refresh_request: RefreshTokenRequest,
        db: AsyncSession = Depends(get_db)
):
    """Refresh access token."""
    payload = decode_token(refresh_request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new tokens
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
        current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return current_user


@router.post("/logout")
async def logout(
        current_user: User = Depends(get_current_active_user)
):
    """Logout (client should discard tokens)."""
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Successfully logged out"}
