"""
Standardized Event Taxonomy for Brand Guardian AI (Phase 6).
Defines stable event names used across API, authentication, audit execution,
worker lifecycle, queue operations, LangGraph agents, verifier, and evaluations.
"""

from enum import Enum


class ObservabilityEvent(str, Enum):
    # --- API Events ---
    HTTP_REQUEST_STARTED = "http_request_started"
    HTTP_REQUEST_COMPLETED = "http_request_completed"
    HTTP_REQUEST_FAILED = "http_request_failed"

    # --- Authentication Events ---
    AUTH_LOGIN_SUCCESS = "auth_login_success"
    AUTH_LOGIN_FAILURE = "auth_login_failure"
    AUTH_REGISTRATION = "auth_registration"
    AUTH_FORBIDDEN = "auth_forbidden"

    # --- Audit Lifecycle Events ---
    AUDIT_CREATED = "audit_created"
    AUDIT_QUEUED = "audit_queued"
    AUDIT_STARTED = "audit_started"
    AUDIT_STAGE_STARTED = "audit_stage_started"
    AUDIT_STAGE_COMPLETED = "audit_stage_completed"
    AUDIT_COMPLETED = "audit_completed"
    AUDIT_FAILED = "audit_failed"
    AUDIT_CANCELLED = "audit_cancelled"
    AUDIT_DEGRADED_MODE = "audit_degraded_mode"

    # --- Worker Lifecycle Events ---
    WORKER_STARTED = "worker_started"
    WORKER_JOB_RECEIVED = "worker_job_received"
    WORKER_JOB_COMPLETED = "worker_job_completed"
    WORKER_JOB_FAILED = "worker_job_failed"
    WORKER_JOB_RETRY = "worker_job_retry"
    WORKER_SHUTDOWN = "worker_shutdown"

    # --- Queue Events ---
    QUEUE_ENQUEUE = "queue_enqueue"
    QUEUE_DEQUEUE = "queue_dequeue"
    QUEUE_UNAVAILABLE = "queue_unavailable"
    QUEUE_RETRY = "queue_retry"
    QUEUE_ACKNOWLEDGED = "queue_acknowledged"
    QUEUE_STALE_RECOVERED = "queue_stale_recovered"
    QUEUE_DEAD_LETTER = "queue_dead_letter"
    QUEUE_HEARTBEAT = "queue_heartbeat"

    # --- LangGraph & Agent Traceability ---
    GRAPH_RUN_STARTED = "graph_run_started"
    GRAPH_RUN_COMPLETED = "graph_run_completed"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    AGENT_TOOL_STARTED = "agent_tool_started"
    AGENT_TOOL_COMPLETED = "agent_tool_completed"

    # --- Verifier & Bounded Iteration Events ---
    VERIFIER_STARTED = "verifier_started"
    VERIFIER_COMPLETED = "verifier_completed"
    AUDIT_ITERATION_REQUESTED = "audit_iteration_requested"
    AUDIT_ITERATION_LIMIT_REACHED = "audit_iteration_limit_reached"
    AUDIT_ROUTED_TO_REPORT = "audit_routed_to_report"

    # --- Evaluation Events ---
    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_CASE_STARTED = "evaluation_case_started"
    EVALUATION_CASE_COMPLETED = "evaluation_case_completed"
    EVALUATION_COMPLETED = "evaluation_completed"
    EVALUATION_FAILED = "evaluation_failed"
