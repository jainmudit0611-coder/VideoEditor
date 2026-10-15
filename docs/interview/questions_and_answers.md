# Brand Guardian AI — Technical Interview Questions & Answers

A comprehensive compendium of 40 in-depth technical interview questions and answers covering system architecture, agentic AI, multimodal processing, evaluation, security, production engineering, and tradeoffs.

---

## 1. System Architecture

### Q1: Why did you use LangGraph instead of a standard linear pipeline?
**Answer**: Linear pipelines assume deterministic progression where step $N+1$ always follows step $N$. In compliance auditing, evidence sufficiency is nondeterministic. The auditor may find an apparent violation, but upon verification, the evidence may be ambiguous or contradicted by another channel (e.g. OCR text contradicts speech). LangGraph allows us to model a cyclic state graph with conditional edges, enabling the verifier to route back to the auditor for additional evidence retrieval, while enforcing strict iteration caps.

### Q2: Why not a simple sequential Python script?
**Answer**: A sequential script either stuffs all multimodal evidence and policy rules into one monolithic prompt—leading to prompt bloat, lost attention in long contexts, and hallucinations—or executes rigid steps that cannot recover when an early step makes an inaccurate deduction. LangGraph separates concerns into distinct nodes (Planner, Tool-Assisted Auditor, Verifier, Report Generator) with typed state schemas, making the execution inspectable, testable, and resilient.

### Q3: Why use Redis as the message broker?
**Answer**: Redis provides lightweight, in-memory queue primitives (`LPUSH` / `BLPOP`) with sub-millisecond dispatch latency. It has minimal operational overhead for local and containerized development, and supports Append-Only File (AOF) persistence so queued jobs survive unexpected broker restarts. It decouples the web tier from the processing tier cleanly.

### Q4: Why PostgreSQL instead of a NoSQL document database?
**Answer**: Audit jobs, user accounts, and evaluation runs have strict relational constraints and ownership relationships. PostgreSQL allows us to enforce foreign keys, composite unique indexes (`created_by`, `status`, `created_at`), and ACID transactional guarantees. For unstructured findings, PostgreSQL's JSON/JSONB support provides the flexibility of document storage while retaining relational guarantees for authorization.

### Q5: Why is asynchronous processing essential here?
**Answer**: Video compliance auditing involves network downloads, OpenCV frame extraction, audio transcription parsing, and multiple LLM API roundtrips. A complete audit takes 8 to 30 seconds. Running this synchronously inside an HTTP request would block web worker threads, exhaust connection pools, and trigger HTTP 504 gateway timeouts. Asynchronous processing returns `202 Accepted` immediately, allowing the client to poll or receive webhooks.

### Q6: Why did you choose Angular for the frontend?
**Answer**: Angular 21 provides a robust, enterprise-grade architecture out of the box: standalone components, reactive signals, built-in dependency injection for singleton services, and native HTTP interceptors. This ensures type safety between backend Pydantic models and TypeScript interfaces, and allows clean management of complex UI states (e.g. polling with backoff, authentication interceptors, and comparison matrix dashboards).

### Q7: Why FastAPI over Django or Flask?
**Answer**: FastAPI natively supports asynchronous Python (`async`/`await`), has first-class integration with Pydantic v2 for request validation and schema generation, generates automatic interactive OpenAPI documentation, and provides a powerful dependency injection system (`Depends`) used for authentication and database sessions.

---

## 2. Agentic AI & Reasoning

### Q8: What specifically makes this system "agentic"?
**Answer**: In this architecture, "agentic" does not mean unconstrained autonomous behavior. It refers to:
1. **Planning**: An Audit Planner decomposes the task into specific regulatory hypotheses.
2. **Tool Selection**: The Auditor dynamically queries discrete tools for evidence rather than ingesting a raw dump.
3. **Automated Reflection**: An independent Verifier evaluates auditor findings against retrieved evidence.
4. **Stateful Iteration**: The system conditionally loops back to re-evaluate when findings are unsupported.
5. **Bounded Refinement**: A stateful graph boundary limits loops to prevent non-terminating execution.

### Q9: What does the Audit Planner do?
**Answer**: The Planner acts as an initial reasoning stage. It reviews the video metadata (duration, title, detected languages, visual scene frequency) and formulates an audit strategy: which regulatory frameworks apply (e.g. FTC, FDA, COPPA), what specific disclosure patterns to seek, and which evidence channels should be prioritized.

### Q10: What tools can the Auditor agent use?
**Answer**: The Auditor interacts with four specialized evidence tools:
- `search_policy_rules`: Queries the compliance knowledge base (via vector search or local index) for specific regulatory clauses.
- `search_transcript_evidence`: Searches timestamped spoken audio for keywords and phrases.
- `search_ocr_evidence`: Queries detected burned-in onscreen text by time window and content.
- `search_visual_evidence`: Retrieves observations from extracted keyframes (e.g. product placement, logos).

### Q11: Why have an independent Verifier node?
**Answer**: LLMs are generative and susceptible to confirmation bias—if asked to find violations, an auditor model may over-interpret ambiguous statements as definitive breaches. The Verifier acts as an adversarial filter. It checks whether the claimed violation is strictly substantiated by the cited timestamps and excerpts. If not, it rejects the finding.

### Q12: Why are iterations bounded?
**Answer**: If an audit agent and verifier disagree indefinitely on an ambiguous video, an unbounded loop would exhaust API budgets and hang background workers. Enforcing a hard ceiling (default 2 iterations) guarantees deterministic termination. If the ceiling is reached, the system compiles findings using the best available grounded evidence and flags the ambiguity in telemetry.

### Q13: How do you prevent infinite reasoning loops?
**Answer**: In LangGraph, the graph state tracks an `iteration_count` integer. The conditional edge exiting the Verifier checks:
`if is_verified or iteration_count >= MAX_ITERATIONS: return "report"`
`else: return "auditor"`
This guarantees termination regardless of model output.

### Q14: How do you prevent unsupported findings (hallucinations)?
**Answer**: Every finding must adhere to a strict Pydantic schema requiring `timestamp`, `category`, `severity`, `description`, `evidence_excerpt`, and `policy_citation`. The Verifier cross-references the `evidence_excerpt` against the raw tool search outputs. Any finding that fails this cross-check is pruned before report generation.

### Q15: How is evidence grounded across time?
**Answer**: Every extracted piece of evidence (transcript word, OCR bounding box, visual frame) retains its original second-level timestamp (e.g. `00:04.200`). When findings are generated, they must reference these exact temporal cues, enabling human auditors to jump directly to the relevant video frame.

---

## 3. Multimodal AI

### Q16: Why use transcript + OCR + vision instead of just one?
**Answer**: Compliance disclosures are distributed across modalities. An influencer may say "Thanks to Brand X" verbally (Transcript), display "#ad" in small onscreen text (OCR), or hold up a branded package with a disclaimer badge (Visual). Relying on any single modality guarantees false positives or false negatives.

### Q17: How are timestamps synchronized across channels?
**Answer**: All extraction modules normalize temporal markers to floating-point seconds from video start (`t=0.0`). The transcript uses audio cue timestamps, OCR frames are timestamped at the extracted video timecode, and OpenCV keyframes are named and indexed by second offsets (`frame_0004_t00.16.jpg`).

### Q18: What happens if native vision (Azure OpenAI GPT-4o) is unavailable?
**Answer**: The system detects missing credentials or API downtime and automatically activates `DEGRADED_OCR_FALLBACK`. In this mode, OpenCV extracts frames and runs local OCR and basic heuristics. Crucially, the system records `audit_degraded_mode` in structured logs and marks the report as degraded so human operators know visual reasoning was limited.

### Q19: How do you evaluate visual evidence objectively?
**Answer**: In benchmark cases, visual observations are evaluated by checking whether expected visual elements (e.g. "Brand logo on bottom right at 00:02") were detected and whether claims regarding visual prominence match the ground-truth annotations.

---

## 4. AI Evaluation Framework

### Q20: How do you evaluate the AI system?
**Answer**: We built an independent evaluation suite (`backend/evaluation/`) that runs a benchmark dataset of labeled video fixtures. It calculates metrics across five categories:
1. Finding Accuracy (Precision, Recall, F1).
2. Evidence Grounding (Support Rate, Unsupported Finding Rate).
3. Citation Quality (Presence Rate, Completeness).
4. Schema Conformance (Pydantic validation).
5. Verifier Agreement (Alignment with expected verifier decisions).

### Q21: What does "100% F1" mean in your benchmark report?
**Answer**: It means that across our $N=6$ reference benchmark cases (`dataset v1`), the pipeline correctly identified all annotated compliance issues without generating false positives or false negatives. It proves the pipeline logic, tool integration, and schema parsing function properly on reference data—it does **not** prove the system is 100% accurate across all arbitrary internet videos.

### Q22: Why is $N=6$ insufficient to claim production-wide accuracy?
**Answer**: Six cases cannot capture the immense variance of real-world video content: background music interference, colloquial speech, regional dialects, motion blur, novel visual disclosure formats, and edge-case regulatory interpretations. A production evaluation would require hundreds of stratified real-world video samples.

### Q23: How would you expand the evaluation dataset?
**Answer**: By creating a stratified benchmark pipeline:
1. Ingest 200+ multi-platform short-form videos (YouTube Shorts, TikTok, Reels).
2. Stratify across compliant, borderline, and non-compliant samples.
3. Have two certified legal/compliance reviewers dual-annotate ground truth and calculate inter-annotator agreement (Cohen's Kappa).
4. Automate daily regression runs in CI/CD.

### Q24: How do you test for false positives?
**Answer**: We include negative test cases—videos that are fully compliant, containing proper verbal and visual disclosures. If the auditor flags a compliant video as non-compliant, precision drops and the unsupported finding rate increases.

### Q25: How do you test for false negatives?
**Answer**: We include cases with deliberate, subtle violations: disclosures placed off-screen, disclosures hidden in white text on a white background, or sponsorship mentioned only 10 minutes into a video. If the system fails to detect these, recall drops.

---

## 5. Security & Threat Modeling

### Q26: How does JWT authentication work in this application?
**Answer**: The client sends credentials to `POST /auth/login`. Upon bcrypt password verification, the server issues a signed JWT containing `sub` (user_id), `role` (`USER` or `ADMIN`), and `exp`. Subsequent requests include `Authorization: Bearer <token>`. FastAPI's `get_current_active_user` dependency verifies the signature, algorithm (`HS256`), and expiration, resolving the active user from the database.

### Q27: How did you prevent Insecure Direct Object References (IDOR)?
**Answer**: Every database query for an audit (`GET /audits/{id}`, `/report`, `/status`, `/cancel`) filters by both the audit ID and the authenticated user's ID: `filter(AuditJob.id == audit_id, AuditJob.created_by == current_user.id)`. Even if an attacker guesses a valid UUID belonging to another customer, the query returns no record, yielding a safe `404 Not Found`.

### Q28: How is role-based access control (RBAC) enforced?
**Answer**: Roles are encoded in the JWT and verified server-side against the database. Sensitive routes (like `/api/admin/observability/summary` and creating baseline evaluations) enforce the `require_admin` dependency. Normal `USER` accounts receive an immediate `403 Forbidden`. The frontend cannot bypass this by modifying client-side role state.

### Q29: How did you prevent role escalation attacks?
**Answer**: 
1. `UserRegisterRequest` schemas strictly omit role fields—all new registrations default to `USER`.
2. The user update endpoints do not allow self-promotion.
3. JWT tokens are verified using a server-side secret key; token tampering invalidates the signature immediately.

### Q30: How does your SSRF protection work?
**Answer**: Video URLs submitted to `POST /audits` undergo multi-layer inspection before any network request:
1. Scheme must be `http` or `https`.
2. Hostname blocklist rejects `localhost`, `0.0.0.0`, and cloud metadata hostnames (`metadata.google.internal`).
3. IP address inspection blocks all RFC 1918 private ranges, loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), and AWS/Azure metadata IPs (`169.254.169.254`).
4. DNS resolution is performed to inspect resolved IP addresses, mitigating DNS rebinding attacks.

### Q31: What is the remaining residual SSRF limitation?
**Answer**: When downloading YouTube videos, `yt-dlp` executes as a subprocess. If a malicious video URL issues an HTTP 302/307 redirect after the initial connection, `yt-dlp` may follow the redirect internally. Complete mitigation requires network-level egress filtering (e.g. AWS Security Groups, Kubernetes NetworkPolicies, or firewall egress proxies blocking internal IP ranges).

### Q32: Why not trust the frontend role or client headers?
**Answer**: Client-side code runs in an untrusted environment. Attackers can forge headers, edit localStorage, and manipulate JavaScript state in the browser dev tools. All authorization checks, ownership validation, and role enforcement are executed authoritatively inside FastAPI route dependencies.

---

## 6. Production & Observability

### Q33: How does the worker process jobs reliably?
**Answer**: The worker runs an infinite polling loop using Redis `BLPOP` with a 2-second timeout. When a job is dequeued, it establishes a correlation context, creates a database session, invokes `AuditTaskProcessor`, updates the job status to `COMPLETED` or `FAILED`, and sends an acknowledgement (`SREM`) to the queue.

### Q34: What happens if Redis goes down?
**Answer**: 
- In production (`REDIS_REQUIRED=true`), the API returns `503 Service Unavailable`, and `/health/ready` probe fails immediately, alerting container orchestrators.
- The worker catches the connection error, logs `queue_unavailable` telemetry, backs off, and attempts reconnection loops.
- In development mode (`REDIS_REQUIRED=false`), the system gracefully falls back to an in-memory queue to facilitate offline testing.

### Q35: What happens if a worker process crashes mid-audit?
**Answer**: The job's status in PostgreSQL remains `PROCESSING`. When workers initialize or during periodic reconciliation sweeps, jobs stuck in `PROCESSING` beyond a heartbeat threshold are identified and retried up to `MAX_RETRIES=3`. If retries are exhausted, the job transitions to `FAILED` with error code `WORKER_TIMEOUT`.

### Q36: How do you trace a single audit across services?
**Answer**: We use distributed correlation identifiers:
- `request_id`: Originates from client `X-Request-ID` or generated by FastAPI middleware.
- `audit_id`: Persistent PostgreSQL UUID.
- `worker_id`: Worker process identity (`hostname-pid-uuid`).
All three IDs are stored in an asynchronous `ContextVar` and automatically injected into every structured JSON log line. Operators can query `grep audit_id` to see the full trace from HTTP ingress to worker execution.

### Q37: How do you prevent sensitive data and credentials from leaking into logs?
**Answer**: We implemented a custom `SensitiveDataRedactionFilter` attached to all Python loggers. It recursively sanitizes log records, regex-scrubbing:
- Passwords and password hashes.
- Bearer tokens (`Authorization: Bearer [REDACTED]`).
- Raw JWT strings.
- Database and Redis connection URLs (`postgresql://user:[REDACTED]@host...`).
- SAS tokens and sensitive query parameters in video URLs.

### Q38: How would you deploy this system to Kubernetes or cloud containers?
**Answer**: 
- **API**: Deployed as a stateless Deployment behind an Ingress controller with Horizontal Pod Autoscaling (HPA) based on CPU/HTTP latency.
- **Worker**: Deployed as a separate Deployment with KEDA (Kubernetes Event-driven Autoscaling) scaling worker pods based on Redis queue length.
- **PostgreSQL / Redis**: Managed cloud services (e.g. Azure Database for PostgreSQL, Azure Cache for Redis).
- **Ingress**: Reverse proxy routing `/` to the Angular Nginx pods and `/api` to the FastAPI pods.

---

## 7. Retrospective & Tradeoffs

### Q39: What would you change or improve with more time?
**Answer**: 
1. **Queue Architecture**: Upgrade from single Redis lists to Redis Streams or RabbitMQ with consumer groups, automatic dead-letter queues, and job acknowledgements.
2. **Video Streaming Pipeline**: Handle video ingestion via direct presigned S3/Azure Blob uploads rather than having the worker download via external URLs.
3. **Evaluation Dataset**: Expand the benchmark from 6 curated fixtures to 200+ diverse video samples with dual-annotator verification.
4. **Token Management**: Add refresh token rotation and automated token revocation via a Redis-backed blacklist.

### Q40: What are the biggest limitations of the current system?
**Answer**:
1. **Azure Cloud Dependency**: Native visual reasoning requires Azure OpenAI GPT-4o credentials; offline execution relies on degraded OCR heuristics.
2. **Evaluation Sample Size**: $N=6$ proves architectural correctness and metric pipelines, but cannot prove universal compliance accuracy.
3. **Subprocess SSRF Egress**: Subprocess redirects inside video extraction tools require container network egress isolation.
4. **Single-Node Worker Concurrency**: The worker daemon currently processes jobs sequentially per process; high concurrency requires multiple worker container replicas.
