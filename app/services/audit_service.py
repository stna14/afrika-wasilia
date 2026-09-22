import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


# Fields never written to audit snapshots
SENSITIVE_FIELDS = {"password_hash", "two_factor_secret"}


def snapshot(obj: Any, exclude: set[str] | None = None) -> dict | None:
    """Convert a SQLAlchemy model instance into a JSON-safe dict."""
    if obj is None:
        return None

    exclude = (exclude or set()) | SENSITIVE_FIELDS
    mapper = sa_inspect(obj).mapper
    out: dict[str, Any] = {}

    for col in mapper.columns:
        name = col.key
        if name in exclude:
            continue
        val = getattr(obj, name)
        if val is None:
            out[name] = None
        elif isinstance(val, uuid.UUID):
            out[name] = str(val)
        elif isinstance(val, datetime):
            out[name] = val.isoformat()
        else:
            out[name] = val

    return out


async def log_audit(
    db: AsyncSession,
    *,
    admin_id: str | None,
    action: str,
    module: str | None = None,
    record_type: str | None = None,
    record_id: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Append an audit row. Caller is responsible for committing."""
    entry = AuditLog(
        admin_id=admin_id,
        action=action,
        module=module,
        record_type=record_type,
        record_id=record_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    return entry


async def list_audit_logs(
    db: AsyncSession,
    *,
    admin_id: str | None = None,
    module: str | None = None,
    action: str | None = None,
    record_type: str | None = None,
    record_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    """Filtered + paginated audit log query."""
    stmt = select(AuditLog)

    conditions = []
    if admin_id:
        conditions.append(AuditLog.admin_id == admin_id)
    if module:
        conditions.append(AuditLog.module == module)
    if action:
        conditions.append(AuditLog.action == action)
    if record_type:
        conditions.append(AuditLog.record_type == record_type)
    if record_id:
        conditions.append(AuditLog.record_id == record_id)
    if date_from:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to:
        conditions.append(AuditLog.created_at <= date_to)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

    return list((await db.scalars(stmt)).all())


async def count_audit_logs(
    db: AsyncSession,
    *,
    admin_id: str | None = None,
    module: str | None = None,
    action: str | None = None,
    record_type: str | None = None,
    record_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> int:
    from sqlalchemy import func

    stmt = select(func.count()).select_from(AuditLog)
    conditions = []
    if admin_id:
        conditions.append(AuditLog.admin_id == admin_id)
    if module:
        conditions.append(AuditLog.module == module)
    if action:
        conditions.append(AuditLog.action == action)
    if record_type:
        conditions.append(AuditLog.record_type == record_type)
    if record_id:
        conditions.append(AuditLog.record_id == record_id)
    if date_from:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to:
        conditions.append(AuditLog.created_at <= date_to)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    return int(await db.scalar(stmt) or 0)