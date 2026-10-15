import unittest
from fastapi.testclient import TestClient
from backend.src.api.server import app

class TestSecurityHeaders(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_defense_in_depth_security_headers_present(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)

        # 1. Content-Type sniffing protection
        self.assertEqual(res.headers.get("x-content-type-options"), "nosniff")

        # 2. Clickjacking protection
        self.assertEqual(res.headers.get("x-frame-options"), "DENY")

        # 3. Referrer leak protection
        self.assertEqual(res.headers.get("referrer-policy"), "strict-origin-when-cross-origin")

        # 4. Content Security Policy
        self.assertEqual(res.headers.get("content-security-policy"), "default-src 'self'")

    def test_hsts_header_on_https_requests(self):
        # TestClient with base_url using https scheme
        https_client = TestClient(app, base_url="https://testserver")
        res = https_client.get("/health")
        self.assertEqual(res.status_code, 200)

        hsts = res.headers.get("strict-transport-security")
        self.assertIsNotNone(hsts)
        self.assertIn("max-age=31536000", hsts)
        self.assertIn("includeSubDomains", hsts)

    def test_hsts_not_added_to_plain_http(self):
        http_client = TestClient(app, base_url="http://testserver")
        res = http_client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.headers.get("strict-transport-security"))

if __name__ == "__main__":
    unittest.main()
