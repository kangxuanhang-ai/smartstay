import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from slowapi import Limiter
from slowapi.util import get_remote_address
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

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

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
    return {"matched": confidence >= 75, "confidence": confidence}


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
@limiter.limit("10/minute")
async def search_face_login(request: Request, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    image_bytes = await file.read()
    logger.info("[FaceSearch] 收到图片，大小: %d bytes", len(image_bytes))

    # 1. 活体检测
    try:
        living_result = detect_living_face(image_bytes)
        living_data = living_result.get("Data") or living_result.get("data", {})
        elements = living_data.get("Elements", []) if living_data else []
        living_pass = False
        if elements and elements[0].get("Results", []):
            r = elements[0]["Results"][0]
            living_pass = r.get("Suggestion") == "pass" and (r.get("Rate", 0) or 0) >= 50
            logger.info("[FaceSearch] 活体检测: suggestion=%s, rate=%s, pass=%s", r.get('Suggestion'), r.get('Rate'), living_pass)
        else:
            logger.warning("[FaceSearch] 活体检测无结果, elements=%s", elements)
            living_pass = False  # 明确设置为 False
        if not living_pass:
            logger.warning("[FaceSearch] 活体检测未通过，拒绝请求")
            raise HTTPException(status_code=400, detail="活体检测未通过")
    except HTTPException:
        raise  # 重新抛出 HTTP 异常
    except Exception as e:
        logger.error("[FaceSearch] 活体检测异常: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"活体检测服务异常: {str(e)}")

    # 2. 人脸搜索
    try:
        search_result = search_face(settings.ALIYUN_FACE_DB_NAME, image_bytes)
        search_data = search_result.get("Data") or search_result.get("data", {})
        match_list = search_data.get("MatchList", []) if search_data else []
        logger.info("[FaceSearch] 人脸搜索返回 %d 个匹配结果", len(match_list))

        if not match_list:
            logger.warning("[FaceSearch] 未找到匹配人脸")
            raise HTTPException(status_code=404, detail="未找到匹配的人脸，请先到前台登记入住")

        # 3. 遍历所有匹配结果，找到第一个 is_active 的住客
        all_candidates = []  # 收集所有候选以便日志
        for match in match_list:
            face_items = match.get("FaceItems", []) if match else []
            for face in face_items:
                confidence = face.get("Confidence", 0)
                entity_id = face.get("EntityId", "unknown")
                all_candidates.append({"entity_id": entity_id, "confidence": confidence})

                if confidence < 70:
                    logger.debug("[FaceSearch] 跳过低置信度: entity=%s, confidence=%.1f%%", entity_id, confidence)
                    continue
                if not entity_id or entity_id == "unknown":
                    logger.warning("[FaceSearch] entity_id 为空")
                    continue

                try:
                    guest_uuid = uuid.UUID(entity_id)
                except ValueError:
                    logger.warning("[FaceSearch] 无效的 entity_id: %s", entity_id)
                    continue

                result_db = await db.execute(select(Guest).where(Guest.id == guest_uuid))
                guest = result_db.scalar_one_or_none()
                if not guest:
                    logger.warning("[FaceSearch] 数据库中未找到住客: entity_id=%s (UUID=%s)", entity_id, guest_uuid)
                    # 查询数据库中所有住客的 ID，帮助排查
                    all_guests_result = await db.execute(select(Guest.id))
                    all_guest_ids = [str(gid) for gid in all_guests_result.scalars().all()]
                    logger.info("[FaceSearch] 数据库中现有住客 ID 列表: %s", all_guest_ids)
                    continue
                if not guest.is_active:
                    logger.info("[FaceSearch] 住客已退房: entity=%s, guest_id=%s", entity_id, guest_uuid)
                    continue

                # 找到活跃住客，签发 JWT
                guest_uuid_str = str(guest_uuid)
                token_data = {"sub": guest_uuid_str, "role": "guest", "user_type": "guest"}
                access_token = create_access_token(token_data)
                refresh_token = create_refresh_token(token_data)
                logger.info("[FaceSearch] 登录成功! guest_id=%s, name=%s, confidence=%.1f%%", guest_uuid, guest.name, confidence)
                return {
                    "success": True,
                    "guest_id": guest_uuid_str,
                    "confidence": confidence,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }

        # 如果走到这里，说明没有符合条件的住客
        logger.warning("[FaceSearch] 所有匹配结果均不符合条件: %s", all_candidates)
        raise HTTPException(status_code=404, detail="未找到有效住客，请先到前台办理入住")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[FaceSearch] 人脸搜索异常: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"人脸搜索服务异常: {str(e)}")
