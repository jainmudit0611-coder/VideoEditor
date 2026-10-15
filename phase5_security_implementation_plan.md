# Phase 5 — Security, Authentication & Authorization Implementation Plan
**Project:** Brand Guardian AI / VIDEO_AUDIT_PROJ  
**Document:** `phase5_security_implementation_plan.md`  
**Status:** PROPOSED & READY FOR REVIEW  

---

## 1. Overview & Strategy

This implementation plan defines the step-by-step roadmap to transition **Brand Guardian AI** from an open, unauthenticated prototype into a hardened, production-grade platform with:
* Secure JWT-based Authentication (OAuth2 Bearer standard)
* Role-Based Access Control (`USER`, `ADMIN`)
* Strict Row-Level Data Ownership & IDOR elimination
* Hardened CORS & Security Headers
* Reinforced SSRF protections
* Complete Angular 21 frontend integration with reactive auth state, HTTP interceptor, and route guards.

### Core Non-Breaking Principles
1. **Preserve LangGraph Compliance Workflow:** Agent graph execution, evidence verification, and report generation remain completely untouched.
2. **Preserve Redis Queue & Worker:** The worker remains decoupled; job serialization continues using existing schemas with trusted `created_by` attributes passed from the API.
3. **Preserve Evaluation Harness:** Benchmark evaluation metrics and runner execution remain intact.
4. **Preserve Test Suites:** All existing 73 backend unit tests and 32 Angular unit tests will continue passing. Test fixtures will be cleanly equipped with authentication mocks/headers.

---

## 2. Staged Implementation Sequence

```text
Phase 5.1  ──►  Authentication Foundation (Models, Hashing, JWT Utils, Migrations)
Phase 5.2  ──►  Auth Endpoints & Current-User Dependency Injection
Phase 5.3  ──►  Audit Ownership & IDOR Protection in Repositories/Routers
Phase 5.4  ──►  Evaluation Run Ownership & Baseline Segregation
Phase 5.5  ──►  CORS Hardening, Security Headers & SSRF Reinforcement
Phase 5.6  ──►  Angular Authentication (AuthService, Interceptor, Guards, Login UI)
Phase 5.7  ──►  Comprehensive Security Test Suite (401, 403, IDOR, SSRF, CORS)
Phase 5.8  ──►  Configuration, Verification & Final Delivery
```

---

### Phase 5.1: Authentication Foundation

#### Objectives
1. Create database model for user identity:
   * Fields: `id` (UUID), `email` (unique index), `hashed_password` (str), `full_name` (str), `role` (`USER` or `ADMIN`), `is_active` (bool), `created_at`, `updated_at`.
2. Implement cryptographic password hashing using `passlib[bcrypt]` or `pwdlib[argon2]`.
3. Implement JWT utility functions:
   * `create_access_token(data: dict, expires_delta: Optional[timedelta]) -> str`
   * `decode_access_token(token: str) -> dict`
   * Configurable secret `JWT_SECRET_KEY` and algorithm `HS256` in `Settings`.
4. Generate Alembic migration for the `users` table and foreign key reference on `audit_jobs.created_by`.

#### Affected Files
* `backend/src/config.py` — Add `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
* `backend/src/db/models.py` — Add `User` model, update `AuditJob.created_by` reference.
* `backend/src/security/` (New module):
  * `backend/src/security/passwords.py` — Hashing and verification.
  * `backend/src/security/tokens.py` — JWT creation and validation.
* `alembic/versions/` — New migration script for user table.

---

### Phase 5.2: Auth Endpoints & Current-User Dependency

#### Objectives
1. Define Pydantic request/response schemas:
   * `UserRegisterRequest`, `UserResponse`, `TokenResponse`, `LoginRequest`.
2. Implement Authentication router (`backend/src/api/auth_routes.py`):
   * `POST /auth/register` — Create new account (default role: `USER`).
   * `POST /auth/login` — Authenticate credentials, return JWT access token.
   * `GET /auth/me` — Return current authenticated user profile.
3. Build FastAPI dependency injection providers:
   * `get_current_user`: Extracts Bearer token via `OAuth2PasswordBearer`, verifies signature and expiration, retrieves user from database.
   * `get_current_active_user`: Ensures `user.is_active` is True.
   * `require_admin`: Verifies `user.role == "ADMIN"`, raises HTTP 403 Forbidden otherwise.

#### Affected Files
* `backend/src/api/auth_routes.py` (New file)
* `backend/src/api/dependencies.py` (New or updated dependencies)
* `backend/src/api/server.py` — Mount `/auth` router.

---

### Phase 5.3: Audit Ownership & IDOR Protection

#### Objectives
1. Bind audit creation directly to the authenticated user:
   * `POST /audits`: Read `current_user.id` from dependency. Never trust client-supplied `created_by`.
2. Update `AuditRepository` with row-level filtering:
   * `get(audit_id: str, owner_id: Optional[str] = None)`
   * `get_report(audit_id: str, owner_id: Optional[str] = None)`
   * `cancel(audit_id: str, owner_id: Optional[str] = None)`
   * `list(owner_id: Optional[str] = None, skip: int, limit: int)`
3. Enforce authorization rules in router:
   * Regular users (`USER`) can only read and cancel audits where `audit.created_by == current_user.id`.
   * Admins (`ADMIN`) can read and cancel any audit across the system.
   * If a user requests an audit ID belonging to another user, return HTTP 404 (or 403) to prevent enumeration.

#### Affected Files
* `backend/src/db/repositories.py`
* `backend/src/api/server.py` (Audit endpoints: `/audits`, `/audits/{id}`, `/audits/{id}/report`, `/audits/{id}/cancel`).

---

### Phase 5.4: Evaluation Run Ownership & Baseline Segregation

#### Objectives
1. Maintain global accessibility for standard benchmark datasets and baseline runs while protecting user-created runs.
2. Add `created_by` and `is_baseline: bool` to `EvaluationRun`:
   * Official baseline runs (`is_baseline=True`) are readable by all authenticated users.
   * Custom evaluation runs created by users are private to that user (unless Admin).
   * Creating a baseline run requires `require_admin`.
3. Update `EvaluationRepository` and `evaluation_routes.py` to filter accordingly.

#### Affected Files
* `backend/src/db/models.py` — Add `created_by`, `is_baseline` to `EvaluationRun`.
* `backend/src/db/evaluation_repository.py`
* `backend/src/api/evaluation_routes.py`

---

### Phase 5.5: CORS Hardening, Security Headers & SSRF Reinforcement

#### Objectives
1. **CORS Remediation:**
   * Replace `allow_origins=["*"]` with explicit configuration from `Settings.CORS_ORIGINS` (e.g. `http://localhost:4200,http://127.0.0.1:4200`).
   * Preserve `allow_credentials=True` safely with explicit origins.
2. **Security Headers Middleware:**
   * Add middleware setting:
     * `X-Content-Type-Options: nosniff`
     * `X-Frame-Options: DENY`
     * `Referrer-Policy: strict-origin-when-cross-origin`
     * `Content-Security-Policy: default-src 'self'` (configured for API)
3. **SSRF Reinforcement:**
   * Update `validate_video_url` in `server.py` to use Python `ipaddress` module.
   * Validate resolved IP addresses against `ipaddress.ip_network("172.16.0.0/12")`, `169.254.0.0/16`, `fe80::/10`, and reserved ranges.

#### Affected Files
* `backend/src/config.py`
* `backend/src/api/server.py`
* `backend/src/services/video_indexer.py`

---

### Phase 5.6: Angular Frontend Authentication

#### Objectives
1. Implement `AuthService` (`src/app/core/services/auth.service.ts`):
   * Reactive signal/observable tracking `currentUser`, `token`, `isAuthenticated`, `isAdmin`.
   * Methods: `login(email, password)`, `register(email, password, name)`, `logout()`.
   * Secure in-memory token retention with optional `sessionStorage` fallback.
2. Implement `AuthInterceptor` (`src/app/core/interceptors/auth.interceptor.ts`):
   * Clones outgoing requests and attaches `Authorization: Bearer <token>` when authenticated.
   * Handles 401 Unauthorized responses by clearing auth state and routing to `/login`.
3. Implement `AuthGuard` (`src/app/core/guards/auth.guard.ts`):
   * Guards routes (`/audits`, `/evaluations`) from unauthenticated access.
4. Implement Login / Register Components:
   * Clean, brand-aligned modal or page for signing in.
   * Header integration displaying user avatar, name, and logout button.

#### Affected Files
* `frontend-angular/src/app/core/services/auth.service.ts`
* `frontend-angular/src/app/core/interceptors/auth.interceptor.ts`
* `frontend-angular/src/app/core/guards/auth.guard.ts`
* `frontend-angular/src/app/features/auth/`
* `frontend-angular/src/app/layout/header/header.component.ts`
* `frontend-angular/src/app/app.routes.ts`

---

### Phase 5.7: Comprehensive Security Test Suite

#### Objectives
1. **Authentication Tests:**
   * 401 on unauthenticated access to `/audits`, `/audits/{id}`, `/api/evaluations/runs`.
   * Successful registration and login generating valid JWT.
   * Rejection of expired, forged, or malformed tokens.
2. **Authorization & IDOR Tests:**
   * User A creates audit; User B cannot read `GET /audits/{UserA_id}` (returns 404/403).
   * User B cannot cancel `POST /audits/{UserA_id}/cancel`.
   * Admin can read and cancel audits of any user.
3. **CORS & SSRF Tests:**
   * Verification of rejection for `172.17.0.1`, `fe80::1`, cloud metadata IP.
   * Verification of allowed origins headers in responses.
4. **Angular Tests:**
   * Unit tests for `AuthService`, `AuthInterceptor`, and `AuthGuard`.

#### Affected Files
* `tests/test_auth.py` (New test suite)
* `tests/test_idor.py` (New test suite)
* `tests/test_ssrf.py` (Extended test cases)
* `frontend-angular/src/app/core/services/auth.service.spec.ts`

---

### Phase 5.8: Production Configuration & Validation

#### Objectives
1. Verify database migration scripts with SQLite and PostgreSQL compatibility.
2. Run full test suite:
   * Python backend tests (ensure >85 tests passing).
   * Angular unit tests (ensure >40 tests passing).
   * Full frontend build validation.
3. Update documentation with authentication guide and API credentials.

---

## 3. Rollback & Contingency Plan
* Each sub-phase is isolated behind version-controlled branches/commits.
* Test suite mocks allow testing of underlying workflow nodes independently of authentication headers.
* Existing public health endpoints (`/health/ready`) remain unauthenticated for load-balancer probes.
