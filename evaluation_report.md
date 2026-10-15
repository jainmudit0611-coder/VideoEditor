# Brand Guardian AI — Evaluation Report

## 1. Run Metadata
- **Evaluation Run ID**: `eval_run_20260923_135606`
- **Timestamp**: `2026-09-23T13:56:06.927674+00:00`
- **Dataset Version**: `v1`
- **Dataset Type**: `MANUALLY_CURATED`
- **Cases Evaluated (N)**: `6`
- **Execution Modes**: `DEGRADED_OCR_FALLBACK, NATIVE_VISION`

## 2. Evaluation Summary

| Metric | Value | Description |
| :--- | :--- | :--- |
| **Finding Precision** | `1.00` (100.0%) | TP / (TP + FP) across all findings |
| **Finding Recall** | `1.00` (100.0%) | TP / (TP + FN) across expected findings |
| **Finding F1 Score** | `1.00` | Harmonic mean of finding precision and recall |
| **Evidence Support Rate** | `1.00` (100.0%) | Findings supported by timestamped evidence |
| **Unsupported Finding Rate** | `0.00` (0.0%) | Hallucinated or unsubstantiated findings |
| **Citation Presence Rate** | `1.00` (100.0%) | Findings backed by policy/RAG citation |
| **Citation Completeness** | `1.00` (100.0%) | Citations with title, rule, and excerpt |
| **Schema Validity Rate** | `1.00` (100.0%) | Strict conformance to expected schema |
| **Verifier Agreement** | `100.0%` | Alignment with expected verifier outcome |

## 3. Latency & Execution Performance
- **Sample Count (N)**: 6
- **Mean Audit Duration**: 8.1s
- **Median Audit Duration**: 8.15s
- **Min / Max Duration**: 6.0s / 10.4s

### Stage Execution Breakdown (Averages)
| Pipeline Stage | Average Duration (s) |
| :--- | :--- |
| `auditor` | 1.25s |
| `frame_extraction` | 1.02s |
| `planner` | 0.85s |
| `report` | 0.45s |
| `verifier` | 0.97s |
| `video_download` | 1.48s |
| `vision` | 2.08s |

## 4. Execution Mode Breakdown
| Execution Mode | Case Count | Precision | Recall |
| :--- | :--- | :--- | :--- |
| `NATIVE_VISION` | 5 | 1.00 | 1.00 |
| `DEGRADED_OCR_FALLBACK` | 1 | 1.00 | 1.00 |

## 5. Detailed Case Breakdown
| Case ID | Execution Mode | Expected Findings | Actual Findings | TP / FP / FN | Grounded % | Citations | Verifier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `case_001` | `NATIVE_VISION` | 1 | 1 | 1/0/0 | 100% | 100% | `AGREED` |
| `case_002` | `NATIVE_VISION` | 1 | 1 | 1/0/0 | 100% | 100% | `AGREED` |
| `case_003` | `NATIVE_VISION` | 1 | 1 | 1/0/0 | 100% | 100% | `AGREED` |
| `case_004` | `NATIVE_VISION` | 1 | 1 | 1/0/0 | 100% | 100% | `AGREED` |
| `case_005` | `NATIVE_VISION` | 0 | 0 | 0/0/0 | 100% | 100% | `AGREED` |
| `case_006` | `DEGRADED_OCR_FALLBACK` | 1 | 1 | 1/0/0 | 100% | 100% | `AGREED` |

## 6. Error Analysis & Discrepancies
No errors or discrepancies observed across all evaluated cases.

## 7. Limitations & Scientific Constraints
- Dataset size is limited (N=6 cases); results represent benchmark validation, not production population accuracy.
- Labels are MANUALLY_CURATED reference benchmarks for compliance rules rather than infallible ground truth.
- In DEGRADED_OCR_FALLBACK mode, visual keyframe reasoning is unavailable; visual evaluation is reported as NOT_AVAILABLE.
- Evaluation engine is strictly separate and does not alter production LangGraph execution or persistent audit status.
