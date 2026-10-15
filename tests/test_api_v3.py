import unittest
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.config import settings
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.models import AuditStatus
from backend.src.db.repositories import AuditRepository
from backend.src.queue.redis_queue import audit_queue

class TestAPIV3Endpoints(unittest.TestCase):
    def setUp(self):
        audit_queue.redis_required = False
        audit_queue.clear()
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

        from backend.src.security.passwords import hash_password
        from backend.src.db.user_repository import UserRepository
        from backend.src.services.auth_service import AuthService
        self.test_user = UserRepository.create_user(
            session=self.db,
            email="test_v3@brandguardian.ai",
            password_hash=hash_password("test_pass_123"),
            display_name="Test V3 User",
            is_active=True
        )
        token = AuthService.create_token_for_user(self.test_user)
        self.auth_headers = {"Authorization": f"Bearer {token}"}
        self.client.headers.update(self.auth_headers)

    def tearDown(self):
        self.client.headers.clear()
        audit_queue.redis_required = False
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_health_endpoints(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "healthy")

        resp_live = self.client.get("/health/live")
        self.assertEqual(resp_live.status_code, 200)

    def test_readiness_probe_behavior(self):
        orig_avail = audit_queue.is_redis_available
        orig_req = audit_queue.redis_required
        try:
            # Force Redis offline state for deterministic fallback testing
            audit_queue.is_redis_available = False

            # 1. Local Dev Mode (REDIS_REQUIRED=False) -> 200 OK with memory fallback
            audit_queue.redis_required = False
            resp_ready_dev = self.client.get("/health/ready")
            self.assertEqual(resp_ready_dev.status_code, 200)
            self.assertEqual(resp_ready_dev.json()["status"], "ready")
            self.assertEqual(resp_ready_dev.json()["redis"], "memory_fallback_active")

            # 2. Production Mode (REDIS_REQUIRED=True) + Redis Down -> 503 Service Unavailable
            audit_queue.redis_required = True
            resp_ready_prod = self.client.get("/health/ready")
            self.assertEqual(resp_ready_prod.status_code, 503)
            self.assertEqual(resp_ready_prod.json()["status"], "unready")
            self.assertEqual(resp_ready_prod.json()["redis"], "unavailable")
        finally:
            audit_queue.is_redis_available = orig_avail
            audit_queue.redis_required = orig_req

    def test_ssrf_url_validation(self):
        # Invalid protocol
        resp_file = self.client.post("/audits", json={"video_url": "file:///etc/passwd"})
        self.assertEqual(resp_file.status_code, 400)
        self.assertIn("Invalid URL protocol", resp_file.json()["detail"])

        # Private IP
        resp_local = self.client.post("/audits", json={"video_url": "http://localhost:8000/test"})
        self.assertEqual(resp_local.status_code, 400)
        self.assertIn("restricted", resp_local.json()["detail"])

    def test_create_async_audit_and_status(self):
        # 1. Create Audit Job
        resp = self.client.post("/audits", json={"video_url": "https://www.youtube.com/watch?v=valid_test_url"})
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        audit_id = data["audit_id"]
        self.assertEqual(data["status"], "QUEUED")

        # 2. Get Audit Status
        status_resp = self.client.get(f"/audits/{audit_id}/status")
        self.assertEqual(status_resp.status_code, 200)
        s_data = status_resp.json()
        self.assertEqual(s_data["audit_id"], audit_id)
        self.assertEqual(s_data["status"], "QUEUED")

        # 3. Get Details
        det_resp = self.client.get(f"/audits/{audit_id}")
        self.assertEqual(det_resp.status_code, 200)
        self.assertEqual(det_resp.json()["video_url"], "https://www.youtube.com/watch?v=valid_test_url")

    def test_enqueue_failure_when_redis_required(self):
        orig_avail = audit_queue.is_redis_available
        orig_req = audit_queue.redis_required
        try:
            # Simulate Redis unavailable when REDIS_REQUIRED is enforced
            audit_queue.is_redis_available = False
            audit_queue.redis_required = True
            resp = self.client.post("/audits", json={"video_url": "https://www.youtube.com/watch?v=prod_fail_test"})
            self.assertEqual(resp.status_code, 503)
            self.assertIn("Queue service unavailable", resp.json()["detail"])
        finally:
            audit_queue.is_redis_available = orig_avail
            audit_queue.redis_required = orig_req

    def test_idempotency_header(self):
        headers = {"Idempotency-Key": "idempotent_test_key_123", **self.auth_headers}
        payload = {"video_url": "https://www.youtube.com/watch?v=idempotent_url"}

        resp1 = self.client.post("/audits", json=payload, headers=headers)
        self.assertEqual(resp1.status_code, 202)
        audit_id_1 = resp1.json()["audit_id"]

        # Duplicate Request with Same Idempotency Key
        resp2 = self.client.post("/audits", json=payload, headers=headers)
        self.assertEqual(resp2.status_code, 202)
        audit_id_2 = resp2.json()["audit_id"]

        self.assertEqual(audit_id_1, audit_id_2)

    def test_report_endpoint_conflict_when_processing(self):
        resp = self.client.post("/audits", json={"video_url": "https://www.youtube.com/watch?v=conflict_test"})
        audit_id = resp.json()["audit_id"]

        # Report requested before job completes -> HTTP 409
        rep_resp = self.client.get(f"/audits/{audit_id}/report")
        self.assertEqual(rep_resp.status_code, 409)

        # Manually complete job in DB
        AuditRepository.save_result(
            self.db,
            audit_id,
            result={"final_report": "# Test Completed Markdown Report"},
            timing_metrics={"test": 1.0}
        )

        rep_resp_done = self.client.get(f"/audits/{audit_id}/report")
        self.assertEqual(rep_resp_done.status_code, 200)
        self.assertEqual(rep_resp_done.json()["final_report"], "# Test Completed Markdown Report")

    def test_cancel_audit_endpoint(self):
        resp = self.client.post("/audits", json={"video_url": "https://www.youtube.com/watch?v=cancel_test"})
        audit_id = resp.json()["audit_id"]

        cancel_resp = self.client.post(f"/audits/{audit_id}/cancel")
        self.assertEqual(cancel_resp.status_code, 200)
        self.assertEqual(cancel_resp.json()["status"], "CANCELLED")

        # Confirm status in DB
        status_resp = self.client.get(f"/audits/{audit_id}/status")
        self.assertEqual(status_resp.json()["status"], "CANCELLED")

if __name__ == "__main__":
    unittest.main()
