from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.audit import AuditLogEntry, AuditLogPage
from app.services import audit_service

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("/", response_model=AuditLogPage)
async def list_logs(
    admin_id: str | None = Query(default=None),
    module: str | None = Query(default=None),
    action: str | None = Query(default=None),
    record_type: str | None = Query(default=None),
    record_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin=Depends(require_permission("admin.audit.view")),
    db: AsyncSession = Depends(get_db),
):
    items = await audit_service.list_audit_logs(
        db,
        admin_id=admin_id,
        module=module,
        action=action,
        record_type=record_type,
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    total = await audit_service.count_audit_logs(
        db,
        admin_id=admin_id,
        module=module,
        action=action,
        record_type=record_type,
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
    )
    return AuditLogPage(
        total=total,
        limit=limit,
        offset=offset,
        items=[AuditLogEntry.model_validate(i) for i in items],
    )