import unittest
from backend.src.config import Settings

class TestConfigurationSecurity(unittest.TestCase):

    def test_development_mode_allows_dev_defaults(self):
        cfg = Settings(
            ENVIRONMENT="development",
            JWT_SECRET_KEY="brand-guardian-dev-insecure-secret-key-change-in-prod",
            DATABASE_URL="sqlite:///./brand_guardian.db",
            REDIS_REQUIRED=False,
            CORS_ORIGINS="http://localhost:4200",
            DEBUG=False
        )
        res = cfg.validate_production_configuration(raise_on_error=False)
        self.assertEqual(res["status"], "VALID")
        self.assertFalse(res["is_production"])
        self.assertEqual(len(res["issues"]), 0)

    def test_production_rejects_default_insecure_jwt_secret(self):
        cfg = Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="brand-guardian-dev-insecure-secret-key-change-in-prod",
            DATABASE_URL="postgresql://user:pass@localhost:5432/brand_guardian",
            REDIS_REQUIRED=True,
            CORS_ORIGINS="https://app.brandguardian.ai",
            DEBUG=False
        )
        res = cfg.validate_production_configuration(raise_on_error=False)
        self.assertEqual(res["status"], "INVALID")
        self.assertTrue(any("JWT_SECRET_KEY" in issue for issue in res["issues"]))

        with self.assertRaises(ValueError):
            cfg.validate_production_configuration(raise_on_error=True)

    def test_production_rejects_short_jwt_secret(self):
        cfg = Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="short-secret-key-12345",  # < 32 characters
            DATABASE_URL="postgresql://user:pass@localhost:5432/brand_guardian",
            REDIS_REQUIRED=True,
            CORS_ORIGINS="https://app.brandguardian.ai",
            DEBUG=False
        )
        res = cfg.validate_production_configuration(raise_on_error=False)
        self.assertEqual(res["status"], "INVALID")
        self.assertTrue(any("at least 32 characters" in issue for issue in res["issues"]))

    def test_production_rejects_redis_required_false(self):
        cfg = Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="a-very-secure-random-32-byte-production-key-value",
            DATABASE_URL="postgresql://user:pass@localhost:5432/brand_guardian",
            REDIS_REQUIRED=False,  # Unacceptable in prod to silently drop to memory queue
            CORS_ORIGINS="https://app.brandguardian.ai",
            DEBUG=False
        )
        res = cfg.validate_production_configuration(raise_on_error=False)
        self.assertEqual(res["status"], "INVALID")
        self.assertTrue(any("REDIS_REQUIRED=true" in issue for issue in res["issues"]))

    def test_production_rejects_wildcard_cors(self):
        cfg = Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="a-very-secure-random-32-byte-production-key-value",
            DATABASE_URL="postgresql://user:pass@localhost:5432/brand_guardian",
            REDIS_REQUIRED=True,
            CORS_ORIGINS="*",
            DEBUG=False
        )
        res = cfg.validate_production_configuration(raise_on_error=False)
        self.assertEqual(res["status"], "INVALID")
        self.assertTrue(any("wildcard" in issue.lower() for issue in res["issues"]))

    def test_production_rejects_debug_mode_enabled(self):
        cfg = Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="a-very-secure-random-32-byte-production-key-value",
            DATABASE_URL="postgresql://user:pass@localhost:5432/brand_guardian",
            REDIS_REQUIRED=True,
            CORS_ORIGINS="https://app.brandguardian.ai",
            DEBUG=True
        )
        res = cfg.validate_production_configuration(raise_on_error=False)
        self.assertEqual(res["status"], "INVALID")
        self.assertTrue(any("DEBUG=False" in issue for issue in res["issues"]))

    def test_production_accepts_hardened_settings(self):
        cfg = Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="a-very-secure-random-32-byte-production-key-value",
            DATABASE_URL="postgresql://user:pass@localhost:5432/brand_guardian",
            REDIS_REQUIRED=True,
            CORS_ORIGINS="https://app.brandguardian.ai,https://admin.brandguardian.ai",
            DEBUG=False
        )
        res = cfg.validate_production_configuration(raise_on_error=True)
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(len(res["issues"]), 0)

if __name__ == "__main__":
    unittest.main()
