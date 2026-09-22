import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Nullable so system-triggered actions (e.g. auto-lockout) can log with admin_id = NULL
    admin_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("admin_users.admin_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    module: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Polymorphic link — relates to any module's table
    record_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    record_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    # Relationship
    admin = relationship("AdminUser", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by={self.admin_id}>"