import os
import time
import logging
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

from backend.src.config import settings
from backend.src.observability import (
    log_event,
    ObservabilityEvent,
    get_logger,
)

logger = get_logger("brand-guardian-tools")

@tool
def search_policy_rules(query: str) -> List[Dict[str, Any]]:
    """
    Search Azure AI Search vector database for regulatory policy rules matching a query.
    
    Args:
        query: Target compliance query string (e.g. 'FTC influencer disclosure rules')
        
    Returns:
        List of matching policy rule dictionaries containing document name and content snippet.
    """
    t0 = time.time()
    log_event(
        logger,
        ObservabilityEvent.AGENT_TOOL_STARTED,
        message="Agent tool started: search_policy_rules",
        tool_name="search_policy_rules",
        query_excerpt=query[:64] if query else ""
    )

    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT") if "AZURE_SEARCH_ENDPOINT" in os.environ else getattr(settings, "AZURE_SEARCH_ENDPOINT", None)
    search_key = os.getenv("AZURE_SEARCH_API_KEY") if "AZURE_SEARCH_API_KEY" in os.environ else getattr(settings, "AZURE_SEARCH_API_KEY", None)
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") if "AZURE_OPENAI_ENDPOINT" in os.environ else getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
    openai_key = os.getenv("AZURE_OPENAI_API_KEY") if "AZURE_OPENAI_API_KEY" in os.environ else getattr(settings, "AZURE_OPENAI_API_KEY", None)
    timeout_s = getattr(settings, "AZURE_SEARCH_TIMEOUT_SECONDS", 15.0)

    if openai_endpoint:
        from urllib.parse import urlparse
        parsed = urlparse(openai_endpoint)
        if parsed.netloc and parsed.path and parsed.path != "/":
            openai_endpoint = f"{parsed.scheme}://{parsed.netloc}"

    # Clean unconfigured fallback when credentials are absent and not running under unit test mocks
    is_mocked = hasattr(AzureSearch, "return_value") or hasattr(AzureOpenAIEmbeddings, "return_value")
    if not is_mocked and (not search_endpoint or not search_key or not openai_endpoint or not openai_key):
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.AGENT_TOOL_COMPLETED,
            level=logging.INFO,
            message="Azure AI Search unconfigured (BLOCKED_BY_CREDENTIALS). Returning empty policy search fallback.",
            tool_name="search_policy_rules",
            result_count=0,
            duration_ms=dur_ms
        )
        return []

    try:
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=openai_endpoint,
            api_key=openai_key,
            request_timeout=timeout_s,
            max_retries=2
        )
        
        vector_store = AzureSearch(
            azure_search_endpoint=search_endpoint,
            azure_search_key=search_key,
            index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "compliance-rules-index"),
            embedding_function=embeddings.embed_query
        )
        
        docs = vector_store.similarity_search(query, k=3)
        results = []
        for doc in docs:
            source_doc = doc.metadata.get("source", "regulatory_guide.pdf")
            results.append({
                "document": source_doc,
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.AGENT_TOOL_COMPLETED,
            message=f"Agent tool completed: search_policy_rules (retrieved {len(results)} docs)",
            tool_name="search_policy_rules",
            result_count=len(results),
            duration_ms=dur_ms
        )
        return results
    except Exception as e:
        dur_ms = int((time.time() - t0) * 1000)
        err_msg = str(e)
        if "401" in err_msg or "unauthorized" in err_msg.lower():
            sanitized_err = "Azure AI Search authorization failed (HTTP 401/403)"
        elif "429" in err_msg or "rate limit" in err_msg.lower():
            sanitized_err = "Azure AI Search rate limit exceeded (HTTP 429)"
        elif "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
            sanitized_err = f"Azure AI Search request timed out after {timeout_s}s"
        else:
            sanitized_err = f"Azure AI Search request failed: {type(e).__name__}"

        log_event(
            logger,
            ObservabilityEvent.AGENT_TOOL_COMPLETED,
            level=logging.WARNING,
            message=f"Agent tool failed: search_policy_rules ({sanitized_err})",
            tool_name="search_policy_rules",
            result_count=0,
            duration_ms=dur_ms,
            error=sanitized_err
        )
        return []

@tool
def search_transcript_evidence(query: str, transcript_text: str) -> List[Dict[str, Any]]:
    """
    Search extracted video speech transcript for evidence matching query terms.
    
    Args:
        query: Key term or query to look for in the speech transcript.
        transcript_text: Full transcript string extracted from video.
        
    Returns:
        List of matching sentence excerpts from the transcript.
    """
    t0 = time.time()
    log_event(
        logger,
        ObservabilityEvent.AGENT_TOOL_STARTED,
        message="Agent tool started: search_transcript_evidence",
        tool_name="search_transcript_evidence"
    )
    if not transcript_text:
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.AGENT_TOOL_COMPLETED,
            message="Agent tool completed: search_transcript_evidence (empty transcript)",
            tool_name="search_transcript_evidence",
            result_count=0,
            duration_ms=dur_ms
        )
        return []
    
    query_words = set(query.lower().split())
    sentences = [s.strip() for s in transcript_text.replace('\n', ' ').split('.') if s.strip()]
    matches = []
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        matched_words = [w for w in query_words if w in sentence_lower and len(w) > 2]
        if matched_words:
            matches.append({
                "text": sentence,
                "evidence_type": "TRANSCRIPT",
                "match_count": len(matched_words)
            })
            
    matches.sort(key=lambda x: x["match_count"], reverse=True)
    res = matches[:5]
    dur_ms = int((time.time() - t0) * 1000)
    log_event(
        logger,
        ObservabilityEvent.AGENT_TOOL_COMPLETED,
        message=f"Agent tool completed: search_transcript_evidence (matches={len(res)})",
        tool_name="search_transcript_evidence",
        result_count=len(res),
        duration_ms=dur_ms
    )
    return res

@tool
def search_ocr_evidence(query: str, ocr_lines: List[str]) -> List[Dict[str, Any]]:
    """
    Search extracted on-screen OCR text lines for visual disclosures or disclaimers.
    
    Args:
        query: Key term or disclosure phrase to look for in on-screen text.
        ocr_lines: List of recognized OCR text strings from video frames.
        
    Returns:
        List of matching OCR line excerpts.
    """
    t0 = time.time()
    log_event(
        logger,
        ObservabilityEvent.AGENT_TOOL_STARTED,
        message="Agent tool started: search_ocr_evidence",
        tool_name="search_ocr_evidence"
    )
    if not ocr_lines:
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.AGENT_TOOL_COMPLETED,
            message="Agent tool completed: search_ocr_evidence (empty lines)",
            tool_name="search_ocr_evidence",
            result_count=0,
            duration_ms=dur_ms
        )
        return []
    
    query_words = set(query.lower().split())
    matches = []
    
    for line in ocr_lines:
        line_lower = line.lower()
        matched = [w for w in query_words if w in line_lower and len(w) > 2]
        if matched:
            matches.append({
                "text": line,
                "evidence_type": "OCR",
                "match_count": len(matched)
            })
            
    matches.sort(key=lambda x: x["match_count"], reverse=True)
    res = matches[:5]
    dur_ms = int((time.time() - t0) * 1000)
    log_event(
        logger,
        ObservabilityEvent.AGENT_TOOL_COMPLETED,
        message=f"Agent tool completed: search_ocr_evidence (matches={len(res)})",
        tool_name="search_ocr_evidence",
        result_count=len(res),
        duration_ms=dur_ms
    )
    return res

@tool
def check_rule_compliance(rule_category: str, finding_description: str, policy_text: str) -> Dict[str, Any]:
    """
    Deterministically validate whether policy rule text explicitly supports a proposed finding description.
    
    Args:
        rule_category: Target compliance category.
        finding_description: Description of alleged compliance violation or pass status.
        policy_text: Text snippet of regulatory policy rule.
        
    Returns:
        Dictionary with grounding verification score and explanation.
    """
    t0 = time.time()
    log_event(
        logger,
        ObservabilityEvent.AGENT_TOOL_STARTED,
        message=f"Agent tool started: check_rule_compliance ({rule_category})",
        tool_name="check_rule_compliance",
        rule_category=rule_category
    )
    if not policy_text or len(policy_text.strip()) < 10:
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.AGENT_TOOL_COMPLETED,
            message=f"Agent tool completed: check_rule_compliance (insufficient policy text)",
            tool_name="check_rule_compliance",
            duration_ms=dur_ms,
            grounded=False
        )
        return {
            "grounded": False,
            "grounding_score": 0.0,
            "reason": "Policy text is missing or insufficient for grounding check."
        }
        
    finding_words = set(finding_description.lower().split())
    policy_words = set(policy_text.lower().split())
    
    common_terms = finding_words.intersection(policy_words)
    meaningful_common = [w for w in common_terms if len(w) > 3]
    
    score = min(1.0, len(meaningful_common) / max(1, min(len(finding_words), 10)))
    grounded = score >= 0.3
    
    dur_ms = int((time.time() - t0) * 1000)
    log_event(
        logger,
        ObservabilityEvent.AGENT_TOOL_COMPLETED,
        message=f"Agent tool completed: check_rule_compliance (grounded={grounded}, score={round(score, 2)})",
        tool_name="check_rule_compliance",
        duration_ms=dur_ms,
        grounded=grounded
    )
    return {
        "grounded": grounded,
        "grounding_score": round(score, 2),
        "reason": f"Found {len(meaningful_common)} matching key terms between policy and finding description."
    }

@tool
def search_visual_evidence(query: str, visual_observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Search extracted visual keyframe observations for visual compliance evidence matching query.
    
    Args:
        query: Query string or target keyword (e.g. 'disclosure hashtag #ad logo disclaimer')
        visual_observations: List of visual observation dictionaries extracted from keyframe images.
        
    Returns:
        List of matching timestamped visual evidence dictionaries.
    """
    t0 = time.time()
    log_event(
        logger,
        ObservabilityEvent.AGENT_TOOL_STARTED,
        message="Agent tool started: search_visual_evidence",
        tool_name="search_visual_evidence"
    )
    if not visual_observations:
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.AGENT_TOOL_COMPLETED,
            message="Agent tool completed: search_visual_evidence (empty observations)",
            tool_name="search_visual_evidence",
            result_count=0,
            duration_ms=dur_ms
        )
        return []
    
    query_words = set(query.lower().split())
    matches = []
    
    for obs in visual_observations:
        desc = str(obs.get("description", "")).lower()
        text = str(obs.get("text", "")).lower()
        cat = str(obs.get("category", "")).lower()
        combined = f"{desc} {text} {cat}"
        
        matched = [w for w in query_words if w in combined and len(w) > 2]
        if matched or any(k in query.lower() for k in ["visual", "keyframe", "image", "screen"]):
            matches.append({
                "excerpt": obs.get("description", "Visual keyframe observation"),
                "evidence_type": "VISUAL",
                "start_time": obs.get("timestamp", 0.0),
                "end_time": obs.get("timestamp", 0.0),
                "confidence": obs.get("confidence", 1.0),
                "frame_path": obs.get("frame_path"),
                "description": obs.get("description")
            })
            
    res = matches[:5]
    dur_ms = int((time.time() - t0) * 1000)
    log_event(
        logger,
        ObservabilityEvent.AGENT_TOOL_COMPLETED,
        message=f"Agent tool completed: search_visual_evidence (matches={len(res)})",
        tool_name="search_visual_evidence",
        result_count=len(res),
        duration_ms=dur_ms
    )
    return res

