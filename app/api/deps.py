from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import AdminUser, Permission, RolePermission

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Decode the JWT and return the AdminUser. Raises 401 if invalid."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    admin = await db.get(AdminUser, admin_id)
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")

    if admin.account_status != "active":
        raise HTTPException(
            status_code=403,
            detail=f"Account is {admin.account_status}",
        )

    return admin


async def get_admin_permissions(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> set[str]:
    """Return the set of permission keys for the current admin's role."""
    rows = await db.execute(
        select(Permission.permission_key)
        .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
        .where(RolePermission.role_id == admin.role_id)
    )
    return {row[0] for row in rows.all()}


def require_permission(*required_keys: str):
    """
    Dependency factory. Usage:

        @router.post("/x")
        async def x(admin = Depends(require_permission("wisac.nominees.create"))):
            ...

    Multiple keys = requires ALL of them.
    """

    async def checker(
        admin: AdminUser = Depends(get_current_admin),
        permissions: set[str] = Depends(get_admin_permissions),
    ) -> AdminUser:
        missing = [k for k in required_keys if k not in permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission(s): {', '.join(missing)}",
            )
        return admin

    return checker