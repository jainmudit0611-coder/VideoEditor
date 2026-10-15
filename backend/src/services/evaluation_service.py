import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.src.db.models import EvaluationRun, EvaluationRunStatus
from backend.src.db.evaluation_repository import EvaluationRepository
from backend.evaluation.runner import EvaluationSuiteRunner, load_evaluation_cases
from backend.evaluation.constants import (
    EVALUATION_VERSION,
    DATASET_VERSION,
    DATASET_TYPE,
    CASE_COUNT_BENCHMARK,
)

from backend.src.observability import (
    log_event,
    ObservabilityEvent,
    get_logger,
    set_correlation_context,
)

logger = get_logger("brand-guardian-evaluation-service")

class EvaluationService:
    """
    Orchestration service for executing and managing evaluation runs.
    Reuses the Phase 4B EvaluationSuiteRunner for deterministic metric computation.
    """

    def __init__(self, cases_dir: Optional[Path] = None, fixtures_dir: Optional[Path] = None):
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.cases_dir = cases_dir or (project_root / "backend" / "evaluation" / "cases")
        self.fixtures_dir = fixtures_dir or (project_root / "backend" / "evaluation" / "fixtures")
        self.runner = EvaluationSuiteRunner()

    def execute_run(self, session: Session, run_id: str) -> Optional[EvaluationRun]:
        """
        Executes an evaluation run lifecycle:
        QUEUED -> RUNNING -> Suite Execution -> Metrics Persisted -> COMPLETED.
        """
        run = EvaluationRepository.get_run(session, run_id)
        if not run:
            logger.error(f"Cannot execute evaluation run: run_id {run_id} not found.")
            return None

        set_correlation_context(evaluation_run_id=run_id)

        # Mark RUNNING
        EvaluationRepository.mark_running(session, run_id)
        start_time = time.time()

        log_event(
            logger,
            ObservabilityEvent.EVALUATION_STARTED,
            message=f"Evaluation run started: run_id={run_id}, model={run.model_name}",
            evaluation_run_id=run_id,
            model_name=run.model_name,
            provider=run.model_provider,
            dataset_version=run.dataset_version
        )

        try:
            logger.info(f"Loading evaluation cases from {self.cases_dir}...")
            cases = load_evaluation_cases(self.cases_dir)

            logger.info(f"Executing EvaluationSuiteRunner across {len(cases)} cases...")
            summary = self.runner.run_suite(
                cases=cases,
                outputs_dir=self.fixtures_dir,
                run_id=run.id,
                config_id=f"{run.model_name}:{run.prompt_version}:{run.config_version}",
                dataset_version=run.dataset_version
            )

            duration_ms = int((time.time() - start_time) * 1000)

            log_event(
                logger,
                ObservabilityEvent.EVALUATION_COMPLETED,
                message=f"Evaluation run completed: run_id={run_id} in {duration_ms}ms (cases={summary.n_cases})",
                evaluation_run_id=run_id,
                case_count=summary.n_cases,
                duration_ms=duration_ms
            )

            # Extract serializable discrepancies
            discrepancies_list = [d.model_dump() for d in summary.error_analysis]

            # Extract case-by-case summary records for UI drilldown
            case_results_list = [
                {
                    "case_id": cr.case_id,
                    "execution_mode": cr.execution_mode,
                    "findings_summary": {
                        "expected": cr.finding_metrics.total_expected,
                        "actual": cr.finding_metrics.total_actual,
                        "tp": cr.finding_metrics.true_positives,
                        "fp": cr.finding_metrics.false_positives,
                        "fn": cr.finding_metrics.false_negatives,
                        "precision": cr.finding_metrics.precision,
                        "recall": cr.finding_metrics.recall,
                        "f1": cr.finding_metrics.f1_score,
                    },
                    "grounding": {
                        "support_rate": cr.grounding_metrics.evidence_support_rate,
                        "supported": cr.grounding_metrics.supported_findings,
                        "total": cr.grounding_metrics.total_findings,
                    },
                    "citation": {
                        "presence_rate": cr.citation_metrics.citation_presence_rate,
                        "completeness_rate": cr.citation_metrics.completeness_rate,
                    },
                    "schema": {
                        "is_valid": cr.schema_metrics.is_valid,
                        "validity_rate": cr.schema_metrics.schema_validity_rate,
                    },
                    "verifier": {
                        "status": cr.verifier_metrics.status,
                        "expected": cr.verifier_metrics.expected_status,
                        "actual": cr.verifier_metrics.actual_status,
                    },
                    "timing": cr.timing_metrics or {},
                    "discrepancy_count": len(cr.discrepancies)
                }
                for cr in summary.case_results
            ]

            summary_dict = {
                "dataset_version": summary.dataset_version,
                "dataset_type": summary.dataset_type,
                "cases_evaluated": summary.n_cases,
                "execution_modes": summary.execution_modes,
                "case_results": case_results_list,
                "limitations": summary.limitations
            }

            completed_run = EvaluationRepository.save_run_results(
                session=session,
                run_id=run.id,
                metrics=summary.aggregate_metrics,
                summary=summary_dict,
                discrepancies=discrepancies_list,
                duration_ms=duration_ms,
                case_count=len(cases)
            )
            return completed_run

        except Exception as e:
            err_msg = f"Evaluation run failed: {str(e)}"
            logger.exception(err_msg)
            log_event(
                logger,
                ObservabilityEvent.EVALUATION_FAILED,
                level=logging.ERROR,
                message=err_msg,
                evaluation_run_id=run_id,
                error=str(e)
            )
            EvaluationRepository.mark_failed(session, run_id, error_message=err_msg)
            return None

    @staticmethod
    def compare_runs(runs: List[EvaluationRun]) -> Dict[str, Any]:
        """
        Builds a neutral, descriptive comparison across two or more evaluation runs.
        Computes metric differences and metadata comparison without assigning winner or ranking.
        """
        if not runs:
            return {"runs": [], "metrics": [], "differences": []}

        # Serialized run summaries
        runs_data = [
            {
                "id": r.id,
                "run_name": r.run_name,
                "status": r.status.value if isinstance(r.status, EvaluationRunStatus) else str(r.status),
                "model_name": r.model_name,
                "model_provider": r.model_provider,
                "prompt_version": r.prompt_version,
                "config_version": r.config_version,
                "dataset_version": r.dataset_version,
                "dataset_type": r.dataset_type,
                "case_count": r.case_count,
                "duration_ms": r.duration_ms,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]

        # Key metrics to compare
        metric_keys = [
            ("Finding Precision", "finding_precision", "%"),
            ("Finding Recall", "finding_recall", "%"),
            ("Finding F1 Score", "finding_f1", "float"),
            ("Evidence Support Rate", "evidence_support_rate", "%"),
            ("Unsupported Finding Rate", "unsupported_finding_rate", "%"),
            ("Citation Presence Rate", "citation_presence_rate", "%"),
            ("Citation Completeness", "citation_completeness_rate", "%"),
            ("Schema Validity Rate", "schema_validity_rate", "%"),
            ("Verifier Agreement", "verifier_agreement_rate", "%"),
        ]

        compared_metrics = []
        for label, key, display_type in metric_keys:
            row: Dict[str, Any] = {
                "metric": label,
                "key": key,
                "display_type": display_type,
                "values": {}
            }
            for r in runs:
                m = r.metrics or {}
                val = m.get(key)
                row["values"][r.id] = val

            # If exactly 2 runs, calculate numerical delta (Run B - Run A)
            if len(runs) == 2:
                v0 = row["values"].get(runs[0].id)
                v1 = row["values"].get(runs[1].id)
                if v0 is not None and v1 is not None and isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                    row["delta"] = round(float(v1) - float(v0), 4)
                else:
                    row["delta"] = None

            compared_metrics.append(row)

        # Metadata comparison differences
        metadata_fields = [
            ("Model Name", "model_name"),
            ("Model Provider", "model_provider"),
            ("Prompt Version", "prompt_version"),
            ("Config Version", "config_version"),
            ("Dataset Version", "dataset_version"),
            ("Case Count", "case_count"),
        ]
        differences = []
        for label, field in metadata_fields:
            vals = {r.id: getattr(r, field) for r in runs}
            has_difference = len(set(vals.values())) > 1
            differences.append({
                "field": label,
                "values": vals,
                "has_difference": has_difference
            })

        return {
            "runs": runs_data,
            "metrics": compared_metrics,
            "differences": differences
        }
