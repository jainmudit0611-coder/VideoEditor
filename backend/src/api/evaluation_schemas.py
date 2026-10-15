from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CreateEvaluationRunRequest(BaseModel):
    run_name: Optional[str] = Field(default=None, description="Optional custom name for this evaluation run")
    model_name: Optional[str] = Field(default="gpt-4o", description="Model identifier used in evaluation")
    model_provider: Optional[str] = Field(default="azure_openai", description="Model provider")
    dataset_version: Optional[str] = Field(default="v1", description="Dataset version to evaluate against")
    prompt_version: Optional[str] = Field(default="v1", description="Prompt revision label")
    config_version: Optional[str] = Field(default="v1", description="Pipeline configuration version")
    is_baseline: bool = Field(default=False, description="Flag indicating if this run is an official baseline reference run (Admin only)")

class CreateEvaluationRunResponse(BaseModel):
    id: str
    run_name: str
    status: str
    is_baseline: bool = False
    created_by: Optional[str] = None
    message: str = "Evaluation run accepted and queued."

class EvaluationRunStatusResponse(BaseModel):
    id: str
    run_name: str
    status: str
    progress: Optional[int] = None
    duration_ms: Optional[int] = None
    case_count: int
    is_baseline: bool = False
    created_by: Optional[str] = None
    error_message: Optional[str] = None

class EvaluationRunSummaryResponse(BaseModel):
    id: str
    run_name: str
    status: str
    dataset_version: str
    dataset_type: str
    case_count: int
    model_name: str
    model_provider: str
    prompt_version: str
    config_version: str
    evaluation_version: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: Optional[str] = None
    is_baseline: bool = False
    created_by: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    discrepancy_count: int = 0

class EvaluationRunDetailResponse(BaseModel):
    id: str
    run_name: str
    status: str
    dataset_version: str
    dataset_type: str
    case_count: int
    model_name: str
    model_provider: str
    prompt_version: str
    config_version: str
    evaluation_version: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    is_baseline: bool = False
    created_by: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    discrepancies: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: Optional[str] = None

class MetricComparisonRow(BaseModel):
    metric: str
    key: str
    display_type: str
    values: Dict[str, Any]
    delta: Optional[float] = None

class MetadataDifferenceRow(BaseModel):
    field: str
    values: Dict[str, Any]
    has_difference: bool

class EvaluationComparisonResponse(BaseModel):
    runs: List[Dict[str, Any]]
    metrics: List[MetricComparisonRow]
    differences: List[MetadataDifferenceRow]
