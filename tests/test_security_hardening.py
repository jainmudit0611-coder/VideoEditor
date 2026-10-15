import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.src.api.server import app, validate_video_url

class TestSecurityHardening(unittest.TestCase):
    """
    Test suite for Phase 5.5:
    - HTTP Security Headers middleware
    - Explicit CORS configuration
    - SSRF prevention (RFC 1918, 172.16.0.0/12, IPv6, cloud metadata, DNS rebinding)
    """

    def setUp(self):
        self.client = TestClient(app)

    def test_security_headers_present(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)

        # 1. X-Content-Type-Options
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")

        # 2. X-Frame-Options
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")

        # 3. Referrer-Policy
        self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

        # 4. Content-Security-Policy
        self.assertIn("default-src 'self'", resp.headers.get("Content-Security-Policy", ""))

    def test_cors_explicit_origins(self):
        # 1. Allowed origin (http://localhost:4200)
        resp_allowed = self.client.get(
            "/health",
            headers={"Origin": "http://localhost:4200"}
        )
        self.assertEqual(resp_allowed.status_code, 200)
        self.assertEqual(resp_allowed.headers.get("access-control-allow-origin"), "http://localhost:4200")
        self.assertEqual(resp_allowed.headers.get("access-control-allow-credentials"), "true")

        # 2. Disallowed origin (http://malicious-site.com)
        resp_disallowed = self.client.get(
            "/health",
            headers={"Origin": "http://malicious-site.com"}
        )
        self.assertEqual(resp_disallowed.status_code, 200)
        self.assertNotEqual(resp_disallowed.headers.get("access-control-allow-origin"), "http://malicious-site.com")

    def test_ssrf_validation_blocked_ips(self):
        blocked_targets = [
            "http://127.0.0.1/evil",
            "http://127.0.0.2:8080/evil",
            "http://localhost:8000/evil",
            "http://10.0.0.1/secret",
            "http://172.16.0.1/docker-internal",
            "http://172.31.255.255/vpc",
            "http://192.168.1.1/router",
            "http://169.254.169.254/latest/meta-data/",
            "http://0.0.0.0:8000/",
            "http://[::1]/internal",
            "http://[fe80::1]/link-local",
            "http://metadata.google.internal/computeMetadata/v1/",
            "file:///etc/passwd",
            "ftp://fileserver/data",
        ]

        for target in blocked_targets:
            with self.subTest(target=target):
                with self.assertRaises(HTTPException) as cm:
                    validate_video_url(target)
                self.assertEqual(cm.exception.status_code, 400)
                self.assertTrue(
                    "restricted" in cm.exception.detail.lower()
                    or "invalid url protocol" in cm.exception.detail.lower()
                    or "not allowed" in cm.exception.detail.lower()
                )

    def test_ssrf_dns_rebinding_prevention(self):
        # Mock getaddrinfo returning a private IP for an arbitrary domain
        fake_resolved = [(2, 1, 0, "", ("169.254.169.254", 80))]
        with patch("socket.getaddrinfo", return_value=fake_resolved):
            with self.assertRaises(HTTPException) as cm:
                validate_video_url("http://rebound-evil-domain.com/video.mp4")
            self.assertEqual(cm.exception.status_code, 400)
            self.assertIn("restricted", cm.exception.detail.lower())

    def test_ssrf_public_urls_allowed(self):
        # Legitimate public YouTube URLs must be permitted
        public_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://vimeo.com/12345678",
        ]
        for url in public_urls:
            with self.subTest(url=url):
                try:
                    validate_video_url(url)
                except HTTPException as e:
                    self.fail(f"Public URL '{url}' was unexpectedly blocked: {e.detail}")

if __name__ == "__main__":
    unittest.main()
