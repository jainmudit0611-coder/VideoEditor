from typing import List, Dict, Any
from backend.evaluation.schemas import ExpectedCitation, CitationEvaluationResult

def evaluate_citations(
    expected_citations: List[ExpectedCitation],
    actual_citations: List[Dict[str, Any]],
    actual_findings: List[Dict[str, Any]]
) -> CitationEvaluationResult:
    """
    Evaluates policy citations attached to audit results.
    Measures Citation Presence Rate and Citation Completeness.
    """
    total_findings = len(actual_findings)
    details = []
    
    # 1. Check if overall citations list is populated
    has_global_citations = bool(actual_citations and len(actual_citations) > 0)
    
    # 2. Check each finding for policy citation support
    findings_with_citations = 0
    complete_citations = 0

    for idx, finding in enumerate(actual_findings):
        # A finding can have policy_evidence or match an item in global citations
        policy_ev = finding.get("policy_evidence") or finding.get("citation")
        cat = (finding.get("category") or finding.get("rule_category") or "").lower()

        finding_cited = False
        is_complete = False

        if policy_ev and isinstance(policy_ev, dict):
            finding_cited = True
            doc = policy_ev.get("document") or policy_ev.get("source") or policy_ev.get("policy_name")
            content = policy_ev.get("content") or policy_ev.get("rule_text")
            if doc and content:
                is_complete = True
        elif has_global_citations:
            # Check if any citation matches finding category
            for cite in actual_citations:
                cite_doc = (cite.get("document") or cite.get("source") or cite.get("policy_name") or "").lower()
                cite_content = (cite.get("content") or cite.get("rule_text") or "").lower()
                if cat in cite_doc or cat in cite_content or len(actual_citations) >= total_findings:
                    finding_cited = True
                    if cite_doc and cite_content:
                        is_complete = True
                    break

        if finding_cited:
            findings_with_citations += 1
        if is_complete:
            complete_citations += 1

        details.append({
            "finding_index": idx,
            "category": finding.get("category"),
            "has_citation": finding_cited,
            "is_complete": is_complete
        })

    # When no findings exist, presence rate is 1.0 (no uncited claims)
    if total_findings > 0:
        presence_rate = round(findings_with_citations / total_findings, 4)
        completeness_rate = round(complete_citations / total_findings, 4)
    else:
        presence_rate = 1.0 if has_global_citations or not expected_citations else 0.0
        completeness_rate = 1.0 if has_global_citations or not expected_citations else 0.0

    return CitationEvaluationResult(
        total_findings=total_findings,
        cited_findings=findings_with_citations,
        citation_presence_rate=presence_rate,
        complete_citations_count=complete_citations,
        completeness_rate=completeness_rate,
        details=details
    )
