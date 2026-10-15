"""
Log Redaction & Sanitization Engine for Brand Guardian AI (Phase 6).
Guarantees that secrets, tokens, passwords, database credentials, and
sensitive URL query parameters are never exposed in application logs.
"""

import re
import logging
from typing import Any, Dict, List, Union
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# Patterns for sensitive patterns
_BEARER_TOKEN_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE)
_JWT_PATTERN = re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]+")
_CONN_STRING_PWD_PATTERN = re.compile(r"://([^:]+):([^@]+)@")
_REDIS_PASSWORD_PATTERN = re.compile(r"(redis://:[^@]+@)", re.IGNORECASE)
_INLINE_SECRET_PATTERN = re.compile(r"((?:password|password_hash|pwd|secret|api_key)[\"'\s:=]+)[\"']?([^\s,\"'}]+)[\"']?", re.IGNORECASE)

# Sensitive dictionary keys to redact
SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "pwd",
    "secret",
    "jwt_secret_key",
    "access_token",
    "token",
    "authorization",
    "api_key",
    "azure_openai_api_key",
    "azure_search_api_key",
    "applicationinsights_connection_string",
    "database_url",
    "redis_url",
    "azure_storage_connection_string",
}

# Sensitive query params in URLs
SENSITIVE_QUERY_PARAMS = {
    "sig",
    "token",
    "key",
    "apikey",
    "api_key",
    "secret",
    "password",
    "access_token",
    "auth",
}


def sanitize_url(url_str: str) -> str:
    """
    Sanitizes URLs by stripping credentials from userinfo (e.g., redis://:pass@host)
    and redacting sensitive query parameters (e.g., ?sig=..., ?token=...).
    """
    if not isinstance(url_str, str):
        return url_str

    # Sanitize embedded passwords in scheme://user:pass@host
    url_cleaned = _CONN_STRING_PWD_PATTERN.sub(r"://\1:[REDACTED]@", url_str)
    url_cleaned = _REDIS_PASSWORD_PATTERN.sub("redis://:[REDACTED]@", url_cleaned)

    try:
        parsed = urlparse(url_cleaned)
        if not parsed.query:
            return url_cleaned

        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        sanitized_params = []
        for k, v in query_params:
            if k.lower() in SENSITIVE_QUERY_PARAMS:
                sanitized_params.append((k, "[REDACTED]"))
            else:
                sanitized_params.append((k, v))

        new_query = urlencode(sanitized_params)
        return urlunparse(parsed._replace(query=new_query))
    except Exception:
        return url_cleaned


def redact_sensitive_data(data: Any) -> Any:
    """
    Recursively redacts sensitive strings, dicts, and lists.
    """
    if isinstance(data, str):
        # 1. Bearer tokens
        redacted = _BEARER_TOKEN_PATTERN.sub(r"\1[REDACTED]", data)
        # 2. Standalone JWTs
        redacted = _JWT_PATTERN.sub("[REDACTED_JWT]", redacted)
        # 3. Connection string passwords
        redacted = _CONN_STRING_PWD_PATTERN.sub(r"://\1:[REDACTED]@", redacted)
        redacted = _REDIS_PASSWORD_PATTERN.sub("redis://:[REDACTED]@", redacted)
        # 4. Inline secrets/passwords (e.g. password: Secret123)
        redacted = _INLINE_SECRET_PATTERN.sub(r"\1[REDACTED]", redacted)
        # 5. URLs with query params if it looks like a URL
        if "://" in redacted and "?" in redacted:
            redacted = sanitize_url(redacted)
        return redacted

    elif isinstance(data, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned

    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]

    elif isinstance(data, tuple):
        return tuple(redact_sensitive_data(item) for item in data)

    return data


class SensitiveDataRedactionFilter(logging.Filter):
    """
    A Python logging filter that intercepts log records and scrubs any sensitive
    data from messages and argument lists before emission.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_sensitive_data(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(redact_sensitive_data(a) for a in record.args)
            try:
                # Merge and redact to eliminate sensitive values while keeping format intact
                formatted = record.msg % record.args
                record.msg = redact_sensitive_data(formatted)
                record.args = None
            except Exception:
                pass
        elif isinstance(record.msg, str):
            record.msg = redact_sensitive_data(record.msg)

        return True
