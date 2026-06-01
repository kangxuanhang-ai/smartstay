import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.deps import require_role
from app.core.security import create_access_token, create_refresh_token
from app.models.guest import Guest
from app.aliyun.face import (
    detect_face,
    compare_face,
    detect_living_face,
    add_face,
    search_face,
)
from app.core.config import settings

router = APIRouter(prefix="/api/face", tags=["face"])


@router.post("/detect")
async def detect_face_endpoint(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = detect_face(image_bytes)
    data = result.get("data", {})
    face_count = len(data.get("faceCount", [])) if data else 0
    return {"face_count": face_count, "quality_ok": face_count > 0}


@router.post("/verify")
async def verify_face(
    id_card_image: UploadFile = File(...),
    live_image: UploadFile = File(...),
):
    id_card_bytes = await id_card_image.read()
    live_bytes = await live_image.read()
    result = compare_face(id_card_bytes, live_bytes)
    data = result.get("data", {})
    confidence = (data.get("confidence", 0) if data else 0) / 100.0
    return {"matched": confidence >= 0.8, "confidence": confidence}


@router.post("/register")
async def register_face(
    guest_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("front_desk")),
):
    image_bytes = await file.read()
    result = add_face(settings.ALIYUN_FACE_DB_NAME, guest_id, image_bytes)
    data = result.get("data", {})
    face_id = (data.get("faceId", [])[0] if data and data.get("faceId") else None)
    if not face_id:
        raise HTTPException(status_code=500, detail="人脸注册失败")
    stmt = select(Guest).where(Guest.id == uuid.UUID(guest_id))
    result_db = await db.execute(stmt)
    guest = result_db.scalar_one_or_none()
    if guest:
        guest.face_id = face_id
        guest.face_registered = True
        db.add(guest)
        await db.commit()
    return {"success": True, "face_id": face_id}


@router.post("/search")
async def search_face_login(file: UploadFile = File(...)):
    image_bytes = await file.read()
    # 1. 活体检测
    living_result = detect_living_face(image_bytes)
    living_data = living_result.get("data", {})
    if not living_data or living_data.get("confidence", 0) < 0.5:
        raise HTTPException(status_code=400, detail="活体检测未通过")
    # 2. 人脸搜索
    search_result = search_face(settings.ALIYUN_FACE_DB_NAME, image_bytes)
    search_data = search_result.get("data", {})
    match_list = search_data.get("matchList", []) if search_data else []
    if not match_list:
        raise HTTPException(status_code=404, detail="未找到匹配的人脸，请先到前台登记入住")
    best_match = match_list[0]
    confidence = best_match.get("confidence", 0) / 100.0
    if confidence < 0.85:
        raise HTTPException(status_code=400, detail="人脸匹配度不足，请重试")
    entity_id = best_match.get("entityId")
    # 3. 签发 JWT
    token_data = {"sub": entity_id, "role": "guest", "user_type": "guest"}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {
        "success": True,
        "guest_id": entity_id,
        "confidence": confidence,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
