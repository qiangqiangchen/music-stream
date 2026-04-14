"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys
from pathlib import Path

from app.core.config import settings
from app.core.database import init_db
from app.api import api_router


from app.core.limiter import limiter
from slowapi.errors import RateLimitExceeded
from starlette.websockets import WebSocket

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL
)

# Ensure log directory exists
log_dir = settings.DATA_DIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    log_dir / "app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Music Stream Server...")

    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    logger.info(f"Media directory: {settings.MEDIA_DIR}")
    logger.info(f"Database URL: {settings.DATABASE_URL}")

    yield

    logger.info("Shutting down Music Stream Server...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加限流器状态
app.state.limiter = limiter


# 限流异常处理器
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "请求过于频繁，请稍后再试",
            "retry_after": exc.retry_after
        }
    )


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://*:5500",  # 允许任何来源的 5500 端口
        "http://*:5501",
        "*"  # 开发环境可以暂时允许所有
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全头中间件
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")
from app.api.v1 import chat
app.include_router(chat.router, prefix="/api/v1")
# print("Registered routes:", [route.path for route in app.routes])
print("=" * 50)
print("Registered routes:")
for route in app.routes:
    print(f"  {route.path} - {route.methods if hasattr(route, 'methods') else 'WEBSOCKET'}")
print("=" * 50)

@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}


@app.websocket("/test-ws")
async def test_websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello!")
    await websocket.close()