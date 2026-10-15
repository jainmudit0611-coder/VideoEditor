import unittest
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.observability.correlation import (
    generate_request_id,
    validate_request_id,
    set_correlation_context,
    get_request_id,
    clear_correlation_context,
    get_correlation_context,
)


class TestRequestIdAndCorrelation(unittest.TestCase):
    """
    Tests correlation ID generation, validation, ContextVar isolation,
    and HTTP header propagation across incoming and outgoing requests.
    """

    def setUp(self):
        clear_correlation_context()
        self.client = TestClient(app)

    def tearDown(self):
        clear_correlation_context()

    def test_generate_request_id_format(self):
        """Verifies generate_request_id outputs unique, prefix-compliant IDs."""
        id1 = generate_request_id()
        id2 = generate_request_id()
        self.assertTrue(id1.startswith("req_"))
        self.assertTrue(id2.startswith("req_"))
        self.assertNotEqual(id1, id2)
        self.assertLessEqual(len(id1), 64)

    def test_validate_request_id(self):
        """Verifies validation rules for client-provided X-Request-ID."""
        # Valid cases
        self.assertEqual(validate_request_id("req_123456"), "req_123456")
        self.assertEqual(validate_request_id("custom-uuid-001"), "custom-uuid-001")
        self.assertEqual(validate_request_id("ABC_123-xyz"), "ABC_123-xyz")

        # Invalid cases
        self.assertIsNone(validate_request_id(None))
        self.assertIsNone(validate_request_id(""))
        self.assertIsNone(validate_request_id("   "))
        self.assertIsNone(validate_request_id("invalid spaces in id"))
        self.assertIsNone(validate_request_id("bad;chars!@#$%^&*()"))
        self.assertIsNone(validate_request_id("a" * 65))  # Exceeds 64 chars

    def test_contextvar_storage_and_clear(self):
        """Verifies contextvars correctly isolate correlation values."""
        self.assertIsNone(get_request_id())
        set_correlation_context(request_id="test_req_001", audit_id="audit_abc", worker_id="w1")

        ctx = get_correlation_context()
        self.assertEqual(ctx["request_id"], "test_req_001")
        self.assertEqual(ctx["audit_id"], "audit_abc")
        self.assertEqual(ctx["worker_id"], "w1")

        clear_correlation_context()
        self.assertIsNone(get_request_id())

    def test_http_response_generates_request_id_when_missing(self):
        """Verifies that an incoming request without X-Request-ID receives a generated one."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Request-ID", response.headers)
        req_id = response.headers["X-Request-ID"]
        self.assertTrue(req_id.startswith("req_"))

    def test_http_response_preserves_valid_request_id(self):
        """Verifies that an incoming request with valid X-Request-ID echoes it in response headers."""
        custom_id = "client-trace-777-xyz"
        response = self.client.get("/health", headers={"X-Request-ID": custom_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Request-ID"), custom_id)

    def test_http_response_replaces_invalid_request_id(self):
        """Verifies that an invalid client X-Request-ID is replaced by a safe generated ID."""
        invalid_id = "malicious;id with spaces and dangerous'quotes"
        response = self.client.get("/health", headers={"X-Request-ID": invalid_id})
        self.assertEqual(response.status_code, 200)
        returned_id = response.headers.get("X-Request-ID")
        self.assertNotEqual(returned_id, invalid_id)
        self.assertTrue(returned_id.startswith("req_"))

    def test_http_error_response_contains_request_id(self):
        """Verifies that 404 and other error responses also include X-Request-ID."""
        response = self.client.get("/non-existent-endpoint")
        self.assertEqual(response.status_code, 404)
        self.assertIn("X-Request-ID", response.headers)


if __name__ == "__main__":
    unittest.main()
