# Brand Guardian AI — Portfolio Case Study

A comprehensive case study showcasing **Brand Guardian AI**, designed for an engineering portfolio, personal website, or GitHub presentation.

---

## At a Glance

* **Role**: Lead Systems & AI Engineer
* **Domain**: Agentic AI, Multimodal Systems, Enterprise Compliance, Distributed Backend
* **Core Technologies**: Python, FastAPI, LangGraph, Redis, PostgreSQL, SQLAlchemy, Angular 21, TypeScript, OpenCV, FFmpeg, Docker Compose
* **Validation Baseline**: 205 Backend Tests, 64 Angular Tests, 100% Compileall & Build Success

---

## 1. Challenge & Problem Statement

Digital advertising regulations require influencers and brands to prominently disclose sponsorships, commercial relationships, and health/financial disclaimers. With millions of short-form promotional videos published monthly, manual review is bottlenecked by human labor costs, while generic single-prompt LLM solutions fail due to:
1. **Severe Hallucinations**: Claiming disclosures exist when they do not, or fabricating regulatory violations.
2. **Context Blindness**: Overlooking small, fleeting burned-in text disclosures (OCR) or subtle visual brand badges while focusing only on audio.
3. **Gateway Timeouts**: Processing multi-minute video downloads and multimodal inference synchronously within standard HTTP requests.

---

## 2. Solution: Agentic Multimodal Compliance Platform

Brand Guardian AI transforms video auditing into a resilient, stateful, multi-agent inspection system:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        BRAND GUARDIAN AI SYSTEM                        │
├────────────────────┬────────────────────┬──────────────────────────────┤
│ 1. Tri-Channel     │ 2. LangGraph Multi-│ 3. Asynchronous Broker       │
│    Evidence        │    Agent Pipeline  │    & Decoupled Worker        │
│                    │                    │                              │
│ • Audio Transcript │ • Audit Planner    │ • Non-blocking FastAPI API   │
│ • OCR Onscreen     │ • Tool-Assisted    │ • Redis 7 Task Queue         │
│ • Visual Frames    │   Auditor          │ • Python Worker Daemon       │
│                    │ • Adversarial      │ • PostgreSQL 16 State Store  │
│                    │   Evidence         │ • Angular 21 Reactive SPA    │
│                    │   Verifier         │ • End-to-end Correlation     │
└────────────────────┴────────────────────┴──────────────────────────────┘
```

---

## 3. Engineering Highlights

### A. Stateful Multi-Agent Reasoning via LangGraph
Instead of an ungrounded one-shot prompt, the compliance engine models auditing as a directed state graph:
* **The Audit Planner** maps out applicable regulatory clauses based on video metadata.
* **The Auditor Agent** queries isolated evidence tools (`search_policy_rules`, `search_transcript_evidence`, `search_ocr_evidence`, `search_visual_evidence`) to retrieve timestamped evidence snippets.
* **The Evidence Verifier** evaluates candidate findings against the evidence. If a finding is unsupported, the verifier rejects it and triggers a bounded iterative loop (capped at 2 iterations) to re-evaluate or prune the violation.

### B. High-Throughput Asynchronous Decoupling
To eliminate HTTP gateway timeouts:
* The web tier immediately returns `202 Accepted` upon payload validation.
* Redis manages queue serialization with Append-Only File (AOF) persistence.
* An autonomous background worker daemon handles video downloads, OpenCV frame processing, and LangGraph workflow orchestration independently.

### C. Enterprise Security & Threat Defense
* **IDOR Elimination**: Strict server-side ownership filters (`created_by == current_user.id`) ensure zero cross-customer data leakage.
* **SSRF Hardening**: Custom multi-pass validator blocks private RFC 1918 ranges, loopback, cloud metadata IPs, and checks pre-fetch DNS resolution to stop DNS rebinding.
* **Stateless RBAC**: Dual-tier `USER` vs `ADMIN` roles enforced cryptographically via signed JWT tokens.

### D. Production Observability & Zero-Leakage Redaction
* Propagates distributed correlation IDs (`X-Request-ID` $\rightarrow$ `audit_id` $\rightarrow$ `worker_id`) across all services.
* Formats logs as single-line structured JSON with stage execution latencies and standardized error codes.
* Built-in `SensitiveDataRedactionFilter` scrubs passwords, JWTs, Bearer tokens, and connection strings before emission.

---

## 4. Measurable Outcomes & Quality Metrics

* **Evaluation Benchmark ($N=6$, Dataset `v1`)**:
  * Finding Precision: **1.00**
  * Finding Recall: **1.00**
  * Finding F1: **1.00**
  * Evidence Support Rate: **1.00**
  * Unsupported Finding Rate: **0.00**
  * Mean Audit Latency: **8.10 seconds**
* **Test Automation**:
  * **205 Backend Tests** passing across unit, security, IDOR, SSRF, observability, and evaluation suites.
  * **64 Angular Unit Tests** passing across components, interceptors, and guards.
  * **100% Clean Python Compilation** and zero build errors in Angular production bundling.

---

## 5. Architectural Retrospective & Honest Boundaries

* **Live Cloud Execution**: Cloud multimodal inspection is environment-dependent; the system cleanly activates local degraded OCR fallback (`DEGRADED_OCR_FALLBACK`) when Azure credentials are unconfigured.
* **Benchmark Scope**: The 1.00 F1 score is strictly grounded in the 6 reference benchmark fixtures and represents pipeline verification rather than universal real-world accuracy.
* **Containerization**: Full 6-container Docker Compose architecture is implemented with non-root security and healthchecks; live container execution is documented as pending host Docker installation.
