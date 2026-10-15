import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.evaluation.schemas import (
    EvaluationCase,
    CaseEvaluationResult,
    EvaluationRunSummary,
    Discrepancy,
)
from backend.evaluation.evaluator import AuditEvaluator
from backend.evaluation.metrics.latency_metrics import calculate_latency_summary
from backend.src.observability import (
    log_event,
    ObservabilityEvent,
    get_logger,
)

logger = get_logger("brand-guardian-evaluation-runner")

def load_evaluation_cases(cases_dir: Path) -> List[EvaluationCase]:
    """Loads all valid JSON evaluation cases from the specified directory."""
    cases: List[EvaluationCase] = []
    if not cases_dir.exists():
        raise FileNotFoundError(f"Cases directory does not exist: {cases_dir}")

    for file_path in sorted(cases_dir.glob("*.json")):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            cases.append(EvaluationCase.model_validate(data))
    return cases

def load_case_audit_output(outputs_dir: Path, case_id: str) -> Optional[Dict[str, Any]]:
    """Loads a corresponding audit output JSON fixture for a given case_id."""
    candidates = [
        outputs_dir / f"{case_id}_output.json",
        outputs_dir / f"{case_id}.json",
    ]
    for cand in candidates:
        if cand.exists():
            with open(cand, "r", encoding="utf-8") as f:
                return json.load(f)
    return None

class EvaluationSuiteRunner:
    """
    Orchestrates batch or offline evaluation across test cases and produces
    aggregate metrics, regression summaries, and error analysis reports.
    """

    def __init__(self, evaluator: Optional[AuditEvaluator] = None):
        self.evaluator = evaluator or AuditEvaluator()

    def run_suite(
        self,
        cases: List[EvaluationCase],
        outputs_dir: Path,
        run_id: Optional[str] = None,
        config_id: Optional[str] = None,
        dataset_version: str = "v1"
    ) -> EvaluationRunSummary:
        now_iso = datetime.now(timezone.utc).isoformat()
        eval_run_id = run_id or f"eval_run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        model_config = config_id or "gpt4o_audit_pipeline_v1"

        case_results: List[CaseEvaluationResult] = []
        all_discrepancies: List[Discrepancy] = []
        execution_modes_set = set()
        timing_samples: List[Dict[str, float]] = []

        # Totals for aggregate calculation
        agg_tp = 0
        agg_fp = 0
        agg_fn = 0
        total_expected_findings = 0
        total_actual_findings = 0

        total_grounding_findings = 0
        supported_grounding_findings = 0

        total_citation_findings = 0
        cited_findings_count = 0
        complete_citations_count = 0

        valid_schemas_count = 0
        verifier_agreed_count = 0
        verifier_evaluable_count = 0

        # Mode-specific stats
        mode_stats: Dict[str, Dict[str, int]] = {}

        for case in cases:
            log_event(
                logger,
                ObservabilityEvent.EVALUATION_CASE_STARTED,
                message=f"Evaluation case started: {case.case_id}",
                case_id=case.case_id,
                evaluation_run_id=eval_run_id
            )
            output = load_case_audit_output(outputs_dir, case.case_id)
            if output is None:
                # Discrepancy for missing audit result
                missing_disc = Discrepancy(
                    case_id=case.case_id,
                    failure_type="SCHEMA_ERROR",
                    expected="Valid audit result output file",
                    actual="None (File Not Found)",
                    observed_discrepancy=f"Audit output file not found in {outputs_dir} for case {case.case_id}."
                )
                all_discrepancies.append(missing_disc)
                continue

            case_res = self.evaluator.evaluate_case(case, output)
            case_results.append(case_res)
            execution_modes_set.add(case_res.execution_mode)

            log_event(
                logger,
                ObservabilityEvent.EVALUATION_CASE_COMPLETED,
                message=f"Evaluation case completed: {case.case_id} (mode={case_res.execution_mode})",
                case_id=case.case_id,
                evaluation_run_id=eval_run_id,
                execution_mode=case_res.execution_mode,
                findings_f1=case_res.finding_metrics.f1_score
            )

            # Record mode
            mode = case_res.execution_mode
            if mode not in mode_stats:
                mode_stats[mode] = {"tp": 0, "fp": 0, "fn": 0, "cases": 0}
            mode_stats[mode]["cases"] += 1
            mode_stats[mode]["tp"] += case_res.finding_metrics.true_positives
            mode_stats[mode]["fp"] += case_res.finding_metrics.false_positives
            mode_stats[mode]["fn"] += case_res.finding_metrics.false_negatives

            # Aggregate finding metrics
            agg_tp += case_res.finding_metrics.true_positives
            agg_fp += case_res.finding_metrics.false_positives
            agg_fn += case_res.finding_metrics.false_negatives
            total_expected_findings += case_res.finding_metrics.total_expected
            total_actual_findings += case_res.finding_metrics.total_actual

            # Aggregate grounding metrics
            total_grounding_findings += case_res.grounding_metrics.total_findings
            supported_grounding_findings += case_res.grounding_metrics.supported_findings

            # Aggregate citations
            total_citation_findings += case_res.citation_metrics.total_findings
            cited_findings_count += case_res.citation_metrics.cited_findings
            complete_citations_count += case_res.citation_metrics.complete_citations_count

            # Aggregate schema
            if case_res.schema_metrics.is_valid:
                valid_schemas_count += 1

            # Aggregate verifier
            if case_res.verifier_metrics.status != "NOT_AVAILABLE":
                verifier_evaluable_count += 1
                if case_res.verifier_metrics.status == "AGREED":
                    verifier_agreed_count += 1

            # Discrepancies
            all_discrepancies.extend(case_res.discrepancies)

            # Timings
            if case_res.timing_metrics:
                timing_samples.append(case_res.timing_metrics)

        # Calculate overall precision, recall, F1
        p_denom = agg_tp + agg_fp
        overall_precision = round(agg_tp / p_denom, 4) if p_denom > 0 else (1.0 if agg_fn == 0 else 0.0)

        r_denom = agg_tp + agg_fn
        overall_recall = round(agg_tp / r_denom, 4) if r_denom > 0 else (1.0 if agg_fp == 0 else 0.0)

        f1_denom = overall_precision + overall_recall
        overall_f1 = round(2 * (overall_precision * overall_recall) / f1_denom, 4) if f1_denom > 0 else 0.0

        evidence_support_rate = round(supported_grounding_findings / total_grounding_findings, 4) if total_grounding_findings > 0 else 1.0
        unsupported_finding_rate = round(1.0 - evidence_support_rate, 4)

        citation_presence_rate = round(cited_findings_count / total_citation_findings, 4) if total_citation_findings > 0 else 1.0
        citation_completeness_rate = round(complete_citations_count / total_citation_findings, 4) if total_citation_findings > 0 else 1.0

        n_evaluated = len(case_results)
        schema_validity_rate = round(valid_schemas_count / n_evaluated, 4) if n_evaluated > 0 else 1.0

        verifier_agreement_rate = (
            round(verifier_agreed_count / verifier_evaluable_count, 4)
            if verifier_evaluable_count > 0
            else None
        )

        latency_summary = calculate_latency_summary(timing_samples)

        aggregate_metrics = {
            "finding_precision": overall_precision,
            "finding_recall": overall_recall,
            "finding_f1": overall_f1,
            "true_positives": agg_tp,
            "false_positives": agg_fp,
            "false_negatives": agg_fn,
            "total_expected_findings": total_expected_findings,
            "total_actual_findings": total_actual_findings,
            "evidence_support_rate": evidence_support_rate,
            "unsupported_finding_rate": unsupported_finding_rate,
            "citation_presence_rate": citation_presence_rate,
            "citation_completeness_rate": citation_completeness_rate,
            "schema_validity_rate": schema_validity_rate,
            "verifier_agreement_rate": verifier_agreement_rate,
            "latency": latency_summary.model_dump(),
            "mode_breakdown": {
                m: {
                    "cases": stats["cases"],
                    "precision": round(stats["tp"] / (stats["tp"] + stats["fp"]), 4) if (stats["tp"] + stats["fp"]) > 0 else 1.0,
                    "recall": round(stats["tp"] / (stats["tp"] + stats["fn"]), 4) if (stats["tp"] + stats["fn"]) > 0 else 1.0,
                }
                for m, stats in mode_stats.items()
            }
        }

        limitations = [
            f"Dataset size is limited (N={len(cases)} cases); results represent benchmark validation, not production population accuracy.",
            "Labels are MANUALLY_CURATED reference benchmarks for compliance rules rather than infallible ground truth.",
            "In DEGRADED_OCR_FALLBACK mode, visual keyframe reasoning is unavailable; visual evaluation is reported as NOT_AVAILABLE.",
            "Evaluation engine is strictly separate and does not alter production LangGraph execution or persistent audit status."
        ]

        return EvaluationRunSummary(
            evaluation_run_id=eval_run_id,
            timestamp=now_iso,
            dataset_version=dataset_version,
            dataset_type="MANUALLY_CURATED",
            n_cases=len(cases),
            execution_modes=sorted(list(execution_modes_set)),
            aggregate_metrics=aggregate_metrics,
            case_results=case_results,
            error_analysis=all_discrepancies,
            limitations=limitations
        )

def generate_markdown_report(summary: EvaluationRunSummary) -> str:
    """Formats an EvaluationRunSummary into a clean, human-readable markdown report."""
    agg = summary.aggregate_metrics
    modes_str = ", ".join(summary.execution_modes) if summary.execution_modes else "N/A"

    v_agree_str = f"{agg['verifier_agreement_rate'] * 100:.1f}%" if agg['verifier_agreement_rate'] is not None else "N/A (insufficient reference)"
    lat = agg.get("latency", {})
    lat_mean = f"{lat.get('mean_duration_sec', 'N/A')}s" if lat.get("mean_duration_sec") is not None else "N/A"
    lat_median = f"{lat.get('median_duration_sec', 'N/A')}s" if lat.get("median_duration_sec") is not None else "N/A"
    lat_min = f"{lat.get('min_duration_sec', 'N/A')}s" if lat.get("min_duration_sec") is not None else "N/A"
    lat_max = f"{lat.get('max_duration_sec', 'N/A')}s" if lat.get("max_duration_sec") is not None else "N/A"

    lines = [
        "# Brand Guardian AI — Evaluation Report",
        "",
        "## 1. Run Metadata",
        f"- **Evaluation Run ID**: `{summary.evaluation_run_id}`",
        f"- **Timestamp**: `{summary.timestamp}`",
        f"- **Dataset Version**: `{summary.dataset_version}`",
        f"- **Dataset Type**: `{summary.dataset_type}`",
        f"- **Cases Evaluated (N)**: `{summary.n_cases}`",
        f"- **Execution Modes**: `{modes_str}`",
        "",
        "## 2. Evaluation Summary",
        "",
        "| Metric | Value | Description |",
        "| :--- | :--- | :--- |",
        f"| **Finding Precision** | `{agg['finding_precision']:.2f}` ({agg['finding_precision']*100:.1f}%) | TP / (TP + FP) across all findings |",
        f"| **Finding Recall** | `{agg['finding_recall']:.2f}` ({agg['finding_recall']*100:.1f}%) | TP / (TP + FN) across expected findings |",
        f"| **Finding F1 Score** | `{agg['finding_f1']:.2f}` | Harmonic mean of finding precision and recall |",
        f"| **Evidence Support Rate** | `{agg['evidence_support_rate']:.2f}` ({agg['evidence_support_rate']*100:.1f}%) | Findings supported by timestamped evidence |",
        f"| **Unsupported Finding Rate** | `{agg['unsupported_finding_rate']:.2f}` ({agg['unsupported_finding_rate']*100:.1f}%) | Hallucinated or unsubstantiated findings |",
        f"| **Citation Presence Rate** | `{agg['citation_presence_rate']:.2f}` ({agg['citation_presence_rate']*100:.1f}%) | Findings backed by policy/RAG citation |",
        f"| **Citation Completeness** | `{agg['citation_completeness_rate']:.2f}` ({agg['citation_completeness_rate']*100:.1f}%) | Citations with title, rule, and excerpt |",
        f"| **Schema Validity Rate** | `{agg['schema_validity_rate']:.2f}` ({agg['schema_validity_rate']*100:.1f}%) | Strict conformance to expected schema |",
        f"| **Verifier Agreement** | `{v_agree_str}` | Alignment with expected verifier outcome |",
        "",
        "## 3. Latency & Execution Performance",
        f"- **Sample Count (N)**: {lat.get('n_samples', 0)}",
        f"- **Mean Audit Duration**: {lat_mean}",
        f"- **Median Audit Duration**: {lat_median}",
        f"- **Min / Max Duration**: {lat_min} / {lat_max}",
        "",
        "### Stage Execution Breakdown (Averages)",
    ]

    stage_lat = lat.get("stage_latencies", {})
    if stage_lat:
        lines.append("| Pipeline Stage | Average Duration (s) |")
        lines.append("| :--- | :--- |")
        for stage, dur in sorted(stage_lat.items()):
            lines.append(f"| `{stage}` | {dur:.2f}s |")
    else:
        lines.append("*No stage latency breakdowns recorded in sample.*")

    lines.extend([
        "",
        "## 4. Execution Mode Breakdown",
        "| Execution Mode | Case Count | Precision | Recall |",
        "| :--- | :--- | :--- | :--- |"
    ])
    for mode_name, m_metrics in agg.get("mode_breakdown", {}).items():
        lines.append(f"| `{mode_name}` | {m_metrics['cases']} | {m_metrics['precision']:.2f} | {m_metrics['recall']:.2f} |")

    lines.extend([
        "",
        "## 5. Detailed Case Breakdown",
        "| Case ID | Execution Mode | Expected Findings | Actual Findings | TP / FP / FN | Grounded % | Citations | Verifier |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ])

    for cr in summary.case_results:
        fm = cr.finding_metrics
        gm = cr.grounding_metrics
        cm = cr.citation_metrics
        vm = cr.verifier_metrics
        v_status = vm.status if vm.status != "NOT_AVAILABLE" else "N/A"
        lines.append(
            f"| `{cr.case_id}` | `{cr.execution_mode}` | {fm.total_expected} | {fm.total_actual} | "
            f"{fm.true_positives}/{fm.false_positives}/{fm.false_negatives} | "
            f"{gm.evidence_support_rate*100:.0f}% | {cm.citation_presence_rate*100:.0f}% | `{v_status}` |"
        )

    lines.extend([
        "",
        "## 6. Error Analysis & Discrepancies",
    ])

    if summary.error_analysis:
        for idx, disc in enumerate(summary.error_analysis, 1):
            lines.extend([
                f"### Discrepancy #{idx}: Case `{disc.case_id}`",
                f"- **Failure Type**: `{disc.failure_type}`",
                f"- **Expected**: {disc.expected or 'N/A'}",
                f"- **Actual**: {disc.actual or 'N/A'}",
                f"- **Observed Discrepancy**: {disc.observed_discrepancy}",
                ""
            ])
    else:
        lines.append("No errors or discrepancies observed across all evaluated cases.")

    lines.extend([
        "",
        "## 7. Limitations & Scientific Constraints",
    ])
    for lim in summary.limitations:
        lines.append(f"- {lim}")

    lines.append("")
    return "\n".join(lines)

def run_evaluation(
    cases_dir: Optional[Path] = None,
    outputs_dir: Optional[Path] = None,
    output_json: Optional[Path] = None,
    output_md: Optional[Path] = None,
    run_id: Optional[str] = None,
    config_id: Optional[str] = None,
) -> EvaluationRunSummary:
    """Main program entrypoint for running evaluation."""
    project_root = Path(__file__).resolve().parent.parent.parent
    c_dir = cases_dir or (project_root / "backend" / "evaluation" / "cases")
    o_dir = outputs_dir or (project_root / "backend" / "evaluation" / "fixtures")
    out_json = output_json or (project_root / "evaluation_report.json")
    out_md = output_md or (project_root / "evaluation_report.md")

    cases = load_evaluation_cases(c_dir)
    runner = EvaluationSuiteRunner()
    summary = runner.run_suite(
        cases=cases,
        outputs_dir=o_dir,
        run_id=run_id,
        config_id=config_id
    )

    # Write JSON report
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary.model_dump(), f, indent=2)

    # Write Markdown report
    md_content = generate_markdown_report(summary)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"=== Brand Guardian AI Evaluation Complete ===")
    print(f"Evaluated Cases: {summary.n_cases}")
    print(f"Finding Precision: {summary.aggregate_metrics['finding_precision']:.2f}")
    print(f"Finding Recall:    {summary.aggregate_metrics['finding_recall']:.2f}")
    print(f"Finding F1:        {summary.aggregate_metrics['finding_f1']:.2f}")
    print(f"Evidence Support:  {summary.aggregate_metrics['evidence_support_rate']:.2f}")
    print(f"Citation Presence: {summary.aggregate_metrics['citation_presence_rate']:.2f}")
    print(f"Schema Validity:   {summary.aggregate_metrics['schema_validity_rate']:.2f}")
    print(f"Reports saved to:")
    print(f"  JSON: {out_json}")
    print(f"  MD:   {out_md}")

    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brand Guardian AI Audit Evaluation Runner")
    parser.add_argument("--cases-dir", type=str, default=None, help="Directory containing reference case JSON files")
    parser.add_argument("--outputs-dir", type=str, default=None, help="Directory containing audit output fixture JSON files")
    parser.add_argument("--output-json", type=str, default=None, help="Output path for evaluation_report.json")
    parser.add_argument("--output-md", type=str, default=None, help="Output path for evaluation_report.md")
    parser.add_argument("--run-id", type=str, default=None, help="Optional evaluation run identifier")
    parser.add_argument("--config-id", type=str, default=None, help="Optional model/prompt configuration identifier")

    args = parser.parse_args()

    c_path = Path(args.cases_dir) if args.cases_dir else None
    o_path = Path(args.outputs_dir) if args.outputs_dir else None
    j_path = Path(args.output_json) if args.output_json else None
    m_path = Path(args.output_md) if args.output_md else None

    run_evaluation(
        cases_dir=c_path,
        outputs_dir=o_path,
        output_json=j_path,
        output_md=m_path,
        run_id=args.run_id,
        config_id=args.config_id
    )
