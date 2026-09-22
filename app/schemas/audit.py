from datetime import datetime

from pydantic import BaseModel


class AuditLogEntry(BaseModel):
    log_id: str
    admin_id: str | None
    action: str
    module: str | None
    record_type: str | None
    record_id: str | None
    old_value: dict | None
    new_value: dict | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuditLogEntry]