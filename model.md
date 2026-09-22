
| Relationship | Type | Enforced by |
|---|---|---|
| Roles → Admin Users | 1:M | FK, RESTRICT on delete |
| Roles ↔ Permissions | M:N | `role_permissions`, CASCADE |
| Admin Users → Sessions | 1:M | FK, app-logic revoke on disable |
| Admin Users → Login Attempts | Loose (email match) | No FK, intentional |
| Admin Users → Password Resets | 1:M with exclusivity rule | FK + app logic |
| Admin Users → Audit Logs | 1:M | FK, SET NULL |
| Admin Users → Admin Users | 1:M self-referential | FK `created_by` |
| Audit Logs → *any table* | Polymorphic 1:M | No FK, `record_type` + `record_id` |

---

## 5. Key Design Decisions

### 5.1 UUIDs as CHAR(36), not native UUID
MySQL 8 has no native `UUID` type. We store them as `CHAR(36)` strings
generated in Python via `uuid.uuid4()`. This is portable, works with any DB,
and avoids ID-guessing attacks.

### 5.2 Hashes stored, never raw tokens
- `admin_users.password_hash` — bcrypt/argon2
- `admin_sessions.token_hash` — SHA-256 (refresh tokens)
- `password_resets.token_hash` — SHA-256 (reset tokens)

If the DB leaks, none of the hashes are directly usable by an attacker.

### 5.3 `DATETIME`, not `TIMESTAMP`
MySQL's `TIMESTAMP` has a 2038 upper limit and timezone quirks.
`DATETIME` is timezone-naive storage and lives well past 2038.

### 5.4 Indexing on hot query paths
Every column that will be filtered or joined frequently has `index=True`:
- `admin_users.email` — login lookup
- `admin_sessions.admin_id`, `.is_active` — list/revoke
- `login_attempts.email`, `.ip_address`, `.attempted_at` — rate limit + lockout
- `audit_logs.admin_id`, `.module`, `.record_type`, `.created_at` — filters

### 5.5 Cascade rules match the spec exactly

| FK | On delete | Why |
|---|---|---|
| `admin_users.role_id` → `roles` | RESTRICT | Can't orphan admins |
| `admin_users.created_by` → `admin_users` | SET NULL | Deleting a creator keeps their admins |
| `admin_sessions.admin_id` → `admin_users` | CASCADE | Sessions die with admin |
| `password_resets.admin_id` → `admin_users` | CASCADE | Same |
| `audit_logs.admin_id` → `admin_users` | SET NULL | Audit survives |
| `role_permissions.*` | CASCADE | Junction rows auto-clean |

---

## 6. How Tables Get Created

We are **not using Alembic** for now. Instead:

1. `app/models/__init__.py` imports all 8 model classes in dependency order.
2. `app/main.py` lifespan calls `Base.metadata.create_all()` on startup.
3. SQLAlchemy inspects the DB, creates any missing tables, and **leaves existing ones alone**.

When the schema needs to change later, we'll write plain `.sql` files under
`migrations/` and run them manually. Once the schema stabilizes, we can
adopt Atlas (declarative, no Python revision scripts) instead of Alembic.

---

## 7. What Comes Next

After `create_all()` runs and tables appear in MySQL:

1. **Seed script** — inserts the 5 roles + all permission keys + the first Super Admin.
2. **Auth service** — password hashing, JWT issuance, login flow.
3. **Permission middleware** — resolves `admin → role → permissions` per request.
4. **Audit helper** — `logAudit()` reused by every future module.

---

*End of Models documentation.*