import unittest
import jwt
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.config import settings
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.models import User, UserRole
from backend.src.db.user_repository import UserRepository
from backend.src.services.auth_service import AuthService
from backend.src.security.passwords import hash_password
from backend.src.security.tokens import create_access_token

class TestAuthSecurity(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    # --- REGISTRATION SECURITY TESTS ---

    def test_registration_valid_payload(self):
        payload = {
            "email": "valid_user@brandguardian.ai",
            "password": "StrongPassword123!",
            "display_name": "Valid User"
        }
        res = self.client.post("/auth/register", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["email"], "valid_user@brandguardian.ai")
        self.assertEqual(data["role"], "USER")
        self.assertTrue(data["is_active"])
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)

    def test_registration_duplicate_email_rejected_409(self):
        payload = {
            "email": "duplicate@brandguardian.ai",
            "password": "InitialPassword123",
            "display_name": "User One"
        }
        res1 = self.client.post("/auth/register", json=payload)
        self.assertEqual(res1.status_code, 201)

        res2 = self.client.post("/auth/register", json=payload)
        self.assertEqual(res2.status_code, 409)
        self.assertIn("already exists", res2.json()["detail"].lower())

    def test_registration_invalid_email_format_rejected(self):
        invalid_emails = [
            "not-an-email",
            "user@",
            "@domain.com",
            "user@domain",
            "user space@domain.com"
        ]
        for bad_email in invalid_emails:
            payload = {
                "email": bad_email,
                "password": "Password123!",
                "display_name": "Bad Email"
            }
            res = self.client.post("/auth/register", json=payload)
            self.assertEqual(res.status_code, 422, f"Expected 422 for invalid email: {bad_email}")

    def test_registration_short_password_rejected(self):
        payload = {
            "email": "short_pw@brandguardian.ai",
            "password": "12345",  # Less than 6 characters
            "display_name": "Short PW User"
        }
        res = self.client.post("/auth/register", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_registration_missing_required_fields(self):
        cases = [
            {"password": "Password123!", "display_name": "No Email"},
            {"email": "no_pw@brandguardian.ai", "display_name": "No PW"},
            {"email": "no_name@brandguardian.ai", "password": "Password123!"}
        ]
        for payload in cases:
            res = self.client.post("/auth/register", json=payload)
            self.assertEqual(res.status_code, 422)

    # --- LOGIN SECURITY TESTS ---

    def test_login_success_with_valid_credentials(self):
        UserRepository.create_user(
            self.db,
            email="auth_user@brandguardian.ai",
            password_hash=hash_password("CorrectPassword123!"),
            display_name="Auth User"
        )
        res = self.client.post("/auth/login", json={
            "email": "auth_user@brandguardian.ai",
            "password": "CorrectPassword123!"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_login_incorrect_password_rejected_401(self):
        UserRepository.create_user(
            self.db,
            email="victim@brandguardian.ai",
            password_hash=hash_password("RealPassword123!"),
            display_name="Victim"
        )
        res = self.client.post("/auth/login", json={
            "email": "victim@brandguardian.ai",
            "password": "WrongPasswordAttempt"
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Incorrect email or password", res.json()["detail"])

    def test_login_unknown_email_rejected_generic_message(self):
        # Must not reveal whether email exists (prevents account enumeration)
        res = self.client.post("/auth/login", json={
            "email": "does_not_exist@brandguardian.ai",
            "password": "SomePassword123"
        })
        self.assertEqual(res.status_code, 401)
        self.assertIn("Incorrect email or password", res.json()["detail"])

    def test_login_inactive_user_rejected_403(self):
        UserRepository.create_user(
            self.db,
            email="disabled@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="Disabled User",
            is_active=False
        )
        res = self.client.post("/auth/login", json={
            "email": "disabled@brandguardian.ai",
            "password": "Pass123456"
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("inactive", res.json()["detail"].lower())

    def test_login_missing_fields_rejected_422(self):
        res1 = self.client.post("/auth/login", json={"email": "only_email@test.com"})
        self.assertEqual(res1.status_code, 422)

        res2 = self.client.post("/auth/login", json={"password": "only_password"})
        self.assertEqual(res2.status_code, 422)

    # --- JWT BEARER SECURITY TESTS ---

    def test_jwt_missing_authorization_header(self):
        res = self.client.get("/auth/me")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.headers.get("WWW-Authenticate"), "Bearer")

    def test_jwt_malformed_bearer_token(self):
        malformed_headers = [
            "Bearer",
            "Bearer ",
            "Bearer invalid.token",
            "Basic dXNlcjpwYXNz",
            "Token 12345"
        ]
        for header_val in malformed_headers:
            res = self.client.get("/auth/me", headers={"Authorization": header_val})
            self.assertEqual(res.status_code, 401)

    def test_jwt_invalid_signature_rejected(self):
        user = UserRepository.create_user(
            self.db,
            email="sig_test@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="Sig Test"
        )
        # Sign with an arbitrary attacker key
        fake_token = jwt.encode(
            {"sub": user.id, "email": user.email, "role": "USER"},
            "attacker-compromised-secret-key-xyz-1234567890",
            algorithm="HS256"
        )
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("Could not validate credentials", res.json()["detail"])

    def test_jwt_expired_token_rejected_401(self):
        user = UserRepository.create_user(
            self.db,
            email="expired_jwt@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="Expired User"
        )
        expired_token = create_access_token(
            {"sub": user.id, "email": user.email, "role": "USER"},
            expires_delta=timedelta(seconds=-30)
        )
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("expired", res.json()["detail"].lower())

    def test_jwt_missing_sub_claim_rejected(self):
        # Token missing 'sub'
        bad_token = jwt.encode(
            {"email": "no_sub@brandguardian.ai", "role": "USER"},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
        self.assertEqual(res.status_code, 401)

    def test_jwt_nonexistent_user_sub_rejected(self):
        ghost_token = jwt.encode(
            {"sub": "non-existent-user-uuid-9999", "email": "ghost@brandguardian.ai", "role": "USER"},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {ghost_token}"})
        self.assertEqual(res.status_code, 401)

    def test_jwt_inactive_user_with_valid_jwt_rejected_403(self):
        inactive_user = UserRepository.create_user(
            self.db,
            email="deactivated@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="Deactivated",
            is_active=False
        )
        valid_token = AuthService.create_token_for_user(inactive_user)
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {valid_token}"})
        self.assertEqual(res.status_code, 403)
        self.assertIn("inactive", res.json()["detail"].lower())

    def test_jwt_invalid_algorithm_none_rejected(self):
        # Attempt 'none' algorithm bypass
        token = jwt.encode(
            {"sub": "any-id", "email": "test@test.com", "role": "USER"},
            "",
            algorithm="none"
        )
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 401)

    def test_jwt_server_side_role_authoritative_over_token_claim(self):
        """
        Verify that even if an attacker tampers with or forges a JWT claiming role="ADMIN",
        the server-side database record is authoritative and denies admin access.
        """
        normal_user = UserRepository.create_user(
            self.db,
            email="normal_user@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="Normal User",
            role=UserRole.USER
        )
        # Create token with forged role="ADMIN" claim using legitimate JWT key
        forged_admin_token = jwt.encode(
            {"sub": normal_user.id, "email": normal_user.email, "role": "ADMIN"},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        # Attempt to access an admin-only endpoint: POST /api/evaluations/runs with is_baseline=True
        res = self.client.post(
            "/api/evaluations/runs",
            headers={"Authorization": f"Bearer {forged_admin_token}"},
            json={"is_baseline": True}
        )
        # Because the DB user has role=USER, require_admin looks up DB and returns 403
        self.assertEqual(res.status_code, 403)
        self.assertIn("Administrative privileges required", res.json()["detail"])

if __name__ == "__main__":
    unittest.main()
