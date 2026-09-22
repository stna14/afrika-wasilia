"""
Import every model here so SQLAlchemy's metadata registry knows about them
before `Base.metadata.create_all()` runs.

Order matters: tables with FKs must be imported after the tables they reference.
"""

from app.models.role import Role
from app.models.permission import Permission, RolePermission
from app.models.admin_user import AdminUser
from app.models.session import AdminSession
from app.models.login_attempt import LoginAttempt
from app.models.password_reset import PasswordReset
from app.models.audit_log import AuditLog

__all__ = [
    "Role",
    "Permission",
    "RolePermission",
    "AdminUser",
    "AdminSession",
    "LoginAttempt",
    "PasswordReset",
    "AuditLog",
]