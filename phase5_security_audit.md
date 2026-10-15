# Phase 5 — Comprehensive Security & Architecture Audit Report
**Project:** Brand Guardian AI / VIDEO_AUDIT_PROJ  
**Target:** Fast-API Backend, LangGraph Agent Workflow, Redis/Worker Pipeline, PostgreSQL Persistence, Angular 21 Frontend, Evaluation Framework  
**Status:** COMPLETE  
**Date:** September 2026  

---

## 1. Executive Summary

A comprehensive architectural and security audit of the **Brand Guardian AI** platform was conducted prior to implementing authentication and authorization. The system is a multimodal, agentic video compliance platform featuring a FastAPI backend, asynchronous Redis task queue, worker process executing a LangGraph compliance workflow, PostgreSQL database with SQLAlchemy repositories, an independent AI evaluation harness, and an Angular 21 frontend.

### Primary Audit Verdict
* **Security Posture:** Zero authentication or authorization currently exists across any backend endpoint. All endpoints (`/audits`, `/audits/{id}`, `/api/evaluations/runs`, etc.) are publicly accessible without identity verification.
* **Data Isolation:** All audit jobs and evaluation runs are globally readable and mutable by anyone possessing or generating UUIDs (High Priority IDOR vulnerability).
* **CORS Insecurity:** CORS middleware in `backend/src/api/server.py` pairs `allow_origins=["*"]` with `allow_credentials=True`, which is an insecure configuration that browsers reject when credentials/tokens are used.
* **SSRF Protection:** URL validation exists and blocks common loopback and RFC 1918 addresses, but lacks CIDR range checking (missing `172.16.0.0/12`), link-local IPv6, and is vulnerable to DNS rebinding and redirect-based SSRF.
* **Positive Findings:** No live production credentials or secrets are committed to the repository; sensitive environment settings are masked; temporary video files and frames are strictly pruned in `finally` blocks; and SQLAlchemy parameterized queries prevent SQL injection.

---

## 2. Full Repository & Architecture Inspection

### 2.1 Backend Architecture
* **API Entrypoint (`backend/src/api/server.py`):**
  * Mounts FastAPI application.
  * Middleware: `CORSMiddleware` configured with wildcard origins and credentials enabled.
  * Dependency Injection: Provides `get_db` session generator, `get_audit_repository`, and queue dependencies.
  * No security headers middleware, no rate limiting middleware, no authentication dependencies.
* **Evaluation Routes (`backend/src/api/evaluation_routes.py`):**
  * Endpoints for running benchmarks (`POST /runs`), fetching status (`GET /runs/{id}/status`), full results (`GET /runs/{id}`), comparing runs (`GET /compare`), and listing runs (`GET /runs`).
  * Unauthenticated and accessible to any client.
* **Worker & Processor (`backend/src/worker/worker.py`, `backend/src/worker/processor.py`):**
  * Asynchronous Redis consumer with reliable ACK handling (`acknowledge_completed`, `acknowledge_failed`).
  * Deserializes JSON payloads from Redis queue without cryptographic signature. Assumes the worker and Redis operate within an isolated, trusted boundary.
* **Database & Persistence (`backend/src/db/models.py`, `backend/src/db/repositories.py`, `backend/src/db/evaluation_repository.py`):**
  * `AuditJob`: Has a `created_by: str` column with default `"system"`. It is populated via request body if supplied, but never verified or used for row-level access control.
  * `EvaluationRun`: Contains benchmark metrics and test case results, but has no `created_by` or owner association.
* **Configuration & Secret Handling (`backend/src/config.py`):**
  * Pydantic `BaseSettings` reading from `.env`.
  * Secrets masked in `validate_environment()`: returns `"configured"` or `"missing"` without exposing string values.

### 2.2 Frontend Architecture (`frontend-angular/`)
* **Core Services (`src/app/core/services/`):**
  * `ApiService`: Centralized HTTP client wrapping Angular `HttpClient`.
  * `AuditService`: Manages audit creation, polling, cancellation, and report retrieval.
  * `EvaluationService`: Manages evaluation execution, run retrieval, and comparisons.
* **Auth State:**
  * No `AuthService`, no `AuthInterceptor`, no route guards (`canActivate`), no user profile components.
  * UI routes (`/audits`, `/audits/:id`, `/evaluations`) are completely open.

### 2.3 Containers & Environment
* `docker-compose.yml`: Defines `postgres` (password `postgrespassword`), `redis`, `api`, `worker`, and `frontend`. Environment credentials are placeholders.
* `Dockerfile`: Multi-stage build for Python backend and frontend.

---

## 3. Security Threat Model

| Asset | Sensitivity | Threats & Impact |
| :--- | :--- | :--- |
| **Azure Video Indexer Credentials** | Critical | Account takeover, quota exhaustion, unauthorized video indexing |
| **Azure OpenAI Credentials** | Critical | API quota theft, prompt injection abuse, unauthorized model inference |
| **PostgreSQL Database** | Critical | Data exfiltration, cross-tenant audit access, deletion of compliance records |
| **Redis Queue** | High | Queue poisoning, unauthorized job dispatch, DoS via payload flooding |
| **Audit Reports & Evidence** | High | Leakage of pre-release advertising campaigns, non-public media disclosures |
| **Evaluation Benchmarks** | Medium | Tampering with compliance benchmark standards and baseline metrics |
| **User Identity & Passwords** | Critical | Credential stuffing, account compromise, impersonation |

### Threat Vectors Evaluated

#### A. Authentication
* **Unauthenticated API Access:** Any internet-facing client can invoke audit jobs, trigger expensive Azure OpenAI calls, and read reports.
* **Forged Identity:** Clients can set `"created_by": "admin"` in `POST /audits` without verification.

#### B. Authorization & IDOR
* **Cross-User Audit Access:** Knowing an `audit_id` (UUIDv4) allows any user to inspect the audit report, view video evidence, or cancel the ongoing audit (`POST /audits/{id}/cancel`).
* **Cross-User Evaluation Access:** Anyone can list, inspect, or trigger evaluation runs without administrative authorization.

#### C. SSRF (Server-Side Request Forgery)
* **Current Check:** `validate_video_url` checks protocol (`http`/`https`) and blocks `localhost`, `127.0.0.1`, `0.0.0.0`, `::1`, `169.254.169.254`, `192.168.*`, `10.*`.
* **Gaps:**
  1. `172.16.0.0/12` (private Class B network, commonly used by Docker default bridges like `172.17.0.1`) is **not** blocked.
  2. IPv6 link-local addresses (`fe80::*`) and decimal/octal/hex IP encodings are not explicitly resolved.
  3. **DNS Rebinding & Redirects:** `yt_dlp` resolves and fetches URLs in a separate network step. A malicious domain pointing to a public IP during validation can rebind to `127.0.0.1` or redirect to cloud metadata (`http://169.254.169.254/latest/meta-data/`).

#### D. Input Abuse & Resource Exhaustion
* **Payload Limits:** Request bodies in FastAPI are not bounded by an explicit max body size middleware.
* **Video Duration / Size:** Limits defined in `Settings` (`MAX_VIDEO_SIZE_MB: 500`, `MAX_VIDEO_DURATION_SECONDS: 3600`), but validation occurs post-download rather than during URL pre-flight inspection.

#### E. Video Processing & OpenCV Safety
* **Protected:** OpenCV keyframe extraction writes images to isolated temporary directories (`tempfile.mkdtemp(prefix="brand_guardian_frames_")`).
* **Protected:** Both the temporary frame directory and downloaded MP4 files are cleanly removed in `finally` blocks in `backend/src/graph/nodes.py`.

#### F. Logging & Information Leakage
* **Protected:** Secrets are not logged in standard startup logs.
* **Concern:** Exception traces on unexpected 500 errors could expose internal file paths or database host names if not caught by a global exception handler.

---

## 4. Current Authentication & Authorization State

| Question | Current Implementation Status |
| :--- | :--- |
| **Is there authentication?** | **NO**. Zero authentication. |
| **Is there authorization?** | **NO**. Zero authorization checks on any route. |
| **Is there a user model?** | **NO**. Neither in SQLAlchemy models nor in Alembic migrations. |
| **Is there a user ID on `audit_jobs`?** | `created_by` column exists as a plain string, defaulting to `"system"`. |
| **Is `created_by` enforced?** | **NO**. It is not verified against any authenticated principal. |
| **Is `created_by` trusted from client?** | **YES** (Vulnerability). Clients can submit arbitrary string values. |
| **Are evaluation runs associated with users?** | **NO**. `EvaluationRun` has no user association. |
| **Are APIs publicly callable?** | **YES**. 100% of endpoints are unauthenticated. |
| **Does Angular have an auth service?** | **NO**. |
| **Does Angular have an HTTP interceptor?** | **NO**. |
| **Are protected routes defined in Angular?** | **NO**. All routes load without guards. |

### Current Request Flow vs Target Secure Request Flow

```text
CURRENT (INSECURE):
Angular UI (Public)
  ↓ (No Auth Header)
FastAPI Router (No Dependency)
  ↓
Service / Queue
  ↓
Repository (SELECT * FROM audit_jobs WHERE id = :id) -- NO USER CHECK!
  ↓
PostgreSQL

TARGET (SECURE PHASE 5):
Angular UI (AuthService + AuthInterceptor)
  ↓ Bearer JWT Token
FastAPI Router (Depends(get_current_active_user))
  ↓ CurrentUser(id, email, role)
Service
  ↓
Repository (SELECT * FROM audit_jobs WHERE id = :id AND created_by = :user_id) [or Admin Bypass]
  ↓
PostgreSQL
```

---

## 5. Data Ownership Audit & IDOR Vulnerabilities

### Current Schema Inspection
1. **`AuditJob` Model (`backend/src/db/models.py`):**
   ```python
   class AuditJob(Base):
       id = Column(String(36), primary_key=True)  # UUID
       created_by = Column(String(100), nullable=True, default="system")
   ```
2. **`AuditRepository` Methods (`backend/src/db/repositories.py`):**
   * `get(audit_id: str) -> Optional[AuditJob]`: Queries strictly by `id`.
   * `get_report(audit_id: str) -> Optional[AuditReport]`: Queries strictly by `audit_id`.
   * `cancel(audit_id: str) -> bool`: Cancels strictly by `audit_id`.
   * `list(skip, limit) -> List[AuditJob]`: Returns all audits across all users!

### Critical IDOR Impact
* **`GET /audits/{id}`**: Any user can view metadata of any audit job.
* **`GET /audits/{id}/report`**: Any user can view full compliance findings, transcript, and OCR evidence of any audit job.
* **`POST /audits/{id}/cancel`**: Any user can cancel any other user's active compliance audit.
* **`GET /audits`**: Enumerates all audits submitted by all users.

### Ownership Model Recommendation
For Brand Guardian AI, a clean and robust model is:
```text
User (id, email, hashed_password, role, is_active)
 ├── AuditJobs (created_by = User.id)
 └── EvaluationRuns (created_by = User.id, or is_baseline=True for global)
```
* **Regular Users (`USER`):** Can only view, create, and cancel their own audits and personal evaluation runs.
* **Administrators (`ADMIN`):** Can view all audits, inspect system health, trigger official baseline evaluation runs, and manage users.

---

## 6. CORS & Secret Management Audit

### 6.1 CORS Configuration Audit
* **Current Setting in `backend/src/api/server.py`:**
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
* **Security Flaw:** Under W3C CORS specifications, `Access-Control-Allow-Origin: *` cannot be combined with `Access-Control-Allow-Credentials: true`. Modern browsers will block requests with credentials or Authorization headers under this wildcard configuration.
* **Recommended Mitigation:**
  Configure allowed origins strictly via environment variable `CORS_ORIGINS` (defaulting to `http://localhost:4200,http://127.0.0.1:4200` in development).

### 6.2 Secret Inventory & Validation
* **Configuration Keys Inventory:**
  * `AZURE_OPENAI_API_KEY` (Server-only secret)
  * `AZURE_OPENAI_ENDPOINT` (Server-only configuration)
  * `AZURE_VI_API_KEY` (Server-only secret)
  * `DATABASE_URL` (Server-only secret containing DB credentials)
  * `REDIS_URL` (Server-only configuration)
  * `JWT_SECRET_KEY` (New server-only secret required for Phase 5)
* **Committed Secrets Audit:**
  * Checked `.env`: Only placeholder tokens present. No actual production secrets committed.
  * Checked `docker-compose.yml`: Default Postgres credentials (`postgrespassword`) present for local containerization.
  * Checked Frontend: Angular `environment.ts` contains only `apiUrl: 'http://localhost:8000'`. No secrets bundled.

---

## 7. Classified Findings Summary

| ID | Category | Severity | Finding & Location | Impact | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Authentication | **CRITICAL** | Total absence of authentication across all FastAPI endpoints (`server.py`, `evaluation_routes.py`) | Any unauthenticated client can invoke AI workflows and consume Azure budget | **OPEN** |
| **SEC-02** | Authorization | **CRITICAL** | IDOR vulnerability on Audit endpoints (`/audits/{id}`, `/cancel`, `/report`) | Cross-tenant data exposure and unauthorized audit cancellation | **OPEN** |
| **SEC-03** | Authorization | **HIGH** | IDOR vulnerability on Evaluation endpoints (`/api/evaluations/runs/{id}`) | Unauthorized access to benchmark metrics and test case evaluations | **OPEN** |
| **SEC-04** | Configuration | **HIGH** | Insecure CORS configuration (`allow_origins=["*"]` + `allow_credentials=True`) | Browser CORS rejection with auth headers; potential cross-origin leaks | **OPEN** |
| **SEC-05** | SSRF | **MEDIUM** | URL validator missing `172.16.0.0/12` and DNS rebinding protections (`server.py`) | Potential SSRF into internal Docker containers or VPC services | **OPEN** |
| **SEC-06** | Headers | **LOW** | Missing HTTP Security Headers (CSP, HSTS, X-Content-Type-Options) | Missing defense-in-depth protection against clickjacking and MIME sniffing | **OPEN** |
| **SEC-07** | DoS / Limits | **LOW** | Request body size limit not enforced by middleware | Potential memory exhaustion from excessively large HTTP payloads | **OPEN** |
| **SEC-08** | Database | **PROTECTED** | Parameterized SQL queries via SQLAlchemy ORM | SQL Injection is prevented by design | **PROTECTED** |
| **SEC-09** | Filesystem | **PROTECTED** | Temporary video and keyframe directory cleanup in `finally` blocks | Disk space exhaustion and frame leakage prevented | **PROTECTED** |
| **SEC-10** | Secrets | **PROTECTED** | No live API keys or passwords committed in repo; masked in `Settings` | Secret leakage via Git history or startup logs prevented | **PROTECTED** |

---

## 8. Authentication & Authorization Recommendations

### Recommended Authentication Architecture: JWT Bearer (FastAPI + OAuth2PasswordBearer)
* **Choice:** JWT Bearer token authentication with local user management (email/password with bcrypt hashing).
* **Rationale:**
  1. **Self-Contained & Deterministic:** Does not require external SaaS identity providers (Auth0/Clerk/Entra ID) which would break local offline development and test suites.
  2. **FastAPI Native:** Built-in support via `OAuth2PasswordBearer` and `Depends`.
  3. **Angular Compatibility:** Cleanly attaches via an Angular `HttpInterceptorFn` without third-party SDK bloat.
  4. **Production Ready:** Can easily be transitioned to asymmetric RSA/JWKS validation or federated Azure AD if desired in future enterprise deployments.

### Recommended Authorization Model: Role-Based & Row-Level Ownership
* **Roles:** `USER` (default), `ADMIN`.
* **Row-Level Ownership Matrix:**

| Endpoint / Operation | USER Role | ADMIN Role |
| :--- | :--- | :--- |
| `POST /auth/register` & `/login` | Public | Public |
| `POST /audits` | Allowed (assigned to user) | Allowed (assigned to admin) |
| `GET /audits` | Lists only user's audits | Lists all audits in system |
| `GET /audits/{id}` | Allowed only if owner | Allowed for all audits |
| `GET /audits/{id}/report` | Allowed only if owner | Allowed for all audits |
| `POST /audits/{id}/cancel` | Allowed only if owner | Allowed for all audits |
| `POST /api/evaluations/runs` | Allowed (user runs) | Allowed (can set baseline) |
| `GET /api/evaluations/runs` | Lists own + public baseline runs | Lists all runs |
| `GET /api/evaluations/runs/{id}` | Allowed if owner or baseline | Allowed for all runs |
| `GET /health/ready` | Public / Monitoring | Public / Monitoring |
