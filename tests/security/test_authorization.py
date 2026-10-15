import unittest
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.models import User, UserRole, AuditStatus, AuditJob
from backend.src.db.user_repository import UserRepository
from backend.src.db.repositories import AuditRepository
from backend.src.services.auth_service import AuthService
from backend.src.security.passwords import hash_password

class TestAuthorizationAndIDOR(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

        # Ensure clean state across tests
        self.db.query(AuditJob).delete()
        self.db.query(User).delete()
        self.db.commit()

        # Create User A
        self.user_a = UserRepository.create_user(
            self.db,
            email="auth_sec_user_a@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="User A",
            role=UserRole.USER
        )
        self.token_a = AuthService.create_token_for_user(self.user_a)

        # Create User B
        self.user_b = UserRepository.create_user(
            self.db,
            email="auth_sec_user_b@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="User B",
            role=UserRole.USER
        )
        self.token_b = AuthService.create_token_for_user(self.user_b)

        # Create Admin
        self.admin = UserRepository.create_user(
            self.db,
            email="auth_sec_admin@brandguardian.ai",
            password_hash=hash_password("AdminPass123!"),
            display_name="Admin Sec",
            role=UserRole.ADMIN
        )
        self.token_admin = AuthService.create_token_for_user(self.admin)

        # Create Audit owned by User A
        self.audit_a = AuditRepository.create_audit(
            self.db,
            video_url="https://www.youtube.com/watch?v=user_a_video",
            created_by=self.user_a.id
        )


    def tearDown(self):
        try:
            self.db.query(AuditJob).delete()
            self.db.query(User).delete()
            self.db.commit()
        except Exception:
            pass
        self.db.close()
        Base.metadata.drop_all(bind=engine)


    def test_idor_get_audit_details_denied_for_other_user(self):
        # User A can access own audit
        res_a = self.client.get(
            f"/audits/{self.audit_a.id}",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res_a.status_code, 200)

        # User B cannot access User A's audit (returns 404 to avoid leaking existence)
        res_b = self.client.get(
            f"/audits/{self.audit_a.id}",
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res_b.status_code, 404)
        self.assertIn("not found", res_b.json()["detail"].lower())

    def test_idor_get_audit_status_denied_for_other_user(self):
        res = self.client.get(
            f"/audits/{self.audit_a.id}/status",
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res.status_code, 404)

    def test_idor_get_audit_report_denied_for_other_user(self):
        AuditRepository.save_result(
            self.db,
            audit_id=self.audit_a.id,
            result={"compliance_status": "PASS", "findings": []}
        )
        res = self.client.get(
            f"/audits/{self.audit_a.id}/report",
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res.status_code, 404)

    def test_idor_cancel_audit_denied_for_other_user(self):
        res = self.client.post(
            f"/audits/{self.audit_a.id}/cancel",
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res.status_code, 404)

    def test_audit_listing_isolates_private_records(self):
        # Create audit for User B
        audit_b = AuditRepository.create_audit(
            self.db,
            video_url="https://www.youtube.com/watch?v=user_b_video",
            created_by=self.user_b.id
        )

        # User A listing only shows Audit A
        res_a = self.client.get(
            "/audits",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res_a.status_code, 200)
        jobs_a = res_a.json()
        ids_a = [j["audit_id"] for j in jobs_a]
        self.assertIn(self.audit_a.id, ids_a)
        self.assertNotIn(audit_b.id, ids_a)

        # User B listing only shows Audit B
        res_b = self.client.get(
            "/audits",
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res_b.status_code, 200)
        jobs_b = res_b.json()
        ids_b = [j["audit_id"] for j in jobs_b]
        self.assertNotIn(self.audit_a.id, ids_b)
        self.assertIn(audit_b.id, ids_b)

    def test_forged_ownership_payload_rejected_in_favor_of_jwt(self):
        """
        Verify that passing 'created_by' in request body cannot spoof audit ownership.
        """
        res = self.client.post(
            "/audits",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={
                "video_url": "https://www.youtube.com/watch?v=forged_ownership",
                "created_by": self.user_a.id  # Attempt to spoof ownership as User A
            }
        )
        self.assertEqual(res.status_code, 202)
        audit_id = res.json()["audit_id"]

        # Verify DB record is owned by User B, not User A
        job = AuditRepository.get_audit(self.db, audit_id)
        self.assertIsNotNone(job)
        self.assertEqual(job.created_by, self.user_b.id)
        self.assertNotEqual(job.created_by, self.user_a.id)


    def test_admin_can_access_all_audits(self):
        res = self.client.get(
            f"/audits/{self.audit_a.id}",
            headers={"Authorization": f"Bearer {self.token_admin}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["audit_id"], self.audit_a.id)

    def test_unauthenticated_request_rejected(self):
        res = self.client.get(f"/audits/{self.audit_a.id}")
        self.assertEqual(res.status_code, 401)

if __name__ == "__main__":
    unittest.main()
