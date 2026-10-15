import unittest
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.evaluation_repository import EvaluationRepository
from backend.src.services.evaluation_service import EvaluationService
from backend.src.security.passwords import hash_password
from backend.src.db.user_repository import UserRepository
from backend.src.services.auth_service import AuthService

class TestEvaluationAPIEndpoints(unittest.TestCase):
    """Integration tests for /api/evaluations FastAPI endpoints."""

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

        self.test_user = UserRepository.create_user(
            session=self.db,
            email="eval_api_user@brandguardian.ai",
            password_hash=hash_password("eval_pass_123"),
            display_name="Eval API User",
            is_active=True
        )
        token = AuthService.create_token_for_user(self.test_user)
        self.auth_headers = {"Authorization": f"Bearer {token}"}
        self.client.headers.update(self.auth_headers)

    def tearDown(self):
        self.client.headers.clear()
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_create_evaluation_run(self):
        payload = {
            "run_name": "API Test Run",
            "model_name": "gpt-4o",
            "dataset_version": "v1"
        }
        resp = self.client.post("/api/evaluations/runs", json=payload)
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertIn("id", data)
        self.assertEqual(data["run_name"], "API Test Run")
        self.assertEqual(data["status"], "QUEUED")
        self.assertEqual(data["created_by"], self.test_user.id)
        self.assertFalse(data["is_baseline"])

    def test_list_and_get_runs(self):
        # Create a run via repository and execute it
        run = EvaluationRepository.create_run(
            self.db,
            run_name="List Test Run",
            model_name="gpt-4o",
            created_by=self.test_user.id
        )
        service = EvaluationService()
        service.execute_run(self.db, run.id)

        # Test list
        resp_list = self.client.get("/api/evaluations/runs")
        self.assertEqual(resp_list.status_code, 200)
        items = resp_list.json()
        self.assertGreaterEqual(len(items), 1)
        self.assertEqual(items[0]["id"], run.id)
        self.assertIn("finding_f1", items[0]["metrics"])

        # Test get detail
        resp_detail = self.client.get(f"/api/evaluations/runs/{run.id}")
        self.assertEqual(resp_detail.status_code, 200)
        detail = resp_detail.json()
        self.assertEqual(detail["id"], run.id)
        self.assertEqual(detail["status"], "COMPLETED")
        self.assertIn("case_results", detail["summary"])

    def test_get_run_status(self):
        run = EvaluationRepository.create_run(
            self.db,
            run_name="Status Test Run",
            created_by=self.test_user.id
        )
        resp = self.client.get(f"/api/evaluations/runs/{run.id}/status")
        self.assertEqual(resp.status_code, 200)
        status_data = resp.json()
        self.assertEqual(status_data["id"], run.id)
        self.assertEqual(status_data["status"], "QUEUED")

    def test_get_nonexistent_run(self):
        resp = self.client.get("/api/evaluations/runs/nonexistent-id-123")
        self.assertEqual(resp.status_code, 404)

    def test_compare_runs_endpoint(self):
        run1 = EvaluationRepository.create_run(
            self.db,
            run_name="Run 1",
            created_by=self.test_user.id
        )
        run2 = EvaluationRepository.create_run(
            self.db,
            run_name="Run 2",
            created_by=self.test_user.id
        )

        EvaluationRepository.save_run_results(
            self.db, run1.id, {"finding_precision": 0.85, "finding_f1": 0.88}, {}, [], 5000, 6
        )
        EvaluationRepository.save_run_results(
            self.db, run2.id, {"finding_precision": 0.90, "finding_f1": 0.92}, {}, [], 4500, 6
        )

        resp = self.client.get(f"/api/evaluations/compare?run_ids={run1.id},{run2.id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["runs"]), 2)
        self.assertGreater(len(data["metrics"]), 0)
        self.assertGreater(len(data["differences"]), 0)

    def test_compare_runs_insufficient_ids(self):
        resp = self.client.get("/api/evaluations/compare?run_ids=single_id")
        self.assertEqual(resp.status_code, 400)

if __name__ == "__main__":
    unittest.main()
