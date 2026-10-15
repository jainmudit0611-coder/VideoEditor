import re
from typing import List, Dict, Any, Optional
from backend.evaluation.schemas import ExpectedEvidence, GroundingEvaluationResult, Discrepancy

def _normalize_text(text: Optional[str]) -> str:
    """Normalizes text for robust substring matching (lowercase, strip punctuation/spaces)."""
    if not text:
        return ""
    cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
    return " ".join(cleaned.split())

def _has_timestamp(val: Any) -> bool:
    """Checks if timestamp information is attached to an evidence record."""
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str) and len(val.strip()) > 0:
        return bool(re.search(r'\d', val))
    return False

def evaluate_grounding(
    expected_evidence: List[ExpectedEvidence],
    actual_evidence: List[Dict[str, Any]],
    actual_findings: List[Dict[str, Any]],
    is_degraded_vision_mode: bool = False,
    case_id: str = "case"
) -> GroundingEvaluationResult:
    """
    Evaluates grounding quality of audit findings and evidence items.
    Checks:
    1. Finding Grounding: Does each finding have timestamped/substantiating evidence?
    2. Expected Signal Presence: Are expected key phrases captured in actual evidence?
    3. Multimodal integrity: Transcript, OCR, and Visual support.
    """
    total_findings = len(actual_findings)
    supported_findings = 0
    unsupported_findings = 0
    details = []

    # 1. Evaluate finding-level evidence support
    for idx, finding in enumerate(actual_findings):
        # A finding can have attached video_evidence or timestamp
        has_direct_evidence = bool(finding.get("video_evidence"))
        has_timestamp = _has_timestamp(finding.get("timestamp")) or _has_timestamp(
            (finding.get("video_evidence") or {}).get("start_time")
        )
        has_evidence_ref = bool(finding.get("evidence_ref") or finding.get("description"))

        # We also check if any actual_evidence item shares timestamp or relevance
        corroborated_in_stream = False
        if actual_evidence:
            finding_text = _normalize_text(finding.get("description", ""))
            finding_ts = str(finding.get("timestamp") or "").strip()
            for ev in actual_evidence:
                ev_ts = str(ev.get("timestamp") or ev.get("start_time") or "").strip()
                if finding_ts and ev_ts and (finding_ts in ev_ts or ev_ts in finding_ts):
                    corroborated_in_stream = True
                    break
                ev_content = _normalize_text(
                    ev.get("content") or ev.get("excerpt") or ev.get("text") or ev.get("description", "")
                )
                if ev_content and finding_text and any(w in ev_content for w in finding_text.split()[:4] if len(w) > 3):
                    corroborated_in_stream = True
                    break

        is_supported = (has_direct_evidence and has_timestamp) or (has_timestamp and corroborated_in_stream) or (has_timestamp and has_evidence_ref)
        
        if is_supported:
            supported_findings += 1
        else:
            unsupported_findings += 1

        details.append({
            "finding_index": idx,
            "category": finding.get("category") or finding.get("rule_category"),
            "supported": is_supported,
            "has_timestamp": has_timestamp,
            "has_direct_evidence": has_direct_evidence
        })

    # 2. Evaluate expected evidence signal containment
    transcript_matches = 0
    ocr_matches = 0
    visual_matches = 0

    for exp_ev in expected_evidence:
        exp_text = _normalize_text(exp_ev.contains)
        matched = False

        for act_ev in actual_evidence:
            ev_type = (act_ev.get("type") or act_ev.get("evidence_type") or "").upper()
            if ev_type != exp_ev.type.upper():
                continue

            act_text = _normalize_text(
                act_ev.get("content") or act_ev.get("excerpt") or act_ev.get("text") or act_ev.get("description", "")
            )
            if exp_text in act_text or act_text in exp_text:
                matched = True
                if ev_type == "TRANSCRIPT":
                    transcript_matches += 1
                elif ev_type == "OCR":
                    ocr_matches += 1
                elif ev_type == "VISUAL":
                    visual_matches += 1
                break

    # Calculate rates
    if total_findings > 0:
        support_rate = round(supported_findings / total_findings, 4)
        unsupported_rate = round(unsupported_findings / total_findings, 4)
    else:
        # If there are 0 findings and 0 expected findings, grounding is 1.0 (no unsupported claims)
        support_rate = 1.0
        unsupported_rate = 0.0

    visual_status = "NOT_AVAILABLE" if is_degraded_vision_mode else "AVAILABLE"

    return GroundingEvaluationResult(
        total_findings=total_findings,
        supported_findings=supported_findings,
        unsupported_findings=unsupported_findings,
        evidence_support_rate=support_rate,
        unsupported_finding_rate=unsupported_rate,
        transcript_matches=transcript_matches,
        ocr_matches=ocr_matches,
        visual_matches=visual_matches,
        visual_evaluation_status=visual_status,
        details=details
    )
