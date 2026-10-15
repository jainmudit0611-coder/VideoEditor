import json
import logging
import unittest
from io import StringIO

from backend.src.observability.redaction import (
    redact_sensitive_data,
    sanitize_url,
    SensitiveDataRedactionFilter,
)
from backend.src.observability.structured_logger import (
    StructuredJsonFormatter,
    get_logger,
)


class TestLogRedaction(unittest.TestCase):
    """
    Tests security redaction utilities and logging filter to ensure zero secrets,
    passwords, tokens, or credentials appear in application logs.
    """

    def setUp(self):
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setFormatter(StructuredJsonFormatter())
        self.test_logger = get_logger("test-redaction-logger")
        self.test_logger.setLevel(logging.INFO)
        self.test_logger.addHandler(self.handler)

    def tearDown(self):
        self.test_logger.removeHandler(self.handler)

    def _get_last_log_json(self):
        output = self.log_stream.getvalue().strip()
        lines = [line for line in output.split("\n") if line.strip()]
        self.assertTrue(len(lines) > 0, "No log lines recorded")
        return json.loads(lines[-1])

    def test_redact_bearer_token_string(self):
        """Verifies Bearer tokens in strings are replaced with [REDACTED]."""
        raw = "Header Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID"
        redacted = redact_sensitive_data(raw)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", redacted)
        self.assertIn("Bearer [REDACTED]", redacted)

    def test_redact_standalone_jwt(self):
        """Verifies raw JWT tokens in log strings are scrubbed."""
        raw = "User token is eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozG4"
        redacted = redact_sensitive_data(raw)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", redacted)
        self.assertIn("[REDACTED_JWT]", redacted)

    def test_redact_dict_sensitive_keys(self):
        """Verifies passwords, hashes, and secrets in dictionaries are masked."""
        payload = {
            "email": "user@example.com",
            "password": "SuperSecretPassword123!",
            "password_hash": "$2b$12$eX4mpleHashString...",
            "jwt_secret_key": "insecure-key-xyz",
            "api_key": "azure-key-secret-999",
            "nested": {
                "access_token": "token-12345",
                "normal_field": "visible_value"
            }
        }
        cleaned = redact_sensitive_data(payload)

        self.assertEqual(cleaned["password"], "[REDACTED]")
        self.assertEqual(cleaned["password_hash"], "[REDACTED]")
        self.assertEqual(cleaned["jwt_secret_key"], "[REDACTED]")
        self.assertEqual(cleaned["api_key"], "[REDACTED]")
        self.assertEqual(cleaned["nested"]["access_token"], "[REDACTED]")
        self.assertEqual(cleaned["nested"]["normal_field"], "visible_value")
        self.assertEqual(cleaned["email"], "user@example.com")

    def test_sanitize_connection_strings(self):
        """Verifies database and Redis connection passwords are redacted."""
        db_url = "postgresql://dbuser:superSecretPass@localhost:5432/brand_guardian"
        redis_url = "redis://:redisSecretPassword@redis-host:6379/0"

        clean_db = sanitize_url(db_url)
        clean_redis = sanitize_url(redis_url)

        self.assertNotIn("superSecretPass", clean_db)
        self.assertIn("dbuser:[REDACTED]@", clean_db)

        self.assertNotIn("redisSecretPassword", clean_redis)
        self.assertIn("redis://:[REDACTED]@", clean_redis)

    def test_sanitize_url_query_parameters(self):
        """Verifies sensitive query parameters in video or blob URLs are redacted."""
        url = "https://storage.azure.com/videos/audit.mp4?sig=secretSignature123&token=abc789&view=true"
        sanitized = sanitize_url(url)

        self.assertNotIn("secretSignature123", sanitized)
        self.assertNotIn("abc789", sanitized)
        self.assertIn("view=true", sanitized)
        self.assertIn("sig=%5BREDACTED%5D", sanitized)

    def test_logging_filter_scrubs_log_emission(self):
        """Verifies logging filter prevents sensitive arguments from reaching JSON output."""
        self.test_logger.info(
            "User login attempt with password: %s",
            "SensitivePassword999!"
        )
        data = self._get_last_log_json()

        self.assertNotIn("SensitivePassword999!", data["message"])
        self.assertNotIn("SensitivePassword999!", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
