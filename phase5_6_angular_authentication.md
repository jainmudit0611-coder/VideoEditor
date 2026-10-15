# Phase 5.6 — Angular Authentication, Interceptor, Guards & Login UI

## Executive Summary

Phase 5.6 introduces frontend authentication into **Brand Guardian AI** (`VIDEO_AUDIT_PROJ`). The Angular frontend now integrates seamlessly with the authoritative FastAPI JWT authentication foundation established in Phases 5.1–5.5.

**Status**: `PHASE_5_6_STATUS = COMPLETE`

---

## 1. Frontend vs. Backend Security Boundary

> **CRITICAL SECURITY PRINCIPLE**:
> Angular route guards and UI state are **UX protection only**; FastAPI authentication and authorization remain the sole authoritative security boundary.

* **Client (Angular)**: Responsible for capturing credentials, holding session tokens in memory/storage, attaching `Bearer <token>` headers, directing navigation based on authenticated status, and providing clear user feedback. It never attempts to determine record authorization on its own.
* **Server (FastAPI)**: Validates cryptographic JWT signatures, enforces token expiration, resolves the current active user from PostgreSQL, and authoritatively validates RBAC and audit/evaluation ownership for every request.

---

## 2. Authentication Architecture

```text
User Action (Login / Register)
             ↓
        AuthService
             ↓
   POST /auth/login or /auth/register
             ↓
    Store Access Token (localStorage + Signal)
             ↓
    GET /auth/me (Hydrate Profile)
             ↓
      Signals Updated:
  currentUser, token, isAuthenticated
             ↓
      Router Navigation
  (/dashboard or returnUrl)
```

### Request Flow
```text
HTTP Request from Angular Services (AuditService, EvaluationService)
             ↓
    authInterceptor
             ↓
Is target URL backend API origin?
  ├── Yes → Attach 'Authorization: Bearer <token>'
  └── No  → Pass untouched (prevent token leakage to third parties)
             ↓
FastAPI Backend
  ├── 200/201/202 → Successful response returned to caller
  ├── 401 Unauthorized → Clear session signals & localStorage → Redirect to /login?returnUrl=...
  └── 403 Forbidden → Propagate permission error to component (NO auto-logout)
```

---

## 3. Core Components & Implementation Details

### 3.1. Authentication Model (`core/models/auth.model.ts`)
Matches backend Pydantic schemas exactly:
* `UserRole`: `'USER' | 'ADMIN'`
* `User`: `{ id, email, display_name, role, is_active, created_at }`
* `TokenResponse`: `{ access_token, token_type }`
* `LoginRequest`: `{ email, password }`
* `RegisterRequest`: `{ email, password, display_name }`

### 3.2. AuthService (`core/services/auth.service.ts`)
* Implements reactive authentication state using Angular Signals:
  * `currentUser`: `Signal<User | null>`
  * `token`: `Signal<string | null>`
  * `isAuthenticated`: `Computed<boolean>` (`!!currentUser() && !token()`)
  * `isLoading`: `Signal<boolean>`
  * `isInitialized`: `Signal<boolean>`
* Key methods:
  * `login(credentials)`: Authenticates against `/auth/login`, saves token, and fetches active user via `loadCurrentUser()`.
  * `register(data)`: Posts to `/auth/register`.
  * `loadCurrentUser()`: Calls `GET /auth/me` to refresh the active profile.
  * `logout()`: Clears memory signals, removes stored token, and redirects to `/login`.
  * `clearSession()`: Clears state without navigation (used by interceptor upon 401).
  * `initAuth()`: Invoked on startup to hydrate session if a token exists in storage.

### 3.3. Token Storage Tradeoffs
* **Storage Medium**: `localStorage` key `bg_auth_token`.
* **Security Consideration & Tradeoff**:
  * For this portfolio architecture, `localStorage` provides persistent session capability across browser reloads without complex cookie setup.
  * *XSS Tradeoff*: Storing access tokens in `localStorage` exposes them to potential exfiltration if an XSS vulnerability exists. In future production hardening, HttpOnly cookies with `SameSite=Lax/Strict` and CSRF protection can be implemented.
  * No passwords, refresh tokens, or sensitive user secrets are ever stored in `localStorage`.
  * Tokens are never passed in URL route parameters or query strings.
  * Tokens and passwords are never logged to console or telemetry.

### 3.4. HTTP Interceptor (`core/interceptors/auth.interceptor.ts`)
* Uses modern Angular functional interceptor: `HttpInterceptorFn`.
* Inspects target URL: ensures `req.url.startsWith(environment.apiBaseUrl) || req.url.startsWith('/')` before attaching `Authorization: Bearer <token>`.
* Intercepts `401 Unauthorized` responses:
  * Clears session (`authService.clearSession()`).
  * If not already on `/login` or `/register`, navigates to `/login` preserving `returnUrl` query parameter.
* Handles `403 Forbidden` responses:
  * Preserves session and user identity; avoids treating lack of authorization for a specific action as session expiration.

### 3.5. Route Guards (`core/guards/auth.guard.ts` & `admin.guard.ts`)
* `authGuard`:
  * Verifies `authService.getAccessToken()`.
  * If unauthenticated, returns a `UrlTree` directing to `/login` with `queryParams: { returnUrl: state.url }`.
  * Protects:
    * `/dashboard`
    * `/audits/new`
    * `/audits/:id`
    * `/evaluations`
    * `/evaluations/:id`
* `adminGuard`:
  * Verifies `currentUser()?.role === 'ADMIN'`.
  * Returns `UrlTree` to `/dashboard` if user lacks admin role (UX routing defense only; FastAPI `require_admin()` remains authoritative).

### 3.6. App Shell & Layout Integration (`layout/`)
* **Header (`header.component.ts`)**:
  * Displays authenticated user `display_name` and a role badge (`USER` / `ADMIN`).
  * Provides a dedicated "Sign Out" button calling `authService.logout()`.
  * Preserves system health pills (API Online, DB status, Redis status).
* **Sidebar (`sidebar.component.ts`)**:
  * Preserves clean navigation: Dashboard, New Audit, Evaluations, History.
* **Layout (`layout.component.ts`)**:
  * Automatically detects `/login` and `/register` routes to suppress header/sidebar, rendering a distraction-free, full-screen authentication experience.

### 3.7. Authentication UI Pages (`features/auth/pages/`)
* **Login (`login.component.ts`)**:
  * Input validation, loading indicators (`Signing in...`), disabled duplicate submissions, clear error alerts for invalid credentials or server errors.
* **Register (`register.component.ts`)**:
  * Full name, email, password, and confirm password fields.
  * Client-side validation: required fields, 6-character minimum, password confirmation match.
  * Automatic sign-in and redirect to `/dashboard` upon successful registration.

---

## 4. Verification & Test Results

### 4.1. Angular Unit Tests
Executed via Vitest (`npm test -- --watch=false`):
```text
✓ src/app/features/audits/components/findings-list/findings-list.component.spec.ts (2 tests)
✓ src/app/core/services/evaluation.service.spec.ts (5 tests)
✓ src/app/shared/components/status-badge/status-badge.component.spec.ts (4 tests)
✓ src/app/features/evaluations/components/run-comparison/run-comparison.component.spec.ts (4 tests)
✓ src/app/features/audits/components/workflow-progress/workflow-progress.component.spec.ts (3 tests)
✓ src/app/core/guards/auth.guard.spec.ts (5 tests)
✓ src/app/core/services/audit.service.spec.ts (4 tests)
✓ src/app/core/interceptors/auth.interceptor.spec.ts (6 tests)
✓ src/app/core/services/auth.service.spec.ts (9 tests)
✓ src/app/app.spec.ts (2 tests)
✓ src/app/features/evaluations/pages/evaluations-dashboard/evaluations-dashboard.component.spec.ts (4 tests)
✓ src/app/features/audits/pages/new-audit/new-audit.component.spec.ts (4 tests)
✓ src/app/features/auth/pages/register/register.component.spec.ts (6 tests)
✓ src/app/features/auth/pages/login/login.component.spec.ts (6 tests)

Test Files  14 passed (14)
     Tests  64 passed (64)
```
* **Result**: **64 / 64 tests passing** (100% pass rate, zero failures).

### 4.2. Angular Production Build
Executed via `npm run build`:
```text
Application bundle generation complete. [3.792 seconds]
Output location: dist/frontend-angular
Exit Code: 0 (PASS)
```

### 4.3. Backend Regression Tests
Executed via `python -m unittest discover -s tests -p "test_*.py"`:
```text
Ran 100 tests in 25.307s
OK
```
* **Result**: **100 / 100 tests passing**.

### 4.4. Backend Compilation Check
Executed via `python -m compileall backend main.py alembic tests`:
```text
Exit Code: 0 (PASS)
```

---

## 5. Security Checklist Confirmation

* [x] **JWTs are not logged**: Verified; neither `AuthService` nor `authInterceptor` log token values.
* [x] **Passwords are not logged**: Verified; form components and services do not log plaintext passwords.
* [x] **JWTs are not placed in URLs**: Verified; tokens are sent strictly via the HTTP `Authorization: Bearer` header.
* [x] **Backend remains authorization boundary**: Verified; Angular guards serve UX navigation needs; backend enforces JWT validation, RBAC, and ownership on every route.
* [x] **401 clears invalid session**: Verified; interceptor and service wipe storage and signals on 401 and redirect to `/login`.
* [x] **403 does not log out**: Verified; forbidden access preserves session and does not clear user credentials.
* [x] **No refresh tokens implemented**: Verified; refresh token logic was intentionally excluded in accordance with project scope.

---

## 6. Next Steps

With Phase 5.6 complete and fully validated, the project is ready for:
* **Phase 5.7**: Expanded Security Testing (Automated IDOR testing, SSRF regression tests, authorization matrix verification).
* **Phase 5.8**: Production Configuration & Hardening.
