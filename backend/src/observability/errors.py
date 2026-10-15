"""
Operational Error Taxonomy & Safe Error Response Engine (Phase 6).
Standardizes operational error codes and guarantees client responses remain safe
without exposing internal hostnames, tracebacks, database details, or credentials.
"""

from enum import Enum
from typing import Dict, Any, Optional
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SSRF_BLOCKED = "SSRF_BLOCKED"
    QUEUE_UNAVAILABLE = "QUEUE_UNAVAILABLE"
    VIDEO_DOWNLOAD_ERROR = "VIDEO_DOWNLOAD_ERROR"
    VIDEO_INDEXER_ERROR = "VIDEO_INDEXER_ERROR"
    FRAME_EXTRACTION_ERROR = "FRAME_EXTRACTION_ERROR"
    VISION_ERROR = "VISION_ERROR"
    PLANNER_ERROR = "PLANNER_ERROR"
    AUDITOR_ERROR = "AUDITOR_ERROR"
    VERIFIER_ERROR = "VERIFIER_ERROR"
    REPORT_ERROR = "REPORT_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


SAFE_ERROR_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.AUTHENTICATION_ERROR: "Authentication failed. Please verify your credentials.",
    ErrorCode.AUTHORIZATION_ERROR: "You do not have permission to access or perform this action on the requested resource.",
    ErrorCode.VALIDATION_ERROR: "The submitted request payload or parameters are invalid.",
    ErrorCode.SSRF_BLOCKED: "Access to private or restricted network addresses is not allowed.",
    ErrorCode.QUEUE_UNAVAILABLE: "The audit queue service is temporarily unavailable. Please retry later.",
    ErrorCode.VIDEO_DOWNLOAD_ERROR: "Unable to retrieve the specified video. Please check the URL and accessibility.",
    ErrorCode.VIDEO_INDEXER_ERROR: "Video indexing service encountered an issue while processing the media.",
    ErrorCode.FRAME_EXTRACTION_ERROR: "Frame extraction failed to process the video stream.",
    ErrorCode.VISION_ERROR: "Visual compliance analysis encountered an error.",
    ErrorCode.PLANNER_ERROR: "Compliance audit planning encountered an error.",
    ErrorCode.AUDITOR_ERROR: "Auditor agent encountered an issue during compliance evaluation.",
    ErrorCode.VERIFIER_ERROR: "Verification of compliance findings encountered an error.",
    ErrorCode.REPORT_ERROR: "Compliance report generation failed.",
    ErrorCode.DATABASE_ERROR: "A database error occurred. Please try again later.",
    ErrorCode.CONFIGURATION_ERROR: "A service configuration issue was detected.",
    ErrorCode.UNKNOWN_ERROR: "An unexpected error occurred. Please contact the system administrator.",
}


def get_safe_error_message(code: ErrorCode) -> str:
    """Returns the standardized, user-safe message for a given operational error code."""
    return SAFE_ERROR_MESSAGES.get(code, SAFE_ERROR_MESSAGES[ErrorCode.UNKNOWN_ERROR])


def create_safe_error_response(
    error_code: ErrorCode,
    custom_message: Optional[str] = None,
    request_id: Optional[str] = None,
    status_code: int = 500,
) -> JSONResponse:
    """
    Constructs a standardized, user-safe HTTP JSONResponse with error_code and request_id.
    """
    msg = custom_message or get_safe_error_message(error_code)
    body: Dict[str, Any] = {
        "error_code": error_code.value if isinstance(error_code, ErrorCode) else str(error_code),
        "detail": msg,
    }
    if request_id:
        body["request_id"] = request_id

    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id

    return JSONResponse(status_code=status_code, content=body, headers=headers)
