import uuid
from datetime import time
from sqlmodel import select

from app.core.database import async_session
from app.core.security import get_password_hash
from app.models.user import User
from app.models.room import Room
from app.models.hotel import HotelInfo, Facility

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


async def seed_hotel_info():
    async with async_session() as db:
        result = await db.execute(select(HotelInfo))
        if result.scalar_one_or_none():
            return
        info = HotelInfo(
            name="智宿云酒店",
            address="北京市朝阳区建国路88号SOHO现代城",
            phone="13800000002",
            map_lat=39.9042,
            map_lng=116.4074,
            description="智宿云酒店是一家融合AI智能科技与东方美学的高端商务酒店，坐落于北京CBD核心地段。酒店配备24小时AI虚拟管家、无边际泳池、米其林星级餐厅，为每一位住客提供极致的智慧入住体验。",
            banner_images=[
                "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",
                "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=800",
                "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800",
            ],
        )
        db.add(info)
        await db.commit()


async def seed_facilities():
    async with async_session() as db:
        result = await db.execute(select(Facility))
        if result.scalars().first():
            return
        facilities = [
            Facility(name="24H健身房", type="gym", open_time=time(0, 0), close_time=time(23, 59), is_free=True,
                     dynamic_tip={"equipment": "TechnoGym全套器械", "crowd_level": "空闲"}),
            Facility(name="无边际泳池", type="pool", open_time=time(8, 0), close_time=time(22, 0), is_free=True,
                     dynamic_tip={"water_temp": "26°C", "crowd_level": "适中"}),
            Facility(name="中餐厅·悦府", type="restaurant", open_time=time(11, 0), close_time=time(22, 0), is_free=False, price=0,
                     dynamic_tip={"special": "今日推荐：黑松露和牛套餐", "wait_time": "无需等位"}),
            Facility(name="自助洗衣房", type="laundry", open_time=time(0, 0), close_time=time(23, 59), is_free=True,
                     dynamic_tip={"available_machines": "3/5"}),
        ]
        for f in facilities:
            db.add(f)
        await db.commit()
