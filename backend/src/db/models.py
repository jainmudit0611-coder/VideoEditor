import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, Enum, JSON, Index, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.src.db.database import Base

class AuditStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class AuditStage(str, enum.Enum):
    QUEUED = "QUEUED"
    DOWNLOADING = "DOWNLOADING"
    VIDEO_INDEXING = "VIDEO_INDEXING"
    FRAME_EXTRACTION = "FRAME_EXTRACTION"
    VISION_ANALYSIS = "VISION_ANALYSIS"
    PLANNING = "PLANNING"
    AUDITING = "AUDITING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class AuditJob(Base):
    """
    SQLAlchemy ORM Model representing an asynchronous Multimodal Video Audit Job.
    """
    __tablename__ = "audit_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    status: Mapped[AuditStatus] = mapped_column(Enum(AuditStatus), default=AuditStatus.QUEUED, nullable=False, index=True)
    video_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_stage: Mapped[str] = mapped_column(String(64), default=AuditStage.QUEUED.value, nullable=False)
    iteration_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    error_details: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    
    result: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    timing_metrics: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(128), default="system", nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    __table_args__ = (
        Index("idx_audit_status_created", "status", "created_at"),
        Index("idx_audit_idempotency", "idempotency_key"),
        Index("idx_audit_request_id", "request_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts AuditJob model to dictionary representation."""
        return {
            "audit_id": str(self.id),
            "status": self.status.value if isinstance(self.status, AuditStatus) else str(self.status),
            "video_url": str(self.video_url),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "iteration_count": self.iteration_count,
            "retry_count": self.retry_count,
            "idempotency_key": self.idempotency_key,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "result": self.result,
            "timing_metrics": self.timing_metrics,
            "created_by": self.created_by,
            "request_id": self.request_id,
        }


class EvaluationRunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvaluationRun(Base):
    """
    SQLAlchemy ORM Model representing an evaluation run across a benchmark dataset.
    Stores reproducible metadata, aggregated metrics, per-case summaries, and discrepancies.
    """
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    run_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[EvaluationRunStatus] = mapped_column(Enum(EvaluationRunStatus), default=EvaluationRunStatus.QUEUED, nullable=False, index=True)

    dataset_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    dataset_type: Mapped[str] = mapped_column(String(64), default="MANUALLY_CURATED", nullable=False)
    case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    model_name: Mapped[str] = mapped_column(String(64), default="gpt-4o", nullable=False)
    model_provider: Mapped[str] = mapped_column(String(64), default="azure_openai", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    config_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    evaluation_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    metrics: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    discrepancies: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (
        Index("idx_eval_run_status_created", "status", "created_at"),
        Index("idx_eval_run_dataset", "dataset_version"),
        Index("idx_eval_run_owner_baseline", "created_by", "is_baseline"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts EvaluationRun model to dictionary representation."""
        return {
            "id": str(self.id),
            "run_name": self.run_name,
            "status": self.status.value if isinstance(self.status, EvaluationRunStatus) else str(self.status),
            "dataset_version": self.dataset_version,
            "dataset_type": self.dataset_type,
            "case_count": self.case_count,
            "model_name": self.model_name,
            "model_provider": self.model_provider,
            "prompt_version": self.prompt_version,
            "config_version": self.config_version,
            "evaluation_version": self.evaluation_version,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "metrics": self.metrics or {},
            "summary": self.summary or {},
            "discrepancies": self.discrepancies or [],
            "error_message": self.error_message,
            "created_by": self.created_by,
            "is_baseline": self.is_baseline,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    """
    SQLAlchemy ORM Model representing an authenticated user of Brand Guardian AI.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Converts User model to dictionary, strictly excluding password_hash."""
        return {
            "id": str(self.id),
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role.value if isinstance(self.role, UserRole) else str(self.role),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



