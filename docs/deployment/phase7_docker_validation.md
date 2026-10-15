# Brand Guardian AI — Phase 7: Dockerization & Container Architecture Guide

## Overview & Architecture

Phase 7 defines the containerized local production simulation architecture for **Brand Guardian AI**. The system transitions from separate local processes into a coordinated, multi-container microservice topology with persistent relational storage, persistent task queuing, background task execution, and client-side web serving.

```text
                                 Host Browser
                                      │
                   ┌──────────────────┴──────────────────┐
                   │                                     │
           (HTTP Port 80)                                │ (Direct API fallback)
                   │                                     │ (HTTP Port 8000)
                   ▼                                     ▼
        ┌─────────────────────┐               ┌─────────────────────┐
        │   Angular Frontend   │──Reverse────►│    FastAPI API      │
        │   (Nginx Container) │  Proxy       │   (ASGI Container)  │
        └─────────────────────┘  (/api, /auth)└──────┬───────┬──────┘
                                                     │       │
                                              ┌──────▼──┐ ┌──▼─────────┐
                                              │PostgreSQL│ │   Redis    │
                                              │(v16 DB) │ │(v7 Queue)  │
                                              └──────▲──┘ └──────┬──────┘
                                                     │           │
                                              ┌──────┴───────────▼──────┐
                                              │   Background Worker      │
                                              │  (LangGraph Container)  │
                                              └─────────────────────────┘
```

---

## Service Specifications

| Service | Base Image / Build Context | Container Name | Host Port | Role & Functionality | Health Check Probe |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`postgres`** | `postgres:16-alpine` | `brand_guardian_postgres` | `5432` | Relational persistence for audit jobs, user accounts, and benchmark evaluation runs. | `pg_isready -U postgres -d brand_guardian` |
| **`redis`** | `redis:7-alpine` | `brand_guardian_redis` | `6379` | High-throughput asynchronous audit job broker with AOF (`appendonly yes`) disk persistence. | `redis-cli ping` |
| **`migration`** | Multi-purpose Backend Image (`Dockerfile`) | `brand_guardian_migration` | *None* | Init container: executes `backend.scripts.init_db` to verify declarative schemas and synchronize Alembic version tracking to `head`. Exits cleanly (`restart: "no"`). | Container exit code 0 (`service_completed_successfully`) |
| **`api`** | Multi-purpose Backend Image (`Dockerfile`) | `brand_guardian_api` | `8000` | FastAPI ASGI web server running under production Uvicorn (non-reload, multi-worker). Exposes REST endpoints, authentication, and operator endpoints. | `curl -f http://localhost:8000/health/ready` |
| **`worker`** | Multi-purpose Backend Image (`Dockerfile`) | `brand_guardian_worker` | *None* | Autonomous background worker polling Redis queue. Executes LangGraph pipeline (Indexer, Frame Extraction, OCR/Vision, Planner, Auditor, Verifier, Report Generator). | Process supervisor / queue liveness |
| **`frontend`** | Multi-stage Angular Image (`frontend-angular/Dockerfile`) | `brand_guardian_frontend` | `80` | Multi-stage build (Node 22 compiler -> minimal Nginx runtime). Serves compiled Angular SPA and acts as reverse proxy for `/api/`, `/audits`, `/auth`, and `/health`. | `wget -q --spider http://localhost:80/` |

---

## Port Configuration

| Port | Protocol | Service | Exposure | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`80`** | HTTP | `frontend` | Public / Host | Main entry point for browser UI. |
| **`8000`** | HTTP | `api` | Public / Host | Direct REST API access, Swagger UI (`/docs`), and health endpoints. |
| **`5432`** | TCP | `postgres` | Public / Host (dev) | PostgreSQL database access for operators and DB tools. |
| **`6379`** | TCP | `redis` | Public / Host (dev) | Redis queue access and CLI inspection. |

---

## Startup & Orchestration

### 1. Build Container Images
```bash
docker compose build
```

### 2. Start the Stack
```bash
docker compose up -d
```

### 3. Verify Container Status
```bash
docker compose ps
```
Expected output:
```text
NAME                        IMAGE                    COMMAND                  SERVICE      STATUS
brand_guardian_postgres     postgres:16-alpine       "docker-entrypoint.s…"   postgres     Up (healthy)
brand_guardian_redis        redis:7-alpine           "docker-entrypoint.s…"   redis        Up (healthy)
brand_guardian_migration    video_audit_migration    "python -m backend.s…"   migration    Exited (0)
brand_guardian_api          video_audit_api          "uvicorn backend.src…"   api          Up (healthy)
brand_guardian_worker       video_audit_worker       "python -m backend.w…"   worker       Up (healthy)
brand_guardian_frontend     video_audit_frontend     "/docker-entrypoint.…"   frontend     Up (healthy)
```

### 4. Inspect Consolidated Logs
```bash
docker compose logs -f --tail=100
```

---

## Controlled Database Initialization & Migration Strategy

To prevent race conditions, deadlocks, and schema collisions when multiple service replicas start simultaneously:
1. `postgres` starts and completes initialization until `pg_isready` reports healthy.
2. The dedicated `migration` container starts, executing [`backend/scripts/init_db.py`](file:///d:/VIDEO_AUDIT_PROJ-20260921T163902Z-1-001/VIDEO_AUDIT_PROJ/backend/scripts/init_db.py):
   - Initializes tables from SQLAlchemy Declarative Base (`AuditJob`, `User`, `EvaluationRun`).
   - Stamps Alembic version tracking to `004_add_request_id` (`head`).
   - Exits with return code 0.
3. Both `api` and `worker` depend on `migration` with `condition: service_completed_successfully`. Neither starts until the database schema is confirmed ready.

---

## Health & Readiness Endpoints

The API container provides three health probes:

* **Basic Health (`GET /health`)**:
  Returns service name, version (`3.0.0`), and environment name.
  ```json
  {"status": "healthy", "service": "Brand Guardian AI Platform", "version": "3.0.0", "environment": "production"}
  ```

* **Liveness Probe (`GET /health/live`)**:
  Fast process ping returning `{"status": "alive"}` for Kubernetes/Docker container restart monitoring.

* **Readiness Probe (`GET /health/ready`)**:
  Verifies end-to-end operational readiness by executing `SELECT 1` on PostgreSQL and pinging the Redis queue.
  - Returns `200 OK` when both PostgreSQL and Redis are connected.
  - Returns `503 Service Unavailable` if PostgreSQL or Redis is unreachable when `REDIS_REQUIRED=true`.

---

## Security Hardening in Containers

1. **Non-Root Execution**:
   The backend Dockerfile creates and switches to a dedicated unprivileged user (`appuser:appgroup`, UID/GID 10001).
2. **Zero Credentials in Images**:
   No `.env` files or secrets are baked into images. All configuration parameters (`JWT_SECRET_KEY`, database passwords, Redis credentials) are passed at runtime via container environment variables.
3. **Production CORS Rules**:
   The API validates `CORS_ORIGINS` at startup. Wildcard `*` origins are rejected when credentials/JWTs are enabled. Allowed origins default to explicit container and host addresses (`http://localhost:4200,http://localhost:80,http://localhost:3000`).
4. **Nginx Security Headers**:
   The frontend reverse proxy automatically injects:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `X-XSS-Protection: 1; mode=block`
5. **Automated Secret Redaction**:
   The `SensitiveDataRedactionFilter` scrubs passwords, JWT tokens, Bearer headers, SAS tokens, and database/Redis connection URLs from all container stdout logs.

---

## Troubleshooting Runbooks

### 1. API Container Fails to Start
* **Symptom**: `brand_guardian_api` restarts continuously or exits with code 1.
* **Diagnosis**: Run `docker compose logs api`.
  - If `Production configuration validation failed`: Check `JWT_SECRET_KEY` (must be >= 32 characters and not a development placeholder) and verify `REDIS_REQUIRED=true`.
  - If `PostgreSQL connection refused`: Verify PostgreSQL container status with `docker compose ps postgres`.

### 2. Redis Unavailable
* **Symptom**: API readiness returns `503 Service Unavailable` with `redis: unavailable`.
* **Diagnosis**: Run `docker compose logs redis`.
  - Verify Redis is running with `docker compose exec redis redis-cli ping`.
  - Check network connectivity from API: `docker compose exec api python -c "import redis; r = redis.from_url('redis://redis:6379/0'); print(r.ping())"`.

### 3. Worker Not Processing Jobs
* **Symptom**: Audit jobs stay in `QUEUED` status indefinitely.
* **Diagnosis**:
  - Run `docker compose ps worker` to verify worker is running.
  - Check worker logs: `docker compose logs worker`.
  - Verify worker is listening to Redis: search for `worker_job_received`.
  - Call operator endpoint `GET /api/admin/observability/summary` to inspect queue counts.

### 4. Frontend Cannot Reach API / CORS Error
* **Symptom**: Browser console displays `CORS error` or `net::ERR_CONNECTION_REFUSED`.
* **Diagnosis**:
  - If accessing via port 80: Nginx reverse-proxies `/api/`, `/audits`, and `/auth` directly to `http://api:8000`.
  - If accessing API directly on port 8000: Ensure the browser origin (e.g. `http://localhost:4200` or `http://localhost:80`) is listed in `CORS_ORIGINS` in `.env`.
