import re
from typing import List, Dict, Any, Tuple
from backend.evaluation.schemas import ExpectedFinding, FindingEvaluationResult, Discrepancy

def _normalize_category(val: str) -> str:
    """Normalizes category strings for deterministic comparison."""
    if not val:
        return ""
    # Remove underscores, spaces, dashes and lowercase
    return re.sub(r'[\s_\-]+', '', val.strip().lower())

def _normalize_severity(val: str) -> str:
    """Maps varied severity/status strings into standard tiers."""
    s = (val or "").strip().upper()
    if s in ("CRITICAL", "HIGH", "FAIL", "ERROR"):
        return "HIGH"
    if s in ("MEDIUM", "WARNING", "AMBER"):
        return "MEDIUM"
    if s in ("LOW", "PASS", "INFO", "NONE"):
        return "LOW"
    return s

def _match_finding(expected: ExpectedFinding, actual: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Checks if an actual finding matches an expected finding.
    Returns (is_matched, reason).
    """
    exp_cat = _normalize_category(expected.category)
    act_cat = _normalize_category(actual.get("category", "") or actual.get("rule_category", ""))
    
    if exp_cat != act_cat:
        # Partial containment check (e.g. "disclosure" in "ftcdisclosure")
        if exp_cat not in act_cat and act_cat not in exp_cat:
            return False, "Category mismatch"

    # Severity comparison
    exp_sev = _normalize_severity(expected.severity)
    act_sev = _normalize_severity(actual.get("severity", "") or actual.get("status", ""))
    
    if exp_sev != act_sev:
        return False, f"Severity mismatch: expected {expected.severity}, got {actual.get('severity')}"

    return True, "Category and severity matched"

def evaluate_findings(
    expected_findings: List[ExpectedFinding],
    actual_findings: List[Dict[str, Any]],
    case_id: str = "case"
) -> FindingEvaluationResult:
    """
    Evaluates model-produced compliance findings against reference expected findings.
    Computes TP, FP, FN, Precision, Recall, and F1 score with full error analysis.
    """
    matched_actual_indices = set()
    matched_expected_indices = set()
    discrepancies: List[Discrepancy] = []

    # 1. Match expected findings against actual findings
    for exp_idx, exp in enumerate(expected_findings):
        found_match = False
        for act_idx, act in enumerate(actual_findings):
            if act_idx in matched_actual_indices:
                continue
            
            is_match, reason = _match_finding(exp, act)
            if is_match:
                matched_actual_indices.add(act_idx)
                matched_expected_indices.add(exp_idx)
                found_match = True
                break

        if not found_match:
            # Check if there was a category match but severity mismatch
            partial_match = None
            for act_idx, act in enumerate(actual_findings):
                if act_idx in matched_actual_indices:
                    continue
                exp_cat = _normalize_category(exp.category)
                act_cat = _normalize_category(act.get("category", "") or act.get("rule_category", ""))
                if exp_cat == act_cat or exp_cat in act_cat or act_cat in exp_cat:
                    partial_match = act
                    break
            
            if partial_match:
                discrepancies.append(Discrepancy(
                    case_id=case_id,
                    failure_type="SEVERITY_MISMATCH",
                    expected=f"{exp.category} [{exp.severity}]",
                    actual=f"{partial_match.get('category')} [{partial_match.get('severity')}]",
                    observed_discrepancy=f"Finding category found but severity differed: expected {exp.severity}, got {partial_match.get('severity')}."
                ))
            else:
                discrepancies.append(Discrepancy(
                    case_id=case_id,
                    failure_type="FALSE_NEGATIVE",
                    expected=f"{exp.category} [{exp.severity}]",
                    actual=None,
                    observed_discrepancy=f"Expected finding '{exp.category}' with severity '{exp.severity}' was not reported by auditor."
                ))

    # 2. Check for unexpected actual findings (False Positives)
    for act_idx, act in enumerate(actual_findings):
        if act_idx not in matched_actual_indices:
            act_cat = act.get("category") or act.get("rule_category") or "Unknown"
            act_sev = act.get("severity") or act.get("status") or "Unknown"
            
            # If actual finding is PASS / Low, it's not a false positive violation flag unless expected was FAIL
            if _normalize_severity(act_sev) == "LOW" and not expected_findings:
                continue

            discrepancies.append(Discrepancy(
                case_id=case_id,
                failure_type="FALSE_POSITIVE",
                expected=None,
                actual=f"{act_cat} [{act_sev}]",
                evidence=act.get("description"),
                observed_discrepancy=f"Auditor reported finding '{act_cat}' with severity '{act_sev}' not present in reference labels."
            ))

    tp = len(matched_expected_indices)
    fn = len(expected_findings) - tp
    # FP counts actual findings that were neither matched nor benign PASS assertions
    fp = len([d for d in discrepancies if d.failure_type == "FALSE_POSITIVE"])

    # Precision & Recall calculations
    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if not expected_findings and not actual_findings else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if not expected_findings else 0.0)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return FindingEvaluationResult(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        matched_count=tp,
        total_expected=len(expected_findings),
        total_actual=len(actual_findings),
        discrepancies=discrepancies
    )
