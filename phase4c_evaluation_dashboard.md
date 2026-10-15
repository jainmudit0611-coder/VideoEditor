# Phase 4C — Evaluation Dashboard & Reproducible Runs

## 1. Overview & Architecture

Phase 4C introduces an interactive, reproducible evaluation dashboard for Brand Guardian AI. Building upon the independent Phase 4B evaluation engine, Phase 4C exposes persistent historical runs, real-time benchmark execution, metric drill-downs, error analysis, and neutral side-by-side run comparisons through both a dedicated FastAPI namespace (`/api/evaluations`) and a responsive Angular interface (`/evaluations`, `/evaluations/:id`).

### Conceptual Architecture
```text
Dataset Version
      +
Model / Provider
      +
Prompt Version
      +
Config Version
      ↓
Evaluation Run (PostgreSQL: evaluation_runs)
      ↓
Existing Phase 4B Evaluator Engine
      ↓
Metrics + Discrepancies
      ↓
PostgreSQL Persistence (EvaluationRepository)
      ↓
FastAPI Endpoints (/api/evaluations)
      ↓
Angular Evaluation Dashboard (/evaluations)
```

The production LangGraph pipeline, Redis queue, background workers, and PostgreSQL audit job persistence remain completely isolated from evaluation logic.

---

## 2. Database Schema

Evaluation runs are persisted in the `evaluation_runs` table (`EvaluationRun` ORM model in `backend/src/db/models.py`):

| Column | Type | Constraints / Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `String(36)` | Primary Key, Index | Unique UUID for the run |
| `run_name` | `String(256)` | Not Null | Human-readable title |
| `status` | `Enum(EvaluationRunStatus)` | Index, default: `QUEUED` | `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED` |
| `dataset_version`| `String(32)` | default: `v1` | Benchmark dataset revision |
| `dataset_type` | `String(64)` | default: `MANUALLY_CURATED` | Provenance classification |
| `case_count` | `Integer` | default: `6` | Total cases evaluated in run |
| `model_name` | `String(64)` | default: `gpt-4o` | Model under evaluation |
| `model_provider`| `String(64)` | default: `azure_openai` | Model hosting provider |
| `prompt_version`| `String(32)` | default: `v1` | System prompt version tag |
| `config_version`| `String(32)` | default: `v1` | Architecture configuration tag |
| `evaluation_version` | `String(32)` | default: `v1` | Evaluation framework version |
| `started_at` | `DateTime(UTC)` | Nullable | Execution start timestamp |
| `completed_at` | `DateTime(UTC)` | Nullable | Completion timestamp |
| `duration_ms` | `Integer` | Nullable | Wall-clock run duration |
| `metrics` | `JSON` | Nullable | Aggregated classification & grounding metrics |
| `summary` | `JSON` | Nullable | Case-level evaluation summaries |
| `discrepancies` | `JSON` | Nullable | Itemized discrepancy / error records |
| `error_message` | `String(2048)`| Nullable | Failure details if status is `FAILED` |
| `created_at` | `DateTime(UTC)` | Not Null, Index | Creation timestamp |

---

## 3. Versioning Model

All versioning parameters are centralized in `backend/evaluation/constants.py`:
- `EVALUATION_VERSION = "v1"`
- `DATASET_VERSION = "v1"`
- `DATASET_TYPE = "MANUALLY_CURATED"`
- `PROMPT_VERSION = "v1"`
- `CONFIG_VERSION = "v1"`
- `DEFAULT_MODEL_NAME = "gpt-4o"`
- `DEFAULT_MODEL_PROVIDER = "azure_openai"`
- `CASE_COUNT_BENCHMARK = 6`

Every run explicitly records this configuration, guaranteeing that historical metrics can be reproduced and traced.

---

## 4. Evaluation Run Lifecycle

```text
POST /api/evaluations/runs
          │
          ▼
Create EvaluationRun (status: QUEUED)
          │
          ▼
Background Task Dispatched (status: RUNNING, started_at set)
          │
          ▼
Execute EvaluationSuiteRunner
- Load benchmark cases from backend/evaluation/cases/
- Match against fixtures / outputs in backend/evaluation/fixtures/
- Calculate classification metrics (TP, FP, FN, Precision, Recall, F1)
- Verify multimodal evidence grounding (transcript, OCR, keyframe status)
- Verify regulatory citations and structured schema validity
- Assess verifier outcome agreement
- Collect structured discrepancies
          │
          ▼
Persist Aggregates, Case Results & Discrepancies (status: COMPLETED, duration_ms set)
(or status: FAILED with error_message if unhandled error occurs)
```

---

## 5. Backend API Endpoints

Mounted under `/api/evaluations` in `backend/src/api/server.py`:

### 1. `POST /api/evaluations/runs` (202 Accepted)
Enqueues an asynchronous benchmark evaluation run.
- **Request Body**: `CreateEvaluationRunRequest` (optional `run_name`, `model_name`, `dataset_version`, `prompt_version`, `config_version`).
- **Response**: `CreateEvaluationRunResponse` with run `id` and status `QUEUED`.

### 2. `GET /api/evaluations/runs` (200 OK)
Lists evaluation runs ordered newest first with optional filters (`dataset_version`, `status`, `model_name`, `limit`, `offset`).

### 3. `GET /api/evaluations/runs/{run_id}` (200 OK)
Returns complete run details, aggregated metrics, per-case breakdown, and itemized discrepancies.

### 4. `GET /api/evaluations/runs/{run_id}/status` (200 OK)
Lightweight status endpoint for UI polling (`status`, `progress`, `duration_ms`, `error_message`).

### 5. `GET /api/evaluations/compare?run_ids=id1,id2` (200 OK)
Compares two or more runs side-by-side:
- Returns runs metadata.
- Returns numerical metric comparisons with delta difference ($\Delta$).
- Highlights configuration differences.
- Neutral reporting: no "winner" or ranking claims.

---

## 6. Angular Frontend Integration

### Pages & Routes
- `/evaluations`: `EvaluationsDashboardComponent`
  - Prominent dataset header: `Dataset: v1 • MANUALLY_CURATED • 6 cases`.
  - Prominent methodology callout emphasizing reference benchmark constraints.
  - "Run Evaluation" trigger action with real-time polling.
  - Latest Run Overview card.
  - Grouped Primary Metric cards.
  - Error Analysis / Discrepancies table.
  - Historical Runs list with multi-select checkboxes for comparison.
- `/evaluations/:id`: `EvaluationDetailsComponent`
  - Comprehensive run metadata.
  - Grouped metric categories (Finding Quality, Evidence Grounding, Citations & Verifier, Pipeline Latency Performance).
  - Case-by-case benchmark breakdown table (N=6).
  - Itemized error analysis cards.
- Embedded Component: `RunComparisonComponent`
  - Side-by-side run header cards.
  - Side-by-side metrics table with Delta ($\Delta$) column.
  - Configuration differences table.

### Navigation
- Sidebar updated with an "Evaluations" link pointing to `/evaluations`.

---

## 7. Known Limitations & Scientific Discipline

1. **Benchmark Scope (N=6)**: The dataset is a curated benchmark for compliance rules (FTC disclosures, health substantiations, organic editorial controls); it does not constitute population-wide production accuracy.
2. **Provenance Transparency**: Clearly labeled `MANUALLY_CURATED`, not infallible ground truth.
3. **Degraded Mode Distinction**: In `DEGRADED_OCR_FALLBACK` mode, visual keyframe analysis is reported as `NOT_AVAILABLE`.
4. **Citation Grounding**: Measures structural presence and retrieval keyword matches rather than legal factuality.
