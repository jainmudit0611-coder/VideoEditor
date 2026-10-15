import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db, SessionLocal
from backend.src.db.evaluation_repository import EvaluationRepository
from backend.src.services.evaluation_service import EvaluationService
from backend.src.db.models import User, UserRole
from backend.src.api.auth_dependencies import get_current_active_user
from backend.src.api.evaluation_schemas import (
    CreateEvaluationRunRequest,
    CreateEvaluationRunResponse,
    EvaluationRunStatusResponse,
    EvaluationRunSummaryResponse,
    EvaluationRunDetailResponse,
    EvaluationComparisonResponse,
)

logger = logging.getLogger("evaluation-routes")
router = APIRouter(prefix="/api/evaluations", tags=["Evaluations"])

def _execute_run_background(run_id: str):
    """Background task worker function to run evaluation asynchronously."""
    session = SessionLocal()
    try:
        service = EvaluationService()
        service.execute_run(session, run_id)
    except Exception as e:
        logger.error(f"Background evaluation run {run_id} failed: {e}")
    finally:
        session.close()

@router.post("/runs", response_model=CreateEvaluationRunResponse, status_code=status.HTTP_202_ACCEPTED)
def create_evaluation_run(
    request: CreateEvaluationRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Creates and enqueues a new evaluation run across the benchmark dataset.
    Requires authentication. Only ADMINs can designate a run as an official baseline.
    Returns HTTP 202 Accepted with the queued run ID.
    """
    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    if request.is_baseline and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to create an official baseline evaluation run."
        )

    is_baseline = request.is_baseline if is_admin else False

    run = EvaluationRepository.create_run(
        session=db,
        run_name=request.run_name,
        model_name=request.model_name,
        model_provider=request.model_provider,
        dataset_version=request.dataset_version,
        prompt_version=request.prompt_version,
        config_version=request.config_version,
        created_by=current_user.id,
        is_baseline=is_baseline,
    )

    # Launch evaluation asynchronously
    background_tasks.add_task(_execute_run_background, run.id)

    return CreateEvaluationRunResponse(
        id=run.id,
        run_name=run.run_name,
        status=run.status.value,
        is_baseline=run.is_baseline,
        created_by=run.created_by,
        message="Evaluation run accepted and queued."
    )

@router.get("/runs", response_model=List[EvaluationRunSummaryResponse])
def list_evaluation_runs(
    dataset_version: Optional[str] = None,
    status: Optional[str] = None,
    model_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lists historical evaluation runs.
    USER sees their own runs and official baseline runs.
    ADMIN sees all runs.
    """
    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    runs = EvaluationRepository.list_runs(
        session=db,
        current_user_id=current_user.id,
        is_admin=is_admin,
        dataset_version=dataset_version,
        status=status,
        model_name=model_name,
        limit=limit,
        offset=offset
    )

    results = []
    for r in runs:
        discrepancies = r.discrepancies or []
        results.append(EvaluationRunSummaryResponse(
            id=r.id,
            run_name=r.run_name,
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            dataset_version=r.dataset_version,
            dataset_type=r.dataset_type,
            case_count=r.case_count,
            model_name=r.model_name,
            model_provider=r.model_provider,
            prompt_version=r.prompt_version,
            config_version=r.config_version,
            evaluation_version=r.evaluation_version,
            started_at=r.started_at.isoformat() if r.started_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            duration_ms=r.duration_ms,
            created_at=r.created_at.isoformat() if r.created_at else None,
            is_baseline=r.is_baseline,
            created_by=r.created_by,
            metrics=r.metrics or {},
            discrepancy_count=len(discrepancies)
        ))
    return results

@router.get("/runs/{run_id}", response_model=EvaluationRunDetailResponse)
def get_evaluation_run_detail(
    run_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves full details for an evaluation run with ownership and baseline authorization.
    """
    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    run = EvaluationRepository.get_run(
        session=db,
        run_id=run_id,
        current_user_id=current_user.id,
        is_admin=is_admin
    )
    if not run:
        raise HTTPException(status_code=404, detail=f"Evaluation run '{run_id}' not found.")

    return EvaluationRunDetailResponse(
        id=run.id,
        run_name=run.run_name,
        status=run.status.value if hasattr(run.status, "value") else str(run.status),
        dataset_version=run.dataset_version,
        dataset_type=run.dataset_type,
        case_count=run.case_count,
        model_name=run.model_name,
        model_provider=run.model_provider,
        prompt_version=run.prompt_version,
        config_version=run.config_version,
        evaluation_version=run.evaluation_version,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        duration_ms=run.duration_ms,
        is_baseline=run.is_baseline,
        created_by=run.created_by,
        metrics=run.metrics or {},
        summary=run.summary or {},
        discrepancies=run.discrepancies or [],
        error_message=run.error_message,
        created_at=run.created_at.isoformat() if run.created_at else None,
    )

@router.get("/runs/{run_id}/status", response_model=EvaluationRunStatusResponse)
def get_evaluation_run_status(
    run_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the execution status of an evaluation run for polling with authorization check.
    """
    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    run = EvaluationRepository.get_run(
        session=db,
        run_id=run_id,
        current_user_id=current_user.id,
        is_admin=is_admin
    )
    if not run:
        raise HTTPException(status_code=404, detail=f"Evaluation run '{run_id}' not found.")

    status_val = run.status.value if hasattr(run.status, "value") else str(run.status)
    progress = 100 if status_val == "COMPLETED" else (50 if status_val == "RUNNING" else 0)

    return EvaluationRunStatusResponse(
        id=run.id,
        run_name=run.run_name,
        status=status_val,
        progress=progress,
        duration_ms=run.duration_ms,
        case_count=run.case_count,
        is_baseline=run.is_baseline,
        created_by=run.created_by,
        error_message=run.error_message
    )

@router.get("/compare", response_model=EvaluationComparisonResponse)
def compare_evaluation_runs(
    run_ids: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Compares two or more evaluation runs side-by-side.
    Rejects request if any requested run is unauthorized for current user.
    """
    ids = [i.strip() for i in run_ids.split(",") if i.strip()]
    if len(ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 comma-separated run IDs must be provided for comparison (e.g. ?run_ids=id1,id2)."
        )

    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    runs = []
    for r_id in ids:
        r = EvaluationRepository.get_run(
            session=db,
            run_id=r_id,
            current_user_id=current_user.id,
            is_admin=is_admin
        )
        if not r:
            raise HTTPException(status_code=404, detail=f"Evaluation run '{r_id}' not found or unauthorized.")
        runs.append(r)

    comparison = EvaluationService.compare_runs(runs)
    return EvaluationComparisonResponse.model_validate(comparison)
