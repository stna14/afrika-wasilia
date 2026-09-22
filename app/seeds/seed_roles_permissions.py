"""
Idempotent seed script. Safe to run multiple times.

Creates:
  1. The 5 default roles
  2. All permission keys for the Admin & Security module
  3. Role → permission mappings (Super Admin = all)
  4. The first Super Admin account (if none exists)

Run from project root:
    python -m app.seeds.seed_roles_permissions
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models import (
    AdminUser,
    Permission,
    Role,
    RolePermission,
)

# ---- Config for first Super Admin ----
FIRST_ADMIN_EMAIL = "admin@mwafrikaasilia.com"
FIRST_ADMIN_PASSWORD = "ChangeMe#2025!"  # CHANGE ON FIRST LOGIN
FIRST_ADMIN_NAME = "Super Admin"


# ---- The 5 roles ----
ROLES = [
    {
        "role_name": "Super Admin",
        "description": "Full control of the entire system",
        "is_system_role": True,
    },
    {
        "role_name": "Content Manager",
        "description": "Newsroom, Gallery, Projects, Pages",
        "is_system_role": True,
    },
    {
        "role_name": "WISAC Manager",
        "description": "Nominees, Categories, Voting, Winners",
        "is_system_role": True,
    },
    {
        "role_name": "Finance/Admin",
        "description": "Payments, Tickets, Revenue Reports",
        "is_system_role": True,
    },
    {
        "role_name": "Applications Manager",
        "description": "Talent Portal, Volunteers, Partnerships, Bookings",
        "is_system_role": True,
    },
]


# ---- Permissions grouped by module ----
PERMISSIONS = [
    # CMS
    ("cms.pages.create", "CMS", "Create pages"),
    ("cms.pages.edit", "CMS", "Edit pages"),
    ("cms.pages.delete", "CMS", "Delete pages"),
    ("cms.newsroom.create", "CMS", "Create newsroom posts"),
    ("cms.newsroom.edit", "CMS", "Edit newsroom posts"),
    ("cms.newsroom.delete", "CMS", "Delete newsroom posts"),
    ("cms.gallery.manage", "CMS", "Manage gallery"),
    ("cms.projects.manage", "CMS", "Manage projects"),

    # WISAC
    ("wisac.editions.manage", "WISAC", "Manage WISAC editions"),
    ("wisac.categories.manage", "WISAC", "Manage categories"),
    ("wisac.nominees.create", "WISAC", "Create nominees"),
    ("wisac.nominees.edit", "WISAC", "Edit nominees"),
    ("wisac.nominees.delete", "WISAC", "Delete nominees"),
    ("wisac.voting.manage", "WISAC", "Manage voting"),
    ("wisac.voting.approve_winner", "WISAC", "Approve winners"),
    ("wisac.sponsors.manage", "WISAC", "Manage sponsors"),
    ("wisac.livestream.manage", "WISAC", "Manage livestream"),

    # Payments
    ("payments.view", "Payments", "View payments"),
    ("payments.refund", "Payments", "Issue refunds"),
    ("tickets.manage", "Payments", "Manage tickets"),
    ("reports.financial.view", "Payments", "View financial reports"),

    # Applications
    ("applications.manage", "Applications", "Manage applications"),
    ("volunteers.manage", "Applications", "Manage volunteers"),
    ("partnerships.manage", "Applications", "Manage partnerships"),
    ("bookings.manage", "Applications", "Manage bookings"),

    # Admin & Security
    ("admin.users.create", "Admin", "Create admin users"),
    ("admin.users.edit", "Admin", "Edit admin users"),
    ("admin.users.delete", "Admin", "Delete admin users"),
    ("admin.roles.assign", "Admin", "Assign roles"),
    ("admin.roles.manage", "Admin", "Manage roles + permissions"),
    ("admin.audit.view", "Admin", "View audit logs"),
    ("admin.sessions.manage", "Admin", "Force-logout sessions"),
]


# Role → which permission modules they get
ROLE_PERMISSION_MAP = {
    "Super Admin": "*",  # all
    "Content Manager": {"CMS"},
    "WISAC Manager": {"WISAC"},
    "Finance/Admin": {"Payments"},
    "Applications Manager": {"Applications"},
}


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ---- 1. Roles ----
        print("Seeding roles...")
        for role_data in ROLES:
            existing = await db.scalar(
                select(Role).where(Role.role_name == role_data["role_name"])
            )
            if not existing:
                db.add(Role(**role_data))
                print(f"  + {role_data['role_name']}")
            else:
                print(f"  = {role_data['role_name']} (exists)")
        await db.commit()

        # ---- 2. Permissions ----
        print("Seeding permissions...")
        for key, module, desc in PERMISSIONS:
            existing = await db.scalar(
                select(Permission).where(Permission.permission_key == key)
            )
            if not existing:
                db.add(Permission(permission_key=key, module=module, description=desc))
                print(f"  + {key}")
        await db.commit()

        # ---- 3. Role → Permission mappings ----
        print("Mapping roles to permissions...")
        all_roles = {r.role_name: r for r in (await db.scalars(select(Role))).all()}
        all_perms = (await db.scalars(select(Permission))).all()

        for role_name, scope in ROLE_PERMISSION_MAP.items():
            role = all_roles.get(role_name)
            if not role:
                continue

            if scope == "*":
                target_perms = all_perms
            else:
                target_perms = [p for p in all_perms if p.module in scope]

            for perm in target_perms:
                exists = await db.scalar(
                    select(RolePermission).where(
                        RolePermission.role_id == role.role_id,
                        RolePermission.permission_id == perm.permission_id,
                    )
                )
                if not exists:
                    db.add(
                        RolePermission(
                            role_id=role.role_id, permission_id=perm.permission_id
                        )
                    )
            print(f"  {role_name}: {len(target_perms)} permissions")
        await db.commit()

        # ---- 4. First Super Admin ----
        print("Seeding first Super Admin...")
        existing_admin = await db.scalar(
            select(AdminUser).where(AdminUser.email == FIRST_ADMIN_EMAIL)
        )
        if existing_admin:
            print(f"  = {FIRST_ADMIN_EMAIL} (exists)")
        else:
            super_role = all_roles.get("Super Admin")
            if not super_role:
                raise RuntimeError("Super Admin role missing — cannot seed admin")

            admin = AdminUser(
                full_name=FIRST_ADMIN_NAME,
                email=FIRST_ADMIN_EMAIL,
                password_hash=hash_password(FIRST_ADMIN_PASSWORD),
                role_id=super_role.role_id,
                account_status="active",
            )
            db.add(admin)
            await db.commit()
            print(f"  + {FIRST_ADMIN_EMAIL}")
            print(f"    password: {FIRST_ADMIN_PASSWORD}")
            print("    ⚠ CHANGE THIS ON FIRST LOGIN")

        print("\n✅ Seed complete.")


if __name__ == "__main__":
    async def main():
        try:
            await seed()
        finally:
            from app.core.database import engine
            await engine.dispose()

    asyncio.run(main())