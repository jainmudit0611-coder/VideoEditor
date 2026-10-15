"""
Correlation ID context management for Brand Guardian AI (Phase 6).
Provides async-safe ContextVar storage for request_id, audit_id, worker_id, and evaluation_run_id.
"""

import re
import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any

_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_audit_id_var: ContextVar[Optional[str]] = ContextVar("audit_id", default=None)
_worker_id_var: ContextVar[Optional[str]] = ContextVar("worker_id", default=None)
_evaluation_run_id_var: ContextVar[Optional[str]] = ContextVar("evaluation_run_id", default=None)

# Valid correlation ID pattern: alphanumeric, hyphen, underscore, 1 to 64 chars
_VALID_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def validate_request_id(candidate: Optional[str]) -> Optional[str]:
    """
    Validates candidate request/correlation ID.
    Must be 1-64 characters and contain only alphanumeric, hyphens, and underscores.
    Returns cleaned ID if valid, or None if invalid.
    """
    if not candidate or not isinstance(candidate, str):
        return None
    cleaned = candidate.strip()
    if _VALID_ID_PATTERN.match(cleaned):
        return cleaned
    return None


def generate_request_id() -> str:
    """Generates a secure, cryptographically random request correlation ID."""
    return f"req_{uuid.uuid4().hex[:16]}"


def get_request_id() -> Optional[str]:
    """Returns the current request_id from context, if any."""
    return _request_id_var.get()


def get_audit_id() -> Optional[str]:
    """Returns the current audit_id from context, if any."""
    return _audit_id_var.get()


def get_worker_id() -> Optional[str]:
    """Returns the current worker_id from context, if any."""
    return _worker_id_var.get()


def get_evaluation_run_id() -> Optional[str]:
    """Returns the current evaluation_run_id from context, if any."""
    return _evaluation_run_id_var.get()


def set_correlation_context(
    request_id: Optional[str] = None,
    audit_id: Optional[str] = None,
    worker_id: Optional[str] = None,
    evaluation_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sets correlation identifiers in the current async context.
    Returns a dict of tokens that can be used to reset if needed.
    """
    tokens = {}
    if request_id is not None:
        tokens["request_id"] = _request_id_var.set(request_id)
    if audit_id is not None:
        tokens["audit_id"] = _audit_id_var.set(audit_id)
    if worker_id is not None:
        tokens["worker_id"] = _worker_id_var.set(worker_id)
    if evaluation_run_id is not None:
        tokens["evaluation_run_id"] = _evaluation_run_id_var.set(evaluation_run_id)
    return tokens


def get_correlation_context() -> Dict[str, Optional[str]]:
    """Returns all current correlation identifiers as a dictionary."""
    return {
        "request_id": _request_id_var.get(),
        "audit_id": _audit_id_var.get(),
        "worker_id": _worker_id_var.get(),
        "evaluation_run_id": _evaluation_run_id_var.get(),
    }


def clear_correlation_context():
    """Resets all correlation identifiers in the current async context."""
    _request_id_var.set(None)
    _audit_id_var.set(None)
    _worker_id_var.set(None)
    _evaluation_run_id_var.set(None)
