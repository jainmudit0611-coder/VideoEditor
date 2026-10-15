import unittest
import jwt
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.config import settings
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.models import User, UserRole
from backend.src.db.user_repository import UserRepository
from backend.src.services.auth_service import AuthService
from backend.src.security.passwords import hash_password

class TestRoleEscalationSecurity(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

        self.normal_user = UserRepository.create_user(
            self.db,
            email="normal_officer@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="Normal Officer",
            role=UserRole.USER
        )
        self.normal_token = AuthService.create_token_for_user(self.normal_user)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_registration_payload_cannot_grant_admin_role(self):
        # Attempt to register with role="ADMIN"
        res = self.client.post("/auth/register", json={
            "email": "hacker@brandguardian.ai",
            "password": "Password123!",
            "display_name": "Hacker",
            "role": "ADMIN"
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["role"], "USER")

        # Verify DB persisted role is USER
        db_user = UserRepository.get_by_email(self.db, "hacker@brandguardian.ai")
        self.assertEqual(db_user.role, UserRole.USER)

    def test_login_payload_cannot_alter_role(self):
        res = self.client.post("/auth/login", json={
            "email": "normal_officer@brandguardian.ai",
            "password": "Pass123456",
            "role": "ADMIN"
        })
        self.assertEqual(res.status_code, 200)
        token = res.json()["access_token"]
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        self.assertEqual(payload.get("role"), "USER")

    def test_forged_jwt_role_claim_rejected_by_authoritative_db(self):
        """
        Token forged with role="ADMIN" but associated with a USER sub ID must be denied.
        """
        forged_token = jwt.encode(
            {"sub": self.normal_user.id, "email": self.normal_user.email, "role": "ADMIN"},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        res = self.client.post(
            "/api/evaluations/runs",
            headers={"Authorization": f"Bearer {forged_token}"},
            json={"is_baseline": True}
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Administrative privileges required", res.json()["detail"])

    def test_query_parameter_role_escalation_ignored(self):
        # Pass ?role=ADMIN or ?is_admin=true to create baseline
        res = self.client.post(
            "/api/evaluations/runs?role=ADMIN&is_admin=true",
            headers={"Authorization": f"Bearer {self.normal_token}"},
            json={"is_baseline": True}
        )
        self.assertEqual(res.status_code, 403)

if __name__ == "__main__":
    unittest.main()
