import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    admin_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Never plain text — bcrypt/argon2 hash, 60 chars fits bcrypt
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("roles.role_id", ondelete="RESTRICT"),
        nullable=False,
    )

    # active | suspended | disabled
    account_status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )

    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    profile_image: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Self-referencing — which admin created this account
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("admin_users.admin_id", ondelete="SET NULL"),
        nullable=True,
    )

    date_created: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    date_updated: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    role = relationship("Role", back_populates="admin_users")

    sessions = relationship(
        "AdminSession",
        back_populates="admin",
        cascade="all, delete-orphan",
        foreign_keys="AdminSession.admin_id",
    )

    password_resets = relationship(
        "PasswordReset",
        back_populates="admin",
        cascade="all, delete-orphan",
        foreign_keys="PasswordReset.admin_id",
    )

    audit_logs = relationship(
        "AuditLog",
        back_populates="admin",
        foreign_keys="AuditLog.admin_id",
    )

    # Self-referential: admin I created
    created_admins = relationship(
        "AdminUser",
        backref="creator",
        remote_side="AdminUser.admin_id",
        foreign_keys=[created_by],
    )

    def __repr__(self) -> str:
        return f"<AdminUser {self.email} ({self.account_status})>"