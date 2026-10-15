# Phase 4B — AI Evaluation & Audit Quality Framework

## 1. Objective

Phase 4B establishes a dedicated, deterministic evaluation layer around the Brand Guardian AI compliance platform. The objective is to transition from merely reporting what findings the AI produced to quantifying **how reliable, grounded, and compliant** those findings are.

Key guarantees of this framework:
- **Decoupled Architecture**: The evaluation engine evaluates outputs independently; it never modifies the production LangGraph workflow, database records, or worker queue.
- **Offline & Deterministic Execution**: Operates over saved audit results without dependency on external Azure cloud services or live network connections.
- **Transparent Metrics**: Avoids unscientific composite "AI Quality" scores; reports explicit Precision, Recall, F1, Grounding Support, Citation Completeness, Schema Validity, and Verifier Agreement.

---

## 2. Architecture

```text
                               AI Audit Output
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
          Findings                 Evidence               Citations
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      ▼
                           Audit Evaluator Engine
                                      │
        ┌─────────────┬───────────────┼───────────────┬─────────────┐
        ▼             ▼               ▼               ▼             ▼
     Finding      Grounding        Citation        Schema       Verifier
    Precision/   Support Rate      Presence       Validity      Agreement
    Recall/F1    (Multimodal)    & Completeness     Rate
        │             │               │               │             │
        └─────────────┴───────────────┼───────────────┴─────────────┘
                                      ▼
                           Evaluation Suite Runner
                                      │
                      ┌───────────────┴───────────────┐
                      ▼                               ▼
            evaluation_report.json          evaluation_report.md
```

### Components
1. **`backend/evaluation/schemas.py`**: Strongly-typed Pydantic schemas for test cases, findings, evidence signals, discrepancies, and aggregate reports.
2. **`backend/evaluation/cases/`**: Versioned reference cases (`v1`, `MANUALLY_CURATED`).
3. **`backend/evaluation/fixtures/`**: Deterministic saved audit outputs for reproducible offline evaluation.
4. **`backend/evaluation/metrics/`**: Modular metric calculators:
   - `finding_metrics.py`: Normalized matching for categories and severities; TP/FP/FN accounting.
   - `grounding_metrics.py`: Timestamp alignment and multimodal signal containment (transcript, OCR, keyframes).
   - `citation_metrics.py`: Regulatory document reference presence and completeness.
   - `schema_metrics.py`: Structured conformance validation against compliance schema contracts.
   - `verifier_metrics.py`: Alignment with expected critic verification state.
   - `latency_metrics.py`: Latency aggregation across pipeline stages.
5. **`backend/evaluation/evaluator.py`**: Case-level evaluation engine `AuditEvaluator`.
6. **`backend/evaluation/runner.py`**: Suite runner orchestrating batch evaluation, mode breakdown, and markdown/JSON report emission.

---

## 3. Dataset

The initial reference dataset comprises 6 manually curated benchmark cases:
- **Dataset Version**: `v1`
- **Dataset Provenance**: `MANUALLY_CURATED`

| Case ID | Policy Domain | Scenario | Expected Outcome | Execution Mode |
| :--- | :--- | :--- | :--- | :--- |
| `case_001` | FTC Endorsement (16 CFR 255) | Missing influencer sponsorship disclosure on gifted review | FAIL | `NATIVE_VISION` |
| `case_002` | FTC Endorsement (16 CFR 255) | Clear audible disclosure in video introduction | PASS | `NATIVE_VISION` |
| `case_003` | FTC Endorsement (16 CFR 255) | Prominent on-screen OCR partnership banner | PASS | `NATIVE_VISION` |
| `case_004` | FTC / FDA Substantiation | Unsubstantiated medical cure claim for chronic migraines | FAIL | `NATIVE_VISION` |
| `case_005` | Editorial / Organic | Organic cooking tutorial without commercial promotion | PASS (no findings) | `NATIVE_VISION` |
| `case_006` | FTC Endorsement (16 CFR 255) | Vague disclosure in degraded OCR mode requiring review | WARNING (NEEDS_MORE_EVIDENCE) | `DEGRADED_OCR_FALLBACK` |

---

## 4. Metrics & Methodology

### A. Finding Classification
- **Matching Rule**: Findings are matched on normalized `category` (or `rule_category`) and normalized `severity` (e.g. `FAIL`, `WARNING`, `PASS`).
- **Precision**: $\frac{\text{TP}}{\text{TP} + \text{FP}}$
- **Recall**: $\frac{\text{TP}}{\text{TP} + \text{FN}}$
- **F1 Score**: $2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$

### B. Evidence Grounding
- Verifies that every finding is linked to a timestamp and supported by text in the transcript or OCR stream.
- In `DEGRADED_OCR_FALLBACK` mode, visual keyframe analysis is marked `NOT_AVAILABLE` rather than falsely reported as passed.

### C. Policy Citations
- Verifies presence of regulatory citations (`citation_presence_rate`).
- Assesses citation completeness: title, category, and relevant content excerpt (`citation_completeness_rate`).

### D. Schema Validity
- Verifies that audit results include required top-level keys (`status`, `final_report`, `compliance_results`), conforming data types, and valid enums.

### E. Verifier Evaluation
- Measures whether the auditor critic reached the expected verification state (`VERIFIED` vs `NEEDS_MORE_EVIDENCE`).

---

## 5. Evaluation Results

Results generated across the reference benchmark suite (N=6):

```text
Brand Guardian AI — Evaluation Summary
=======================================
Cases Evaluated (N):       6
Dataset Version:           v1 (MANUALLY_CURATED)
Execution Modes:           NATIVE_VISION (5), DEGRADED_OCR_FALLBACK (1)

Finding Precision:         1.00 (100.0%)
Finding Recall:            1.00 (100.0%)
Finding F1:                1.00
Evidence Support Rate:     1.00 (100.0%)
Unsupported Finding Rate:  0.00 (0.0%)
Citation Presence Rate:    1.00 (100.0%)
Citation Completeness:     1.00 (100.0%)
Schema Validity Rate:      1.00 (100.0%)
Verifier Agreement:        100.0%

Latency (N=6):
Mean Duration:             8.10s
Median Duration:           8.15s
Min / Max:                 6.00s / 10.40s
```

### Execution Mode Breakdown
- **`NATIVE_VISION` (N=5)**: Precision: 1.00, Recall: 1.00
- **`DEGRADED_OCR_FALLBACK` (N=1)**: Precision: 1.00, Recall: 1.00

---

## 6. Error Analysis

The evaluation engine features an automated discrepancy recorder. When a test case exhibits an anomaly, it produces a structured discrepancy entry:

```text
Case ID: case_003
Failure Type: FALSE_NEGATIVE
Expected: FTC_DISCLOSURE [FAIL]
Actual: None
Observed Discrepancy: Expected finding 'FTC_DISCLOSURE' with severity 'FAIL' was not reported by auditor.
```

In the baseline benchmark run across the 6 curated reference fixtures, all expected findings matched exactly, resulting in 0 discrepancies. In the unit test suite (`tests/evaluation/`), synthetic discrepancies for false positives, false negatives, severity mismatches, ungrounded claims, and schema anomalies are actively exercised and verified.

---

## 7. Limitations & Scientific Constraints

1. **Benchmark Scope (N=6)**: The evaluation dataset is a curated benchmark for compliance rules; it does not constitute population-level statistical accuracy for arbitrary open-web video content.
2. **Reference Provenance**: Labels are manually curated policy benchmarks (`MANUALLY_CURATED`), not infallible ground truth.
3. **Degraded Vision Mode**: When Azure OpenAI Vision is unconfigured, the system runs with local OCR fallback. Visual evaluation metrics are reported as `NOT_AVAILABLE`.
4. **Citation Factuality vs Presence**: Current citation checks verify structural presence and keyword relevance in retrieved regulatory snippets, not legal truthfulness.

---

## 8. Future Improvements

1. Expand reference dataset to 50+ diverse video benchmarks across FTC, FDA, and financial promotion regulations.
2. Add automated regression benchmarking to CI/CD when prompt or model configurations are modified.
3. Incorporate LLM-assisted semantic grounding evaluation for visual reasoning once Azure Vision credentials are live.
4. Support side-by-side model comparison runs (e.g. GPT-4o vs GPT-4o-mini).
