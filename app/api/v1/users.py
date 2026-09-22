from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.database import get_db
from app.models import AdminUser
from app.schemas.admin import (
    AdminCreate,
    AdminDetail,
    AdminRoleUpdate,
    AdminStatusUpdate,
    AdminUpdate,
)
from app.schemas.auth import AdminSummary
from app.services import audit_service, user_service
from app.services.auth_service import get_admin_role_name
from app.services.user_service import UserServiceError

router = APIRouter(prefix="/users", tags=["users"])


def _req_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


async def _detail(db: AsyncSession, admin: AdminUser) -> AdminDetail:
    return AdminDetail(
        admin_id=admin.admin_id,
        full_name=admin.full_name,
        email=admin.email,
        phone=admin.phone,
        role_id=admin.role_id,
        role_name=await get_admin_role_name(db, admin.role_id),
        account_status=admin.account_status,
        two_factor_enabled=admin.two_factor_enabled,
        profile_image=admin.profile_image,
        last_login=admin.last_login.isoformat() if admin.last_login else None,
        created_by=admin.created_by,
    )


@router.get("/", response_model=list[AdminSummary])
async def list_admins(
    _admin=Depends(require_permission("admin.users.create")),
    db: AsyncSession = Depends(get_db),
):
    admins = (await db.scalars(select(AdminUser).order_by(AdminUser.date_created))).all()
    out = []
    for a in admins:
        out.append(
            AdminSummary(
                admin_id=a.admin_id,
                full_name=a.full_name,
                email=a.email,
                role_name=await get_admin_role_name(db, a.role_id),
                account_status=a.account_status,
            )
        )
    return out


@router.post("/", response_model=AdminDetail, status_code=201)
async def create_admin(
    payload: AdminCreate,
    request: Request,
    actor: AdminUser = Depends(require_permission("admin.users.create")),
    db: AsyncSession = Depends(get_db),
):
    try:
        admin = await user_service.create_admin(db, payload, actor)
    except UserServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    ip, ua = _req_meta(request)
    await audit_service.log_audit(
        db,
        admin_id=actor.admin_id,
        action="CREATE_ADMIN",
        module="Admin",
        record_type="admin_user",
        record_id=admin.admin_id,
        new_value=audit_service.snapshot(admin),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return await _detail(db, admin)


@router.get("/{admin_id}", response_model=AdminDetail)
async def get_admin(
    admin_id: str,
    _admin=Depends(require_permission("admin.users.create")),
    db: AsyncSession = Depends(get_db),
):
    try:
        admin = await user_service.get_admin_or_404(db, admin_id)
    except UserServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    return await _detail(db, admin)


@router.put("/{admin_id}", response_model=AdminDetail)
async def update_admin(
    admin_id: str,
    payload: AdminUpdate,
    request: Request,
    actor: AdminUser = Depends(require_permission("admin.users.edit")),
    db: AsyncSession = Depends(get_db),
):
    before = await user_service.get_admin_or_404(db, admin_id)
    old_snapshot = audit_service.snapshot(before)

    try:
        admin = await user_service.update_admin(db, admin_id, payload)
    except UserServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    ip, ua = _req_meta(request)
    await audit_service.log_audit(
        db,
        admin_id=actor.admin_id,
        action="UPDATE_ADMIN",
        module="Admin",
        record_type="admin_user",
        record_id=admin.admin_id,
        old_value=old_snapshot,
        new_value=audit_service.snapshot(admin),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return await _detail(db, admin)


@router.put("/{admin_id}/role", response_model=AdminDetail)
async def reassign_role(
    admin_id: str,
    payload: AdminRoleUpdate,
    request: Request,
    actor: AdminUser = Depends(require_permission("admin.roles.assign")),
    db: AsyncSession = Depends(get_db),
):
    before = await user_service.get_admin_or_404(db, admin_id)
    old_snapshot = audit_service.snapshot(before)

    try:
        admin = await user_service.reassign_role(db, admin_id, payload.role_id, actor)
    except UserServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    ip, ua = _req_meta(request)
    await audit_service.log_audit(
        db,
        admin_id=actor.admin_id,
        action="REASSIGN_ROLE",
        module="Admin",
        record_type="admin_user",
        record_id=admin.admin_id,
        old_value=old_snapshot,
        new_value=audit_service.snapshot(admin),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return await _detail(db, admin)


@router.put("/{admin_id}/status", response_model=AdminDetail)
async def change_status(
    admin_id: str,
    payload: AdminStatusUpdate,
    request: Request,
    actor: AdminUser = Depends(require_permission("admin.users.edit")),
    db: AsyncSession = Depends(get_db),
):
    before = await user_service.get_admin_or_404(db, admin_id)
    old_snapshot = audit_service.snapshot(before)

    try:
        admin = await user_service.change_status(
            db, admin_id, payload.account_status, actor
        )
    except UserServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    ip, ua = _req_meta(request)
    await audit_service.log_audit(
        db,
        admin_id=actor.admin_id,
        action="CHANGE_STATUS",
        module="Admin",
        record_type="admin_user",
        record_id=admin.admin_id,
        old_value=old_snapshot,
        new_value=audit_service.snapshot(admin),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return await _detail(db, admin)


@router.delete("/{admin_id}", response_model=AdminDetail)
async def delete_admin(
    admin_id: str,
    request: Request,
    actor: AdminUser = Depends(require_permission("admin.users.delete")),
    db: AsyncSession = Depends(get_db),
):
    before = await user_service.get_admin_or_404(db, admin_id)
    old_snapshot = audit_service.snapshot(before)

    try:
        admin = await user_service.soft_delete_admin(db, admin_id, actor)
    except UserServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    ip, ua = _req_meta(request)
    await audit_service.log_audit(
        db,
        admin_id=actor.admin_id,
        action="DELETE_ADMIN",
        module="Admin",
        record_type="admin_user",
        record_id=admin.admin_id,
        old_value=old_snapshot,
        new_value=audit_service.snapshot(admin),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    return await _detail(db, admin)