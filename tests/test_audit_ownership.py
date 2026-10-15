import unittest
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.models import AuditJob, AuditStatus, User, UserRole
from backend.src.db.repositories import AuditRepository
from backend.src.db.user_repository import UserRepository
from backend.src.services.auth_service import AuthService
from backend.src.security.passwords import hash_password
from backend.src.queue.redis_queue import audit_queue

class TestAuditOwnershipAndIDOR(unittest.TestCase):
    def setUp(self):
        audit_queue.redis_required = False
        audit_queue.clear()
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

        # Create User A
        self.user_a = UserRepository.create_user(
            self.db,
            email="usera@brandguardian.ai",
            password_hash=hash_password("PassA123!"),
            display_name="User Alpha",
            role=UserRole.USER
        )
        self.token_a = AuthService.create_token_for_user(self.user_a)
        self.headers_a = {"Authorization": f"Bearer {self.token_a}"}

        # Create User B
        self.user_b = UserRepository.create_user(
            self.db,
            email="userb@brandguardian.ai",
            password_hash=hash_password("PassB123!"),
            display_name="User Beta",
            role=UserRole.USER
        )
        self.token_b = AuthService.create_token_for_user(self.user_b)
        self.headers_b = {"Authorization": f"Bearer {self.token_b}"}

        # Create Admin User
        self.admin_user = UserRepository.create_user(
            self.db,
            email="admin@brandguardian.ai",
            password_hash=hash_password("AdminPass123!"),
            display_name="System Admin",
            role=UserRole.ADMIN
        )
        self.admin_token = AuthService.create_token_for_user(self.admin_user)
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_audit_creation_server_assigns_ownership(self):
        # Client tries to pass a forged created_by in the payload
        payload = {
            "video_url": "https://www.youtube.com/watch?v=legit_video_url",
            "created_by": "forged_malicious_user_id"
        }
        resp = self.client.post("/audits", json=payload, headers=self.headers_a)
        self.assertEqual(resp.status_code, 202)
        audit_id = resp.json()["audit_id"]

        # Check DB: created_by MUST be User A's id, ignoring client's forged value
        job = AuditRepository.get_audit(self.db, audit_id)
        self.assertIsNotNone(job)
        self.assertEqual(job.created_by, self.user_a.id)
        self.assertNotEqual(job.created_by, "forged_malicious_user_id")

    def test_idor_get_audit_and_status(self):
        # User A creates an audit
        job = AuditRepository.create_audit(
            session=self.db,
            video_url="https://www.youtube.com/watch?v=user_a_video",
            created_by=self.user_a.id
        )

        # 1. User A can retrieve details and status
        resp_a_details = self.client.get(f"/audits/{job.id}", headers=self.headers_a)
        self.assertEqual(resp_a_details.status_code, 200)
        self.assertEqual(resp_a_details.json()["audit_id"], job.id)

        resp_a_status = self.client.get(f"/audits/{job.id}/status", headers=self.headers_a)
        self.assertEqual(resp_a_status.status_code, 200)
        self.assertEqual(resp_a_status.json()["audit_id"], job.id)

        # 2. User B tries to retrieve User A's audit -> 404 Not Found (IDOR denied)
        resp_b_details = self.client.get(f"/audits/{job.id}", headers=self.headers_b)
        self.assertEqual(resp_b_details.status_code, 404)

        resp_b_status = self.client.get(f"/audits/{job.id}/status", headers=self.headers_b)
        self.assertEqual(resp_b_status.status_code, 404)

        # 3. Admin user CAN retrieve User A's audit
        resp_admin_details = self.client.get(f"/audits/{job.id}", headers=self.admin_headers)
        self.assertEqual(resp_admin_details.status_code, 200)

    def test_idor_report_endpoint(self):
        # User A creates and completes an audit
        job = AuditRepository.create_audit(
            session=self.db,
            video_url="https://www.youtube.com/watch?v=report_test",
            created_by=self.user_a.id
        )
        AuditRepository.save_result(
            session=self.db,
            audit_id=job.id,
            result={"final_report": "# User A Confidential Report"}
        )

        # User A can view report
        resp_a = self.client.get(f"/audits/{job.id}/report", headers=self.headers_a)
        self.assertEqual(resp_a.status_code, 200)
        self.assertIn("Confidential Report", resp_a.json()["final_report"])

        # User B CANNOT view User A's report -> 404 Not Found
        resp_b = self.client.get(f"/audits/{job.id}/report", headers=self.headers_b)
        self.assertEqual(resp_b.status_code, 404)

        # Admin CAN view report
        resp_admin = self.client.get(f"/audits/{job.id}/report", headers=self.admin_headers)
        self.assertEqual(resp_admin.status_code, 200)

    def test_idor_cancel_endpoint(self):
        # User A creates an audit
        job = AuditRepository.create_audit(
            session=self.db,
            video_url="https://www.youtube.com/watch?v=cancel_target",
            created_by=self.user_a.id
        )

        # User B attempts to cancel User A's audit -> 404 Not Found
        resp_b = self.client.post(f"/audits/{job.id}/cancel", headers=self.headers_b)
        self.assertEqual(resp_b.status_code, 404)

        # Verify job was NOT cancelled
        fresh_job = AuditRepository.get_audit(self.db, job.id)
        self.assertEqual(fresh_job.status, AuditStatus.QUEUED)

        # User A cancels own audit -> 200 OK
        resp_a = self.client.post(f"/audits/{job.id}/cancel", headers=self.headers_a)
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_a.json()["status"], "CANCELLED")

    def test_audit_listing_isolation(self):
        # Create 2 audits for User A, 1 for User B
        AuditRepository.create_audit(self.db, "https://www.youtube.com/watch?v=a1", created_by=self.user_a.id)
        AuditRepository.create_audit(self.db, "https://www.youtube.com/watch?v=a2", created_by=self.user_a.id)
        AuditRepository.create_audit(self.db, "https://www.youtube.com/watch?v=b1", created_by=self.user_b.id)

        # User A only receives their 2 audits
        resp_a = self.client.get("/audits", headers=self.headers_a)
        self.assertEqual(resp_a.status_code, 200)
        audits_a = resp_a.json()
        self.assertEqual(len(audits_a), 2)
        for a in audits_a:
            self.assertEqual(a["created_by"], self.user_a.id)

        # User B only receives their 1 audit
        resp_b = self.client.get("/audits", headers=self.headers_b)
        self.assertEqual(resp_b.status_code, 200)
        audits_b = resp_b.json()
        self.assertEqual(len(audits_b), 1)
        self.assertEqual(audits_b[0]["created_by"], self.user_b.id)

        # Admin receives all 3 audits
        resp_admin = self.client.get("/audits", headers=self.admin_headers)
        self.assertEqual(resp_admin.status_code, 200)
        audits_admin = resp_admin.json()
        self.assertEqual(len(audits_admin), 3)

    def test_legacy_endpoint_authentication_enforced(self):
        # Legacy /audit must reject unauthenticated requests
        resp_unauth = self.client.post("/audit", json={"video_url": "https://www.youtube.com/watch?v=legacy_video"})
        self.assertEqual(resp_unauth.status_code, 401)

if __name__ == "__main__":
    unittest.main()
