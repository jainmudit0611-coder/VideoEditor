import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from backend.src.db.models import AuditJob, AuditStatus, AuditStage

logger = logging.getLogger("brand-guardian-repository")

class AuditRepository:
    """
    Repository encapsulating all database operations for AuditJob entities.
    """

    @staticmethod
    def create_audit(
        session: Session,
        video_url: str,
        audit_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        created_by: Optional[Any] = "system",
        request_id: Optional[str] = None,
    ) -> AuditJob:
        """Creates and persists a new AuditJob record."""
        job_id = str(audit_id) if audit_id else str(uuid.uuid4())
        creator = str(created_by) if created_by is not None else "system"
        job = AuditJob(
            id=job_id,
            status=AuditStatus.QUEUED,
            video_url=video_url,
            created_at=datetime.now(timezone.utc),
            progress=0,
            current_stage=AuditStage.QUEUED.value,
            idempotency_key=idempotency_key,
            created_by=creator,
            request_id=request_id,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        logger.info(f"Created AuditJob record in DB: audit_id={job_id}, status={job.status.value}, request_id={request_id}")
        return job

    @staticmethod
    def get_audit(session: Session, audit_id: str, owner_id: Optional[Any] = None) -> Optional[AuditJob]:
        """Retrieves an AuditJob by primary key ID, optionally enforcing owner_id constraint."""
        query = session.query(AuditJob).filter(AuditJob.id == str(audit_id))
        if owner_id is not None:
            query = query.filter(AuditJob.created_by == str(owner_id))
        return query.first()

    @staticmethod
    def get_audit_by_idempotency_key(session: Session, idempotency_key: str) -> Optional[AuditJob]:
        """Retrieves an existing AuditJob by its unique idempotency key."""
        if not idempotency_key:
            return None
        return session.query(AuditJob).filter(AuditJob.idempotency_key == idempotency_key).first()

    @staticmethod
    def update_status(
        session: Session,
        audit_id: str,
        status: AuditStatus,
        stage: Optional[str] = None,
        progress: Optional[int] = None
    ) -> Optional[AuditJob]:
        """Updates audit job status, stage, and progress."""
        job = session.query(AuditJob).filter(AuditJob.id == audit_id).first()
        if not job:
            return None

        job.status = status
        if stage is not None:
            job.current_stage = stage
        if progress is not None:
            job.progress = progress

        now = datetime.now(timezone.utc)
        if status == AuditStatus.PROCESSING and not job.started_at:
            job.started_at = now
        elif status in (AuditStatus.COMPLETED, AuditStatus.FAILED, AuditStatus.CANCELLED):
            job.completed_at = now

        session.commit()
        session.refresh(job)
        logger.info(f"Updated AuditJob {audit_id}: status={status.value}, stage={job.current_stage}, progress={job.progress}%")
        return job

    @staticmethod
    def update_progress(
        session: Session,
        audit_id: str,
        progress: int,
        stage: Optional[str] = None
    ) -> Optional[AuditJob]:
        """Updates progress percentage and optional current stage."""
        job = session.query(AuditJob).filter(AuditJob.id == audit_id).first()
        if not job:
            return None

        job.progress = min(max(progress, 0), 100)
        if stage is not None:
            job.current_stage = stage

        session.commit()
        session.refresh(job)
        return job

    @staticmethod
    def save_result(
        session: Session,
        audit_id: str,
        result: Dict[str, Any],
        timing_metrics: Optional[Dict[str, float]] = None,
        iteration_count: int = 0
    ) -> Optional[AuditJob]:
        """Saves final audit results and marks job COMPLETED."""
        job = session.query(AuditJob).filter(AuditJob.id == audit_id).first()
        if not job:
            return None

        job.result = result
        if timing_metrics:
            job.timing_metrics = timing_metrics
        job.iteration_count = iteration_count
        job.status = AuditStatus.COMPLETED
        job.current_stage = AuditStage.COMPLETED.value
        job.progress = 100
        job.completed_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(job)
        logger.info(f"Saved audit result for {audit_id}: status=COMPLETED")
        return job

    @staticmethod
    def mark_failed(
        session: Session,
        audit_id: str,
        error_code: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Optional[AuditJob]:
        """Marks audit job FAILED with structured error details."""
        job = session.query(AuditJob).filter(AuditJob.id == audit_id).first()
        if not job:
            return None

        job.status = AuditStatus.FAILED
        job.current_stage = AuditStage.FAILED.value
        job.error_code = error_code
        job.error_message = error_message
        job.error_details = error_details or {}
        job.completed_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(job)
        logger.error(f"Marked AuditJob {audit_id} FAILED: [{error_code}] {error_message}")
        return job

    @staticmethod
    def cancel_audit(session: Session, audit_id: str, owner_id: Optional[Any] = None) -> Optional[AuditJob]:
        """Cancels a queued or processing audit job, optionally enforcing owner_id constraint."""
        query = session.query(AuditJob).filter(AuditJob.id == str(audit_id))
        if owner_id is not None:
            query = query.filter(AuditJob.created_by == str(owner_id))
        job = query.first()
        if not job:
            return None

        if job.status in (AuditStatus.COMPLETED, AuditStatus.FAILED):
            return job

        job.status = AuditStatus.CANCELLED
        job.current_stage = AuditStage.CANCELLED.value
        job.completed_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(job)
        logger.info(f"Cancelled AuditJob {audit_id}")
        return job

    @staticmethod
    def increment_retry_count(session: Session, audit_id: str) -> int:
        """Increments and returns the retry_count for transient error retry handling."""
        job = session.query(AuditJob).filter(AuditJob.id == str(audit_id)).first()
        if not job:
            return 0
        job.retry_count += 1
        session.commit()
        session.refresh(job)
        return job.retry_count

    @staticmethod
    def list_audits(session: Session, owner_id: Optional[Any] = None, limit: int = 20, offset: int = 0) -> List[AuditJob]:
        """Lists recent audit jobs ordered by creation timestamp descending, optionally filtered by owner_id."""
        query = session.query(AuditJob)
        if owner_id is not None:
            query = query.filter(AuditJob.created_by == str(owner_id))
        return (
            query.order_by(AuditJob.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
