# Brand Guardian AI — Resume Bullet Points

Crafted resume descriptions tailored for different document formats. All bullet points are grounded strictly in verified engineering implementations, avoiding inflated claims or unverified statements.

---

## 1. Short Version (1-Page Resume / General Software Engineer)

* **Brand Guardian AI — Full-Stack Agentic AI Platform**
  * Engineered an asynchronous multimodal video compliance auditing platform using **FastAPI**, **LangGraph**, **Redis**, and **Angular 21**, enabling automated inspection of advertising disclosures across audio transcripts, onscreen text (OCR), and visual keyframes.
  * Designed a reflective verification multi-agent workflow with bounded iterative refinement, backed by **PostgreSQL** relational persistence, stateless **JWT/RBAC** security with IDOR protection, and a 205-test automated validation suite.

---

## 2. Standard Version (Standard Software Engineer / AI Engineer Resume)

* **Brand Guardian AI — Multimodal Video Compliance Auditing System**
  * Architected a distributed, asynchronous compliance auditing system utilizing **FastAPI**, **LangGraph**, **Redis queue broker**, and an autonomous **Python background worker daemon**, reducing audit response times via non-blocking job ingestion.
  * Implemented an agentic inspection pipeline featuring an Audit Planner, dynamic evidence retrieval tools, and an adversarial **Evidence Verifier** node with bounded feedback loops to eliminate ungrounded findings and hallucinations.
  * Developed an independent AI evaluation framework calculating precision, recall, temporal grounding, and citation completeness across curated benchmark fixtures, achieving verified 1.00 F1 on reference datasets.
  * Hardened enterprise security and operational observability: built server-side IDOR defense, multi-tier SSRF protection with DNS resolution checks, structured JSON logging with correlation IDs (`X-Request-ID`), and automated log credential redaction.

---

## 3. Detailed Version (Senior Engineer / Technical CV / Project Portfolio)

* **Brand Guardian AI — Enterprise Agentic Multimodal Compliance Platform**
  * **Distributed Systems & Asynchronous Processing**: Designed and implemented an asynchronous microservice architecture using **FastAPI** (ASGI), **PostgreSQL 16** (SQLAlchemy 2.0 ORM), and **Redis 7** task queues. Deployed an autonomous Python background worker daemon utilizing non-blocking `BLPOP` polling to isolate long-running video downloads and OpenCV frame extraction from the web tier.
  * **Stateful Agentic Multi-Agent Orchestration**: Built a stateful graph workflow using **LangGraph** (`StateGraph`) that decomposes regulatory auditing into an Audit Planner, a tool-assisted Auditor agent (querying compliance rule vector stores and temporal evidence indices), an adversarial Evidence Verifier, and a final Report Generator. Enforced strict 2-iteration loop boundaries to prevent runaway LLM execution.
  * **Multimodal Evidence Grounding**: Synchronized tri-channel evidence (second-level audio transcripts, OCR text bounding boxes, and OpenCV visual keyframes) with automated fallback to local degraded OCR heuristics (`DEGRADED_OCR_FALLBACK`) when cloud vision APIs are unconfigured.
  * **AI Evaluation & Quality Assurance**: Built an independent benchmark evaluation framework (`backend/evaluation/`) calculating finding precision, recall, F1, citation completeness, and verifier agreement rates against curated ground-truth fixtures, paired with an Angular comparison dashboard.
  * **Security & Threat Mitigation**: Implemented stateless **JWT authentication** (`bcrypt`), dual-tier RBAC (`USER` vs `ADMIN`), and database-level object ownership checks to eliminate Insecure Direct Object References (IDOR). Hardened the API with multi-layer SSRF protection blocking private RFC 1918 IPs, loopback, and cloud metadata addresses with DNS rebinding mitigation.
  * **Observability & Operational Readiness**: Established end-to-end correlation propagation (`X-Request-ID` $\rightarrow$ `audit_id` $\rightarrow$ `worker_id`), single-line structured JSON logging, stage latency metrics, and a regex-driven logging redaction filter guaranteeing zero leakage of passwords, tokens, or connection strings across 205 passing backend unit/security tests.
  * **Containerized Production Topology**: Configured a 6-container production architecture in Docker Compose (`postgres`, `redis`, `migration`, `api`, `worker`, and `frontend`) featuring non-root execution (`appuser`), health probes, and an Nginx reverse proxy.
