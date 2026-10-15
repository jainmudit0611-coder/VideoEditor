"""
Structured JSON Logging Engine for Brand Guardian AI (Phase 6).
Formats log output as standardized JSON with correlation IDs, stable event names,
environment metadata, duration timing, and security redaction.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union

from backend.src.observability.correlation import (
    get_request_id,
    get_audit_id,
    get_worker_id,
    get_evaluation_run_id,
)
from backend.src.observability.redaction import redact_sensitive_data, SensitiveDataRedactionFilter
from backend.src.observability.events import ObservabilityEvent


class StructuredJsonFormatter(logging.Formatter):
    """
    Emits log records as a standardized, single-line JSON string.
    Injects context correlation IDs and standard metadata fields.
    """

    def __init__(
        self,
        service: str = "brand-guardian-api",
        environment: str = "production",
        app_version: str = "3.0.0",
    ):
        super().__init__()
        self.service = service
        self.environment = environment
        self.app_version = app_version

    def format(self, record: logging.LogRecord) -> str:
        # 1. Base log record fields
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        
        # 2. Extract correlation context
        req_id = getattr(record, "request_id", None) or get_request_id()
        audit_id = getattr(record, "audit_id", None) or get_audit_id()
        worker_id = getattr(record, "worker_id", None) or get_worker_id()
        eval_run_id = getattr(record, "evaluation_run_id", None) or get_evaluation_run_id()

        # 3. Extract event name
        event_name = getattr(record, "event", None)
        if isinstance(event_name, ObservabilityEvent):
            event_name = event_name.value
        elif not event_name:
            event_name = "log_message"

        payload: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "event": event_name,
            "service": getattr(record, "service", self.service),
            "environment": getattr(record, "environment", self.environment),
            "app_version": self.app_version,
            "logger": record.name,
        }

        # 4. Optional correlation & tracing identifiers
        if req_id:
            payload["request_id"] = req_id
        if audit_id:
            payload["audit_id"] = audit_id
        if worker_id:
            payload["worker_id"] = worker_id
        if eval_run_id:
            payload["evaluation_run_id"] = eval_run_id

        # 5. Operational telemetry attributes
        if hasattr(record, "stage") and record.stage is not None:
            payload["stage"] = str(record.stage)
        if hasattr(record, "duration_ms") and record.duration_ms is not None:
            payload["duration_ms"] = record.duration_ms
        if hasattr(record, "error_code") and record.error_code is not None:
            payload["error_code"] = (
                record.error_code.value
                if hasattr(record.error_code, "value")
                else str(record.error_code)
            )

        # 6. Message content
        msg = record.getMessage()
        payload["message"] = msg

        # 7. Additional custom/extra attributes passed to log_event
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
            "relativeCreated", "thread", "threadName", "processName", "process", "message",
            "taskName", "service", "environment", "app_version", "logger", "event", "timestamp",
            "level", "request_id", "audit_id", "worker_id", "evaluation_run_id", "stage",
            "duration_ms", "error_code", "details", "exception"
        }
        for k, v in record.__dict__.items():
            if not k.startswith("_") and k not in standard_attrs:
                payload[k] = v

        if hasattr(record, "details") and isinstance(record.details, dict):
            payload["details"] = record.details

        # 8. Exception details (server-side only, non-sensitive)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # 9. Apply security redaction to entire structured JSON payload
        sanitized_payload = redact_sensitive_data(payload)
        return json.dumps(sanitized_payload)


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger with sensitive data redaction filter attached."""
    logger = logging.getLogger(name)
    # Ensure sensitive data redaction filter is present
    has_filter = any(isinstance(f, SensitiveDataRedactionFilter) for f in logger.filters)
    if not has_filter:
        logger.addFilter(SensitiveDataRedactionFilter())
    return logger


def log_event(
    logger: logging.Logger,
    event: Union[ObservabilityEvent, str],
    level: int = logging.INFO,
    message: Optional[str] = None,
    **kwargs: Any,
):
    """
    Standard helper to emit an event-driven structured log with operational attributes.
    """
    event_str = event.value if isinstance(event, ObservabilityEvent) else str(event)
    msg = message or f"Event: {event_str}"

    extra = {"event": event_str}
    for k, v in kwargs.items():
        extra[k] = v

    # Ensure sensitive data in extra dict is redacted
    logger.log(level, msg, extra=extra)
