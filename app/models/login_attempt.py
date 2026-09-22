import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    attempt_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Intentionally NOT a foreign key — attackers probe emails that don't exist.
    # Storing raw email here is a security signal, not a data integrity violation.
    email: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    attempted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<LoginAttempt {self.email} success={self.success}>"