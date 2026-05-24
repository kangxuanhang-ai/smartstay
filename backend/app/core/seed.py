import uuid
from sqlmodel import select

from app.core.database import async_session
from app.core.security import get_password_hash
from app.models.user import User
from app.models.room import Room

DEFAULT_USERS = [
    {"id_card": "dianzhang", "phone": "13800000001", "name": "总店长", "role": "manager"},
    {"id_card": "qiantai", "phone": "13800000002", "name": "前台张", "role": "front_desk"},
    {"id_card": "admin", "phone": "13800000003", "name": "管理员", "role": "admin"},
    {"id_card": "100000000000000101", "phone": "13800000101", "name": "住客李", "role": "guest"},
]

DEFAULT_ROOMS = [
    {"room_number": "301", "room_type": "big_bed", "base_price": 30000, "floor": 3},
    {"room_number": "302", "room_type": "big_bed", "base_price": 30000, "floor": 3},
    {"room_number": "303", "room_type": "twin", "base_price": 35000, "floor": 3},
    {"room_number": "304", "room_type": "twin", "base_price": 35000, "floor": 3},
    {"room_number": "305", "room_type": "suite", "base_price": 60000, "floor": 3},
    {"room_number": "401", "room_type": "big_bed", "base_price": 32000, "floor": 4},
    {"room_number": "402", "room_type": "big_bed", "base_price": 32000, "floor": 4},
    {"room_number": "403", "room_type": "twin", "base_price": 37000, "floor": 4},
    {"room_number": "404", "room_type": "suite", "base_price": 66000, "floor": 4},
    {"room_number": "501", "room_type": "suite", "base_price": 72000, "floor": 5},
]


async def seed_default_users():
    async with async_session() as db:
        for u in DEFAULT_USERS:
            result = await db.execute(select(User).where(User.id_card == u["id_card"]))
            if not result.scalar_one_or_none():
                user = User(
                    id_card=u["id_card"],
                    phone=u["phone"],
                    name=u["name"],
                    role=u["role"],
                    hashed_password=get_password_hash("123456"),
                    is_first_login=True,
                )
                db.add(user)
        await db.commit()


async def seed_default_rooms():
    async with async_session() as db:
        for r in DEFAULT_ROOMS:
            result = await db.execute(select(Room).where(Room.room_number == r["room_number"]))
            if not result.scalar_one_or_none():
                room = Room(
                    room_number=r["room_number"],
                    room_type=r["room_type"],
                    base_price=r["base_price"],
                    current_price=r["base_price"],
                    floor=r["floor"],
                    status="vacant",
                )
                db.add(room)
        await db.commit()
