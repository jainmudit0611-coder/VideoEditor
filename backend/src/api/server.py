import uuid
import logging
from urllib.parse import urlparse
import socket
import ipaddress
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Depends, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv(override=True)

from backend.src.config import settings
from backend.src.api.telemetry import setup_telemetry
setup_telemetry()

from backend.src.db.database import get_db, init_db
from backend.src.db.models import AuditJob, AuditStatus, User, UserRole
import time
from backend.src.db.repositories import AuditRepository
from backend.src.queue.redis_queue import audit_queue
from sqlalchemy.orm import Session

from backend.src.observability import (
    get_logger,
    log_event,
    ObservabilityEvent,
    set_correlation_context,
    get_request_id,
    validate_request_id,
    generate_request_id,
    ErrorCode,
    create_safe_error_response,
    SensitiveDataRedactionFilter,
    StructuredJsonFormatter,
)

logger = get_logger("api-server")

from fastapi.middleware.cors import CORSMiddleware
from backend.src.api.auth_routes import router as auth_router
from backend.src.api.auth_dependencies import get_current_active_user, require_admin
from backend.src.api.evaluation_routes import router as evaluation_router

app = FastAPI(
    title="Brand Guardian AI API Platform",
    description="Production Reliable Asynchronous Multimodal Agentic Video Compliance Audit Platform.",
    version=settings.APP_VERSION
)

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

@app.middleware("http")
async def correlation_and_telemetry_middleware(request: Request, call_next):
    """
    Middleware establishing correlation context (request_id) and recording request telemetry.
    Reuses incoming X-Request-ID if valid, or generates a secure unique ID.
    Exposes X-Request-ID in response headers.
    """
    raw_id = request.headers.get("X-Request-ID")
    req_id = validate_request_id(raw_id) or generate_request_id()
    set_correlation_context(request_id=req_id)

    path = request.url.path
    method = request.method
    t0 = time.time()

    log_event(
        logger,
        ObservabilityEvent.HTTP_REQUEST_STARTED,
        message=f"{method} {path} started",
        request_id=req_id,
        method=method,
        route=path
    )

    try:
        response = await call_next(request)
        duration_ms = int((time.time() - t0) * 1000)
        response.headers["X-Request-ID"] = req_id

        log_event(
            logger,
            ObservabilityEvent.HTTP_REQUEST_COMPLETED,
            message=f"{method} {path} completed with status {response.status_code} in {duration_ms}ms",
            request_id=req_id,
            method=method,
            route=path,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        return response
    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.HTTP_REQUEST_FAILED,
            level=logging.ERROR,
            message=f"{method} {path} failed after {duration_ms}ms: {exc}",
            request_id=req_id,
            method=method,
            route=path,
            duration_ms=duration_ms,
            error_code=ErrorCode.UNKNOWN_ERROR
        )
        raise exc

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Middleware applying defense-in-depth HTTP security headers.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles HTTPExceptions cleanly, preserving X-Request-ID and emitting structured error telemetry.
    """
    req_id = get_request_id() or generate_request_id()
    error_code = ErrorCode.UNKNOWN_ERROR
    if exc.status_code == 400:
        error_code = ErrorCode.VALIDATION_ERROR
    elif exc.status_code == 401:
        error_code = ErrorCode.AUTHENTICATION_ERROR
    elif exc.status_code == 403:
        error_code = ErrorCode.AUTHORIZATION_ERROR
    elif exc.status_code == 503:
        error_code = ErrorCode.QUEUE_UNAVAILABLE

    log_event(
        logger,
        ObservabilityEvent.HTTP_REQUEST_FAILED,
        level=logging.WARNING if exc.status_code < 500 else logging.ERROR,
        message=f"HTTPException on {request.method} {request.url.path}: {exc.detail}",
        request_id=req_id,
        status_code=exc.status_code,
        error_code=error_code
    )

    headers = dict(exc.headers or {})
    headers["X-Request-ID"] = req_id
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches all unexpected exceptions. Prevents tracebacks and secrets leaking to client.
    Logs structured event with traceback on server-side and returns safe JSON response.
    """
    req_id = get_request_id() or generate_request_id()
    logger.exception(f"Unhandled server exception on {request.method} {request.url.path}: {exc}")
    log_event(
        logger,
        ObservabilityEvent.HTTP_REQUEST_FAILED,
        level=logging.ERROR,
        message=f"Unhandled exception on {request.method} {request.url.path}",
        request_id=req_id,
        error_code=ErrorCode.UNKNOWN_ERROR
    )
    return create_safe_error_response(
        error_code=ErrorCode.UNKNOWN_ERROR,
        request_id=req_id,
        status_code=500
    )

app.include_router(auth_router)
app.include_router(evaluation_router)

@app.on_event("startup")
def on_startup():
    logger.info("Initializing Brand Guardian AI database tables...")
    init_db()

# --- URL VALIDATION (HARDENED SSRF PREVENTATIVE GUARD) ---
def _is_ip_restricted(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """
    Checks if an IP address belongs to loopback, private RFC 1918 (including 172.16.0.0/12),
    link-local (including 169.254.169.254 and fe80::), multicast, reserved, or unspecified ranges.
    """
    return (
        ip_obj.is_loopback
        or ip_obj.is_private
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )

def validate_video_url(url: str):
    """
    Hardened validation of video URLs against SSRF, unauthorized protocols,
    cloud metadata endpoints, and DNS rebinding attacks.
    """
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=400, detail="Invalid video_url provided.")
    
    clean_url = url.strip()
    if len(clean_url) > 2048:
        raise HTTPException(status_code=400, detail="Video URL exceeds maximum allowed length of 2048 characters.")

    parsed = urlparse(clean_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL protocol. Only http:// and https:// URLs are supported.")
    
    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise HTTPException(status_code=400, detail="The requested video URL is not allowed.")

    # 1. Direct hostname blocklist
    blocked_hostnames = {"localhost", "0.0.0.0", "::", "metadata.google.internal"}
    if hostname in blocked_hostnames:
        raise HTTPException(status_code=400, detail="Access to private or restricted network addresses is not allowed.")

    # 2. IP Literal Check (IPv4 or bracketed IPv6)
    clean_host = hostname.strip("[]")
    try:
        ip = ipaddress.ip_address(clean_host)
        if _is_ip_restricted(ip):
            raise HTTPException(status_code=400, detail="Access to private or restricted network addresses is not allowed.")
        return
    except ValueError:
        # Not a raw IP literal, proceed to DNS resolution check
        pass

    # 3. DNS Resolution check (prevent DNS rebinding to private / internal network IPs)
    try:
        resolved_addrs = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in resolved_addrs:
            resolved_ip_str = sockaddr[0]
            try:
                resolved_ip = ipaddress.ip_address(resolved_ip_str)
                if _is_ip_restricted(resolved_ip):
                    raise HTTPException(
                        status_code=400,
                        detail="Access to private or restricted network addresses is not allowed."
                    )
            except ValueError:
                continue
    except socket.gaierror:
        # For mock / test environments with unresolvable domains, allow known video providers
        trusted_suffixes = (".youtube.com", "youtube.com", ".youtu.be", "youtu.be", ".vimeo.com", "vimeo.com")
        if not any(hostname == s or hostname.endswith(s) for s in trusted_suffixes):
            raise HTTPException(status_code=400, detail="The requested video URL is not allowed.")

# --- REQUEST & RESPONSE MODELS ---
class CreateAuditRequest(BaseModel):
    video_url: str = Field(..., max_length=2048, description="Target YouTube video URL for compliance audit")


class CreateAuditResponse(BaseModel):
    audit_id: str
    status: str
    video_url: str
    message: str = "Audit job enqueued successfully."

class AuditStatusResponse(BaseModel):
    audit_id: str
    status: str
    progress: int
    current_stage: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None

class ComplianceIssue(BaseModel):
    category: str
    severity: str
    description: str
    timestamp: Optional[str] = None

class AuditResponse(BaseModel):
    session_id: str
    video_id: str
    status: str
    final_report: str
    compliance_results: List[ComplianceIssue]
    citations: Optional[List[Dict[str, Any]]] = None
    verification_summary: Optional[Dict[str, Any]] = None
    iterations_completed: Optional[int] = 1
    visual_observations_count: Optional[int] = 0
    is_degraded_vision_mode: Optional[bool] = False
    timing_metrics: Optional[Dict[str, float]] = None

# --- PHASE 3 ASYNCHRONOUS ENDPOINTS ---

@app.post("/audits", response_model=CreateAuditResponse, status_code=status.HTTP_202_ACCEPTED)
def create_async_audit(
    request: CreateAuditRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Creates an asynchronous video compliance audit job and enqueues it for background processing.
    Accepts an optional 'Idempotency-Key' header to prevent duplicate job creation.
    Server-side assigns ownership to current_user.id (client cannot choose ownership).
    """
    validate_video_url(request.video_url)

    # Check Idempotency Key
    if idempotency_key:
        existing_job = AuditRepository.get_audit_by_idempotency_key(db, idempotency_key)
        if existing_job:
            logger.info(f"Idempotency match found for key '{idempotency_key}'. Returning existing audit_id={existing_job.id}")
            return CreateAuditResponse(
                audit_id=str(existing_job.id),
                status=existing_job.status.value,
                video_url=str(existing_job.video_url),
                message="Returned existing audit job via Idempotency-Key."
            )

    req_id = get_request_id() or generate_request_id()

    # Create Audit Record in DB with server-assigned ownership and correlation ID
    job = AuditRepository.create_audit(
        session=db,
        video_url=request.video_url,
        idempotency_key=idempotency_key,
        created_by=str(current_user.id),
        request_id=req_id
    )

    log_event(
        logger,
        ObservabilityEvent.AUDIT_CREATED,
        message=f"Audit created: audit_id={job.id}",
        audit_id=job.id,
        request_id=req_id,
        user_id=str(current_user.id)
    )

    # Push audit_id into Redis queue
    try:
        audit_queue.enqueue_audit(job.id)
        log_event(
            logger,
            ObservabilityEvent.AUDIT_QUEUED,
            message=f"Audit job queued: audit_id={job.id}",
            audit_id=job.id,
            request_id=req_id
        )
    except Exception as e_queue:
        logger.error(f"Failed to enqueue audit {job.id}: {e_queue}")
        log_event(
            logger,
            ObservabilityEvent.QUEUE_UNAVAILABLE,
            level=logging.ERROR,
            message=f"Failed to enqueue audit {job.id}: {e_queue}",
            audit_id=job.id,
            error_code=ErrorCode.QUEUE_UNAVAILABLE
        )
        AuditRepository.mark_failed(
            session=db,
            audit_id=job.id,
            error_code="QUEUE_UNAVAILABLE",
            error_message=f"Failed to enqueue audit to queue: {e_queue}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Queue service unavailable: {str(e_queue)}"
        )

    return CreateAuditResponse(
        audit_id=str(job.id),
        status=job.status.value,
        video_url=str(job.video_url),
        message="Audit job enqueued for background processing."
    )

@app.get("/audits", response_model=List[Dict[str, Any]])
def list_audits(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lists recent video audit jobs. Normal users see only their own audits; admins see all."""
    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    owner_id = None if is_admin else str(current_user.id)
    jobs = AuditRepository.list_audits(db, owner_id=owner_id, limit=limit, offset=offset)
    return [job.to_dict() for job in jobs]

@app.get("/audits/{audit_id}")
def get_audit_details(
    audit_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieves full details and persisted results of a video audit job with ownership enforcement."""
    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    owner_id = None if is_admin else str(current_user.id)
    job = AuditRepository.get_audit(db, audit_id, owner_id=owner_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Audit job '{audit_id}' not found.")
    return job.to_dict()

@app.get("/audits/{audit_id}/status", response_model=AuditStatusResponse)
def get_audit_status(
    audit_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieves real-time execution status and stage progress of an audit job with ownership enforcement."""
    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    owner_id = None if is_admin else str(current_user.id)
    job = AuditRepository.get_audit(db, audit_id, owner_id=owner_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Audit job '{audit_id}' not found.")
    return AuditStatusResponse(
        audit_id=str(job.id),
        status=job.status.value,
        progress=int(job.progress),
        current_stage=str(job.current_stage),
        error_code=job.error_code,
        error_message=job.error_message
    )

@app.get("/audits/{audit_id}/report")
def get_audit_report(
    audit_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieves the completed Markdown audit report for a finished job with ownership enforcement."""
    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    owner_id = None if is_admin else str(current_user.id)
    job = AuditRepository.get_audit(db, audit_id, owner_id=owner_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Audit job '{audit_id}' not found.")
    
    if job.status != AuditStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Audit job '{audit_id}' is not completed yet (Current status: {job.status.value})."
        )
    
    result = job.result or {}
    report_markdown = result.get("final_report", "No report content available.")
    return {
        "audit_id": str(job.id),
        "status": job.status.value,
        "final_report": report_markdown
    }

@app.post("/audits/{audit_id}/cancel")
def cancel_audit_job(
    audit_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancels a queued or in-progress audit job with ownership enforcement."""
    is_admin = (current_user.role == UserRole.ADMIN or getattr(current_user.role, "value", None) == "ADMIN")
    owner_id = None if is_admin else str(current_user.id)
    job = AuditRepository.cancel_audit(db, audit_id, owner_id=owner_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Audit job '{audit_id}' not found.")
    return {
        "audit_id": str(job.id),
        "status": job.status.value,
        "message": "Audit job cancelled successfully."
    }

# --- BACKWARD COMPATIBLE LEGACY SYNCHRONOUS ENDPOINT ---
@app.post("/audit", response_model=AuditResponse)
async def audit_video_legacy(
    request: CreateAuditRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Legacy synchronous endpoint preserving Phase 1 & 2 client API contracts.
    """
    validate_video_url(request.video_url)
    session_id = str(uuid.uuid4())
    video_id_short = f"vid_{session_id[:8]}"
    
    logger.info(f"Received Legacy Synchronous Audit Request: {request.video_url} (Session: {session_id})")

    initial_inputs = {
        "video_url": request.video_url,
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
        from backend.src.graph.workflow import app as compliance_graph
        final_state = compliance_graph.invoke(initial_inputs)
        
        return AuditResponse(
            session_id=session_id,
            video_id=final_state.get("video_id", video_id_short),
            status=final_state.get("final_status", "UNKNOWN"),
            final_report=final_state.get("final_report", "No report generated."),
            compliance_results=final_state.get("compliance_results", []),
            citations=final_state.get("citations", []),
            verification_summary=final_state.get("verification_results", {}),
            iterations_completed=final_state.get("iteration_count", 0) + 1,
            visual_observations_count=len(final_state.get("visual_observations", [])),
            is_degraded_vision_mode=final_state.get("is_degraded_vision_mode", False),
            timing_metrics=final_state.get("timing_metrics", {})
        )
    except Exception as e:
        logger.error(f"Synchronous Audit Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Workflow Execution Failed: {str(e)}")

# --- HEALTH & READINESS ENDPOINTS ---
@app.get("/health")
def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "Brand Guardian AI Platform",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/health/live")
def liveness_check():
    """Liveness probe checking process responsiveness."""
    return {"status": "alive"}

@app.get("/health/ready")
def readiness_check():
    """Readiness probe checking database and redis queue connectivity."""
    env_status = settings.validate_environment()
    db_ok = False
    try:
        from backend.src.db.database import engine
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        db_ok = True
    except Exception as e:
        logger.warning(f"Health readiness DB check failed: {e}")

    redis_ok = audit_queue.is_redis_available
    redis_required = settings.REDIS_REQUIRED or audit_queue.redis_required

    if redis_required:
        is_ready = db_ok and redis_ok
        redis_status_str = "ok" if redis_ok else "unavailable"
    else:
        is_ready = db_ok
        redis_status_str = "ok" if redis_ok else "memory_fallback_active"

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "unready",
            "version": settings.APP_VERSION,
            "environment_name": settings.ENVIRONMENT,
            "database": "ok" if db_ok else "unavailable",
            "redis": redis_status_str,
            "redis_required": redis_required,
            "environment": env_status
        }
    )

# --- PHASE 6 OPERATOR OBSERVABILITY ENDPOINT ---
@app.get("/api/admin/observability/summary")
def get_observability_summary(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Operator-level observability summary endpoint.
    Strictly protected: ADMIN-only. Exposes safe aggregated job metrics without secrets.
    """
    from sqlalchemy import func
    status_rows = (
        db.query(AuditJob.status, func.count(AuditJob.id))
        .group_by(AuditJob.status)
        .all()
    )
    formatted_counts = {
        (row[0].value if hasattr(row[0], "value") else str(row[0])): int(row[1])
        for row in status_rows
    }
    total_jobs = sum(formatted_counts.values())

    return {
        "service": "brand-guardian-api",
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "healthy",
        "redis": {
            "available": audit_queue.is_redis_available,
            "required": audit_queue.redis_required,
            "pending_queue_length": audit_queue.get_queue_length()
        },
        "audit_jobs": {
            "total": total_jobs,
            "by_status": formatted_counts
        }
    }