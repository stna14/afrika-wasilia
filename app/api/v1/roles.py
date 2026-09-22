from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.database import get_db
from app.models import Role
from app.schemas.role import RoleSummary

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=list[RoleSummary])
async def list_roles(
    _admin=Depends(require_permission("admin.users.create")),
    db: AsyncSession = Depends(get_db),
):
    roles = (await db.scalars(select(Role).order_by(Role.role_name))).all()
    return [RoleSummary.model_validate(r) for r in roles]