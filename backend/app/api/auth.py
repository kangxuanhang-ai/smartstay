import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.guest import Guest
from app.models.user import Staff
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    ChangePasswordRequest,
    UserInfo,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def c_login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Guest).where(
            or_(Guest.id_card == req.id_card, Guest.phone == req.id_card),
        ).limit(1)
    )
    guest = result.scalar_one_or_none()
    if not guest or not verify_password(req.password, guest.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not guest.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="未查询到入住信息，请先在前台办理入住")

    access = create_access_token({"sub": str(guest.id), "role": "guest", "user_type": "guest"})
    refresh = create_refresh_token({"sub": str(guest.id), "role": "guest", "user_type": "guest"})
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login/biz", response_model=TokenResponse)
async def b_login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Staff).where(
            or_(Staff.id_card == req.id_card, Staff.phone == req.id_card),
            Staff.role.in_(["front_desk", "manager", "admin"]),
        ).limit(1)
    )
    staff = result.scalar_one_or_none()
    if not staff or not verify_password(req.password, staff.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token({"sub": str(staff.id), "role": staff.role, "user_type": "staff"})
    refresh = create_refresh_token({"sub": str(staff.id), "role": staff.role, "user_type": "staff"})
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    user_type = payload.get("user_type", "staff")
    role = payload.get("role", "guest")

    if user_type == "guest":
        result = await db.execute(select(Guest).where(Guest.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        role = "guest"
    else:
        result = await db.execute(select(Staff).where(Staff.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        role = user.role

    access = create_access_token({"sub": str(user.id), "role": role, "user_type": user_type})
    refresh = create_refresh_token({"sub": str(user.id), "role": role, "user_type": user_type})
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: Guest | Staff = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

    current_user.hashed_password = get_password_hash(req.new_password)
    current_user.is_first_login = False
    db.add(current_user)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: Guest | Staff = Depends(get_current_user)):
    role = "guest" if isinstance(current_user, Guest) else current_user.role
    return UserInfo(
        id=str(current_user.id),
        id_card=current_user.id_card,
        phone=current_user.phone,
        name=current_user.name,
        role=role,
        is_first_login=current_user.is_first_login,
    )
