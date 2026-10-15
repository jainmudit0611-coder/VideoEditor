import unittest
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.models import AuditStatus
from backend.src.worker.worker import WorkerDaemon

from backend.src.queue.redis_queue import audit_queue

class TestAsyncIntegrationV3(unittest.TestCase):
    def setUp(self):
        audit_queue.clear()
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.worker = WorkerDaemon()

        from backend.src.security.passwords import hash_password
        from backend.src.db.user_repository import UserRepository
        from backend.src.services.auth_service import AuthService
        self.test_user = UserRepository.create_user(
            session=self.db,
            email="integration_user@brandguardian.ai",
            password_hash=hash_password("integration_pass_123"),
            display_name="Integration User",
            is_active=True
        )
        token = AuthService.create_token_for_user(self.test_user)
        self.auth_headers = {"Authorization": f"Bearer {token}"}
        self.client.headers.update(self.auth_headers)

    def tearDown(self):
        self.client.headers.clear()
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_full_async_audit_lifecycle(self):
        # 1. Post Async Audit Request
        payload = {"video_url": "https://www.youtube.com/watch?v=jNQXAC9IVRw"}
        post_resp = self.client.post("/audits", json=payload)
        self.assertEqual(post_resp.status_code, 202)
        
        audit_id = post_resp.json()["audit_id"]
        self.assertEqual(post_resp.json()["status"], "QUEUED")

        # 2. Check Initial Status (QUEUED)
        status_resp_1 = self.client.get(f"/audits/{audit_id}/status")
        self.assertEqual(status_resp_1.json()["status"], "QUEUED")

        # 3. Execute Worker Single Loop Processing
        job_processed = self.worker.run_single_loop()
        self.assertTrue(job_processed, "Worker should successfully dequeue and process the job")

        # 4. Check Post-Processing Status (COMPLETED)
        status_resp_2 = self.client.get(f"/audits/{audit_id}/status")
        s_data = status_resp_2.json()
        self.assertEqual(s_data["status"], "COMPLETED")
        self.assertEqual(s_data["progress"], 100)

        # 5. Retrieve Final Markdown Audit Report
        report_resp = self.client.get(f"/audits/{audit_id}/report")
        self.assertEqual(report_resp.status_code, 200)
        report_data = report_resp.json()
        self.assertEqual(report_data["audit_id"], audit_id)
        self.assertIn("# Brand Guardian AI", report_data["final_report"])

        # 6. Retrieve Full Details Endpoint
        details_resp = self.client.get(f"/audits/{audit_id}")
        self.assertEqual(details_resp.status_code, 200)
        det_data = details_resp.json()
        self.assertIsNotNone(det_data["completed_at"])
        self.assertIsNotNone(det_data["timing_metrics"])

if __name__ == "__main__":
    unittest.main()
