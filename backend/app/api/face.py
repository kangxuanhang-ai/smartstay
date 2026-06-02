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
    add_face_entity,
    add_face,
    search_face,
)
from app.core.config import settings

router = APIRouter(prefix="/api/face", tags=["face"])


@router.post("/detect")
async def detect_face_endpoint(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = detect_face(image_bytes)
    data = result.get("Data") or result.get("data", {})
    face_count = data.get("FaceCount", 0) if data else 0
    return {"face_count": face_count, "quality_ok": face_count > 0}


@router.post("/verify")
async def verify_face(
    id_card_image: UploadFile = File(...),
    live_image: UploadFile = File(...),
):
    id_card_bytes = await id_card_image.read()
    live_bytes = await live_image.read()
    result = compare_face(id_card_bytes, live_bytes)
    data = result.get("Data") or result.get("data", {})
    confidence = (data.get("Confidence", 0) if data else 0)
    return {"matched": confidence >= 80, "confidence": confidence}


@router.post("/register")
async def register_face(
    guest_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("front_desk")),
):
    image_bytes = await file.read()
    # Aliyun EntityId cannot contain dashes, strip them from UUID
    clean_id = guest_id.replace("-", "")
    # 先创建实体（如果已存在则忽略）
    try:
        add_face_entity(settings.ALIYUN_FACE_DB_NAME, clean_id)
    except Exception:
        pass  # 实体已存在，继续添加人脸
    result = add_face(settings.ALIYUN_FACE_DB_NAME, clean_id, image_bytes)
    data = result.get("Data") or result.get("data", {})
    # FaceId is a string from Aliyun AddFace API, not a list
    face_id = data.get("FaceId") if data else None
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
    print(f"[FACE SEARCH] received {len(image_bytes)} bytes")
    # 1. 活体检测
    living_result = detect_living_face(image_bytes)
    print(f"[FACE SEARCH] living result: {living_result}")
    living_data = living_result.get("Data") or living_result.get("data", {})
    # DetectLivingFace 响应: Data.Elements[0].Results[0].{Suggestion, Rate}
    elements = living_data.get("Elements", []) if living_data else []
    living_pass = False
    if elements and elements[0].get("Results", []):
        r = elements[0]["Results"][0]
        living_pass = r.get("Suggestion") == "pass" and (r.get("Rate", 0) or 0) >= 50
        print(f"[FACE SEARCH] liveness: suggestion={r.get('Suggestion')}, rate={r.get('Rate')}, pass={living_pass}")
    else:
        print(f"[FACE SEARCH] liveness: no elements/results, elements={elements}")
    if not living_pass:
        raise HTTPException(status_code=400, detail="活体检测未通过")
    # 2. 人脸搜索
    search_result = search_face(settings.ALIYUN_FACE_DB_NAME, image_bytes)
    print(f"[FACE SEARCH] search result: {search_result}")
    search_data = search_result.get("Data") or search_result.get("data", {})
    match_list = search_data.get("MatchList", []) if search_data else []
    print(f"[FACE SEARCH] match_list count={len(match_list)}")
    # SearchFace 响应: MatchList[0].FaceItems[0].{EntityId, Confidence}
    if not match_list:
        raise HTTPException(status_code=404, detail="未找到匹配的人脸，请先到前台登记入住")
    face_items = match_list[0].get("FaceItems", []) if match_list[0] else []
    if not face_items:
        raise HTTPException(status_code=404, detail="未找到匹配的人脸")
    top_face = face_items[0]
    confidence = top_face.get("Confidence", 0)
    if confidence < 70:
        raise HTTPException(status_code=400, detail="人脸匹配度不足，请重试")
    entity_id = top_face.get("EntityId")
    # Convert Aliyun EntityId (no dashes) back to UUID format for JWT sub
    guest_uuid = str(uuid.UUID(entity_id))
    # 3. 签发 JWT
    token_data = {"sub": guest_uuid, "role": "guest", "user_type": "guest"}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {
        "success": True,
        "guest_id": guest_uuid,
        "confidence": confidence,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
