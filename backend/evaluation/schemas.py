from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field

# --- REFERENCE DATASET SCHEMAS ---

class ExpectedFinding(BaseModel):
    """Reference label for an expected compliance finding."""
    category: str = Field(description="Expected category, e.g. FTC_DISCLOSURE, HEALTH_CLAIM")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE", "FAIL", "WARNING", "PASS"] = Field(
        description="Expected severity or status of the finding"
    )
    rule_id: Optional[str] = Field(default=None, description="Optional regulatory rule identifier")
    description_pattern: Optional[str] = Field(default=None, description="Keywords or pattern describing finding")

class ExpectedEvidence(BaseModel):
    """Reference label for expected supporting evidence."""
    type: Literal["TRANSCRIPT", "OCR", "VISUAL"] = Field(description="Expected evidence modality")
    contains: str = Field(description="Substrings or keywords that must appear in the evidence")
    timestamp: Optional[str] = Field(default=None, description="Expected timestamp marker if applicable")
    rule_category: Optional[str] = Field(default=None, description="Associated finding category")

class ExpectedCitation(BaseModel):
    """Reference label for expected policy/regulatory citation."""
    rule_category: str = Field(description="Policy category, e.g. FTC_DISCLOSURE")
    document_contains: Optional[str] = Field(default=None, description="Expected regulatory document snippet or title")

class EvaluationCase(BaseModel):
    """A single manually curated reference evaluation test case."""
    case_id: str = Field(description="Unique case identifier, e.g. case_001")
    description: str = Field(description="Human-readable description of the compliance scenario")
    video_url: str = Field(description="Target video URL or reference test video")
    dataset_version: str = Field(default="v1", description="Dataset schema version")
    dataset_type: Literal["MANUALLY_CURATED", "SYNTHETIC_BENCHMARK"] = Field(
        default="MANUALLY_CURATED",
        description="Dataset provenance label"
    )
    expected_findings: List[ExpectedFinding] = Field(default_factory=list)
    expected_evidence: List[ExpectedEvidence] = Field(default_factory=list)
    expected_citations: List[ExpectedCitation] = Field(default_factory=list)
    expected_verifier_status: Optional[str] = Field(
        default=None,
        description="Expected verification outcome, e.g. VERIFIED or NEEDS_MORE_EVIDENCE"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

# --- EVALUATION METRICS SCHEMAS ---

class FindingMatch(BaseModel):
    expected: ExpectedFinding
    actual: Dict[str, Any]
    matched_by: str

class Discrepancy(BaseModel):
    case_id: str
    failure_type: Literal["FALSE_POSITIVE", "FALSE_NEGATIVE", "SEVERITY_MISMATCH", "UNSUPPORTED_FINDING", "SCHEMA_ERROR"]
    expected: Optional[str] = None
    actual: Optional[str] = None
    evidence: Optional[str] = None
    observed_discrepancy: str

class FindingEvaluationResult(BaseModel):
    """Classification metrics comparing expected vs actual findings."""
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    matched_count: int = 0
    total_expected: int = 0
    total_actual: int = 0
    discrepancies: List[Discrepancy] = Field(default_factory=list)

class GroundingEvaluationResult(BaseModel):
    """Evidence grounding evaluation metrics."""
    total_findings: int = 0
    supported_findings: int = 0
    unsupported_findings: int = 0
    evidence_support_rate: float = 0.0
    unsupported_finding_rate: float = 0.0
    transcript_matches: int = 0
    ocr_matches: int = 0
    visual_matches: int = 0
    visual_evaluation_status: Literal["AVAILABLE", "NOT_AVAILABLE"] = "AVAILABLE"
    details: List[Dict[str, Any]] = Field(default_factory=list)

class CitationEvaluationResult(BaseModel):
    """Policy / RAG citation presence and completeness metrics."""
    total_findings: int = 0
    cited_findings: int = 0
    citation_presence_rate: float = 0.0
    complete_citations_count: int = 0
    completeness_rate: float = 0.0
    details: List[Dict[str, Any]] = Field(default_factory=list)

class SchemaEvaluationResult(BaseModel):
    """Structured output schema conformance metrics."""
    is_valid: bool = True
    schema_validity_rate: float = 1.0
    missing_required_fields: List[str] = Field(default_factory=list)
    invalid_data_types: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)

class VerifierEvaluationResult(BaseModel):
    """Verifier assessment comparing expected vs actual outcome."""
    expected_status: Optional[str] = None
    actual_status: Optional[str] = None
    agreement: Optional[bool] = None
    status: Literal["AGREED", "DISAGREED", "NOT_AVAILABLE"] = "NOT_AVAILABLE"

class LatencySummary(BaseModel):
    """Timing statistics across evaluated runs."""
    n_samples: int = 0
    mean_duration_sec: Optional[float] = None
    median_duration_sec: Optional[float] = None
    min_duration_sec: Optional[float] = None
    max_duration_sec: Optional[float] = None
    stage_latencies: Dict[str, float] = Field(default_factory=dict)

# --- AGGREGATE EVALUATION REPORT SCHEMAS ---

class CaseEvaluationResult(BaseModel):
    """Complete evaluation outcome for a single case."""
    case_id: str
    execution_mode: str
    finding_metrics: FindingEvaluationResult
    grounding_metrics: GroundingEvaluationResult
    citation_metrics: CitationEvaluationResult
    schema_metrics: SchemaEvaluationResult
    verifier_metrics: VerifierEvaluationResult
    timing_metrics: Optional[Dict[str, float]] = None
    discrepancies: List[Discrepancy] = Field(default_factory=list)

class EvaluationRunSummary(BaseModel):
    """Full evaluation suite summary."""
    evaluation_run_id: str
    timestamp: str
    dataset_version: str
    dataset_type: str
    n_cases: int
    execution_modes: List[str]
    aggregate_metrics: Dict[str, Any]
    case_results: List[CaseEvaluationResult]
    error_analysis: List[Discrepancy]
    limitations: List[str]
