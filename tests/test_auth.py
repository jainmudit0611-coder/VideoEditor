import unittest
from datetime import timedelta
from fastapi.testclient import TestClient
from fastapi import Depends

from backend.src.api.server import app
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.models import User, UserRole
from backend.src.db.user_repository import UserRepository
from backend.src.services.auth_service import AuthService
from backend.src.security.passwords import hash_password, verify_password
from backend.src.security.tokens import create_access_token
from backend.src.api.auth_dependencies import require_admin, get_current_active_user

# Admin-only test endpoint to verify require_admin dependency
@app.get("/test/admin-only")
def admin_only_endpoint(admin: User = Depends(require_admin)):
    return {"status": "admin_granted", "admin_id": admin.id}

class TestAuthModule(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_password_hashing_and_verification(self):
        pw = "SuperSecretPassword123!"
        hashed = hash_password(pw)
        self.assertNotEqual(pw, hashed)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))
        self.assertTrue(verify_password(pw, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_user_registration_success(self):
        payload = {
            "email": "auditor@brandguardian.ai",
            "password": "SecurePassword987",
            "display_name": "Compliance Officer"
        }
        resp = self.client.post("/auth/register", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["email"], "auditor@brandguardian.ai")
        self.assertEqual(data["display_name"], "Compliance Officer")
        self.assertEqual(data["role"], "USER")
        self.assertTrue(data["is_active"])
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)

        # Verify DB persistence and password hashing
        user = UserRepository.get_by_email(self.db, "auditor@brandguardian.ai")
        self.assertIsNotNone(user)
        self.assertTrue(verify_password("SecurePassword987", user.password_hash))

    def test_duplicate_email_registration_rejected(self):
        payload = {
            "email": "duplicate@brandguardian.ai",
            "password": "InitialPassword123",
            "display_name": "First User"
        }
        resp1 = self.client.post("/auth/register", json=payload)
        self.assertEqual(resp1.status_code, 201)

        # Second registration with same email
        resp2 = self.client.post("/auth/register", json=payload)
        self.assertEqual(resp2.status_code, 409)
        self.assertIn("already exists", resp2.json()["detail"])

    def test_login_valid_credentials(self):
        # Register user
        UserRepository.create_user(
            self.db,
            email="login_test@brandguardian.ai",
            password_hash=hash_password("ValidPass123!"),
            display_name="Login Test User"
        )

        resp = self.client.post("/auth/login", json={
            "email": "login_test@brandguardian.ai",
            "password": "ValidPass123!"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_login_invalid_password(self):
        UserRepository.create_user(
            self.db,
            email="invalid_pw@brandguardian.ai",
            password_hash=hash_password("RealPass123!"),
            display_name="Invalid PW User"
        )

        resp = self.client.post("/auth/login", json={
            "email": "invalid_pw@brandguardian.ai",
            "password": "WrongPassword!"
        })
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Incorrect email or password", resp.json()["detail"])

    def test_login_nonexistent_account(self):
        resp = self.client.post("/auth/login", json={
            "email": "ghost@brandguardian.ai",
            "password": "GhostPassword"
        })
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Incorrect email or password", resp.json()["detail"])

    def test_get_current_user_me_profile(self):
        user = UserRepository.create_user(
            self.db,
            email="me_profile@brandguardian.ai",
            password_hash=hash_password("MyPass123"),
            display_name="Profile User"
        )
        token = AuthService.create_token_for_user(user)

        resp = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], user.id)
        self.assertEqual(data["email"], "me_profile@brandguardian.ai")
        self.assertEqual(data["display_name"], "Profile User")
        self.assertNotIn("password_hash", data)

    def test_missing_and_invalid_tokens(self):
        # Missing token
        resp_missing = self.client.get("/auth/me")
        self.assertEqual(resp_missing.status_code, 401)

        # Malformed token
        resp_invalid = self.client.get("/auth/me", headers={"Authorization": "Bearer bad.token.here"})
        self.assertEqual(resp_invalid.status_code, 401)

    def test_expired_token_rejected(self):
        user = UserRepository.create_user(
            self.db,
            email="expired@brandguardian.ai",
            password_hash=hash_password("Pass123"),
            display_name="Expired User"
        )
        expired_token = create_access_token(
            {"sub": user.id, "email": user.email, "role": "USER"},
            expires_delta=timedelta(seconds=-10)
        )
        resp = self.client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(resp.status_code, 401)
        self.assertIn("expired", resp.json()["detail"].lower())

    def test_inactive_user_rejected(self):
        inactive_user = UserRepository.create_user(
            self.db,
            email="inactive@brandguardian.ai",
            password_hash=hash_password("Pass123"),
            display_name="Inactive User",
            is_active=False
        )
        token = AuthService.create_token_for_user(inactive_user)
        resp = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 403)
        self.assertIn("inactive", resp.json()["detail"].lower())

    def test_admin_role_authorization(self):
        # 1. Normal user should receive 403 on admin-only endpoint
        normal_user = UserRepository.create_user(
            self.db,
            email="regular@brandguardian.ai",
            password_hash=hash_password("Pass123"),
            display_name="Regular User",
            role=UserRole.USER
        )
        normal_token = AuthService.create_token_for_user(normal_user)
        resp_normal = self.client.get("/test/admin-only", headers={"Authorization": f"Bearer {normal_token}"})
        self.assertEqual(resp_normal.status_code, 403)
        self.assertIn("Administrative privileges required", resp_normal.json()["detail"])

        # 2. Admin user should succeed
        admin_user = UserRepository.create_user(
            self.db,
            email="admin@brandguardian.ai",
            password_hash=hash_password("AdminPass123"),
            display_name="Lead Admin",
            role=UserRole.ADMIN
        )
        admin_token = AuthService.create_token_for_user(admin_user)
        resp_admin = self.client.get("/test/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(resp_admin.status_code, 200)
        self.assertEqual(resp_admin.json()["status"], "admin_granted")
        self.assertEqual(resp_admin.json()["admin_id"], admin_user.id)

if __name__ == "__main__":
    unittest.main()
