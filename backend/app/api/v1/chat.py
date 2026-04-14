# backend/app/api/v1/chat.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.chat_manager import manager

router = APIRouter()


@router.get("/test-chat")
async def test_chat():
    return {"message": "Chat router is working!"}

@router.websocket("/ws")  # 注意：这里只写 /ws
async def websocket_endpoint(
        websocket: WebSocket,
        token: str = Query(...),
        db: AsyncSession = Depends(get_db)
):
    logger.info("=" * 50)
    logger.info(f"[chat.py] WebSocket connection attempt")
    logger.info(f"[chat.py] Token: {token[:50]}...")

    user = None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            await websocket.close(code=4001)
            return

        logger.info(f"[chat.py] ✅ Accepted: {user.username}")
        await manager.connect(websocket, user.id, user.username, user.role.value)

        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat":
                await manager.send_message(user.id, data.get("content", ""))
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"[chat.py] Disconnected: {user.username if user else 'unknown'}")
        if user:
            await manager.disconnect(user.id)
    except JWTError as e:
        logger.error(f"[chat.py] JWT error: {e}")
        await websocket.close(code=4001)
    except Exception as e:
        logger.error(f"[chat.py] Error: {e}")
        if user:
            await manager.disconnect(user.id)