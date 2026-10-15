import json
import logging
import unittest
from io import StringIO

from backend.src.observability.structured_logger import (
    StructuredJsonFormatter,
    log_event,
    get_logger,
)
from backend.src.observability.events import ObservabilityEvent
from backend.src.observability.correlation import (
    set_correlation_context,
    clear_correlation_context,
)
from backend.src.observability.errors import ErrorCode


class TestStructuredLogging(unittest.TestCase):
    """
    Tests JSON structured logging formatting, standard field compliance,
    event taxonomy mapping, and correlation context injection.
    """

    def setUp(self):
        clear_correlation_context()
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.formatter = StructuredJsonFormatter(
            service="test-service",
            environment="test-env",
            app_version="3.0.0"
        )
        self.handler.setFormatter(self.formatter)
        self.test_logger = get_logger("test-structured-logger")
        self.test_logger.setLevel(logging.DEBUG)
        self.test_logger.addHandler(self.handler)

    def tearDown(self):
        self.test_logger.removeHandler(self.handler)
        clear_correlation_context()

    def _get_last_log_json(self):
        output = self.log_stream.getvalue().strip()
        lines = [line for line in output.split("\n") if line.strip()]
        self.assertTrue(len(lines) > 0, "No log lines recorded in stream")
        return json.loads(lines[-1])

    def test_structured_log_contains_standard_fields(self):
        """Verifies standard metadata fields are present in every emitted JSON log."""
        self.test_logger.info("Basic test message")
        data = self._get_last_log_json()

        self.assertIn("timestamp", data)
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["service"], "test-service")
        self.assertEqual(data["environment"], "test-env")
        self.assertEqual(data["app_version"], "3.0.0")
        self.assertEqual(data["message"], "Basic test message")
        self.assertEqual(data["event"], "log_message")

    def test_injects_correlation_context_automatically(self):
        """Verifies request_id, audit_id, and worker_id are pulled from contextvars."""
        set_correlation_context(
            request_id="req_xyz_123",
            audit_id="audit_abc_789",
            worker_id="worker_host_01"
        )

        self.test_logger.info("Contextual message")
        data = self._get_last_log_json()

        self.assertEqual(data.get("request_id"), "req_xyz_123")
        self.assertEqual(data.get("audit_id"), "audit_abc_789")
        self.assertEqual(data.get("worker_id"), "worker_host_01")

    def test_log_event_helper_with_operational_fields(self):
        """Verifies log_event helper formats stable event names and telemetry fields."""
        log_event(
            self.test_logger,
            ObservabilityEvent.AUDIT_STAGE_COMPLETED,
            level=logging.INFO,
            message="Stage verifier completed",
            stage="verifier",
            duration_ms=450,
            audit_id="audit_custom_999"
        )
        data = self._get_last_log_json()

        self.assertEqual(data["event"], "audit_stage_completed")
        self.assertEqual(data["stage"], "verifier")
        self.assertEqual(data["duration_ms"], 450)
        self.assertEqual(data["audit_id"], "audit_custom_999")
        self.assertEqual(data["message"], "Stage verifier completed")

    def test_log_event_with_error_code(self):
        """Verifies error_code enum is serialized properly in structured log."""
        log_event(
            self.test_logger,
            ObservabilityEvent.AUDIT_FAILED,
            level=logging.ERROR,
            message="Audit failed during download",
            error_code=ErrorCode.VIDEO_DOWNLOAD_ERROR,
            duration_ms=1200
        )
        data = self._get_last_log_json()

        self.assertEqual(data["event"], "audit_failed")
        self.assertEqual(data["level"], "ERROR")
        self.assertEqual(data["error_code"], "VIDEO_DOWNLOAD_ERROR")
        self.assertEqual(data["duration_ms"], 1200)

    def test_structured_log_with_exception_traceback(self):
        """Verifies exception stack traces are captured in JSON when exc_info is true."""
        try:
            raise ValueError("Test internal computation error")
        except ValueError:
            self.test_logger.exception("Caught calculation failure")

        data = self._get_last_log_json()
        self.assertEqual(data["level"], "ERROR")
        self.assertIn("exception", data)
        self.assertIn("ValueError: Test internal computation error", data["exception"])


if __name__ == "__main__":
    unittest.main()
