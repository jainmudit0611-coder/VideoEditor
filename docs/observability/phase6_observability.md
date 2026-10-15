# Brand Guardian AI — Phase 6: Observability, Tracing & Production Readiness

## Overview & Architecture

Brand Guardian AI Phase 6 introduces an end-to-end operational observability foundation without altering compliance logic, security boundaries, or existing Agentic AI workflows. The observability architecture allows operators to answer:

> *"A user submitted audit X. What happened, how long did each stage take, which agent/tool ran, what evidence was retrieved, where did it fail, which worker processed it, and what should an operator investigate?"*

### Correlation Flow

```text
HTTP Client (X-Request-ID Header)
         │
         ▼
FastAPI Middleware
  - Validates / generates secure UUIDv4 request_id
  - Sets AsyncIO ContextVar (correlation context)
  - Injects X-Request-ID into HTTP response headers
  - Emits: http_request_started, http_request_completed, http_request_failed
         │
         ▼
Audit Creation & Persistence (PostgreSQL)
  - Persists request_id on AuditJob model
  - Emits: audit_created, audit_queued
         │
         ▼
Redis Production Queue
  - Enqueues job payload carrying audit_id and request_id
  - Emits: queue_enqueue, queue_dequeue, queue_unavailable, queue_retry
         │
         ▼
Background Worker Process
  - Worker identifies self: worker_id (<hostname>-<pid>-<uuid8>)
  - Restores request_id & audit_id ContextVars for worker task
  - Emits: worker_started, worker_job_received, worker_job_completed, worker_job_failed, worker_shutdown
         │
         ▼
LangGraph Agentic Execution
  - Graph node hooks emit: node_started, node_completed, node_failed
  - Tool execution wraps emit: agent_tool_started, agent_tool_completed
  - Verifier reflection emits: verifier_started, verifier_completed, audit_iteration_requested, audit_iteration_limit_reached, audit_routed_to_report
  - Degraded mode triggers emit: audit_degraded_mode
         │
         ▼
Persistence & Final Status
  - Updates AuditJob status, stage_latencies, and findings
  - Emits: audit_completed or audit_failed
```

---

## Correlation Identifiers

Every operationally relevant event includes standard identifiers distinguishing execution scopes:

| Identifier | Context | Description | Lifetime |
| :--- | :--- | :--- | :--- |
| `request_id` | HTTP transaction | Trace ID originating from client `X-Request-ID` or generated via UUIDv4. | Duration of HTTP request / propagated through audit jobs spawned by request. |
| `audit_id` | Audit Job | Persistent UUID identifying the audit record in PostgreSQL. | Persistent lifecycle of an audit job. |
| `worker_id` | Worker process | Identifier formatted as `{hostname}-{pid}-{uuid8}` identifying the specific background worker instance. | Lifetime of worker OS process. |
| `evaluation_run_id` | Evaluation run | Persistent UUID identifying an evaluation run suite. | Duration of benchmark run. |

ContextVars are managed in [`backend/src/observability/correlation.py`](file:///d:/VIDEO_AUDIT_PROJ-20260921T163902Z-1-001/VIDEO_AUDIT_PROJ/backend/src/observability/correlation.py).

---

## Structured Log Schema

Production logs are formatted as single-line JSON records using [`StructuredJsonFormatter`](file:///d:/VIDEO_AUDIT_PROJ-20260921T163902Z-1-001/VIDEO_AUDIT_PROJ/backend/src/observability/structured_logger.py):

```json
{
  "timestamp": "2026-09-23T15:30:00.123456+00:00",
  "level": "INFO",
  "event": "audit_stage_completed",
  "service": "brand-guardian-api",
  "environment": "production",
  "app_version": "3.0.0",
  "logger": "brand-guardian-worker",
  "request_id": "4b68ef5c-9c98-4c28-9472-8877ef9a8001",
  "audit_id": "18cf7934-2e96-419b-a01d-5561abce5412",
  "worker_id": "worker-node-1-48212-9c1a02fe",
  "stage": "verifier",
  "duration_ms": 1240,
  "message": "Audit stage 'verifier' completed in 1240ms."
}
```

### Standard Schema Fields

* `timestamp` (ISO 8601 UTC)
* `level` (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
* `event` (Stable event name from `ObservabilityEvent`)
* `service` (`brand-guardian-api` or configured service name)
* `environment` (`production`, `development`, `staging`, `testing`)
* `app_version` (Authoritative version: `3.0.0`)
* `logger` (Python logger name)
* `request_id` (Correlation UUID if present)
* `audit_id` (Audit UUID if present)
* `worker_id` (Worker identifier if in worker context)
* `evaluation_run_id` (Evaluation UUID if in evaluation context)
* `stage` (Audit pipeline stage name if applicable)
* `duration_ms` (Latency measurement in milliseconds if applicable)
* `error_code` (Standardized operational error code if an error occurred)
* `message` (Sanitized human-readable log message)

---

## Event Taxonomy

All system events use stable identifiers defined in [`ObservabilityEvent`](file:///d:/VIDEO_AUDIT_PROJ-20260921T163902Z-1-001/VIDEO_AUDIT_PROJ/backend/src/observability/events.py):

### 1. HTTP API Events
* `http_request_started`: Inbound HTTP request received by middleware.
* `http_request_completed`: HTTP response emitted successfully.
* `http_request_failed`: Unhandled or 5xx HTTP request failure.

### 2. Authentication Events
* `auth_login_success`: User successfully authenticated via password.
* `auth_login_failure`: Invalid credentials or missing user.
* `auth_registration`: New user account registered.
* `auth_forbidden`: Authenticated user lacks required role (e.g., non-admin accessing admin route).

### 3. Audit Lifecycle Events
* `audit_created`: Audit record initialized and persisted in database.
* `audit_queued`: Audit job dispatched to asynchronous queue.
* `audit_started`: Worker began processing the audit job.
* `audit_stage_started`: Graph or preprocessing stage commenced.
* `audit_stage_completed`: Graph or preprocessing stage succeeded.
* `audit_completed`: Audit successfully completed and report ready.
* `audit_failed`: Audit execution failed (terminal status).
* `audit_cancelled`: Audit execution cancelled upon user request.
* `audit_degraded_mode`: Degraded mode activated (e.g. OCR fallback).

### 4. Background Worker Events
* `worker_started`: Background worker loop initialized.
* `worker_job_received`: Worker dequeued an audit job.
* `worker_job_completed`: Worker finished processing audit.
* `worker_job_failed`: Worker encountered terminal error during job.
* `worker_job_retry`: Job failed transiently; scheduling retry.
* `worker_shutdown`: Worker received graceful termination signal.

### 5. Queue Events
* `queue_enqueue`: Item pushed to Redis queue.
* `queue_dequeue`: Item popped from Redis queue.
* `queue_unavailable`: Redis connection failure or timeout.
* `queue_retry`: Queue retry attempt dispatched.

### 6. Agent & Graph Traceability Events
* `graph_run`: Overall LangGraph execution cycle.
* `node_started`: Specific LangGraph node execution started.
* `node_completed`: LangGraph node execution finished.
* `node_failed`: LangGraph node raised an exception.
* `agent_tool_started`: Evidence or retrieval tool started.
* `agent_tool_completed`: Evidence tool completed (captures count, duration, metadata; omits raw payloads).

### 7. Verifier & Reflection Events
* `verifier_started`: Verifier agent reflection began.
* `verifier_completed`: Verifier agent evaluated findings.
* `audit_iteration_requested`: Verifier rejected findings; looping back for additional evidence.
* `audit_iteration_limit_reached`: Maximum reasoning iterations reached; routing to report.
* `audit_routed_to_report`: Verifier satisfied; proceeding to report generation.

### 8. Evaluation Events
* `evaluation_started`: Evaluation benchmark suite started.
* `evaluation_case_started`: Individual test case evaluation started.
* `evaluation_case_completed`: Test case evaluation completed.
* `evaluation_completed`: Full benchmark suite completed.
* `evaluation_failed`: Benchmark suite encountered error.

---

## Security & Log Redaction

Brand Guardian AI enforces zero credential leakage through automatic filtering in [`backend/src/observability/redaction.py`](file:///d:/VIDEO_AUDIT_PROJ-20260921T163902Z-1-001/VIDEO_AUDIT_PROJ/backend/src/observability/redaction.py):

### Redacted Elements
1. **Passwords**: Key names (`password`, `hashed_password`, `password_hash`, `new_password`) are replaced with `[REDACTED]`.
2. **Bearer & Authorization Tokens**: `Authorization: Bearer <token>` is stripped to `Bearer [REDACTED]`.
3. **Standalone JWTs**: Triple-segment base64 JWT patterns matching headers and payloads are replaced with `[REDACTED_JWT]`.
4. **Database & Redis Passwords**: Connection URIs (e.g. `postgresql://user:pass@host:port/db`, `redis://:pass@host:port/0`) are rewritten to `://user:[REDACTED]@...`.
5. **Signed URLs**: SAS tokens, signatures, and credentials in query parameters (`sig`, `token`, `key`, `secret`, `password`) are scrubbed to `[REDACTED]`.
6. **API & Azure Secrets**: Azure OpenAI keys, AI Search keys, Video Indexer tokens, and JWT secret keys are masked.

---

## Agent & Verifier Traceability

To fulfill Agentic AI auditability requirements while preventing log bloat:
* **Tool Observability**:
  ```json
  {
    "event": "agent_tool_completed",
    "tool_name": "search_policy_rules",
    "result_count": 3,
    "duration_ms": 142
  }
  ```
  Raw evidence corpora are never dumped into logs. Only counts, filter keys, and timing are recorded.
* **Verifier Iterations**:
  Tracks iteration count (`iteration: 1`), whether verification passed (`passed: true/false`), findings count, and next route (`auditor` vs `report`). Chain-of-thought internal reasoning is never logged.

---

## Degraded Mode Observability

When Azure services are unavailable or vision analysis falls back to local OCR:
```json
{
  "event": "audit_degraded_mode",
  "audit_id": "...",
  "mode": "DEGRADED_OCR_FALLBACK",
  "reason": "Azure OpenAI credentials unconfigured. Skipping vision API analysis."
}
```
Degraded OCR fallback is explicitly flagged and never conflated with native visual inspection.

---

## Operational Error Taxonomy

Standardized operational error codes defined in [`ErrorCode`](file:///d:/VIDEO_AUDIT_PROJ-20260921T163902Z-1-001/VIDEO_AUDIT_PROJ/backend/src/observability/errors.py):

* `AUTHENTICATION_ERROR`: Missing or invalid credentials, expired JWT.
* `AUTHORIZATION_ERROR`: Insufficient permissions or role.
* `AUDIT_NOT_FOUND`: Specified audit job ID does not exist.
* `EVALUATION_NOT_FOUND`: Specified evaluation run ID does not exist.
* `VALIDATION_ERROR`: Malformed input payload or schema violation.
* `SSRF_BLOCKED`: Video URL resolved to private/forbidden IP address.
* `QUEUE_UNAVAILABLE`: Redis queue offline and queueing required.
* `VIDEO_DOWNLOAD_ERROR`: Failure downloading video from source URL.
* `VIDEO_INDEXER_ERROR`: Azure Video Indexer processing error.
* `FRAME_EXTRACTION_ERROR`: OpenCV extraction failure.
* `VISION_ERROR`: Azure OpenAI vision model invocation error.
* `PLANNER_ERROR`: Planner agent graph node error.
* `AUDITOR_ERROR`: Compliance auditor graph node error.
* `VERIFIER_ERROR`: Verifier agent reflection error.
* `REPORT_ERROR`: Final report generation error.
* `DATABASE_ERROR`: Database connection or transaction failure.
* `CONFIGURATION_ERROR`: Missing environment configuration.
* `INTERNAL_SERVER_ERROR`: Unhandled internal server exception.

All client-facing responses map error codes to sanitized messages preventing stack trace, schema, or credential exposure.

---

## Operator Troubleshooting Runbooks

### 1. Audit Stuck in `QUEUED` Status
**Diagnostic Trace**:
1. Check HTTP creation: Search for `event="audit_created"` with `audit_id`. Confirm `request_id`.
2. Check Queue Enqueue: Search for `event="queue_enqueue"` with `audit_id`.
   - If missing: Investigate API server log for `event="queue_unavailable"`.
3. Check Worker Receive: Search for `event="worker_job_received"` with `audit_id`.
   - If missing: Workers may be stopped. Check for `event="worker_started"` or `worker_shutdown`.
   - Inspect Redis queue depth via protected endpoint `/api/admin/observability/summary`.

### 2. Audit Fails During Verifier
**Diagnostic Trace**:
1. Search for `audit_id` and `event="verifier_started"`.
2. Locate subsequent event:
   - `event="node_failed"` with `node="verifier"` and `error_code="VERIFIER_ERROR"`.
   - Check `duration_ms` to distinguish LLM timeout from format parsing issues.
3. Verify if iteration limits were exceeded: Search for `event="audit_iteration_limit_reached"`.

### 3. Redis Queue Unavailable
**Diagnostic Trace**:
1. Search for `event="queue_unavailable"`.
2. Inspect log fields: `error_code="QUEUE_UNAVAILABLE"`, `queue_name="video_audits"`.
3. Verify connection sanitized URL to confirm correct host and port without exposing passwords.
4. Check health endpoint: `GET /health/ready` -> `{"status": "degraded", "redis": "unavailable"}`.

---

## Protected Operator Endpoint

For administrative operators, Brand Guardian AI exposes:
```http
GET /api/admin/observability/summary
Authorization: Bearer <ADMIN_JWT>
```

**Response**:
```json
{
  "service": "brand-guardian-api",
  "environment": "production",
  "app_version": "3.0.0",
  "database": "healthy",
  "redis": "healthy",
  "audit_jobs": {
    "total": 42,
    "by_status": {
      "QUEUED": 2,
      "PROCESSING": 1,
      "COMPLETED": 38,
      "FAILED": 1
    }
  },
  "recent_latencies_ms": {
    "sample_size": 25,
    "p50_ms": 4820.0,
    "p95_ms": 12150.0,
    "avg_ms": 5320.1
  }
}
```
Requires `ADMIN` role. Returns safe operational metrics with zero credential exposure.
