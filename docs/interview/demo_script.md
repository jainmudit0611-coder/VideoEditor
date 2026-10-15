# Brand Guardian AI — 5-Minute Technical Interview Demo Script

This script is designed for a technical interview or system demonstration. It walks an interviewer through the problem, architecture, agentic compliance flow, verifier reflection, evaluation framework, security, and observability in exactly five minutes.

---

## Script Overview
* **Target Audience**: Staff / Principal Engineers, Hiring Managers, Technical Interviewers.
* **Core Message**: *Brand Guardian AI is not just another LLM prompt wrapper. It is a resilient, decoupled multimodal system with stateful agentic planning, reflective verification, enterprise security, and production observability.*
* **Demonstration Mode**: Reliable local fixture execution (no live Azure cloud dependency required).

---

## Minute-by-Minute Walkthrough

### 0:00 – 0:30 | The Problem & Business Context
> *"In digital advertising and influencer marketing, regulatory agencies like the FTC in the US and the ASA in the UK require clear disclosures—like '#ad' or verbal sponsorship announcements. Brands sponsor thousands of videos monthly, but manually reviewing them is cost-prohibitive.*
>
> *If you feed a raw 5-minute video transcript to ChatGPT, it hallucinates disclosures that aren't there, misses onscreen hashtags, and can't provide reliable temporal timestamps. Brand Guardian AI solves this by decomposing compliance into a multimodal, agentic audit pipeline."*

**Action**: Open browser to Angular application login screen (`http://localhost:4200/login`).

---

### 0:30 – 1:15 | Architecture Overview
> *"Let's look at the system topology. The application is built as an asynchronous microservice system:
> - **Frontend**: Angular 21 with reactive signals and standalone components.
> - **API**: FastAPI providing authenticated REST endpoints, strict Pydantic schemas, and SSRF validation.
> - **Queue**: Redis managing high-throughput asynchronous job queues.
> - **Worker**: An autonomous Python daemon polling Redis, running the compliance engine, and persisting state to PostgreSQL.
> - **Compliance Engine**: A stateful LangGraph workflow combining planning, evidence tools, and reflective verification."*

**Action**: Log in as `operator@brandguardian.ai`. Show the main Audit Dashboard.

---

### 1:15 – 2:15 | The Multimodal Ingestion & Agentic Workflow
> *"When a video is submitted via `POST /audits`, the API validates the URL against private IP blocks and immediately returns `202 Accepted` with an audit ID. The worker picks up the job and begins multimodal extraction:
> 1. Audio transcript with second-level timestamps.
> 2. Onscreen text (OCR) for burned-in fine print.
> 3. Visual keyframes analyzed via GPT-4o or local OCR fallback.
>
> Next, our **Audit Planner** agent reviews the metadata to construct an inspection plan. The **Auditor Agent** then queries specialized evidence tools—searching our compliance rule vector store, transcript snippets, and visual frames—rather than reading the entire video context at once."*

**Action**: Click into a completed audit (e.g. `audit_id=73c66f54...`). Point out the tri-channel evidence tabs: Transcript timestamps, OCR bounding text, and visual frame observations.

---

### 2:15 – 3:00 | The Verifier & Bounded Reflection
> *"This is the core agentic element: **The Evidence Verifier**. 
>
> Language models are prone to asserting findings that lack grounding. Before any report is finalized, the Verifier node audits the auditor. It inspects each finding's timestamps and policy citations against the actual tool outputs.
>
> If a finding claims 'Missing sponsorship disclosure,' but the OCR search actually found '#ad' on screen at second 4, the verifier rejects the finding and loops the graph back to re-evaluate. We enforce a strict 2-iteration loop bound to prevent infinite reasoning cycles and runaway LLM costs."*

**Action**: Show the Verification Summary badge and feedback card. Highlight the `AGREED` status, zero unsupported findings, and verified regulatory citations.

---

### 3:00 – 3:45 | Independent AI Evaluation Framework
> *"How do we know the AI actually works? We built an independent evaluation suite. 
>
> On our reference benchmark of 6 manually curated ground-truth cases, the platform achieves 1.00 Finding Precision, 1.00 Recall, and 1.00 Evidence Grounding, with an average processing latency of 8.1 seconds.
>
> Crucially, we treat this scientifically: we distinguish between native visual reasoning and degraded OCR fallback, and we never claim this N=6 benchmark represents 100% accuracy on arbitrary internet videos."*

**Action**: Navigate to the **Evaluations Dashboard** (`/evaluations`). Show the benchmark metrics table, run comparison view, and discrepancy analysis.

---

### 3:45 – 4:30 | Enterprise Security & IDOR Defense
> *"Compliance platforms handle sensitive brand partner data. We hardened the security layer:
> - **Stateless JWT + RBAC**: Distinct `USER` and `ADMIN` roles.
> - **IDOR Defense**: All database queries strictly enforce `created_by == current_user.id`. User A cannot view User B's audit even with a known UUID.
> - **SSRF Protection**: We inspect video URLs before downloading, blocking IPv4/IPv6 private ranges, localhost, and cloud metadata IPs, while mitigating DNS rebinding.
> - **Residual Risk Awareness**: We explicitly document that downstream HTTP 302 redirects within extraction subprocesses require container-level network firewalls in production."*

**Action**: Show browser dev tools. Demonstrate the `Authorization: Bearer <JWT>` header and clean `X-Request-ID` propagation.

---

### 4:30 – 5:00 | Production Observability & Wrap-up
> *"Finally, production observability. Every transaction carries an `X-Request-ID` that propagates through FastAPI, into Redis job payloads, into the worker process, and across LangGraph nodes.
>
> All logs are single-line structured JSON with stage durations, error codes, and an automated security filter that scrubs passwords, JWTs, and connection strings before emission. An operator can take any audit ID and instantly reconstruct its complete lifecycle from queue to verifier.
>
> In summary, Brand Guardian AI demonstrates how to build an enterprise-grade agentic AI system that is grounded, secure, observable, and measurable."*

**Action**: Navigate to `/admin` or show terminal structured JSON log output with sanitized credentials and stage latencies. Conclude and invite questions.
