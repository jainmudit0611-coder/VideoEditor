# Phase 5.4–5.5 — Evaluation Authorization, CORS, Security Headers & SSRF Hardening Report

**Project:** Brand Guardian AI / VIDEO_AUDIT_PROJ  
**Implementation Phases:** 5.4 (Evaluation Authorization & Baseline Model), 5.5 (CORS, Security Headers & SSRF Hardening)  
**Status:** COMPLETE  
**Date:** September 2026  

---

## 1. Evaluation Authorization Architecture

### 1.1 Conceptual Ownership Model
The evaluation framework distinguishes between personal evaluations and administrator-designated baselines without modifying the shared benchmark dataset:

```text
                        ┌── Personal Evaluation Run (owned by USER)
Benchmark Dataset ──────┤
(Shared Artifact)       └── Official Reference Baseline (ADMIN designated)
```

* **Dataset:** The manually curated benchmark dataset (`backend/evaluation/cases/`) remains a shared, global artifact providing standard ground-truth evaluation cases.
* **Evaluation Run:** An individual execution of the `EvaluationSuiteRunner` producing reproducible metrics and discrepancies.
* **Baseline Semantics:** An official baseline is an administrator-designated reference run (`is_baseline=True`). It serves as an authoritative benchmark for regressions and comparisons; it is not merely labelled "the best run" or "winner".

### 1.2 Evaluation Data Model & Migration
Updated `backend/src/db/models.py` on entity `EvaluationRun`:
* `created_by = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)`
* `is_baseline = Column(Boolean, default=False, nullable=False, index=True)`
* Composite Index: `Index("idx_eval_run_owner_baseline", "created_by", "is_baseline")`
* **Migration:** Created [`alembic/versions/003_add_evaluation_ownership.py`](file:///d:/VIDEO_AUDIT_PROJ-20260921T163902Z-1-001/VIDEO_AUDIT_PROJ/alembic/versions/003_add_evaluation_ownership.py) adding `created_by` and `is_baseline` non-destructively.

### 1.3 Role Permissions Matrix

| Endpoint | `USER` Role | `ADMIN` Role |
| :--- | :--- | :--- |
| `POST /api/evaluations/runs` | Creates personal run (`is_baseline=False`). Submitting `is_baseline=True` raises **HTTP 403 Forbidden**. | Creates run; can set `is_baseline=True` or `False`. |
| `GET /api/evaluations/runs` | Receives only own runs (`created_by == current_user.id`) + official baselines (`is_baseline == True`). | Receives all runs across all users. |
| `GET /api/evaluations/runs/{id}` | Allowed if owner or if baseline; otherwise returns **HTTP 404 Not Found**. | Allowed for all runs. |
| `GET /api/evaluations/runs/{id}/status` | Allowed if owner or if baseline; otherwise returns **HTTP 404 Not Found**. | Allowed for all runs. |
| `GET /api/evaluations/compare` | Allowed only if **all** requested `run_ids` are owned or baseline. If any run is unauthorized, returns **HTTP 404 Not Found**. | Allowed to compare any runs. |

### 1.4 Service & Repository Boundary
In `backend/src/db/evaluation_repository.py`:
* `get_run(session, run_id, current_user_id=None, is_admin=False)`: Row-level filter `WHERE id = :id AND (created_by = :uid OR is_baseline = True)`.
* `list_runs(session, current_user_id=None, is_admin=False, ...)`: Filters `(created_by == current_user_id) | (is_baseline == True)` when not admin, while preserving `dataset_version`, `status`, and `model_name` filtering.

---

## 2. CORS Hardening

### 2.1 Audit Finding & Remediation
* **Audit Finding:** The previous configuration hardcoded `allow_origins=["*"]` with `allow_credentials=True`. This is insecure and causes browser rejections when Authorization headers are present.
* **Remediation:**
  * Added `CORS_ORIGINS: str = "http://localhost:4200,http://127.0.0.1:4200"` in `backend/src/config.py`.
  * Configured FastAPI `CORSMiddleware`:
    ```python
    cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )
    ```
* **Production Behavior:** In production, `CORS_ORIGINS` is configured via environment variables to specify explicit trusted production domains (e.g. `https://brandguardian.ai`). Wildcard origins with credentials are eliminated.

---

## 3. Defense-in-Depth Security Headers

Implemented via asynchronous FastAPI middleware in `backend/src/api/server.py`:

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

* **`X-Content-Type-Options: nosniff`**: Prevents MIME-type sniffing attacks.
* **`X-Frame-Options: DENY`**: Eliminates clickjacking risks by preventing iframe embedding.
* **`Referrer-Policy: strict-origin-when-cross-origin`**: Protects privacy while retaining essential referrer data for navigation.
* **`Content-Security-Policy: default-src 'self'`**: Restricts resource loading to self.
* **`Strict-Transport-Security` (HSTS)**: Only applied on HTTPS requests (`max-age=31536000; includeSubDomains`), ensuring local HTTP development is not disrupted.

---

## 4. SSRF Hardening & DNS Rebinding Guard

### 4.1 Reinforced Address Validation
The URL guard `validate_video_url` in `backend/src/api/server.py` was rebuilt using the standard library `ipaddress` and `socket` modules.

#### Blocked Address Classes
1. **RFC 1918 Private IPv4:**
   - `10.0.0.0/8`
   - `172.16.0.0/12` (covers Docker bridge networks e.g. `172.17.0.1`, `172.18.0.1`)
   - `192.168.0.0/16`
2. **Loopback:** `127.0.0.0/8`, `localhost`, `::1`
3. **Link-Local & Cloud Metadata:**
   - `169.254.0.0/16` (including Azure / AWS metadata `169.254.169.254`)
   - `fe80::/10` (IPv6 link-local)
   - `metadata.google.internal` (GCP metadata)
4. **Reserved & Unspecified:** `0.0.0.0/8`, `::`, `224.0.0.0/4` (multicast), `240.0.0.0/4` (reserved)
5. **IPv6 Unique-Local:** `fc00::/7`

### 4.2 DNS Rebinding Protection
* After checking raw IP literals, domain names are resolved via `socket.getaddrinfo(hostname, None)`.
* Every resolved socket address is checked against `_is_ip_restricted()`. If a domain resolves to an IP within any prohibited range, the request is rejected with `HTTP 400 Bad Request`.
* Validated in tests via DNS resolution mocking (`test_ssrf_dns_rebinding_prevention`).

### 4.3 Redirect Behavior & Residual Limitations
* **Pre-flight Validation:** `validate_video_url` validates URLs before background task dispatch or worker ingestion.
* **Downloader Scope:** `yt_dlp` is configured for video extraction. While pre-flight prevents passing private/loopback URLs, HTTP-level 302 redirects initiated inside third-party extractor plugins are governed by `yt_dlp`'s internal networking. Full redirect interception would require a custom Python `urllib` / `requests` transport adapter inside `yt_dlp`. This is documented as an acknowledged residual boundary.

---

## 5. Verification & Test Suite Summary

### Test Results
* **Backend Unit Tests:** **100/100 PASS** (`Ran 100 tests in 26.365s — OK`)
  - Original baseline: 73 tests
  - Phase 5.1–5.3 additions: 17 tests
  - Phase 5.4–5.5 additions: **10 new tests**
    - `tests/test_evaluation_auth.py` (5 comprehensive authorization tests)
    - `tests/test_security_hardening.py` (5 CORS, Security Headers, and SSRF tests)
* **Compileall:** `python -m compileall backend main.py alembic tests` — **PASS** (Exit code 0)
* **Angular Tests:** **32/32 PASS** (`npm test -- --watch=false` in `frontend-angular/`)
* **Angular Production Build:** `ng build` — **PASS** (482.39 kB bundle)

---

## 6. What Was NOT Changed

In strict adherence to the project constraints:
* LangGraph compliance agent workflow (`backend/src/graph/`) remains **completely unchanged**.
* Azure Video Indexer, OpenAI, and Search integrations remain **completely unchanged**.
* Redis queue and worker processor remain **completely unchanged**.
* Phase 4B evaluation metrics and test case suite remain **completely unchanged**.
* Phase 4C evaluation dashboard continues operating against the secure API contract.
* Docker production hardening remains **intentionally postponed**.
