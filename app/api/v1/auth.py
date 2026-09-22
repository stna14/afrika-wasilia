from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_refresh_token,
    hash_token,
)
from app.models import AdminSession, AdminUser, Role
from app.schemas.auth import (
    AdminSummary,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from app.services.audit_service import log_audit
from app.services.auth_service import AuthError, authenticate, get_admin_role_name
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["auth"])


async def _admin_summary(db: AsyncSession, admin: AdminUser) -> AdminSummary:
    role_name = await get_admin_role_name(db, admin.role_id)
    return AdminSummary(
        admin_id=admin.admin_id,
        full_name=admin.full_name,
        email=admin.email,
        role_name=role_name,
        account_status=admin.account_status,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        admin, access_token, refresh_token = await authenticate(
            db=db,
            email=payload.email,
            password=payload.password,
            ip=ip,
            user_agent=user_agent,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        admin=await _admin_summary(db, admin),
    )


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = decode_refresh_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(401, "Invalid or expired refresh token")

    if data.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")

    admin_id = data.get("sub")
    token_hash = hash_token(payload.refresh_token)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    session = await db.scalar(
        select(AdminSession).where(
            AdminSession.token_hash == token_hash,
            AdminSession.is_active == True,  # noqa: E712
            AdminSession.expires_at > now,
        )
    )
    if not session:
        raise HTTPException(401, "Session not found or revoked")

    admin = await db.get(AdminUser, admin_id)
    if not admin or admin.account_status != "active":
        raise HTTPException(401, "Admin not found or inactive")

    new_access = create_access_token(
        subject=admin.admin_id, extra={"role_id": admin.role_id}
    )

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    await log_audit(
        db,
        admin_id=admin.admin_id,
        action="REFRESH_TOKEN",
        module="Admin",
        record_type="admin_user",
        record_id=admin.admin_id,
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()

    return TokenResponse(
        access_token=new_access,
        refresh_token=payload.refresh_token,  # reuse existing refresh
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        admin=await _admin_summary(db, admin),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_token(payload.refresh_token)
    session = await db.scalar(
        select(AdminSession).where(AdminSession.token_hash == token_hash)
    )
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if session:
        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await log_audit(
            db,
            admin_id=session.admin_id,
            action="LOGOUT",
            module="Admin",
            record_type="admin_user",
            record_id=session.admin_id,
            ip_address=ip,
            user_agent=ua,
        )
        await db.commit()

    return MessageResponse(message="Logged out")


@router.get("/me", response_model=AdminSummary)
async def me(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _admin_summary(db, admin)