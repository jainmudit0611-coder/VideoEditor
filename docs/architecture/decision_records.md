# Architecture Decision Records (ADRs)

This document records the 14 foundational architectural decisions governing **Brand Guardian AI**, outlining the rationale, rejected alternatives, engineering tradeoffs, and active limitations of each choice.

---

## ADR-01: State Graph Workflow via LangGraph
* **Decision**: Implement the multi-agent compliance pipeline using **LangGraph** (`StateGraph`).
* **Why**: Compliance auditing requires conditional branching, dynamic tool invocation, state reflection, and bounded cyclical refinement loops that cannot be cleanly modeled in rigid sequential chains.
* **Alternatives Considered**: 
  * *Sequential Linear Python Script*: Simple to implement, but unable to re-investigate evidence when findings fail verification.
  * *Autogen / CrewAI*: High abstraction overhead, nondeterministic conversational loops, and opaque state management.
* **Tradeoff**: Increased architectural complexity; requires strict typing and schema serialization across graph state transitions.
* **Current Limitation**: Graph debugging requires inspecting structured telemetry rather than straightforward stack traces.

---

## ADR-02: PostgreSQL Relational Persistence
* **Decision**: Use **PostgreSQL 16** (with SQLite fallback for local developer testing) via SQLAlchemy 2.0.
* **Why**: Audit jobs, user credentials, role permissions, and benchmark evaluation runs have strong relational integrity requirements, distinct ownership models, and complex status filtering needs.
* **Alternatives Considered**: 
  * *MongoDB / Document Store*: Flexible for JSON findings, but weak transactional guarantees and poor relational authorization semantics.
  * *DynamoDB / Cloud NoSQL*: Vendor lock-in, complex local simulation, and cumbersome multi-column indexing.
* **Tradeoff**: Requires database migrations (Alembic) to alter schemas compared to schemaless document stores.
* **Current Limitation**: Deeply nested JSON audit findings are stored in JSONB/JSON columns rather than fully normalized sub-tables.

---

## ADR-03: Redis Asynchronous Queue Broker
* **Decision**: Deploy **Redis 7** with Append-Only File (AOF) persistence as the primary task queue broker.
* **Why**: Low-latency, in-memory queueing with blocking pop primitives (`BLPOP`) and straightforward acknowledgement semantics; lightweight to run locally in containerized environments.
* **Alternatives Considered**: 
  * *RabbitMQ*: Heavier resource footprint, AMQP protocol complexity.
  * *AWS SQS / Azure Service Bus*: Cloud vendor lock-in; cannot be simulated cleanly offline without localstack.
  * *Celery*: High framework magic, rigid serialization restrictions, and complex worker concurrency abstractions.
* **Tradeoff**: In-memory architecture requires disk persistence (`appendonly yes`) to survive broker crashes.
* **Current Limitation**: Advanced queue features (dead-letter queues, priority lanes) are custom-managed rather than native queue primitives.

---

## ADR-04: FastAPI ASGI Web Framework
* **Decision**: Build REST APIs using **FastAPI** on Uvicorn.
* **Why**: High-performance asynchronous I/O, native Pydantic v2 data validation, automated OpenAPI/Swagger documentation, and clean dependency injection (`Depends`) for authentication and database sessions.
* **Alternatives Considered**: 
  * *Django / Django REST Framework*: Heavy monolithic overhead, synchronous ORM complexity in async endpoints.
  * *Flask*: Lacks native async primitives, lacks built-in request/response schema validation.
* **Tradeoff**: Fast-moving ecosystem requires careful version pinning for dependencies like Pydantic and Starlette.
* **Current Limitation**: Large multi-gigabyte video file uploads must be handled asynchronously via URLs rather than direct HTTP streaming through FastAPI.

---

## ADR-05: Angular 21 Standalone Frontend
* **Decision**: Implement the user interface in **Angular 21** using standalone components, reactive signals, and native HTTP interceptors.
* **Why**: Strict enterprise TypeScript typing, built-in dependency injection for authentication services, native route guards for role authorization, and cohesive framework conventions for complex dashboards.
* **Alternatives Considered**: 
  * *React + Vite*: Previously evaluated in early phases; required sprawling third-party libraries for state, routing, and HTTP interceptors.
  * *Next.js*: Server-Side Rendering (SSR) complexity unnecessary for an internal/B2B compliance tool.
* **Tradeoff**: Larger initial JavaScript bundle size (~512 kB) and steeper learning curve compared to lightweight component libraries.
* **Current Limitation**: Production bundle slightly exceeds strict 500 kB initial budget by ~12 kB, requiring future code splitting.

---

## ADR-06: Stateless JWT Authentication
* **Decision**: Authenticate API requests using stateless **JSON Web Tokens (JWT)** signed via HMAC-SHA256 (`HS256`) with salted `bcrypt` password hashing.
* **Why**: Completely decoupled authentication allowing frontend, API replicas, and workers to validate identity without central session store lookups.
* **Alternatives Considered**: 
  * *Server-side Sessions (Redis/Database)*: Introduces session lookup latency on every API request and complex distributed session invalidation.
  * *OAuth2 / OpenID Connect Provider*: Over-engineering for a self-contained local platform; can be integrated as an external identity provider later.
* **Tradeoff**: Tokens cannot be revoked before expiration without maintaining a token blacklist.
* **Current Limitation**: Refresh token rotation is not yet implemented; tokens expire after 24 hours requiring re-authentication.

---

## ADR-07: Dual-Tier Role-Based Access Control (RBAC)
* **Decision**: Enforce explicit role separation with two system roles: **`USER`** and **`ADMIN`**.
* **Why**: Simplifies authorization while strictly protecting administrative operations (evaluating official baselines, viewing operator observability metrics, accessing system summaries).
* **Alternatives Considered**: 
  * *Fine-grained Permissions (PBAC)*: Complex permission matrices overkill for current operational scope.
  * *Single Role with Object Ownership Only*: Lacks ability to designate trusted baseline models or operator views.
* **Tradeoff**: Adding intermediate roles (e.g. `COMPLIANCE_REVIEWER`) will require updating database enums and route dependencies.
* **Current Limitation**: Roles are statically assigned during registration or admin override; no dynamic tenant-based roles.

---

## ADR-08: Tri-Channel Multimodal Evidence Grounding
* **Decision**: Ingest and synchronize evidence across three distinct modalities: **Audio Transcript**, **Onscreen Text (OCR)**, and **Visual Keyframes**.
* **Why**: Advertising disclosures occur across verbal statements ("Sponsored by..."), fine print ("#ad" in corner), and visual logos. Single-modality inspection misses critical disclosures.
* **Alternatives Considered**: 
  * *Transcript-Only Auditing*: Fast and cheap, but blind to onscreen hashtags, captions, and brand badges.
  * *Full Video LLM Ingestion (Video-to-Text)*: Prohibitively expensive, slow, and prone to losing exact second-level timestamps.
* **Tradeoff**: Requires complex preprocessing (FFmpeg downloading, OpenCV frame extraction, OCR engines, Azure Video Indexer).
* **Current Limitation**: Extracted frame density is capped (default 10-20 frames) to control vision API costs and processing duration.

---

## ADR-09: Dedicated Verifier Reflection Node
* **Decision**: Place an autonomous **Evidence Verifier** node between the compliance auditor agent and final report generation.
* **Why**: LLM auditors frequently make plausible-sounding compliance claims that lack grounded evidence. The Verifier acts as an adversarial filter, checking timestamps and retrieved evidence before publication.
* **Alternatives Considered**: 
  * *Direct Single-Pass Generation*: Auditor outputs report directly. High hallucination risk and zero automated quality control.
  * *Human-in-the-Loop Review*: Highest quality, but destroys automated throughput; better suited as an optional escalation path.
* **Tradeoff**: Increases overall audit latency by ~1-2 seconds per iteration due to additional LLM reflection calls.
* **Current Limitation**: Verifier uses structured evaluation criteria; highly ambiguous sarcasm or nuanced humor can challenge automated verification.

---

## ADR-10: Bounded Iterative Refinement Loops
* **Decision**: Implement a hard cap (maximum 2 iterations) on graph feedback cycles between the Verifier and Auditor.
* **Why**: Prevents infinite loops, runaway API costs, and worker timeouts when evidence is genuinely inconclusive or contradictory.
* **Alternatives Considered**: 
  * *Unbounded While-Loops*: High risk of non-terminating execution on ambiguous videos.
  * *Single Feedback Loop Only*: Occasionally insufficient if the second pass retrieves additional partial evidence.
* **Tradeoff**: If maximum iterations are reached, the system must generate a report based on best-available evidence or mark findings unverified.
* **Current Limitation**: Graph defaults to routing to the report generator upon reaching loop limits, noting unverified status in telemetry.

---

## ADR-11: Asynchronous Worker Decoupling
* **Decision**: Decouple API job ingestion (`POST /audits`) from execution using an autonomous background **`WorkerDaemon`**.
* **Why**: Video downloading and multimodal LLM reasoning can take 10 to 60 seconds. Running audits synchronously in the web process would block ASGI worker threads and trigger HTTP gateway timeouts.
* **Alternatives Considered**: 
  * *FastAPI `BackgroundTasks`*: Runs in the same process as the web server; susceptible to server crashes, lacks persistence across restarts, and cannot scale workers independently.
  * *Serverless Functions (AWS Lambda / Azure Functions)*: File system limits (video caching), timeout limits (15 min), and cold starts.
* **Tradeoff**: Requires maintaining a separate daemon process and polling loop.
* **Current Limitation**: Worker concurrency is currently single-threaded per process; scaling requires running multiple worker container replicas.

---

## ADR-12: Independent AI Evaluation Framework
* **Decision**: Build an isolated evaluation suite (`backend/evaluation/`) capable of executing benchmark datasets without web server dependencies.
* **Why**: Ensures audit quality, precision, recall, and grounding metrics can be measured objectively, repeatedly, and versioned over time.
* **Alternatives Considered**: 
  * *Manual Spot-Checking*: Unscientific, non-reproducible, and prone to regression blindness.
  * *Third-Party Eval Platforms (LangSmith / Ragas)*: Useful, but introduces external SaaS dependency and credentials for local CI/CD testing.
* **Tradeoff**: Requires creating and maintaining manual ground-truth test fixtures.
* **Current Limitation**: Reference benchmark currently consists of $N=6$ curated cases; expanding to diverse real-world datasets is ongoing.

---

## ADR-13: Structured JSON Logging, Redaction Filter & Correlation IDs
* **Decision**: Standardize all logging to single-line JSON records using `StructuredJsonFormatter`, with asynchronous `ContextVar` correlation propagation (`request_id`, `audit_id`, `worker_id`) and automated credential redaction.
* **Why**: Enables operators to trace an audit from client request, through the Redis queue, into the worker, across LangGraph nodes, and to report delivery while guaranteeing zero secret leakage.
* **Alternatives Considered**: 
  * *Standard Python Text Logging*: Incompatible with modern log aggregation tools; difficult to parse programmatically.
  * *OpenTelemetry Collector / ELK Stack*: Heavyweight infrastructure for local development; deferred to future production deployment.
* **Tradeoff**: Structured log payloads are larger than simple console text.
* **Current Limitation**: Logs are emitted to stdout/stderr; centralized aggregation (e.g. CloudWatch, Datadog) requires a log shipper daemon.

---

## ADR-14: Multi-Container Docker Topology with Controlled Migrations
* **Decision**: Structure the production simulation into 6 container services (`postgres`, `redis`, `migration`, `api`, `worker`, `frontend`) with a dedicated one-shot migration runner and Nginx reverse proxy.
* **Why**: Eliminates migration race conditions between API and Worker replicas, ensures database and queue readiness before application startup, and protects internal APIs behind a hardened reverse proxy.
* **Alternatives Considered**: 
  * *Single Monolithic Container*: Anti-pattern; prevents independent scaling of API and worker processes.
  * *Auto-Migrate on API Startup*: Causes database deadlocks when multiple API instances launch simultaneously.
* **Tradeoff**: Multi-service compose configurations require container runtime availability on host systems.
* **Current Limitation**: Runtime execution is pending Docker Desktop installation on the current Windows host environment.
