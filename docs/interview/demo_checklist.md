# Brand Guardian AI — Portfolio & Demo Screenshot Checklist

This checklist cataloging the 13 essential user interface screens, system views, and operational traces needed to showcase **Brand Guardian AI** in a portfolio or interview presentation.

---

## Screenshot & Demo Inventory

| # | Screen / State | Target Route / Command | Purpose | Capture Status |
| :---: | :--- | :--- | :--- | :---: |
| **01** | **User Login & Registration** | `/login`, `/register` | Demonstrates JWT authentication, validation error states, and responsive dark-mode styling. | `TODO — capture from running application` |
| **02** | **Main Audit Dashboard** | `/dashboard` | Displays active audits, status badges (`QUEUED`, `PROCESSING`, `COMPLETED`), and historical jobs. | `TODO — capture from running application` |
| **03** | **New Audit Submission** | `/audits/new` | Shows video URL input, instant client-side validation, and asynchronous submission button. | `TODO — capture from running application` |
| **04** | **Audit Workflow Progress** | `/audits/:id` (in progress) | Shows real-time polling progress bar, current stage badge (e.g. `DOWNLOADING`, `AUDITING`), and backoff. | `TODO — capture from running application` |
| **05** | **Multimodal Evidence Explorer** | `/audits/:id` (completed) | Tri-channel tabs displaying timestamped transcript excerpts, OCR text detections, and visual observations. | `TODO — capture from running application` |
| **06** | **Compliance Findings List** | `/audits/:id` (findings tab) | Displays detected violations with severity badges (`CRITICAL`, `WARNING`), timestamps, and descriptions. | `TODO — capture from running application` |
| **07** | **Evidence Verifier Trace** | `/audits/:id` (verifier card) | Shows the Verifier's reflection status (`AGREED`), iteration count, and evidence grounding confirmation. | `TODO — capture from running application` |
| **08** | **Executive Audit Report** | `/audits/:id/report` | Rendered Markdown compliance report with executive summary, regulatory citations, and recommended actions. | `TODO — capture from running application` |
| **09** | **Evaluation Dashboard** | `/evaluations` | Overview of benchmark runs with aggregate Precision, Recall, F1, Grounding Rate, and Latency cards. | `TODO — capture from running application` |
| **10** | **Evaluation Run Comparison** | `/evaluations/compare` | Multi-run matrix comparing baseline model metrics against experimental runs with delta indicators. | `TODO — capture from running application` |
| **11** | **Admin Observability Summary** | `/admin` or `/api/admin/observability/summary` | Protected view showing active queue depth, audit status distribution, and latency percentiles (P50/P95). | `TODO — capture from running application` |
| **12** | **Structured JSON Telemetry** | Terminal output / log stream | Terminal screenshot displaying single-line JSON log events with correlation IDs and redacted credentials. | `TODO — capture from running application` |
| **13** | **Interactive Swagger / OpenAPI** | `http://localhost:8000/docs` | Fast-loading interactive API documentation showing Pydantic schemas, auth endpoints, and health probes. | `TODO — capture from running application` |

---

## Demo Preparation Steps (Host Machine)

When demonstrating the application live in an interview:

1. **Start the API Server**:
   ```bash
   uvicorn backend.src.api.server:app --host 0.0.0.0 --port 8000
   ```
2. **Start the Background Worker Daemon**:
   ```bash
   python -m backend.src.worker.worker
   ```
3. **Start the Angular Development Server**:
   ```bash
   cd frontend-angular && npm start
   ```
4. **Log in with Seed Credentials**:
   - Operator: `operator@brandguardian.ai` / `AdminSecretPass123!`
   - Standard User: `reviewer@brandguardian.ai` / `UserSecretPass123!`
5. **Pre-load Fixture Demo**:
   Navigate to an existing completed fixture audit to ensure zero latency during high-stakes interview segments.
