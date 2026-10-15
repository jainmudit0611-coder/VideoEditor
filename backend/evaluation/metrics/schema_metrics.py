from typing import Dict, Any, List
from backend.evaluation.schemas import SchemaEvaluationResult

REQUIRED_RESULT_KEYS = ["status", "final_report", "compliance_results"]
VALID_AUDIT_STATUSES = {"PASS", "FAIL", "WARNING", "UNRESOLVED", "COMPLETED", "FAILED"}
VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE", "FAIL", "WARNING", "PASS"}

def evaluate_schema(audit_output: Dict[str, Any]) -> SchemaEvaluationResult:
    """
    Validates whether an audit result dictionary conforms to the required
    Brand Guardian AI compliance output schema.
    """
    missing_fields: List[str] = []
    invalid_types: List[str] = []
    validation_errors: List[str] = []

    # 1. Check top-level required fields
    for key in REQUIRED_RESULT_KEYS:
        if key not in audit_output or audit_output[key] is None:
            missing_fields.append(key)

    # 2. Check top-level status value
    status = audit_output.get("status")
    if status is not None:
        if not isinstance(status, str):
            invalid_types.append("status (must be string)")
        elif status.upper() not in VALID_AUDIT_STATUSES:
            validation_errors.append(f"Invalid status enum value '{status}'")

    # 3. Check final_report
    final_report = audit_output.get("final_report")
    if final_report is not None and not isinstance(final_report, str):
        invalid_types.append("final_report (must be string)")

    # 4. Check compliance_results structure
    compliance_results = audit_output.get("compliance_results")
    if compliance_results is not None:
        if not isinstance(compliance_results, list):
            invalid_types.append("compliance_results (must be list)")
        else:
            for idx, issue in enumerate(compliance_results):
                if not isinstance(issue, dict):
                    invalid_types.append(f"compliance_results[{idx}] (must be dict)")
                    continue

                if "category" not in issue and "rule_category" not in issue:
                    missing_fields.append(f"compliance_results[{idx}].category")
                if "severity" not in issue and "status" not in issue:
                    missing_fields.append(f"compliance_results[{idx}].severity")
                if "description" not in issue:
                    missing_fields.append(f"compliance_results[{idx}].description")

                sev = issue.get("severity") or issue.get("status")
                if sev and str(sev).upper() not in VALID_SEVERITIES:
                    validation_errors.append(f"Invalid severity '{sev}' at compliance_results[{idx}]")

    # 5. Check citations structure if present
    citations = audit_output.get("citations")
    if citations is not None and not isinstance(citations, list):
        invalid_types.append("citations (must be list)")

    # 6. Check verification_summary structure if present
    verif = audit_output.get("verification_summary")
    if verif is not None and not isinstance(verif, dict):
        invalid_types.append("verification_summary (must be dict)")

    # Calculate validity rate
    total_checks = len(REQUIRED_RESULT_KEYS) + 4
    failures = len(missing_fields) + len(invalid_types) + len(validation_errors)
    validity_rate = max(0.0, round(1.0 - (failures / total_checks), 4))
    is_valid = failures == 0

    return SchemaEvaluationResult(
        is_valid=is_valid,
        schema_validity_rate=validity_rate if is_valid else min(validity_rate, 0.9),
        missing_required_fields=missing_fields,
        invalid_data_types=invalid_types,
        validation_errors=validation_errors
    )
