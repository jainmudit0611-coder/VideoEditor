import json
import os
import time
import logging
import re
from typing import Dict, Any, List, Literal
from pydantic import BaseModel, Field

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_core.messages import SystemMessage, HumanMessage

# Import State Schema & Structured Models
from backend.src.graph.state import (
    VideoAuditState,
    ComplianceIssue,
    AuditPlan,
    ComplianceFinding,
    VerificationOutcome,
    VerificationResult,
    PolicyCitation,
    VideoEvidence,
    VisualObservation
)

# Import Tools
from backend.src.graph.tools import (
    search_policy_rules,
    search_transcript_evidence,
    search_ocr_evidence,
    search_visual_evidence,
    check_rule_compliance
)

# Import Services
from backend.src.services.video_indexer import VideoIndexerService
from backend.src.services.video_frames import VideoFrameExtractorService
from backend.src.services.vision_analyzer import VisionAnalyzerService

from backend.src.observability import (
    log_event,
    ObservabilityEvent,
    get_logger,
    ErrorCode,
)

# Configure Logger
logger = get_logger("brand-guardian-nodes")

class AuditFindingsResult(BaseModel):
    """Structured response container for the Auditor node."""
    overall_status: Literal["PASS", "FAIL", "WARNING"] = Field(description="Overall compliance verdict")
    findings: List[ComplianceFinding] = Field(description="List of grounded compliance findings")
    summary: str = Field(description="Executive summary of compliance findings")

# --- NODE 1: THE INDEXER ---
def index_video_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Downloads YouTube video, uploads to Azure Video Indexer, and extracts transcript & OCR insights with temporal timestamps.
    """
    start_total = time.time()
    video_url = str(state.get("video_url") or "")
    video_id_input = state.get("video_id", "vid_demo")
    
    log_event(
        logger,
        ObservabilityEvent.NODE_STARTED,
        message=f"Node: indexer started processing: {video_url}",
        node="indexer",
        video_url=video_url
    )
    
    local_filename = f"temp_audit_{video_id_input}.mp4"
    timing = state.get("timing_metrics", {})
    
    try:
        vi_service = VideoIndexerService()
        
        # 1. DOWNLOAD
        t0 = time.time()
        if "youtube.com" in video_url or "youtu.be" in video_url:
            local_path = vi_service.download_youtube_video(video_url, output_path=local_filename)
        else:
            raise Exception("Please provide a valid YouTube URL for this audit.")
        download_dur = round(time.time() - t0, 2)

        # 2. UPLOAD & WAIT IN AZURE VIDEO INDEXER
        t1 = time.time()
        azure_video_id = vi_service.upload_video(local_path, video_name=video_id_input)
        logger.info(f"Upload Success. Azure Video ID: {azure_video_id}")

        raw_insights = vi_service.wait_for_processing(azure_video_id)
        vi_dur = round(time.time() - t1, 2)
        
        # 3. EXTRACT INSIGHTS & TIMESTAMPS
        clean_data = vi_service.extract_data(raw_insights)
        
        timing["download_time"] = download_dur
        timing["vi_processing_time"] = vi_dur
        
        dur_ms = int((time.time() - start_total) * 1000)
        log_event(
            logger,
            ObservabilityEvent.NODE_COMPLETED,
            message=f"Node: indexer completed in {dur_ms}ms (download={download_dur}s, vi={vi_dur}s)",
            node="indexer",
            duration_ms=dur_ms,
            download_duration_s=download_dur,
            vi_duration_s=vi_dur
        )
        return {
            "local_file_path": local_path,  # Retain MP4 path for frame extraction node
            "transcript": clean_data.get("transcript", ""),
            "ocr_text": clean_data.get("ocr_text", []),
            "transcript_items": clean_data.get("transcript_items", []),
            "ocr_items": clean_data.get("ocr_items", []),
            "video_metadata": clean_data.get("video_metadata", {}),
            "timing_metrics": timing,
            "iteration_count": 0,
            "errors": []
        }

    except Exception as e:
        dur_ms = int((time.time() - start_total) * 1000)
        log_event(
            logger,
            ObservabilityEvent.NODE_FAILED,
            level=logging.WARNING,
            message=f"Node: indexer failed: {e}",
            node="indexer",
            error_code=ErrorCode.VIDEO_INDEXER_ERROR,
            duration_ms=dur_ms,
            error=str(e)
        )
        retained_local_path = local_path if ('local_path' in locals() and os.path.exists(local_path)) else None
            
        timing["download_time"] = round(time.time() - start_total, 2)
        return {
            "errors": [str(e)],
            "transcript": "", 
            "ocr_text": [],
            "transcript_items": [],
            "ocr_items": [],
            "local_file_path": retained_local_path,
            "timing_metrics": timing,
            "iteration_count": 0
        }

# --- NODE 2: MULTIMODAL FRAME EXTRACTOR & VISION ANALYZER ---
def extract_multimodal_frames_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Extracts keyframes from downloaded MP4 using OpenCV and runs Azure OpenAI vision analysis with guaranteed file cleanup.
    """
    t_start = time.time()
    log_event(
        logger,
        ObservabilityEvent.NODE_STARTED,
        message="Node: frame_extractor started",
        node="frame_extractor"
    )
    
    local_path = state.get("local_file_path")
    video_id = state.get("video_id", "session_001")
    transcript_items = state.get("transcript_items", [])
    ocr_items = state.get("ocr_items", [])
    timing = state.get("timing_metrics", {})

    interest_timestamps = []
    
    keywords = ["sponsor", "ad", "paid", "promotion", "link", "code", "buy", "guarantee"]
    for t_item in transcript_items:
        txt = t_item.get("text", "").lower()
        if any(k in txt for k in keywords):
            interest_timestamps.append(t_item.get("start_time", 0.0))
            
    for o_item in ocr_items:
        txt = o_item.get("text", "").lower()
        if any(k in txt for k in keywords):
            interest_timestamps.append(o_item.get("start_time", 0.0))

    session_dir = None
    frames = []
    visual_obs = []
    is_degraded = False

    try:
        if local_path and os.path.exists(local_path):
            t0 = time.time()
            frame_extractor = VideoFrameExtractorService()
            frame_result = frame_extractor.extract_frames(local_path, video_id, interest_timestamps)
            session_dir = frame_result.get("session_dir")
            frames = frame_result.get("frames", [])
            timing["frame_extraction_time"] = round(time.time() - t0, 2)

            t1 = time.time()
            vision_service = VisionAnalyzerService()
            visual_obs, is_degraded = vision_service.analyze_batch_frames(frames, ocr_items)
            timing["vision_time"] = round(time.time() - t1, 2)
        else:
            t1 = time.time()
            vision_service = VisionAnalyzerService()
            visual_obs, is_degraded = vision_service.analyze_batch_frames([], ocr_items)
            timing["frame_extraction_time"] = 0.0
            timing["vision_time"] = round(time.time() - t1, 2)

    except Exception as e:
        logger.warning(f"Frame extraction / vision analysis exception: {e}")
        is_degraded = True
    finally:
        # Guaranteed Resource Cleanup in finally block
        if session_dir and 'frame_extractor' in locals():
            frame_extractor.cleanup_session_frames(session_dir)
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"Cleaned up temporary MP4 video file: {local_path}")
            except Exception as e_clean:
                logger.warning(f"Failed to delete MP4 file {local_path}: {e_clean}")

    if is_degraded:
        log_event(
            logger,
            ObservabilityEvent.AUDIT_DEGRADED_MODE,
            level=logging.WARNING,
            message="Visual analysis operating in DEGRADED_OCR_FALLBACK mode (OCR text backup active)",
            mode="DEGRADED_OCR_FALLBACK",
            reason="Azure OpenAI vision unconfigured or encountered error. Falling back to OCR text."
        )

    mode_str = "DEGRADED_OCR_FALLBACK" if is_degraded else "NATIVE_VISION"
    dur_ms = int((time.time() - t_start) * 1000)
    log_event(
        logger,
        ObservabilityEvent.NODE_COMPLETED,
        message=f"Node: frame_extractor completed in {dur_ms}ms (analyzed {len(frames)} frames, mode={mode_str})",
        node="frame_extractor",
        duration_ms=dur_ms,
        frame_count=len(frames),
        is_degraded=is_degraded,
        visual_observations_count=len(visual_obs)
    )
    
    return {
        "local_file_path": None,  # File safely cleaned up
        "visual_observations": visual_obs,
        "extracted_frame_count": len(frames),
        "is_degraded_vision_mode": is_degraded,
        "timing_metrics": timing
    }

# --- NODE 3: THE AUDIT PLANNER ---
def plan_audit_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Constructs a structured audit plan detailing required evidence modalities (POLICY, TRANSCRIPT, OCR, VISUAL).
    """
    t0 = time.time()
    log_event(
        logger,
        ObservabilityEvent.NODE_STARTED,
        message="Node: planner started",
        node="planner"
    )
    
    transcript = state.get("transcript", "")
    ocr_text = state.get("ocr_text", [])
    visual_obs = state.get("visual_observations", [])
    timing = state.get("timing_metrics", {})
    
    if not transcript and not ocr_text and not visual_obs:
        timing["planner_time"] = round(time.time() - t0, 2)
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.NODE_COMPLETED,
            message="Node: planner completed (empty checks)",
            node="planner",
            duration_ms=dur_ms,
            checks_count=0
        )
        return {"audit_plan": {"checks": []}, "timing_metrics": timing}
        
    try:
        openai_ep = os.getenv("AZURE_OPENAI_ENDPOINT") or getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
        if openai_ep:
            from urllib.parse import urlparse
            parsed_ep = urlparse(openai_ep)
            if parsed_ep.netloc and parsed_ep.path and parsed_ep.path != "/":
                openai_ep = f"{parsed_ep.scheme}://{parsed_ep.netloc}"

        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            azure_endpoint=openai_ep,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0.0
        )
        
        structured_planner = llm.with_structured_output(AuditPlan)
        
        prompt = f"""
        You are a Compliance Lead. Formulate a targeted multimodal audit plan for a video advertisement.
        
        VIDEO METADATA: {state.get('video_metadata', {})}
        TRANSCRIPT EXCERPT: {transcript[:1200]}
        OCR TEXT EXCERPTS: {ocr_text[:10]}
        VISUAL OBSERVATIONS EXCERPT: {[v.get('description') for v in visual_obs[:5]]}
        
        Identify specific compliance areas that must be audited (e.g., sponsorship_disclosure, claim_validation, visual_disclaimer_visibility).
        For each area, state the rationale and required evidence modalities (POLICY, TRANSCRIPT, OCR, VISUAL).
        """
        
        plan_obj: AuditPlan = structured_planner.invoke(prompt)
        timing["planner_time"] = round(time.time() - t0, 2)
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.NODE_COMPLETED,
            message=f"Node: planner completed in {dur_ms}ms (created {len(plan_obj.checks)} checks)",
            node="planner",
            duration_ms=dur_ms,
            checks_count=len(plan_obj.checks)
        )
        return {"audit_plan": plan_obj.model_dump(), "timing_metrics": timing}
        
    except Exception as e:
        logger.error(f"Planner failed: {e}. Using default fallback plan.")
        fallback_plan = {
            "checks": [
                {
                    "area": "sponsorship_disclosure",
                    "rationale": "Verify clear and conspicuous FTC disclosure visually and in speech.",
                    "evidence_needed": ["POLICY", "TRANSCRIPT", "OCR", "VISUAL"]
                },
                {
                    "area": "claim_validation",
                    "rationale": "Verify that absolute guarantees or commercial claims are substantiated.",
                    "evidence_needed": ["POLICY", "TRANSCRIPT"]
                }
            ]
        }
        timing["planner_time"] = round(time.time() - t0, 2)
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.NODE_COMPLETED,
            message=f"Node: planner completed with fallback plan in {dur_ms}ms",
            node="planner",
            duration_ms=dur_ms,
            checks_count=len(fallback_plan["checks"]),
            fallback=True
        )
        return {"audit_plan": fallback_plan, "timing_metrics": timing}

# --- NODE 4: THE COMPLIANCE AUDITOR (MULTIMODAL AGENT WITH TOOLS) ---
def audit_content_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Executes compliance audit integrating Policy RAG, Timestamped Transcript, OCR, and Visual Keyframe observations.
    """
    t0 = time.time()
    iteration_count = state.get("iteration_count", 0)
    log_event(
        logger,
        ObservabilityEvent.NODE_STARTED,
        message=f"Node: auditor started (iteration={iteration_count})",
        node="auditor",
        iteration=iteration_count
    )
    
    transcript = state.get("transcript", "")
    ocr_text = state.get("ocr_text", [])
    transcript_items = state.get("transcript_items", [])
    ocr_items = state.get("ocr_items", [])
    visual_obs = state.get("visual_observations", [])
    audit_plan = state.get("audit_plan", {})
    verification_feedback = state.get("verification_feedback")
    is_degraded = state.get("is_degraded_vision_mode", False)
    timing = state.get("timing_metrics", {})
    
    if not transcript and not ocr_text:
        timing["auditor_time"] = round(time.time() - t0, 2)
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.NODE_COMPLETED,
            message=f"Node: auditor skipped (no transcript/OCR) in {dur_ms}ms",
            node="auditor",
            duration_ms=dur_ms,
            outcome="FAIL"
        )
        return {
            "final_status": "FAIL",
            "final_report": "Audit skipped because video processing produced no content.",
            "timing_metrics": timing
        }

    # 1. Execute Policy Retrieval Tools
    retrieved_policies = []
    checks = audit_plan.get("checks", [])
    
    for check in checks:
        area = check.get("area", "general compliance")
        policy_results = search_policy_rules.invoke({"query": f"rules and regulations for {area}"})
        if isinstance(policy_results, list):
            retrieved_policies.extend(policy_results)
            
    unique_policies = []
    seen = set()
    for p in retrieved_policies:
        content = p.get("content", "")
        if content not in seen:
            seen.add(content)
            unique_policies.append(p)

    formatted_policy_context = "\n\n".join([
        f"DOCUMENT: {p.get('document')}\nRULE SNIPPET: {p.get('content')}"
        for p in unique_policies
    ])

    # 2. Execute Visual Evidence Search
    search_visual_evidence.invoke({"query": "disclosure logo ad", "visual_observations": visual_obs})

    # 3. Format Temporal Evidence Timelines
    formatted_transcript_timeline = "\n".join([
        f"[{t.get('start_time', 0.0):.1f}s - {t.get('end_time', 0.0):.1f}s] {t.get('speaker', 'Speaker')}: {t.get('text')}"
        for t in transcript_items[:20]
    ])

    formatted_ocr_timeline = "\n".join([
        f"[{o.get('start_time', 0.0):.1f}s - {o.get('end_time', 0.0):.1f}s] OCR Text: {o.get('text')}"
        for o in ocr_items[:15]
    ])

    formatted_visual_timeline = "\n".join([
        f"[{v.get('timestamp', 0.0):.1f}s] Visual ({v.get('mode', 'NATIVE_VISION')}) [{v.get('category')}]: {v.get('description')}"
        for v in visual_obs[:15]
    ])

    openai_ep = os.getenv("AZURE_OPENAI_ENDPOINT") or getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
    if openai_ep:
        from urllib.parse import urlparse
        parsed_ep = urlparse(openai_ep)
        if parsed_ep.netloc and parsed_ep.path and parsed_ep.path != "/":
            openai_ep = f"{parsed_ep.scheme}://{parsed_ep.netloc}"

    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        azure_endpoint=openai_ep,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        temperature=0.0
    )

    structured_auditor = llm.with_structured_output(AuditFindingsResult)

    feedback_prompt = ""
    if verification_feedback and iteration_count > 0:
        feedback_prompt = f"\nVERIFICATION FEEDBACK FROM PREVIOUS PASS: {verification_feedback}\nPlease address missing timestamp evidence or visual grounding."

    mode_note = "NOTE: Visual evidence mode is DEGRADED (using OCR fallback)." if is_degraded else "NOTE: Visual evidence mode is NATIVE_VISION."

    system_prompt = f"""
    You are a Senior Brand Compliance Auditor. {mode_note}
    
    OFFICIAL REGULATORY RULES (RETRIEVED FROM KNOWLEDGE BASE):
    {formatted_policy_context}
    
    INSTRUCTIONS:
    1. Analyze the video across all modalities: Speech Transcript, On-Screen OCR, and Visual Keyframes.
    2. Provide exact start_time and end_time timestamps in seconds for every finding's video evidence.
    3. Specify evidence_type as TRANSCRIPT, OCR, or VISUAL.
    4. Provide explicit policy citations (document name & quoted passage).
    5. Set status to PASS, FAIL, or WARNING, with severity CRITICAL, HIGH, MEDIUM, LOW, or NONE.{feedback_prompt}
    """

    user_message = f"""
    AUDIT PLAN: {json.dumps(audit_plan)}
    SPEECH TRANSCRIPT TIMELINE:\n{formatted_transcript_timeline}
    ON-SCREEN OCR TIMELINE:\n{formatted_ocr_timeline}
    VISUAL KEYFRAME OBSERVATIONS TIMELINE:\n{formatted_visual_timeline}
    """

    try:
        findings_result: AuditFindingsResult = structured_auditor.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        
        findings_list = [f.model_dump() for f in findings_result.findings]
        
        legacy_issues: List[ComplianceIssue] = []
        citations_list: List[Dict[str, Any]] = []
        
        for f in findings_result.findings:
            if f.status in ["FAIL", "WARNING"]:
                t_str = f"At {f.video_evidence.start_time:.1f}s" if f.video_evidence and f.video_evidence.start_time is not None else None
                legacy_issues.append({
                    "category": f.rule_category,
                    "description": f.description,
                    "severity": f.severity,
                    "timestamp": t_str
                })
            if f.policy_evidence:
                citations_list.append(f.policy_evidence.model_dump())

        timing["auditor_time"] = round(time.time() - t0, 2)
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.NODE_COMPLETED,
            message=f"Node: auditor completed in {dur_ms}ms with outcome {findings_result.overall_status}",
            node="auditor",
            duration_ms=dur_ms,
            outcome=findings_result.overall_status,
            findings_count=len(findings_list),
            iteration=iteration_count
        )
        return {
            "audit_findings": findings_list,
            "compliance_results": legacy_issues,
            "citations": citations_list,
            "retrieved_evidence": unique_policies,
            "final_status": findings_result.overall_status,
            "timing_metrics": timing,
            "confidence": 0.95 if findings_result.overall_status == "PASS" else 0.85
        }

    except Exception as e:
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.NODE_FAILED,
            level=logging.ERROR,
            message=f"Node: auditor failed: {e}",
            node="auditor",
            error_code=ErrorCode.AUDITOR_ERROR,
            duration_ms=dur_ms,
            error=str(e)
        )
        timing["auditor_time"] = round(time.time() - t0, 2)
        return {
            "errors": [f"Auditor execution error: {str(e)}"],
            "final_status": "FAIL",
            "audit_findings": [],
            "timing_metrics": timing
        }

# --- NODE 5: THE EVIDENCE VERIFIER / CRITIC ---
def verify_findings_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Verifies policy grounding, video grounding, temporal grounding, and visual grounding for every finding.
    """
    t0 = time.time()
    log_event(
        logger,
        ObservabilityEvent.VERIFIER_STARTED,
        message="Verifier node started",
        node="verifier"
    )
    log_event(
        logger,
        ObservabilityEvent.NODE_STARTED,
        message="Node: verifier started",
        node="verifier"
    )
    
    findings = state.get("audit_findings", [])
    transcript_items = state.get("transcript_items", [])
    ocr_items = state.get("ocr_items", [])
    visual_obs = state.get("visual_observations", [])
    timing = state.get("timing_metrics", {})
    
    if not findings:
        outcome = VerificationOutcome(
            overall_status="VERIFIED",
            results=[],
            feedback_summary="No compliance findings generated."
        )
        timing["verifier_time"] = round(time.time() - t0, 2)
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.NODE_COMPLETED,
            message=f"Node: verifier completed in {dur_ms}ms with outcome VERIFIED (no findings)",
            node="verifier",
            duration_ms=dur_ms,
            overall_status="VERIFIED"
        )
        return {"verification_results": outcome.model_dump(), "timing_metrics": timing}

    verification_results: List[VerificationResult] = []
    needs_more_evidence = False
    feedback_reasons = []

    for idx, finding in enumerate(findings):
        category = finding.get("rule_category", f"Finding_{idx}")
        policy_ev = finding.get("policy_evidence")
        video_ev = finding.get("video_evidence")
        status = finding.get("status")

        grounded = True
        reason = "Finding is fully grounded in policy and temporal video evidence."
        score = 1.0

        if status in ["FAIL", "WARNING"] and not policy_ev:
            grounded = False
            score -= 0.4
            reason = "Violation alleged without attaching explicit policy citation."

        if status in ["FAIL", "WARNING"] and not video_ev:
            grounded = False
            score -= 0.4
            reason = "Violation alleged without attaching transcript, OCR, or visual video evidence."

        if video_ev and isinstance(video_ev, dict):
            ev_type = video_ev.get("evidence_type", "TRANSCRIPT")
            start_t = video_ev.get("start_time")

            if ev_type == "VISUAL":
                if not visual_obs and not ocr_items:
                    grounded = False
                    score -= 0.5
                    reason = "Visual evidence claimed but no visual observations exist."
                elif start_t is not None:
                    matching_vis = [
                        v for v in visual_obs 
                        if abs(v.get("timestamp", 0.0) - start_t) <= 3.0
                    ]
                    if not matching_vis:
                        score -= 0.2
                        reason = f"Visual keyframe observation at {start_t:.1f}s lacks matching raw keyframe timestamp."

            elif start_t is not None:
                all_times = [t.get("start_time", 0.0) for t in transcript_items + ocr_items]
                if all_times:
                    near_times = [t for t in all_times if abs(t - start_t) <= 5.0]
                    if not near_times:
                        score -= 0.2
                        reason = f"Claimed timestamp {start_t:.1f}s is out of bounds of extracted video speech timeline."

        action_type = "VERIFIED" if grounded else "REQUEST_MORE_EVIDENCE"
        if not grounded:
            needs_more_evidence = True
            feedback_reasons.append(f"[{category}]: {reason}")

        verification_results.append(VerificationResult(
            category=category,
            verified=grounded,
            grounding_score=max(0.0, score),
            reason=reason,
            action=action_type
        ))

    overall = "NEEDS_MORE_EVIDENCE" if needs_more_evidence else "VERIFIED"
    summary_feedback = " ; ".join(feedback_reasons) if feedback_reasons else "All findings successfully verified."

    outcome = VerificationOutcome(
        overall_status=overall,
        results=verification_results,
        feedback_summary=summary_feedback
    )

    timing["verifier_time"] = round(time.time() - t0, 2)
    dur_ms = int((time.time() - t0) * 1000)
    log_event(
        logger,
        ObservabilityEvent.NODE_COMPLETED,
        message=f"Node: verifier completed in {dur_ms}ms with outcome {overall}",
        node="verifier",
        duration_ms=dur_ms,
        overall_status=overall,
        verified_count=sum(1 for r in verification_results if r.verified),
        total_findings=len(verification_results)
    )
    return {
        "verification_results": outcome.model_dump(),
        "verification_feedback": summary_feedback,
        "timing_metrics": timing
    }

# --- NODE 6: REPORT GENERATOR ---
def generate_report_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Formats the final executive compliance report markdown with multimodal temporal breakdown and latency metrics.
    """
    t0 = time.time()
    log_event(
        logger,
        ObservabilityEvent.NODE_STARTED,
        message="Node: report_generator started",
        node="report_generator"
    )
    
    video_id = state.get("video_id", "Unknown")
    final_status = state.get("final_status", "PASS")
    findings = state.get("audit_findings", [])
    citations = state.get("citations", [])
    verification = state.get("verification_results", {})
    iteration_count = state.get("iteration_count", 0)
    frame_count = state.get("extracted_frame_count", 0)
    is_degraded = state.get("is_degraded_vision_mode", False)
    timing = state.get("timing_metrics", {})
    
    mode_banner = "**DEGRADED OCR FALLBACK MODE** (Text Backup Used for Visual Evidence)" if is_degraded else "**NATIVE VISION ANALYSIS MODE** (Azure OpenAI Multimodal Active)"

    report_lines = [
        f"# Brand Guardian AI — Multimodal Compliance Audit Report",
        f"**Execution Mode:** {mode_banner}",
        f"**Video ID:** `{video_id}`",
        f"**Overall Status:** `{final_status}`",
        f"**Audit Iterations:** `{iteration_count + 1}`",
        f"**Keyframes Analyzed:** `{frame_count}`",
        f"**Verification Outcome:** `{verification.get('overall_status', 'VERIFIED')}`",
        "",
        "## Execution Stage Latencies",
        "| Stage | Latency (s) |",
        "| :--- | :--- |",
        f"| Download | `{timing.get('download_time', 0.0):.2f}s` |",
        f"| Azure Video Indexer | `{timing.get('vi_processing_time', 0.0):.2f}s` |",
        f"| Frame Extraction | `{timing.get('frame_extraction_time', 0.0):.2f}s` |",
        f"| Vision Analysis | `{timing.get('vision_time', 0.0):.2f}s` |",
        f"| Audit Planner | `{timing.get('planner_time', 0.0):.2f}s` |",
        f"| Auditor Agent | `{timing.get('auditor_time', 0.0):.2f}s` |",
        f"| Evidence Verifier | `{timing.get('verifier_time', 0.0):.2f}s` |",
        "",
        "## Multimodal Compliance Findings"
    ]

    if findings:
        for idx, f in enumerate(findings, 1):
            category = f.get("category", f.get("rule_category", "General"))
            severity = f.get("severity", "INFO")
            status = f.get("status", "PASS")
            desc = f.get("description", "")
            reasoning = f.get("reasoning", "")
            
            report_lines.append(f"### {idx}. [{severity}] {category} — {status}")
            report_lines.append(f"**Description:** {desc}")
            report_lines.append(f"**Reasoning:** {reasoning}")
            
            p_ev = f.get("policy_evidence")
            if p_ev and isinstance(p_ev, dict):
                report_lines.append(f"**Policy Citation:** *{p_ev.get('document', 'Policy Guide')}* — \"{p_ev.get('content', '')}\"")
                
            v_ev = f.get("video_evidence")
            if v_ev and isinstance(v_ev, dict):
                t_info = ""
                st = v_ev.get("start_time")
                et = v_ev.get("end_time")
                if st is not None and et is not None:
                    t_info = f" at {st:.1f}s–{et:.1f}s"
                elif st is not None:
                    t_info = f" at {st:.1f}s"
                    
                mode_tag = f" [{v_ev.get('mode', 'NATIVE_VISION')}]" if v_ev.get('mode') else ""
                report_lines.append(f"**Video Evidence ({v_ev.get('evidence_type', 'TRANSCRIPT')}{mode_tag}{t_info}):** \"{v_ev.get('excerpt', '')}\"")
            report_lines.append("")
    else:
        report_lines.append("[OK] No compliance violations or warnings detected in this video.")
        report_lines.append("")

    if citations:
        report_lines.append("## Regulatory Policy References")
        for cite in citations:
            doc = cite.get("document", "Policy PDF")
            content = cite.get("content", "")
            report_lines.append(f"- **{doc}**: {content}")
        report_lines.append("")

    report_lines.append("---")
    report_lines.append("*Report generated by Brand Guardian Multimodal Agentic Engine.*")

    full_report = "\n".join(report_lines)

    dur_ms = int((time.time() - t0) * 1000)
    log_event(
        logger,
        ObservabilityEvent.NODE_COMPLETED,
        message=f"Node: report_generator completed in {dur_ms}ms",
        node="report_generator",
        duration_ms=dur_ms
    )

    return {
        "final_report": full_report,
        "final_status": final_status
    }