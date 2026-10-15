import unittest
from fastapi.testclient import TestClient
from backend.src.api.server import app
from backend.src.config import settings

class TestCORSSecurity(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_approved_origin_receives_cors_headers(self):
        res = self.client.get(
            "/health",
            headers={"Origin": "http://localhost:4200"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "http://localhost:4200")
        self.assertEqual(res.headers.get("access-control-allow-credentials"), "true")

    def test_secondary_approved_origin_receives_cors_headers(self):
        res = self.client.get(
            "/health",
            headers={"Origin": "http://127.0.0.1:4200"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "http://127.0.0.1:4200")
        self.assertEqual(res.headers.get("access-control-allow-credentials"), "true")

    def test_unapproved_origin_denied_cors_headers(self):
        unapproved = ["http://evil.com", "https://attacker.org", "http://localhost:3000"]
        for origin in unapproved:
            res = self.client.get(
                "/health",
                headers={"Origin": origin}
            )
            # Unapproved origin must not receive Access-Control-Allow-Origin
            self.assertNotEqual(res.headers.get("access-control-allow-origin"), origin)

    def test_preflight_options_approved_origin(self):
        res = self.client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:4200",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization,Content-Type"
            }
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "http://localhost:4200")
        allowed_methods = res.headers.get("access-control-allow-methods", "")
        self.assertIn("POST", allowed_methods)

    def test_preflight_options_unapproved_origin(self):
        res = self.client.options(
            "/auth/login",
            headers={
                "Origin": "http://malicious.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization,Content-Type"
            }
        )
        self.assertNotEqual(res.headers.get("access-control-allow-origin"), "http://malicious.com")

    def test_no_wildcard_cors_with_credentials(self):
        origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
        self.assertNotIn("*", origins, "CORS_ORIGINS must not include wildcard '*' when credentials are true.")

if __name__ == "__main__":
    unittest.main()
