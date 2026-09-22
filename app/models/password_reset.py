import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PasswordReset(Base):
    __tablename__ = "password_resets"

    reset_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    admin_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("admin_users.admin_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # SHA-256 hash of the reset token sent via email — never the raw token
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationship
    admin = relationship("AdminUser", back_populates="password_resets")

    def __repr__(self) -> str:
        return f"<PasswordReset admin={self.admin_id} used={self.used}>"