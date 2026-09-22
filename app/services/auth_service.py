from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from app.models import AdminSession, AdminUser, LoginAttempt, Role
from app.services.audit_service import log_audit


class AuthError(Exception):
    """Raised for any auth failure. Route layer converts to HTTPException."""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def _log_attempt(
    db: AsyncSession,
    email: str,
    ip: str | None,
    user_agent: str | None,
    success: bool,
) -> None:
    db.add(
        LoginAttempt(
            email=email,
            ip_address=ip,
            user_agent=user_agent,
            success=success,
        )
    )


async def authenticate(
    db: AsyncSession,
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> tuple[AdminUser, str, str]:
    """
    Verify credentials, handle lockout, log attempt, issue tokens.
    Returns (admin, access_token, refresh_token).
    Raises AuthError on failure.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # ---- Find admin ----
    admin = await db.scalar(select(AdminUser).where(AdminUser.email == email))

    # Generic message on purpose — never reveal whether email exists
    if not admin:
        await _log_attempt(db, email, ip, user_agent, success=False)
        await log_audit(
            db,
            admin_id=None,
            action="LOGIN_FAILED",
            module="Admin",
            record_type="admin_user",
            record_id=None,
            new_value={"email": email, "reason": "not_found"},
            ip_address=ip,
            user_agent=user_agent,
        )
        await db.commit()
        raise AuthError("Invalid credentials")

    # ---- Account status check ----
    if admin.account_status != "active":
        await _log_attempt(db, email, ip, user_agent, success=False)
        await log_audit(
            db,
            admin_id=admin.admin_id,
            action="LOGIN_FAILED",
            module="Admin",
            record_type="admin_user",
            record_id=admin.admin_id,
            new_value={"reason": f"account_{admin.account_status}"},
            ip_address=ip,
            user_agent=user_agent,
        )
        await db.commit()
        raise AuthError(f"Account is {admin.account_status}", status_code=403)

    # ---- Lockout check ----
    if admin.locked_until and admin.locked_until > now:
        await _log_attempt(db, email, ip, user_agent, success=False)
        await log_audit(
            db,
            admin_id=admin.admin_id,
            action="LOGIN_FAILED",
            module="Admin",
            record_type="admin_user",
            record_id=admin.admin_id,
            new_value={"reason": "account_locked"},
            ip_address=ip,
            user_agent=user_agent,
        )
        await db.commit()
        remaining = int((admin.locked_until - now).total_seconds() // 60) + 1
        raise AuthError(
            f"Account locked. Try again in {remaining} minutes.",
            status_code=423,
        )

    # ---- Password check ----
    if not verify_password(password, admin.password_hash):
        admin.failed_login_count = (admin.failed_login_count or 0) + 1
        if admin.failed_login_count >= settings.MAX_FAILED_LOGINS:
            admin.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
            admin.failed_login_count = 0  # reset counter, lockout takes over
        await _log_attempt(db, email, ip, user_agent, success=False)
        await log_audit(
            db,
            admin_id=admin.admin_id,
            action="LOGIN_FAILED",
            module="Admin",
            record_type="admin_user",
            record_id=admin.admin_id,
            new_value={"reason": "wrong_password"},
            ip_address=ip,
            user_agent=user_agent,
        )
        await db.commit()
        raise AuthError("Invalid credentials")

    # ---- Success ----
    admin.failed_login_count = 0
    admin.locked_until = None
    admin.last_login = now
    admin.last_login_ip = ip

    access_token = create_access_token(
        subject=admin.admin_id,
        extra={"role_id": admin.role_id},
    )
    refresh_token = create_refresh_token(subject=admin.admin_id)

    # ---- Persist session ----
    session = AdminSession(
        admin_id=admin.admin_id,
        token_hash=hash_token(refresh_token),
        ip_address=ip,
        user_agent=user_agent,
        is_active=True,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)

    # Audit — success login
    await log_audit(
        db,
        admin_id=admin.admin_id,
        action="LOGIN",
        module="Admin",
        record_type="admin_user",
        record_id=admin.admin_id,
        ip_address=ip,
        user_agent=user_agent,
    )

    await _log_attempt(db, email, ip, user_agent, success=True)
    await db.commit()
    await db.refresh(admin)

    return admin, access_token, refresh_token


async def get_admin_role_name(db: AsyncSession, role_id: str) -> str:
    role = await db.scalar(select(Role).where(Role.role_id == role_id))
    return role.role_name if role else "Unknown"