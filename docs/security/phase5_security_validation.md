# Brand Guardian AI — Phase 5.7 & Phase 5.8: Expanded Security Validation & Production Configuration

## Executive Summary

This document details the expanded security verification (Phase 5.7) and production configuration hardening (Phase 5.8) for **Brand Guardian AI** (`VIDEO_AUDIT_PROJ`). 

The security architecture establishes that **FastAPI authentication and authorization serve as the sole authoritative security boundary**, while the Angular client provides UX and navigation controls.

```text
Overall Status:
PHASE_5_7_STATUS = COMPLETE
PHASE_5_8_STATUS = COMPLETE
```

---

## 1. Authentication Architecture

### 1.1. JWT & Cryptographic Standards
* **Algorithm**: HMAC-SHA256 (`HS256`).
* **Signature Verification**: Validated strictly against server-configured `JWT_SECRET_KEY`.
* **Token Expiration**: Enforced by PyJWT (`exp` claim); expired tokens immediately return `401 Unauthorized` with `Token has expired`.
* **Identity Claims**: Tokens encode `sub` (User UUID), `email`, and `role`.
* **Server-Side Authoritative State**: While tokens carry a `role` claim for client convenience, all backend role-sensitive operations (`require_admin`) re-verify the active database record in PostgreSQL/SQLite. Forged token claims for non-admin accounts are immediately rejected.
* **Inactive User Handling**: Valid JWTs associated with inactive accounts (`is_active=False`) are rejected at the `get_current_active_user` dependency with `403 Forbidden` (`Inactive user account`).

### 1.2. Password Hashing & Verification
* **Algorithm**: `bcrypt` via standard salt generation and key stretching.
* **Storage**: Password hashes are stored in `users.password_hash`. Plaintext passwords are never persisted, cached, or logged.
* **Generic Responses**: Failed login attempts return a uniform `401 Unauthorized` (`Incorrect email or password.`) to prevent account enumeration.

---

## 2. Authorization & IDOR Protection

### 2.1. Audit Ownership & IDOR Protection
* **Ownership Derivation**: Audit records derive `created_by` exclusively from the authenticated user's JWT. Payload parameters such as `{"created_by": "attacker_or_victim"}` are completely ignored.
* **Resource Isolation**:
  * `GET /audits/{id}`: Scoped strictly to the record owner or an `ADMIN`. Non-owners receive `404 Not Found` (preventing ID enumeration).
  * `GET /audits/{id}/status`: Scoped to owner; non-owners receive `404 Not Found`.
  * `GET /audits/{id}/report`: Scoped to owner; non-owners receive `404 Not Found`.
  * `POST /audits/{id}/cancel`: Scoped to owner; non-owners receive `404 Not Found`.
  * `GET /audits`: Queries are filtered server-side by `created_by = current_user.id` for standard users. Admins can view all audits.
  * Legacy `POST /audit`: Enforces authentication and associates execution with the user.

### 2.2. Evaluation Authorization & Baseline Access
* **Role Separation**:
  * **USER**: Can create personal evaluation runs, view their own private runs, and view official baseline runs (`is_baseline=True`). Attempting to set `is_baseline=True` without admin privileges returns `403 Forbidden`. Attempting to access another user's private run returns `404 Not Found`.
  * **ADMIN**: Can designate benchmark runs as official baselines (`is_baseline=True`), inspect all evaluation runs across the organization, and run multi-run comparisons.
* **Comparison Guard**: `GET /api/evaluations/compare?run_ids=id1,id2` validates ownership for *every* requested run ID. If any ID belongs to another user's private run, the request returns `404 Not Found`.

---

## 3. CORS Configuration

* **Origin Whitelist**: Configured through `settings.CORS_ORIGINS` (comma-separated list).
  * Development defaults: `http://localhost:4200,http://127.0.0.1:4200`.
  * Production: Explicit domains (e.g. `https://app.brandguardian.ai`).
* **Credentials Support**: `allow_credentials=True` is enabled.
* **No Wildcard with Credentials**: In adherence with CORS specifications, wildcard `*` is explicitly blocked from being used when credentials are required.
* **Allowed Headers**: Explicitly whitelisted (`Authorization`, `Content-Type`, `Idempotency-Key`).
* **Allowed Methods**: Whitelisted (`GET`, `POST`, `OPTIONS`).

---

## 4. Defense-in-Depth HTTP Security Headers

FastAPI HTTP middleware applies the following security headers across all responses:
* `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing.
* `X-Frame-Options: DENY`: Protects against clickjacking attacks.
* `Referrer-Policy: strict-origin-when-cross-origin`: Restricts referrer information sent with outbound links.
* `Content-Security-Policy: default-src 'self'`: Restricts unauthorized script and resource execution.
* `Strict-Transport-Security: max-age=31536000; includeSubDomains`: Automatically injected on all HTTPS requests.

---

## 5. SSRF & DNS-Rebinding Protection

### 5.1. Network Filter Engine
All target video URLs submitted to the platform pass through `validate_video_url()` before any network ingestion or processing:
1. **Protocol Validation**: Strictly restricts protocols to `http://` and `https://`. Protocols such as `file:///`, `ftp://`, `gopher://`, `data:`, and `javascript:` are rejected with `400 Bad Request`.
2. **Length Limit**: URLs exceeding 2048 characters are rejected with `400 Bad Request` / `422 Unprocessable Content`.
3. **Restricted IP Literals**: Rejects direct IP connections across:
   * Loopback (`127.0.0.0/8`, `::1`)
   * Unspecified (`0.0.0.0`, `::`)
   * RFC 1918 Private Ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
   * Cloud Metadata Link-Local (`169.254.0.0/16`, `fe80::/10`)
   * IPv6 Unique Local (`fc00::/7`)
   * Multicast & Reserved ranges (`224.0.0.0/4`, `240.0.0.0/4`)
4. **DNS Resolution & Rebinding Check**: Resolves target hostnames using `socket.getaddrinfo` and inspects **every** resolved IP address. If any returned IP belongs to a restricted subnet, the connection is aborted with `400 Bad Request`.

### 5.2. Remaining SSRF Limitation
> **Documented Limitation**: While direct SSRF connections and initial hostname resolutions are blocked by `validate_video_url()`, the downstream video extractor (`yt-dlp`) operates in its own subprocess. If a malicious video extractor or remote streaming server issues an HTTP 302 redirect after initial resolution, certain extractor-controlled requests may follow redirects outside the Python validator. Complete mitigation of downstream worker egress requires network-level egress firewalls or dedicated container network isolation.

---

## 6. Secret & Configuration Audit

A repository-wide automated scan was conducted for exposed credentials, API keys, private keys, and hardcoded tokens:
* **Scan Results**:
  * `.env`: Contains only empty variable definitions (`AZURE_OPENAI_API_KEY=""`, etc.). No live keys exist in `.env`.
  * `backend/src/config.py`: Contains a clearly marked development placeholder for `JWT_SECRET_KEY` (`"brand-guardian-dev-insecure-secret-key-change-in-prod"`).
  * **No active cloud secrets, API keys, private keys, or passwords were found checked into Git**.
* **Recommendation**: Production deployments must supply real secrets via runtime environment variables or Azure Key Vault secrets, never checking them into version control.

---

## 7. Production Configuration & Validation (Phase 5.8)

### 7.1. Settings Model Enhancements (`backend/src/config.py`)
* `ENVIRONMENT`: `"development"` | `"staging"` | `"production"`.
* `DEBUG`: `bool` (default `False`).
* `ALLOWED_HOSTS`: Comma-separated allowed hostnames.
* `validate_production_configuration(raise_on_error: bool)`:
  * When `ENVIRONMENT="production"`:
    * `JWT_SECRET_KEY` must not be a known development placeholder and must be at least 32 characters long.
    * `DATABASE_URL` must not be empty or in-memory SQLite (`:memory:`).
    * `REDIS_REQUIRED` must be `True` to prevent silent in-memory queue fallback.
    * `CORS_ORIGINS` must not contain wildcard (`*`) and must be non-empty.
    * `DEBUG` must be `False`.

### 7.2. Redis Production Behavior
* **Development Mode**: When Redis is offline and `REDIS_REQUIRED=False`, the application falls back to an internal thread-safe in-memory queue for offline prototyping.
* **Production Mode**: When `REDIS_REQUIRED=True`, if Redis is unavailable, requests fail fast with clear operational alerts and no silent in-memory fallback.

### 7.3. Alembic Database Migrations Review
All Alembic migrations were reviewed for sequencing and relational integrity:
1. `001_initial_audit_jobs`: Creates `audit_jobs` table with indexes on `id`, `status`, `created_at`, `idempotency_key`.
2. `002_add_users_table`: Creates `users` table with unique index on `email` and foreign-key target for audit jobs.
3. `003_add_evaluation_ownership`: Adds `created_by` and `is_baseline` to `evaluation_runs` with composite indexes.
* Migrations apply in strict sequence without circular dependencies or table drops.

---

## 8. Verification & Test Execution Results

### 8.1. Backend Test Suite
Executed using `python -m unittest discover -s tests -p "test_*.py"`:
```text
Ran 168 tests in 44.342s
OK
```
* **Existing Baseline Tests**: 100 tests.
* **New Security Test Suite (`tests/security/`)**: 68 tests.
  * `test_auth_security.py`: 15 tests (Registration, login, JWT validation, role claims, account status).
  * `test_authorization.py`: 7 tests (Audit IDOR, ownership spoofing, listing isolation, admin access).
  * `test_evaluation_authorization.py`: 7 tests (Baseline protection, comparison privacy, ownership derivation).
  * `test_role_escalation.py`: 4 tests (Registration tampering, token role forgery, query param tampering).
  * `test_cors.py`: 6 tests (Approved origins, rejected origins, preflight checks, wildcard prevention).
  * `test_security_headers.py`: 3 tests (X-Content-Type, X-Frame-Options, CSP, HSTS on HTTPS).
  * `test_ssrf.py`: 11 tests (IPv4, IPv6, named hosts, protocol blocking, DNS rebinding).
  * `test_input_validation.py`: 8 tests (Oversized URLs, malformed UUIDs, malformed JSON, negative pagination).
  * `test_configuration_security.py`: 7 tests (Production validation, dev defaults, secret checks).
* **Total Backend Tests**: **168 / 168 passed (100% PASS)**.

### 8.2. Python Compileall Check
Executed using `python -m compileall backend main.py alembic tests`:
```text
Listing 'backend'...
Listing 'backend/data'...
Listing 'backend/evaluation'...
Listing 'backend/scripts'...
Listing 'backend/src'...
Listing 'alembic'...
Listing 'tests'...
Listing 'tests/evaluation'...
Listing 'tests/security'...
Exit Code: 0 (PASS)
```

### 8.3. Angular Unit Tests
Executed using `npm test -- --watch=false` in `frontend-angular/`:
```text
Test Files  14 passed (14)
     Tests  64 passed (64)
Duration    4.83s
Exit Code: 0 (PASS)
```

### 8.4. Angular Production Build
Executed using `npm run build` in `frontend-angular/`:
```text
Application bundle generation complete. [3.953 seconds]
Output location: dist/frontend-angular
Exit Code: 0 (PASS)
```
