import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import or_
from sqlalchemy.orm import Session
from backend.src.db.models import EvaluationRun, EvaluationRunStatus
from backend.evaluation.constants import (
    EVALUATION_VERSION,
    DATASET_VERSION,
    DATASET_TYPE,
    PROMPT_VERSION,
    CONFIG_VERSION,
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_PROVIDER,
    CASE_COUNT_BENCHMARK,
)

logger = logging.getLogger("brand-guardian-evaluation-repository")

class EvaluationRepository:
    """
    Database repository managing persistence and queries for EvaluationRun records.
    """

    @staticmethod
    def create_run(
        session: Session,
        run_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_provider: Optional[str] = None,
        dataset_version: Optional[str] = None,
        prompt_version: Optional[str] = None,
        config_version: Optional[str] = None,
        evaluation_version: Optional[str] = None,
        case_count: int = CASE_COUNT_BENCHMARK,
        created_by: Optional[str] = None,
        is_baseline: bool = False,
        run_id: Optional[str] = None,
    ) -> EvaluationRun:
        """Initializes a new EvaluationRun record in QUEUED status."""
        actual_id = run_id or str(uuid.uuid4())
        name = run_name or f"Benchmark Evaluation {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        
        run = EvaluationRun(
            id=actual_id,
            run_name=name,
            status=EvaluationRunStatus.QUEUED,
            dataset_version=dataset_version or DATASET_VERSION,
            dataset_type=DATASET_TYPE,
            case_count=case_count,
            model_name=model_name or DEFAULT_MODEL_NAME,
            model_provider=model_provider or DEFAULT_MODEL_PROVIDER,
            prompt_version=prompt_version or PROMPT_VERSION,
            config_version=config_version or CONFIG_VERSION,
            evaluation_version=evaluation_version or EVALUATION_VERSION,
            created_by=created_by,
            is_baseline=is_baseline,
            created_at=datetime.now(timezone.utc),
            metrics={},
            summary={},
            discrepancies=[]
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        logger.info(f"Created EvaluationRun in DB: id={run.id}, status={run.status.value}, is_baseline={is_baseline}, created_by={created_by}")
        return run

    @staticmethod
    def get_run(
        session: Session,
        run_id: str,
        current_user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Optional[EvaluationRun]:
        """Retrieves an EvaluationRun by ID with optional ownership and baseline access enforcement."""
        query = session.query(EvaluationRun).filter(EvaluationRun.id == run_id)
        if not is_admin and current_user_id is not None:
            query = query.filter(or_(EvaluationRun.created_by == current_user_id, EvaluationRun.is_baseline == True))
        return query.first()

    @staticmethod
    def list_runs(
        session: Session,
        current_user_id: Optional[str] = None,
        is_admin: bool = False,
        dataset_version: Optional[str] = None,
        status: Optional[str] = None,
        model_name: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[EvaluationRun]:
        """Lists historical evaluation runs with ownership filtering and optional metadata filters."""
        query = session.query(EvaluationRun)
        if not is_admin and current_user_id is not None:
            query = query.filter(or_(EvaluationRun.created_by == current_user_id, EvaluationRun.is_baseline == True))
        if dataset_version:
            query = query.filter(EvaluationRun.dataset_version == dataset_version)
        if status:
            query = query.filter(EvaluationRun.status == status)
        if model_name:
            query = query.filter(EvaluationRun.model_name == model_name)

        return query.order_by(EvaluationRun.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def mark_running(session: Session, run_id: str) -> Optional[EvaluationRun]:
        """Transitions run status to RUNNING and records started_at timestamp."""
        run = session.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
        if not run:
            return None
        run.status = EvaluationRunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(run)
        return run

    @staticmethod
    def save_run_results(
        session: Session,
        run_id: str,
        metrics: Dict[str, Any],
        summary: Dict[str, Any],
        discrepancies: List[Dict[str, Any]],
        duration_ms: int,
        case_count: int
    ) -> Optional[EvaluationRun]:
        """Saves evaluation metrics and transitions run status to COMPLETED."""
        run = session.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
        if not run:
            return None

        now = datetime.now(timezone.utc)
        run.status = EvaluationRunStatus.COMPLETED
        run.completed_at = now
        run.duration_ms = duration_ms
        run.case_count = case_count
        run.metrics = metrics
        run.summary = summary
        run.discrepancies = discrepancies
        run.error_message = None

        session.commit()
        session.refresh(run)
        logger.info(f"Saved evaluation results for run {run_id}: COMPLETED ({duration_ms}ms)")
        return run

    @staticmethod
    def mark_failed(session: Session, run_id: str, error_message: str) -> Optional[EvaluationRun]:
        """Marks an EvaluationRun as FAILED with an error message."""
        run = session.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
        if not run:
            return None

        run.status = EvaluationRunStatus.FAILED
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = error_message

        session.commit()
        session.refresh(run)
        logger.error(f"Marked EvaluationRun {run_id} FAILED: {error_message}")
        return run
