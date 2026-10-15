import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.src.config import settings
from backend.src.db.models import AuditStatus, AuditStage
from backend.src.db.repositories import AuditRepository
from backend.src.graph.workflow import app as compliance_graph
from backend.src.observability import (
    log_event,
    ObservabilityEvent,
    get_logger,
    set_correlation_context,
)

logger = get_logger("brand-guardian-worker-processor")

class AuditTaskProcessor:
    """
    Executes a single async audit job by fetching state from DB, invoking the LangGraph pipeline,
    updating progress, handling retries, and persisting audit results.
    """

    @staticmethod
    def process_audit_job(session: Session, audit_id: str, worker_id: Optional[str] = None) -> bool:
        """
        Processes an audit job by audit_id.
        Returns True if successfully completed, False if failed/retried/cancelled.
        """
        logger.info(f"--- [Worker Processor] Processing Audit Job: audit_id={audit_id} (worker={worker_id}) ---")

        # 1. Fetch AuditJob from DB
        job = AuditRepository.get_audit(session, audit_id)
        if not job:
            logger.error(f"Job not found in database: audit_id={audit_id}")
            return False

        # Set correlation context for worker thread/process
        req_id = getattr(job, "request_id", None)
        set_correlation_context(request_id=req_id, audit_id=audit_id, worker_id=worker_id)

        # 2. Check if job was already processed or cancelled (idempotency check)
        if job.status == AuditStatus.COMPLETED:
            logger.info(f"Audit job audit_id={audit_id} already COMPLETED in database. Skipping duplicate processing.")
            return True
        if job.status in (AuditStatus.CANCELLED, AuditStatus.FAILED):
            log_event(
                logger,
                ObservabilityEvent.AUDIT_CANCELLED if job.status == AuditStatus.CANCELLED else ObservabilityEvent.AUDIT_FAILED,
                message=f"Skipping already terminated job (status={job.status}): audit_id={audit_id}",
                audit_id=audit_id,
                worker_id=worker_id
            )
            return True

        log_event(
            logger,
            ObservabilityEvent.WORKER_JOB_RECEIVED,
            message=f"Worker received audit job: audit_id={audit_id}",
            audit_id=audit_id,
            worker_id=worker_id,
            request_id=req_id,
            attempt=getattr(job, "retry_count", 0) + 1
        )
        log_event(
            logger,
            ObservabilityEvent.AUDIT_STARTED,
            message=f"Audit execution started: audit_id={audit_id}",
            audit_id=audit_id,
            stage=AuditStage.DOWNLOADING.value
        )

        video_url = job.video_url
        video_id_short = f"vid_{audit_id[:8]}"

        # 3. Update Status to PROCESSING (Stage: DOWNLOADING, Progress: 10%)
        AuditRepository.update_status(
            session,
            audit_id,
            status=AuditStatus.PROCESSING,
            stage=AuditStage.DOWNLOADING.value,
            progress=10
        )

        initial_inputs = {
            "video_url": video_url,
            "video_id": video_id_short,
            "compliance_results": [],
            "errors": [],
            "iteration_count": 0,
            "retrieved_evidence": [],
            "visual_observations": [],
            "transcript_items": [],
            "ocr_items": [],
            "extracted_frame_count": 0,
            "is_degraded_vision_mode": False,
            "timing_metrics": {}
        }

        try:
            # 4. Invoke LangGraph Compliance Engine
            AuditRepository.update_progress(session, audit_id, progress=30, stage=AuditStage.VIDEO_INDEXING.value)
            
            t0 = time.time()
            final_state = compliance_graph.invoke(initial_inputs)
            total_duration = round(time.time() - t0, 2)

            # 5. Extract Output Deliverables
            final_status = final_state.get("final_status", "PASS")
            final_report = final_state.get("final_report", "No report generated.")
            compliance_results = final_state.get("compliance_results", [])
            citations = final_state.get("citations", [])
            verification_summary = final_state.get("verification_results", {})
            iterations_completed = final_state.get("iteration_count", 0) + 1
            visual_observations_count = len(final_state.get("visual_observations", []))
            is_degraded = final_state.get("is_degraded_vision_mode", False)
            timing_metrics = final_state.get("timing_metrics", {})
            timing_metrics["total_worker_duration"] = total_duration

            formatted_result = {
                "audit_id": audit_id,
                "video_id": video_id_short,
                "status": final_status,
                "final_report": final_report,
                "compliance_results": compliance_results,
                "citations": citations,
                "verification_summary": verification_summary,
                "iterations_completed": iterations_completed,
                "visual_observations_count": visual_observations_count,
                "is_degraded_vision_mode": is_degraded,
            }

            # 6. Save Result to Database Repository
            AuditRepository.save_result(
                session=session,
                audit_id=audit_id,
                result=formatted_result,
                timing_metrics=timing_metrics,
                iteration_count=iterations_completed
            )
            duration_ms = int(total_duration * 1000)
            log_event(
                logger,
                ObservabilityEvent.WORKER_JOB_COMPLETED,
                message=f"Worker successfully completed audit_id={audit_id} in {duration_ms}ms with status {final_status}",
                audit_id=audit_id,
                worker_id=worker_id,
                request_id=req_id,
                duration_ms=duration_ms,
                status=final_status
            )
            log_event(
                logger,
                ObservabilityEvent.AUDIT_COMPLETED,
                message=f"Audit job completed: audit_id={audit_id}, status={final_status}",
                audit_id=audit_id,
                status=final_status,
                duration_ms=duration_ms
            )
            return True

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing audit job {audit_id}: {error_msg}")

            # Check transient retry candidate
            retry_count = AuditRepository.increment_retry_count(session, audit_id)
            is_transient = any(term in error_msg.lower() for term in ["timeout", "connection", "rate limit", "503", "502"])

            if is_transient and retry_count <= settings.MAX_RETRIES:
                log_event(
                    logger,
                    ObservabilityEvent.WORKER_JOB_RETRY,
                    level=logging.WARNING,
                    message=f"Transient error detected. Retry {retry_count}/{settings.MAX_RETRIES} for audit_id={audit_id}",
                    audit_id=audit_id,
                    worker_id=worker_id,
                    attempt=retry_count,
                    max_attempts=settings.MAX_RETRIES,
                    error_code="TRANSIENT_ERROR"
                )
                AuditRepository.update_status(
                    session,
                    audit_id,
                    status=AuditStatus.QUEUED,
                    stage=AuditStage.QUEUED.value,
                    progress=0
                )
                from backend.src.queue.redis_queue import audit_queue
                audit_queue.acknowledge(audit_id, worker_id=worker_id)
                audit_queue.enqueue_audit(audit_id)
                return False
            else:
                # Non-retryable error or retry limits exhausted
                err_code = "MAX_RETRIES_EXCEEDED" if retry_count > settings.MAX_RETRIES else "WORKFLOW_EXECUTION_ERROR"
                log_event(
                    logger,
                    ObservabilityEvent.WORKER_JOB_FAILED,
                    level=logging.ERROR,
                    message=f"Worker failed processing audit_id={audit_id}: {error_msg}",
                    audit_id=audit_id,
                    worker_id=worker_id,
                    error_code=err_code
                )
                log_event(
                    logger,
                    ObservabilityEvent.AUDIT_FAILED,
                    level=logging.ERROR,
                    message=f"Audit marked as failed: audit_id={audit_id}",
                    audit_id=audit_id,
                    error_code=err_code
                )
                AuditRepository.mark_failed(
                    session,
                    audit_id,
                    error_code=err_code,
                    error_message=f"Audit execution failed: {error_msg}",
                    error_details={"exception": type(e).__name__, "retry_count": retry_count}
                )
                from backend.src.queue.redis_queue import audit_queue
                audit_queue.move_to_dead_letter(
                    audit_id=audit_id,
                    reason=f"failed: [{err_code}] {error_msg[:120]}",
                    worker_id=worker_id
                )
                return False
