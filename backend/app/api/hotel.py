import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from sqlmodel import select

from app.core.database import get_db
from app.models.hotel import HotelInfo, Facility

router = APIRouter(prefix="/api/hotel", tags=["hotel"])


@router.get("/info")
async def get_hotel_info(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HotelInfo).limit(1))
    info = result.scalar_one_or_none()
    if not info:
        raise HTTPException(status_code=404, detail="Hotel info not found")
    return {
        "id": str(info.id),
        "name": info.name,
        "address": info.address,
        "phone": info.phone,
        "map_lat": info.map_lat,
        "map_lng": info.map_lng,
        "description": info.description,
        "banner_images": info.banner_images or [],
    }


@router.get("/facilities")
async def get_facilities(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Facility).order_by(Facility.type))
    facilities = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "name": f.name,
            "type": f.type,
            "open_time": f.open_time.strftime("%H:%M") if f.open_time else None,
            "close_time": f.close_time.strftime("%H:%M") if f.close_time else None,
            "is_free": f.is_free,
            "price": f.price,
            "dynamic_tip": f.dynamic_tip,
        }
        for f in facilities
    ]


@router.get("/facilities/{facility_id}")
async def get_facility_detail(facility_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Facility).where(Facility.id == uuid.UUID(facility_id)))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Facility not found")
    return {
        "id": str(f.id),
        "name": f.name,
        "type": f.type,
        "open_time": f.open_time.strftime("%H:%M") if f.open_time else None,
        "close_time": f.close_time.strftime("%H:%M") if f.close_time else None,
        "is_free": f.is_free,
        "price": f.price,
        "dynamic_tip": f.dynamic_tip,
    }
