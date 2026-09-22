from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import AdminUser, Role
from app.schemas.admin import AdminCreate, AdminUpdate


class UserServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def get_admin_or_404(db: AsyncSession, admin_id: str) -> AdminUser:
    admin = await db.get(AdminUser, admin_id)
    if not admin:
        raise UserServiceError("Admin not found", status_code=404)
    return admin


async def create_admin(
    db: AsyncSession,
    payload: AdminCreate,
    creator: AdminUser,
) -> AdminUser:
    # Email uniqueness
    existing = await db.scalar(
        select(AdminUser).where(AdminUser.email == payload.email)
    )
    if existing:
        raise UserServiceError("Email already in use", status_code=409)

    # Role must exist
    role = await db.get(Role, payload.role_id)
    if not role:
        raise UserServiceError("Role not found", status_code=404)

    admin = AdminUser(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role_id=payload.role_id,
        account_status="active",
        created_by=creator.admin_id,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


async def update_admin(
    db: AsyncSession,
    admin_id: str,
    payload: AdminUpdate,
) -> AdminUser:
    admin = await get_admin_or_404(db, admin_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(admin, k, v)
    admin.date_updated = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(admin)
    return admin


async def reassign_role(
    db: AsyncSession,
    admin_id: str,
    role_id: str,
    actor: AdminUser,
) -> AdminUser:
    admin = await get_admin_or_404(db, admin_id)

    if admin.admin_id == actor.admin_id:
        raise UserServiceError("You cannot change your own role", status_code=400)

    role = await db.get(Role, role_id)
    if not role:
        raise UserServiceError("Role not found", status_code=404)

    admin.role_id = role_id
    admin.date_updated = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(admin)
    return admin


async def change_status(
    db: AsyncSession,
    admin_id: str,
    new_status: str,
    actor: AdminUser,
) -> AdminUser:
    admin = await get_admin_or_404(db, admin_id)

    if admin.admin_id == actor.admin_id:
        raise UserServiceError("You cannot change your own status", status_code=400)

    admin.account_status = new_status
    admin.date_updated = datetime.now(timezone.utc).replace(tzinfo=None)

    # Revoke all sessions if the admin is being suspended/disabled
    if new_status in ("suspended", "disabled"):
        from app.models import AdminSession
        sessions = await db.scalars(
            select(AdminSession).where(
                AdminSession.admin_id == admin_id,
                AdminSession.is_active == True,  # noqa: E712
            )
        )
        for s in sessions.all():
            s.is_active = False
            s.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(admin)
    return admin


async def soft_delete_admin(
    db: AsyncSession,
    admin_id: str,
    actor: AdminUser,
) -> AdminUser:
    admin = await get_admin_or_404(db, admin_id)

    if admin.admin_id == actor.admin_id:
        raise UserServiceError("You cannot delete your own account", status_code=400)

    if admin.account_status == "disabled":
        raise UserServiceError("Admin already disabled", status_code=400)

    admin.account_status = "disabled"
    admin.date_updated = datetime.now(timezone.utc).replace(tzinfo=None)

    # Revoke sessions
    from app.models import AdminSession
    sessions = await db.scalars(
        select(AdminSession).where(
            AdminSession.admin_id == admin_id,
            AdminSession.is_active == True,  # noqa: E712
        )
    )
    for s in sessions.all():
        s.is_active = False
        s.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(admin)
    return admin