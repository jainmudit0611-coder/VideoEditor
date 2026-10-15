# Brand Guardian AI — Evaluation Framework

## 1. Overview & Purpose

The Brand Guardian AI evaluation framework is an independent, deterministic quality-assessment layer built around the AI compliance auditing system. 

While the production pipeline answers:
> *"What compliance findings did the AI produce?"*

The evaluation framework answers:
> *"How reliable, grounded, and compliant are those findings?"*

### Architecture Separation
The evaluation layer is decoupled from production execution:
```text
Production Path:
POST /audits ──► Worker ──► LangGraph ──► Verifier ──► Database/Report

Evaluation Path:
Completed Audit / Saved Output ──┐
                                 ├──► Evaluation Engine ──► Metrics & Error Analysis ──► Report
Reference Benchmark Dataset    ──┘
```

The evaluator **never alters** production findings, verifier decisions, job statuses, database records, or reports.

---

## 2. Directory Structure

```text
backend/evaluation/
├── cases/                     # Reference evaluation test cases (v1 JSON)
│   ├── case_001.json          # FTC missing disclosure
│   ├── case_002.json          # FTC compliant audio disclosure
│   ├── case_003.json          # FTC compliant on-screen OCR badge
│   ├── case_004.json          # FTC/FDA unsubstantiated health claims
│   ├── case_005.json          # Compliant organic editorial video
│   └── case_006.json          # Ambiguous disclosure in degraded OCR mode
├── fixtures/                  # Saved audit output results for offline evaluation
│   ├── case_001_output.json
│   ├── ...
│   └── case_006_output.json
├── metrics/                   # Modular deterministic metric engines
│   ├── finding_metrics.py     # TP, FP, FN, Precision, Recall, F1
│   ├── grounding_metrics.py   # Transcript/OCR/Visual timestamp grounding
│   ├── citation_metrics.py    # Policy/RAG citation presence & completeness
│   ├── schema_metrics.py      # Conformance to structured audit schema
│   ├── verifier_metrics.py    # Verification outcome agreement
│   └── latency_metrics.py     # Mean, median, min, max timing metrics
├── evaluator.py               # Core AuditEvaluator case evaluation engine
├── runner.py                  # CLI test suite runner & report generator
├── schemas.py                 # Pydantic data models for evaluation
└── README.md                  # This documentation
```

---

## 3. Dataset & Reference Labels

The reference benchmark consists of manually curated test scenarios:
- **`dataset_version`**: `"v1"`
- **`dataset_type`**: `"MANUALLY_CURATED"`

> **Scientific / Engineering Note:** Reference labels represent benchmark conditions curated for compliance policies (e.g. FTC Endorsement Guides, Health Substantiation Rules). They are not claimed to be infallible "ground truth" or representative of general production population distributions.

### Case Schema (`EvaluationCase`)
Each case contains:
- `case_id`: Unique identifier (e.g., `case_001`)
- `description`: Scenario narrative
- `video_url`: Video identifier or reference URL
- `expected_findings`: Expected violation/compliance categories and severities (`FAIL`, `WARNING`, `PASS`)
- `expected_evidence`: Modality (`TRANSCRIPT`, `OCR`, `VISUAL`), expected phrase/signal, and timestamp marker
- `expected_citations`: Policy category and expected document reference
- `expected_verifier_status`: Expected verifier outcome (`VERIFIED`, `NEEDS_MORE_EVIDENCE`)

---

## 4. Evaluation Metrics

The framework deliberately avoids an unscientific single composite "score" (e.g. `94/100`), reporting individual transparent metrics:

### 1. Finding Metrics (Classification)
- **True Positives (TP)**: Actual findings matching expected category and severity.
- **False Positives (FP)**: Auditor findings not supported by reference labels.
- **False Negatives (FN)**: Expected findings omitted by the auditor.
- **Precision**: `TP / (TP + FP)`
- **Recall**: `TP / (TP + FN)`
- **F1 Score**: Harmonic mean of Precision and Recall.

### 2. Evidence Grounding Metrics
- **Evidence Support Rate**: Fraction of findings corroborated by timestamped multimodal evidence.
- **Unsupported Finding Rate**: Fraction of reported findings without concrete timestamps or evidence excerpts.
- **Modality Signals**: Matches in transcript speech, on-screen OCR text, and visual keyframe observations.
- **Degraded Mode Handling**: If `is_degraded_vision_mode` is active, visual evaluation is accurately reported as `NOT_AVAILABLE`.

### 3. Policy Citation Metrics
- **Citation Presence Rate**: Fraction of findings with associated regulatory citations.
- **Citation Completeness**: Citations containing document name, rule category, and text excerpts.

### 4. Schema Conformance Metrics
- **Schema Validity Rate**: Conformance to required fields (`status`, `final_report`, `compliance_results`), enum constraints, and typing.

### 5. Verifier Evaluation
- **Verifier Agreement**: Conformance between auditor verifier decision (`VERIFIED` vs `NEEDS_MORE_EVIDENCE`) and reference expectation.

### 6. Latency Metrics
- Statistical aggregation across runs: Mean, Median, Min, Max durations and per-stage averages (`video_download`, `frame_extraction`, `vision`, `planner`, `auditor`, `verifier`, `report`).

---

## 5. Error Analysis & Discrepancies

When a mismatch is detected, the evaluation engine captures a structured `Discrepancy`:
- `case_id`: Identifier of the affected case.
- `failure_type`: `FALSE_POSITIVE`, `FALSE_NEGATIVE`, `SEVERITY_MISMATCH`, `UNSUPPORTED_FINDING`, or `SCHEMA_ERROR`.
- `expected`: Reference expectation.
- `actual`: Auditor output.
- `observed_discrepancy`: Clear factual description of the observed difference without speculative root-cause assertions.

---

## 6. How to Run Evaluation

### Running Full Suite (Offline Mode)
```powershell
C:\Python313\python.exe -m backend.evaluation.runner
```

### Custom Options
```powershell
C:\Python313\python.exe -m backend.evaluation.runner `
  --cases-dir backend/evaluation/cases `
  --outputs-dir backend/evaluation/fixtures `
  --output-json evaluation_report.json `
  --output-md evaluation_report.md `
  --run-id my_custom_eval_01
```

### Running Evaluation Unit Tests
```powershell
C:\Python313\python.exe -m unittest discover tests/evaluation
```
