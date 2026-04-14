# backend/app/services/chat_manager.py
from typing import Dict
from fastapi import WebSocket
from datetime import datetime
from loguru import logger

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.user_info: Dict[int, dict] = {}
        self.message_history: list = []
        self.max_history = 50

    async def connect(self, websocket: WebSocket, user_id: int, username: str, role: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_info[user_id] = {"username": username, "role": role}
        await self.broadcast_system_message(f"{username} 加入了聊天室")
        await self.broadcast_user_list()
        logger.info(f"User {username} connected to chat")

    async def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            username = self.user_info[user_id]["username"]
            del self.active_connections[user_id]
            del self.user_info[user_id]
            await self.broadcast_system_message(f"{username} 离开了聊天室")
            await self.broadcast_user_list()

    async def send_message(self, user_id: int, content: str):
        if user_id not in self.user_info:
            return
        user = self.user_info[user_id]
        message = {
            "type": "chat",
            "user_id": user_id,
            "username": user["username"],
            "role": user["role"],
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        await self.broadcast(message)

    async def broadcast(self, message: dict):
        disconnected = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(user_id)
        for user_id in disconnected:
            await self.disconnect(user_id)

    async def broadcast_system_message(self, content: str):
        await self.broadcast({
            "type": "system",
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def broadcast_user_list(self):
        users = [
            {"user_id": uid, "username": info["username"], "role": info["role"]}
            for uid, info in self.user_info.items()
        ]
        await self.broadcast({
            "type": "user_list",
            "users": users,
            "count": len(users)
        })

manager = ConnectionManager()