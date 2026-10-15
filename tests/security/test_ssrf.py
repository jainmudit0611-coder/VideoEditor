import unittest
import socket
from unittest.mock import patch
from fastapi import HTTPException

from backend.src.api.server import validate_video_url, _is_ip_restricted
import ipaddress

class TestSSRFSecurity(unittest.TestCase):

    def test_restricted_ip_helper_ranges(self):
        # IPv4
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("127.0.0.1")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("0.0.0.0")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("10.0.0.1")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("172.16.0.1")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("172.31.255.254")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("192.168.1.1")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("169.254.169.254")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("224.0.0.1")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("240.0.0.1")))

        # IPv6
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("::1")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("::")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("fe80::1")))
        self.assertTrue(_is_ip_restricted(ipaddress.ip_address("fc00::1")))

        # Public IPs should NOT be restricted
        self.assertFalse(_is_ip_restricted(ipaddress.ip_address("8.8.8.8")))
        self.assertFalse(_is_ip_restricted(ipaddress.ip_address("1.1.1.1")))
        self.assertFalse(_is_ip_restricted(ipaddress.ip_address("142.250.190.46")))

    def test_ssrf_ipv4_literals_blocked(self):
        blocked_urls = [
            "http://127.0.0.1/video.mp4",
            "http://127.0.0.1:8080/video.mp4",
            "http://0.0.0.0/test.mp4",
            "http://10.0.0.1/admin.mp4",
            "http://172.16.0.1/internal.mp4",
            "http://172.31.255.254/video.mp4",
            "http://192.168.1.1/router.mp4",
            "http://169.254.169.254/latest/meta-data/",
            "http://224.0.0.1/stream.mp4",
            "http://240.0.0.1/video.mp4"
        ]
        for url in blocked_urls:
            with self.assertRaises(HTTPException) as ctx:
                validate_video_url(url)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("restricted network addresses", ctx.exception.detail)

    def test_ssrf_ipv6_literals_blocked(self):
        blocked_ipv6 = [
            "http://[::1]/video.mp4",
            "http://[::]/video.mp4",
            "http://[fe80::1]/video.mp4",
            "http://[fc00::1]/video.mp4"
        ]
        for url in blocked_ipv6:
            with self.assertRaises(HTTPException) as ctx:
                validate_video_url(url)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("restricted network addresses", ctx.exception.detail)

    def test_ssrf_named_internal_hosts_blocked(self):
        named_hosts = [
            "http://localhost/video.mp4",
            "http://localhost:5000/api",
            "http://0.0.0.0/video",
            "http://metadata.google.internal/computeMetadata/v1/"
        ]
        for url in named_hosts:
            with self.assertRaises(HTTPException) as ctx:
                validate_video_url(url)
            self.assertEqual(ctx.exception.status_code, 400)

    def test_ssrf_unsupported_protocols_blocked(self):
        unsupported = [
            "ftp://files.example.com/video.mp4",
            "file:///etc/passwd",
            "file:///C:/Windows/win.ini",
            "gopher://evil.com/video",
            "data:text/plain;base64,SGVsbG8=",
            "javascript:alert(1)"
        ]
        for url in unsupported:
            with self.assertRaises(HTTPException) as ctx:
                validate_video_url(url)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("protocol", ctx.exception.detail.lower())

    def test_ssrf_malformed_urls_blocked(self):
        malformed = [
            "",
            "   ",
            "not a url",
            "://missing-scheme.com",
            "http://",
            "https://"
        ]
        for url in malformed:
            with self.assertRaises(HTTPException) as ctx:
                validate_video_url(url)
            self.assertEqual(ctx.exception.status_code, 400)

    def test_dns_rebinding_multihomed_resolution_checks_all_addresses(self):
        """
        Verify that if DNS resolution returns multiple IP addresses (e.g. one public, one private),
        the validator checks every address and blocks the request.
        """
        # Mock getaddrinfo returning one public IP and one internal RFC1918 IP
        mock_addrinfo = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.100", 80))
        ]

        with patch("socket.getaddrinfo", return_value=mock_addrinfo):
            with self.assertRaises(HTTPException) as ctx:
                validate_video_url("https://rebound-domain.example.com/video.mp4")
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("restricted network addresses", ctx.exception.detail)

    def test_dns_rebinding_purely_private_resolution_blocked(self):
        mock_addrinfo = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.50.1", 80))
        ]
        with patch("socket.getaddrinfo", return_value=mock_addrinfo):
            with self.assertRaises(HTTPException) as ctx:
                validate_video_url("https://internal-service.mycompany.net/video.mp4")
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("restricted network addresses", ctx.exception.detail)

    def test_valid_youtube_video_url_passes(self):
        # Should not raise exception
        validate_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

if __name__ == "__main__":
    unittest.main()
