import json
import unittest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.observability.errors import (
    ErrorCode,
    SAFE_ERROR_MESSAGES,
    get_safe_error_message,
    create_safe_error_response,
)


class TestErrorTaxonomy(unittest.TestCase):
    """
    Tests the operational error code taxonomy, safe user message guarantees,
    and FastAPI global exception handling.
    """

    def setUp(self):
        self.client = TestClient(app)

    def test_all_error_codes_have_safe_messages(self):
        """Verifies every defined ErrorCode has an associated user-safe message."""
        for code in ErrorCode:
            self.assertIn(code, SAFE_ERROR_MESSAGES)
            msg = get_safe_error_message(code)
            self.assertIsInstance(msg, str)
            self.assertTrue(len(msg) > 10)

    def test_safe_messages_do_not_leak_secrets_or_infrastructure(self):
        """Guarantees error messages contain no stack traces, IPs, DB strings, or secrets."""
        forbidden_terms = [
            "traceback",
            "password",
            "select",
            "from",
            "redis://",
            "postgres",
            "127.0.0.1",
            "localhost",
            "exception",
            "sqlite",
        ]
        for code, msg in SAFE_ERROR_MESSAGES.items():
            msg_lower = msg.lower()
            for term in forbidden_terms:
                self.assertNotIn(
                    term,
                    msg_lower,
                    f"Safe message for {code} contained forbidden keyword: {term}"
                )

    def test_create_safe_error_response_structure(self):
        """Verifies JSONResponse formatting with error_code and X-Request-ID header."""
        resp = create_safe_error_response(
            error_code=ErrorCode.DATABASE_ERROR,
            request_id="req_test_db_err",
            status_code=500
        )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.headers.get("X-Request-ID"), "req_test_db_err")

        body = json.loads(resp.body.decode("utf-8"))
        self.assertEqual(body.get("error_code"), "DATABASE_ERROR")
        self.assertEqual(body.get("request_id"), "req_test_db_err")
        self.assertIn("database error", body.get("detail", "").lower())

    def test_fastapi_http_exception_handling_preserves_request_id(self):
        """Verifies 400 invalid input exceptions return safe responses with X-Request-ID."""
        # Post invalid payload without auth to check 401 or invalid URL
        response = self.client.post("/audits", json={"video_url": "invalid-format"})
        # Should return 401 (unauthenticated) or 400
        self.assertIn(response.status_code, [400, 401])
        self.assertIn("X-Request-ID", response.headers)


if __name__ == "__main__":
    unittest.main()
