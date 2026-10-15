# Brand Guardian AI — Project Summary

Tiered technical summaries designed for different interview formats, conversation lengths, and audience technical depths.

---

## 1. One-Line Summary

> An agentic multimodal video compliance platform that verifies advertising disclosures across audio, text, and visual frames using tool-assisted LangGraph multi-agent reasoning, an asynchronous Redis worker, and enterprise security controls.

---

## 2. 30-Second Elevator Pitch (Recruiter / Hiring Manager)

> "Brands sponsor thousands of creator videos each month, but manually reviewing them to ensure they follow advertising disclosure laws—like FTC `#ad` rules—is expensive and slow. Feeding raw videos to an LLM produces hallucinations and missed disclosures.
>
> I built **Brand Guardian AI**, an asynchronous platform that extracts speech transcripts, on-screen text, and video frames, then runs an agentic LangGraph workflow where a Planner formulates an inspection plan, an Auditor searches evidence tools, and an independent Verifier validates findings before generating a report. It's powered by FastAPI, PostgreSQL, Redis, and Angular, with strict security, IDOR protection, and production observability."

---

## 3. 2-Minute Technical Summary (Engineering Interview)

> "Brand Guardian AI solves video compliance auditing by decomposing the inspection into a decoupled, asynchronous multi-agent system.
>
> On the frontend, an Angular 21 SPA allows compliance teams to submit videos, monitor real-time polling progress, and review visual evidence.
>
> When an audit is requested, our FastAPI web tier validates the URL against an SSRF filter that blocks private IP ranges and resolves DNS to mitigate rebinding attacks. It persists an `AuditJob` record in PostgreSQL, enqueues the job into a persistent Redis queue, and immediately returns a `202 Accepted` response.
>
> A standalone Python worker daemon picks up the job via `BLPOP`, sets up asynchronous correlation context, and launches our LangGraph compliance engine:
> 1. We extract multimodal evidence: audio transcripts with timestamps, burned-in onscreen text via OCR, and visual keyframes via OpenCV.
> 2. An **Audit Planner** node formulates specific regulatory inspection tasks.
> 3. An **Auditor Agent** queries discrete evidence tools—retrieving relevant regulatory statutes from a vector database and searching our transcript/OCR indices—rather than stuffing everything into a single prompt.
> 4. An independent **Evidence Verifier** node performs adversarial reflection: it cross-checks every proposed violation against retrieved timestamps. If evidence is lacking or contradicted, it loops back to the auditor with feedback, bounded by a strict 2-iteration ceiling to prevent infinite loops.
>
> We backed this with an independent AI evaluation framework achieving 1.00 F1 on our reference benchmark, stateless JWT/RBAC security with server-side IDOR prevention, and structured JSON logging with automated secret redaction."

---

## 4. Deep Technical Architecture Summary (Staff / Principal Interviewer)

### Architecture & Data Flow
* **Ingestion Tier**: FastAPI ASGI server running under Uvicorn. Exposes REST endpoints with strict Pydantic v2 schemas. Employs `correlation_and_telemetry_middleware` which injects or validates client `X-Request-ID` headers and initializes an asynchronous `ContextVar` that follows the request across threads and worker processes.
* **Broker & State Persistence**: Decoupled using Redis 7 with AOF persistence. The web process writes an initial `AuditJob` row to PostgreSQL 16 (storing status, timestamps, user ownership, and idempotency keys) and pushes a lightweight JSON payload (`audit_id`, `request_id`) to the `video_audits` queue.
* **Worker Execution**: An autonomous `WorkerDaemon` process polls Redis. Upon dequeue, it restores the `request_id` context, binds its unique `worker_id` (`hostname-pid-uuid`), transitions the database record to `PROCESSING`, and executes `AuditTaskProcessor`.
* **LangGraph Multi-Agent Engine**:
  * **State Schema**: Central `AgentState` TypedDict maintaining video metadata, extracted transcript chunks, OCR items, visual observations, planning steps, candidate findings, verifier decisions, iteration counters, and timing dictionaries.
  * **Tool Decoupling**: Rather than dumping full video payloads into the auditor prompt, the model is bound to four search tools (`search_policy_rules`, `search_transcript_evidence`, `search_ocr_evidence`, `search_visual_evidence`).
  * **Reflection & Graph Routing**: The Verifier node evaluates the candidate findings against concrete tool responses. The conditional edge dynamically evaluates `is_verified` and `iteration_count`. If findings fail verification and `iteration_count < 2`, it routes back to `auditor` with targeted feedback; otherwise, it routes to `report_generator`.
* **Multimodal Engine & Graceful Degradation**:
  * Native mode utilizes Azure OpenAI GPT-4o multi-frame vision analysis.
  * Degraded mode (`DEGRADED_OCR_FALLBACK`) automatically activates when cloud credentials are unconfigured, falling back to local OpenCV frame difference detection and OCR heuristics while emitting structured `audit_degraded_mode` telemetry.
* **Security & Defense-in-Depth**:
  * **IDOR**: All queries filter by `AuditJob.id == audit_id AND AuditJob.created_by == current_user.id`.
  * **SSRF**: Strict multi-pass validator parsing scheme, host blocklist, IPv4/IPv6 private address checks (`ipaddress`), and pre-fetch DNS resolution to prevent rebinding.
  * **CORS & Headers**: Strict origin checks rejecting wildcards in production; automated injection of `nosniff`, `DENY`, and CSP headers.
* **Observability & Operational Integrity**:
  * Emits single-line JSON logs formatted with ISO 8601 UTC timestamps, log levels, stable event names (`ObservabilityEvent`), stage latencies, error codes, and correlation identifiers.
  * Attached `SensitiveDataRedactionFilter` scrubs passwords, JWTs, Bearer headers, SAS tokens, and database/Redis URIs before stream emission.
* **Testing & Verification**:
  * 205 backend tests (covering unit, integration, authorization, IDOR, SSRF, observability, and evaluation).
  * 64 Angular tests (covering components, services, auth interceptor, and route guards).
  * Zero compileall syntax errors and a successful Angular production build.
