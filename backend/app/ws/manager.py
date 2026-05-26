import uuid
from fastapi import WebSocket, WebSocketDisconnect
from app.core.security import decode_token
from app.core.database import async_session
from app.models.order import Order
from sqlmodel import select


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}
        self._roles: dict[str, str] = {}

    async def connect(self, websocket: WebSocket, token: str) -> tuple[str, str] | None:
        """校验 JWT，建立连接。返回 (user_id, role) 或 None（认证失败）"""
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                await websocket.close(code=4001, reason="Invalid token type")
                return None
            user_id = payload.get("sub")
            role = payload.get("role", "")
            if not user_id:
                await websocket.close(code=4001, reason="Invalid token")
                return None
        except Exception:
            await websocket.close(code=4001, reason="Invalid token")
            return None

        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)
        self._roles[user_id] = role
        return user_id, role

    def disconnect(self, user_id: str, websocket: WebSocket):
        """移除连接"""
        if user_id in self._connections:
            self._connections[user_id] = [ws for ws in self._connections[user_id] if ws is not websocket]
            if not self._connections[user_id]:
                del self._connections[user_id]
                self._roles.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict):
        """向指定用户的所有连接推送消息"""
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def broadcast_to_role(self, role: str, message: dict):
        """向指定角色的所有用户广播"""
        for uid, r in self._roles.items():
            if r == role:
                await self.send_to_user(uid, message)

    async def broadcast_biz(self, message: dict):
        """向所有 B 端用户广播（front_desk + manager + admin）"""
        for uid, r in self._roles.items():
            if r in ("front_desk", "manager", "admin"):
                await self.send_to_user(uid, message)

    async def send_to_room(self, room_id: str, message: dict):
        """向指定房间的住客推送消息（通过 orders 表查找当前入住的 user_id）"""
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(Order.user_id).where(
                        Order.room_id == uuid.UUID(room_id),
                        Order.status == "checked_in",
                    )
                )
                user_id = result.scalar_one_or_none()
                if user_id:
                    await self.send_to_user(str(user_id), message)
        except Exception:
            pass


manager = ConnectionManager()
