from typing import Dict, Any, Optional, List
from backend.evaluation.schemas import (
    EvaluationCase,
    CaseEvaluationResult,
    Discrepancy,
)
from backend.evaluation.metrics.finding_metrics import evaluate_findings
from backend.evaluation.metrics.grounding_metrics import evaluate_grounding
from backend.evaluation.metrics.citation_metrics import evaluate_citations
from backend.evaluation.metrics.schema_metrics import evaluate_schema
from backend.evaluation.metrics.verifier_metrics import evaluate_verifier

class AuditEvaluator:
    """
    Independent AI compliance evaluation engine for Brand Guardian AI.
    Evaluates finding precision/recall, multimodal evidence grounding,
    policy citations, schema conformance, and verifier agreement.
    """

    def evaluate_case(
        self,
        case: EvaluationCase,
        audit_output: Dict[str, Any],
        timing_metrics: Optional[Dict[str, float]] = None
    ) -> CaseEvaluationResult:
        """
        Executes a deterministic evaluation of an audit result against a reference case.
        """
        # Determine execution mode from output
        is_degraded = audit_output.get("is_degraded_vision_mode", False)
        execution_mode = "DEGRADED_OCR_FALLBACK" if is_degraded else "NATIVE_VISION"

        # Extract audit result components
        actual_findings = audit_output.get("compliance_results") or []
        actual_evidence = (
            audit_output.get("retrieved_evidence")
            or audit_output.get("transcript_items", [])
            + audit_output.get("ocr_items", [])
            + audit_output.get("visual_observations", [])
        )
        actual_citations = audit_output.get("citations") or []
        actual_verifier = audit_output.get("verification_summary")
        timings = timing_metrics or audit_output.get("timing_metrics")

        # 1. Schema Evaluation
        schema_res = evaluate_schema(audit_output)

        # 2. Finding Evaluation (TP, FP, FN, Precision, Recall, F1)
        finding_res = evaluate_findings(
            expected_findings=case.expected_findings,
            actual_findings=actual_findings,
            case_id=case.case_id
        )

        # 3. Evidence Grounding Evaluation
        grounding_res = evaluate_grounding(
            expected_evidence=case.expected_evidence,
            actual_evidence=actual_evidence,
            actual_findings=actual_findings,
            is_degraded_vision_mode=is_degraded,
            case_id=case.case_id
        )

        # 4. Policy Citation Evaluation
        citation_res = evaluate_citations(
            expected_citations=case.expected_citations,
            actual_citations=actual_citations,
            actual_findings=actual_findings
        )

        # 5. Verifier Evaluation
        verifier_res = evaluate_verifier(
            expected_status=case.expected_verifier_status,
            actual_verification_summary=actual_verifier
        )

        # 6. Gather all discrepancies for error analysis
        all_discrepancies: List[Discrepancy] = list(finding_res.discrepancies)

        # Add schema discrepancies if any
        if not schema_res.is_valid:
            all_discrepancies.append(Discrepancy(
                case_id=case.case_id,
                failure_type="SCHEMA_ERROR",
                expected="Valid structured schema",
                actual=f"{len(schema_res.missing_required_fields)} missing fields, {len(schema_res.validation_errors)} errors",
                observed_discrepancy=f"Schema validation failed: {schema_res.validation_errors + schema_res.missing_required_fields}"
            ))

        # Add unsupported finding discrepancies
        for d in grounding_res.details:
            if not d.get("supported", True):
                all_discrepancies.append(Discrepancy(
                    case_id=case.case_id,
                    failure_type="UNSUPPORTED_FINDING",
                    expected="Timestamped and grounded multimodal evidence",
                    actual=f"Finding '{d.get('category')}' lacks direct timestamped evidence",
                    observed_discrepancy=f"Finding category '{d.get('category')}' was reported without corroborating evidence in transcript/OCR."
                ))

        return CaseEvaluationResult(
            case_id=case.case_id,
            execution_mode=execution_mode,
            finding_metrics=finding_res,
            grounding_metrics=grounding_res,
            citation_metrics=citation_res,
            schema_metrics=schema_res,
            verifier_metrics=verifier_res,
            timing_metrics=timings,
            discrepancies=all_discrepancies
        )
