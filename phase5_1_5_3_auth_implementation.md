# Phase 5.1–5.3 — Authentication Foundation, Current User & Audit Ownership Implementation Report

**Project:** Brand Guardian AI / VIDEO_AUDIT_PROJ  
**Implementation Phases:** 5.1 (Auth Foundation), 5.2 (Auth Endpoints & Current User), 5.3 (Audit Ownership & IDOR Protection)  
**Status:** COMPLETE  
**Date:** September 2026  

---

## 1. Authentication Architecture

The Brand Guardian AI backend has been upgraded with a native, robust, and standards-compliant JWT Bearer authentication system (`OAuth2PasswordBearer` + JWT + bcrypt).

```text
HTTP Client (e.g. Angular)
        │
        │ Authorization: Bearer <JWT>
        ▼
FastAPI Router (/audits, /audit, /auth/me)
        │
        ▼
get_current_active_user() Dependency
        │
        ▼
CurrentUser (id, email, display_name, role, is_active)
        │
        ▼
API Endpoint Handler
        │
        ▼
AuditRepository (Row-level filtering: WHERE created_by = current_user.id)
        │
        ▼
PostgreSQL / SQLite Database
```

* **Security Truth:** The authenticated JWT token is the sole source of truth for user identity.
* **No Client Trust:** Client-supplied owner fields (such as `created_by` in payloads) are discarded and overridden server-side by `current_user.id`.

---

## 2. User Data Model

A new SQLAlchemy ORM entity `User` and corresponding enum `UserRole` were added to `backend/src/db/models.py`:

```python
class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
```

* **Safe Serialization:** `User.to_dict()` strictly omits `password_hash` to guarantee credentials cannot leak into responses or logs.
* **Normalization:** User emails are trimmed and lowercased upon persistence and query lookups.

---

## 3. Cryptographic Password Hashing

Implemented in `backend/src/security/passwords.py`:
* **Library:** `bcrypt 5.0.0`
* **Salt Handling:** Automatic salt generation via `bcrypt.gensalt()`.
* **Limits:** Safe 72-byte string slicing adhering to standard bcrypt limits.
* **Functions:**
  * `hash_password(password: str) -> str`: Produces a standard bcrypt hash (`$2b$...`).
  * `verify_password(plain_password: str, hashed_password: str) -> bool`: Constant-time hash comparison returning boolean without leaking internal errors.

---

## 4. JWT Configuration & Token Lifecycle

Implemented in `backend/src/config.py` and `backend/src/security/tokens.py`:
* **Settings:**
  * `JWT_SECRET_KEY`: Configured via environment variable; defaults to a development fallback.
  * `JWT_ALGORITHM`: `HS256`.
  * `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Defaults to 1440 minutes (24 hours).
* **Payload Structure:**
  ```json
  {
    "sub": "<user_uuid>",
    "email": "user@brandguardian.ai",
    "role": "USER",
    "iat": 1727100000,
    "exp": 1727186400
  }
  ```
* **Validation:** PyJWT validates signature and expiration. Expired tokens trigger HTTP 401 Unauthorized with clear message `Token has expired. Please log in again.`

---

## 5. Auth Endpoints

Mounted in `backend/src/api/auth_routes.py` with prefix `/auth`:
* `POST /auth/register` (HTTP 201 Created):
  - Request: `{"email": "...", "password": "...", "display_name": "..."}`
  - Checks for duplicate email (returns HTTP 409 Conflict if taken).
  - Returns `UserResponse` (id, email, display_name, role, is_active, created_at).
* `POST /auth/login` (HTTP 200 OK):
  - Request: `{"email": "...", "password": "..."}`
  - Returns: `{"access_token": "...", "token_type": "bearer"}`
  - Generic 401 Unauthorized error prevents account enumeration.
* `GET /auth/me` (HTTP 200 OK):
  - Requires `Authorization: Bearer <token>`.
  - Returns current user profile excluding sensitive hashes.

---

## 6. Current-User Dependency Injection

Implemented in `backend/src/api/auth_dependencies.py`:
* `get_current_user`:
  - Missing token: HTTP 401 Unauthorized
  - Invalid token: HTTP 401 Unauthorized
  - Expired token: HTTP 401 Unauthorized
  - User not found in DB: HTTP 401 Unauthorized
* `get_current_active_user`:
  - Active user: returns `User`
  - Inactive user: HTTP 403 Forbidden
* `require_admin`:
  - Role == `ADMIN`: returns `User`
  - Non-admin: HTTP 403 Forbidden ("Administrative privileges required.")

---

## 7. Audit Ownership & IDOR Protection

All audit endpoints in `backend/src/api/server.py` now require `current_user: User = Depends(get_current_active_user)`:

| Endpoint | Protection Mechanism |
| :--- | :--- |
| `POST /audits` | Sets `created_by = current_user.id`. Any client-supplied `created_by` is discarded. |
| `GET /audits` | Regular users receive only their audits (`WHERE created_by = current_user.id`). Admins receive all audits. |
| `GET /audits/{id}` | Enforces `AuditJob.created_by == current_user.id`. Returns HTTP 404 if unowned. |
| `GET /audits/{id}/status` | Enforces ownership. Returns HTTP 404 if unowned. |
| `GET /audits/{id}/report` | Enforces ownership. Returns HTTP 404 if unowned. |
| `POST /audits/{id}/cancel` | Enforces ownership. Returns HTTP 404 if unowned. |
| `POST /audit` (Legacy) | Requires `get_current_active_user` to prevent auth bypass. |

---

## 8. Worker Decoupling

* **Independent Boundary:** The asynchronous background worker (`backend/src/worker/`) does not accept or inspect browser JWT tokens.
* **Database Trust:** When the API creates an audit, the server-verified `created_by` is persisted into PostgreSQL/SQLite. The worker consumes jobs by `audit_id` from Redis and updates the job state without touching authentication tokens.

---

## 9. Database Migrations

* **Migration Script:** `alembic/versions/002_add_users_table.py`
* **Schema Change:** Creates `users` table with indexes on `id` and `email` (unique).
* **Non-Destructive:** Existing `audit_jobs` and `evaluation_runs` tables are preserved with zero data loss.

---

## 10. Test Coverage & Validation

### Test Suite Growth
* **Before Phase 5.1:** 73 tests passing
* **After Phase 5.1–5.3:** **90 tests passing** (+17 new comprehensive security tests)

### New Security Test Suites
1. **`tests/test_auth.py` (10 tests):**
   - `test_password_hashing_and_verification`
   - `test_user_registration_success`
   - `test_duplicate_email_registration_rejected`
   - `test_login_valid_credentials`
   - `test_login_invalid_password`
   - `test_login_nonexistent_account`
   - `test_get_current_user_me_profile`
   - `test_missing_and_invalid_tokens`
   - `test_expired_token_rejected`
   - `test_inactive_user_rejected`
   - `test_admin_role_authorization`
2. **`tests/test_audit_ownership.py` (6 tests):**
   - `test_audit_creation_server_assigns_ownership`
   - `test_idor_get_audit_and_status`
   - `test_idor_report_endpoint`
   - `test_idor_cancel_endpoint`
   - `test_audit_listing_isolation`
   - `test_legacy_endpoint_authentication_enforced`

### Verification Summary
* **Backend:** 90/90 tests passing (`Ran 90 tests in 16.470s — OK`)
* **Compilation:** `python -m compileall backend main.py alembic tests` — PASS
* **Angular Tests:** 32/32 tests passing (`npm test -- --watch=false`) — PASS
* **Angular Production Build:** `ng build` — PASS (482.17 kB bundle)

---

## 11. Remaining Phase 5 Work

As planned, the following phases are intentionally postponed for upcoming stages:
* **Phase 5.4:** Evaluation authorization (associating evaluation runs with users while preserving global baselines).
* **Phase 5.5:** CORS configuration through environment variables, HTTP security headers, and SSRF CIDR checks.
* **Phase 5.6:** Angular frontend authentication (`AuthService`, `AuthInterceptor`, `AuthGuard`, Login & Register UI).
* **Phase 5.7:** Security test expansion.
* **Phase 5.8:** Production configuration hardening.
