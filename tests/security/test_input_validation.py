import unittest
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.user_repository import UserRepository
from backend.src.services.auth_service import AuthService
from backend.src.security.passwords import hash_password

class TestInputValidationSecurity(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

        self.user = UserRepository.create_user(
            self.db,
            email="input_tester@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="Input Tester"
        )
        self.token = AuthService.create_token_for_user(self.user)
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_excessively_long_url_rejected(self):
        # 10,000 character URL
        huge_url = "https://www.youtube.com/watch?v=" + ("a" * 10000)
        res = self.client.post(
            "/audits",
            headers=self.auth_headers,
            json={"video_url": huge_url}
        )
        self.assertIn(res.status_code, [400, 422])

    def test_malformed_audit_uuid_returns_404_not_500(self):
        malformed_ids = [
            "not-a-uuid",
            "123",
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "null",
            "undefined"
        ]
        for bad_id in malformed_ids:
            res_details = self.client.get(f"/audits/{bad_id}", headers=self.auth_headers)
            self.assertIn(res_details.status_code, [404, 400, 422], f"Failed on id: {bad_id}")

            res_status = self.client.get(f"/audits/{bad_id}/status", headers=self.auth_headers)
            self.assertIn(res_status.status_code, [404, 400, 422])

            res_report = self.client.get(f"/audits/{bad_id}/report", headers=self.auth_headers)
            self.assertIn(res_report.status_code, [404, 400, 422])

            res_cancel = self.client.post(f"/audits/{bad_id}/cancel", headers=self.auth_headers)
            self.assertIn(res_cancel.status_code, [404, 400, 422])

    def test_malformed_evaluation_run_uuid_returns_404_not_500(self):
        bad_run_ids = ["bad-uuid-000", "00000000-0000-0000-0000-000000000000", "select * from runs"]
        for bad_id in bad_run_ids:
            res = self.client.get(f"/api/evaluations/runs/{bad_id}", headers=self.auth_headers)
            self.assertIn(res.status_code, [404, 422])

    def test_malformed_json_body_returns_422_not_500(self):
        res = self.client.post(
            "/auth/login",
            content="this is not valid json {{{",
            headers={"Content-Type": "application/json"}
        )
        self.assertIn(res.status_code, [400, 422])

    def test_negative_pagination_parameters_gracefully_handled(self):
        res = self.client.get(
            "/audits?limit=-10&offset=-5",
            headers=self.auth_headers
        )
        # Should not raise 500 Internal Server Error
        self.assertIn(res.status_code, [200, 400, 422])

if __name__ == "__main__":
    unittest.main()
