import operator
from typing import Annotated, List, Dict, Optional, Any, TypedDict, Literal
from pydantic import BaseModel, Field

# --- PYDANTIC STRUCTURED MODELS FOR NATIVE LLM OUTPUT PARSING ---

class PolicyCitation(BaseModel):
    """Represents a citation reference to a regulatory document."""
    document: str = Field(description="Name of the regulatory PDF document")
    section: Optional[str] = Field(default=None, description="Page number or section header if available")
    content: str = Field(description="Exact rule snippet or passage quoted")
    score: Optional[float] = Field(default=None, description="Vector similarity relevance score")

class VideoEvidence(BaseModel):
    """Represents a temporally grounded excerpt extracted from transcript, OCR, or visual keyframe."""
    excerpt: str = Field(default="", description="Excerpt text or description of evidence")
    text: Optional[str] = Field(default=None, description="Alias for excerpt text for backward compatibility")
    evidence_type: Literal["TRANSCRIPT", "OCR", "VISUAL"] = Field(description="Source modality of video evidence")
    mode: Optional[Literal["NATIVE_VISION", "DEGRADED_OCR_FALLBACK"]] = Field(default="NATIVE_VISION", description="Execution mode of visual evidence")
    start_time: Optional[float] = Field(default=None, description="Start timestamp in seconds")
    end_time: Optional[float] = Field(default=None, description="End timestamp in seconds")
    source: Optional[str] = Field(default=None, description="Source context or channel")
    confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Evidence confidence score")
    frame_path: Optional[str] = Field(default=None, description="Internal frame image reference path if visual")
    description: Optional[str] = Field(default=None, description="Additional context or visual observation detail")
    timestamp: Optional[str] = Field(default=None, description="Formatted string timestamp for legacy display")

    def model_post_init(self, __context):
        if not self.excerpt and self.text:
            self.excerpt = self.text
        elif not self.text and self.excerpt:
            self.text = self.excerpt

class VisualObservation(BaseModel):
    """Represents a visual observation extracted from a video keyframe image by vision models."""
    timestamp: float = Field(description="Exact keyframe timestamp in seconds")
    category: Literal["disclosure", "branding", "cta", "disclaimer"] = Field(description="Visual observation category")
    description: str = Field(description="Description of what is visible in frame")
    text: Optional[str] = Field(default=None, description="Recognized on-screen text snippet if visible")
    visible: bool = Field(default=True, description="True if target visual item is present in frame")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Observation confidence score")
    mode: Literal["NATIVE_VISION", "DEGRADED_OCR_FALLBACK"] = Field(default="NATIVE_VISION", description="Vision extraction mode")
    source_frame: Optional[str] = Field(default=None, description="Keyframe image reference")

class ComplianceFinding(BaseModel):
    """Represents a single compliance audit finding with grounding evidence."""
    rule_category: str = Field(description="Category of rule, e.g. FTC_DISCLOSURE, CLAIM_VALIDATION")
    status: Literal["PASS", "FAIL", "WARNING"] = Field(description="Status of compliance check")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"] = Field(description="Severity of violation")
    description: str = Field(description="Short summary of finding")
    reasoning: str = Field(description="Detailed explanation of why rule is violated or passed")
    policy_evidence: Optional[PolicyCitation] = Field(default=None, description="Policy rule citation")
    video_evidence: Optional[VideoEvidence] = Field(default=None, description="Video transcript, OCR, or visual evidence")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")

class AuditPlanCheck(BaseModel):
    """A planned compliance audit check item."""
    area: str = Field(description="Compliance area to audit, e.g., sponsorship_disclosure")
    rationale: str = Field(description="Reason why this check is required for this video")
    evidence_needed: List[Literal["POLICY", "TRANSCRIPT", "OCR", "VISUAL"]] = Field(
        description="Types of evidence required to evaluate this check"
    )

class AuditPlan(BaseModel):
    """Structured output plan for the compliance audit."""
    checks: List[AuditPlanCheck] = Field(description="List of compliance checks to execute")

class VerificationResult(BaseModel):
    """Verification outcome for a single finding."""
    category: str = Field(description="Category of finding being verified")
    verified: bool = Field(description="True if finding is backed by valid evidence")
    grounding_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Score measuring evidence grounding")
    reason: str = Field(description="Explanation of verification decision")
    action: Literal["VERIFIED", "REQUEST_MORE_EVIDENCE", "REJECTED"] = Field(description="Recommended action")

class VerificationOutcome(BaseModel):
    """Overall verification assessment for all audit findings."""
    overall_status: Literal["VERIFIED", "NEEDS_MORE_EVIDENCE", "UNRESOLVED"] = Field(
        description="Overall verification verdict"
    )
    results: List[VerificationResult] = Field(description="Individual verification results per finding")
    feedback_summary: str = Field(description="Summary feedback for auditor node retry if needed")

# --- LEGACY TYPEDDICT SCHEMA (PRESERVED FOR API BACKWARD COMPATIBILITY) ---
class ComplianceIssue(TypedDict):
    category: str           # e.g., "FTC_DISCLOSURE"
    description: str        # Specific detail of the violation
    severity: str           # "CRITICAL" | "WARNING"
    timestamp: Optional[str]# Timestamp of occurrence (if applicable)

# --- GLOBAL LANGGRAPH EXECUTION STATE ---
class VideoAuditState(TypedDict):
    """
    Defines the data schema for the LangGraph execution context.
    """
    # --- Input Parameters ---
    video_url: str
    video_id: str

    # --- Ingestion & Extraction Data ---
    local_file_path: Optional[str]  
    video_metadata: Dict[str, Any]  # e.g., {"duration": 15, "resolution": "1080p"}
    transcript: Optional[str]       # Full extracted speech-to-text
    ocr_text: List[str]             # List of recognized on-screen text
    transcript_items: List[Dict[str, Any]] # Timestamped transcript items
    ocr_items: List[Dict[str, Any]]        # Timestamped OCR items
    visual_observations: Annotated[List[Dict[str, Any]], operator.add] # Keyframe visual observations
    extracted_frame_count: int
    is_degraded_vision_mode: bool          # True if visual analysis degraded to OCR text backup
    timing_metrics: Dict[str, float]       # Stage execution timing latencies in seconds

    # --- Agentic Planning & Tools ---
    audit_plan: Optional[Dict[str, Any]]
    retrieved_evidence: Annotated[List[Dict[str, Any]], operator.add]
    evidence_requests: List[str]

    # --- Audit Findings & Evidence ---
    audit_findings: List[Dict[str, Any]]
    compliance_results: Annotated[List[ComplianceIssue], operator.add]
    citations: List[Dict[str, Any]]

    # --- Verification & Reflection ---
    verification_results: Optional[Dict[str, Any]]
    verification_feedback: Optional[str]
    iteration_count: int
    confidence: float

    # --- Final Deliverables ---
    final_status: str               # "PASS" | "FAIL" | "UNRESOLVED"
    final_report: str               # Markdown summary for the frontend
    
    # --- System Observability ---
    errors: Annotated[List[str], operator.add]