from typing import Dict, Any, Optional
from backend.evaluation.schemas import VerifierEvaluationResult

VALID_VERIFIER_STATUSES = {"VERIFIED", "NEEDS_MORE_EVIDENCE", "UNRESOLVED", "PASSED"}

def evaluate_verifier(
    expected_status: Optional[str],
    actual_verification_summary: Optional[Dict[str, Any]]
) -> VerifierEvaluationResult:
    """
    Evaluates verifier agent outcome against reference expected status.
    """
    if not expected_status:
        return VerifierEvaluationResult(
            expected_status=None,
            actual_status=None,
            agreement=None,
            status="NOT_AVAILABLE"
        )

    actual_status = None
    if actual_verification_summary:
        actual_status = (
            actual_verification_summary.get("overall_status")
            or actual_verification_summary.get("status")
        )
        if actual_status is None and "verified" in actual_verification_summary:
            actual_status = "VERIFIED" if actual_verification_summary["verified"] else "NEEDS_MORE_EVIDENCE"

    if not actual_status:
        return VerifierEvaluationResult(
            expected_status=expected_status,
            actual_status=None,
            agreement=False,
            status="DISAGREED"
        )

    exp_clean = expected_status.strip().upper()
    act_clean = str(actual_status).strip().upper()

    # Normalization (e.g. PASSED -> VERIFIED)
    if exp_clean == "PASS":
        exp_clean = "VERIFIED"
    if act_clean in ("PASS", "PASSED"):
        act_clean = "VERIFIED"

    agreement = exp_clean == act_clean

    return VerifierEvaluationResult(
        expected_status=expected_status,
        actual_status=str(actual_status),
        agreement=agreement,
        status="AGREED" if agreement else "DISAGREED"
    )
