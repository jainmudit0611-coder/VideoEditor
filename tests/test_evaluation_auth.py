import unittest
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.models import User, UserRole
from backend.src.db.evaluation_repository import EvaluationRepository
from backend.src.db.user_repository import UserRepository
from backend.src.services.auth_service import AuthService
from backend.src.security.passwords import hash_password

class TestEvaluationAuthorization(unittest.TestCase):
    """
    Comprehensive test suite for Phase 5.4 evaluation authorization:
    - Personal runs vs Official Baselines
    - User isolation and 404 on unowned runs
    - Baseline visibility across users
    - Comparison authorization enforcement
    """

    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

        # 1. User Alpha
        self.user_a = UserRepository.create_user(
            self.db,
            email="usera_eval@brandguardian.ai",
            password_hash=hash_password("PassA123!"),
            display_name="User Alpha",
            role=UserRole.USER
        )
        self.token_a = AuthService.create_token_for_user(self.user_a)
        self.headers_a = {"Authorization": f"Bearer {self.token_a}"}

        # 2. User Beta
        self.user_b = UserRepository.create_user(
            self.db,
            email="userb_eval@brandguardian.ai",
            password_hash=hash_password("PassB123!"),
            display_name="User Beta",
            role=UserRole.USER
        )
        self.token_b = AuthService.create_token_for_user(self.user_b)
        self.headers_b = {"Authorization": f"Bearer {self.token_b}"}

        # 3. System Admin
        self.admin = UserRepository.create_user(
            self.db,
            email="admin_eval@brandguardian.ai",
            password_hash=hash_password("AdminPass123!"),
            display_name="Lead Evaluator Admin",
            role=UserRole.ADMIN
        )
        self.admin_token = AuthService.create_token_for_user(self.admin)
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

        # Create evaluation runs:
        # Run A: owned by User A, personal run
        self.run_a = EvaluationRepository.create_run(
            self.db,
            run_name="Run Alpha Personal",
            created_by=self.user_a.id,
            is_baseline=False
        )
        EvaluationRepository.save_run_results(
            self.db, self.run_a.id, {"finding_f1": 0.88}, {}, [], 5000, 6
        )

        # Run B: owned by User B, personal run
        self.run_b = EvaluationRepository.create_run(
            self.db,
            run_name="Run Beta Personal",
            created_by=self.user_b.id,
            is_baseline=False
        )
        EvaluationRepository.save_run_results(
            self.db, self.run_b.id, {"finding_f1": 0.85}, {}, [], 4800, 6
        )

        # Baseline: owned by Admin, official baseline
        self.baseline = EvaluationRepository.create_run(
            self.db,
            run_name="Q3 Golden Baseline",
            created_by=self.admin.id,
            is_baseline=True
        )
        EvaluationRepository.save_run_results(
            self.db, self.baseline.id, {"finding_f1": 0.94}, {}, [], 5200, 6
        )

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_user_a_permissions(self):
        # User A sees Run A
        resp_a = self.client.get(f"/api/evaluations/runs/{self.run_a.id}", headers=self.headers_a)
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_a.json()["id"], self.run_a.id)

        # User A sees Baseline run
        resp_base = self.client.get(f"/api/evaluations/runs/{self.baseline.id}", headers=self.headers_a)
        self.assertEqual(resp_base.status_code, 200)
        self.assertTrue(resp_base.json()["is_baseline"])

        # User A CANNOT see Run B (404 Not Found)
        resp_b = self.client.get(f"/api/evaluations/runs/{self.run_b.id}", headers=self.headers_a)
        self.assertEqual(resp_b.status_code, 404)

        # User A CANNOT query Run B status (404 Not Found)
        resp_b_stat = self.client.get(f"/api/evaluations/runs/{self.run_b.id}/status", headers=self.headers_a)
        self.assertEqual(resp_b_stat.status_code, 404)

        # User A CANNOT create an official baseline (403 Forbidden)
        resp_create_base = self.client.post(
            "/api/evaluations/runs",
            json={"run_name": "Rogue Baseline", "is_baseline": True},
            headers=self.headers_a
        )
        self.assertEqual(resp_create_base.status_code, 403)
        self.assertIn("Administrative privileges required", resp_create_base.json()["detail"])

    def test_user_b_permissions(self):
        # User B sees Run B
        resp_b = self.client.get(f"/api/evaluations/runs/{self.run_b.id}", headers=self.headers_b)
        self.assertEqual(resp_b.status_code, 200)

        # User B sees Baseline run
        resp_base = self.client.get(f"/api/evaluations/runs/{self.baseline.id}", headers=self.headers_b)
        self.assertEqual(resp_base.status_code, 200)

        # User B CANNOT see Run A (404 Not Found)
        resp_a = self.client.get(f"/api/evaluations/runs/{self.run_a.id}", headers=self.headers_b)
        self.assertEqual(resp_a.status_code, 404)

    def test_admin_permissions(self):
        # Admin can see Run A, Run B, and Baseline
        for r_id in (self.run_a.id, self.run_b.id, self.baseline.id):
            resp = self.client.get(f"/api/evaluations/runs/{r_id}", headers=self.admin_headers)
            self.assertEqual(resp.status_code, 200)

        # Admin CAN create an official baseline
        resp_create = self.client.post(
            "/api/evaluations/runs",
            json={"run_name": "Official Admin Baseline", "is_baseline": True},
            headers=self.admin_headers
        )
        self.assertEqual(resp_create.status_code, 202)
        data = resp_create.json()
        self.assertTrue(data["is_baseline"])
        self.assertEqual(data["created_by"], self.admin.id)

    def test_runs_list_filtering(self):
        # User A list: should contain Run A and Baseline, but NOT Run B
        resp_a = self.client.get("/api/evaluations/runs", headers=self.headers_a)
        self.assertEqual(resp_a.status_code, 200)
        items_a = resp_a.json()
        ids_a = {item["id"] for item in items_a}
        self.assertIn(self.run_a.id, ids_a)
        self.assertIn(self.baseline.id, ids_a)
        self.assertNotIn(self.run_b.id, ids_a)

        # User B list: should contain Run B and Baseline, but NOT Run A
        resp_b = self.client.get("/api/evaluations/runs", headers=self.headers_b)
        self.assertEqual(resp_b.status_code, 200)
        items_b = resp_b.json()
        ids_b = {item["id"] for item in items_b}
        self.assertIn(self.run_b.id, ids_b)
        self.assertIn(self.baseline.id, ids_b)
        self.assertNotIn(self.run_a.id, ids_b)

        # Admin list: should contain Run A, Run B, and Baseline
        resp_admin = self.client.get("/api/evaluations/runs", headers=self.admin_headers)
        self.assertEqual(resp_admin.status_code, 200)
        items_admin = resp_admin.json()
        ids_admin = {item["id"] for item in items_admin}
        self.assertIn(self.run_a.id, ids_admin)
        self.assertIn(self.run_b.id, ids_admin)
        self.assertIn(self.baseline.id, ids_admin)

    def test_compare_runs_authorization(self):
        # 1. User A compares Run A and Baseline -> ALLOWED
        resp_allowed = self.client.get(
            f"/api/evaluations/compare?run_ids={self.run_a.id},{self.baseline.id}",
            headers=self.headers_a
        )
        self.assertEqual(resp_allowed.status_code, 200)
        self.assertEqual(len(resp_allowed.json()["runs"]), 2)

        # 2. User A attempts comparison including Run B -> 404 DENIED (cannot access unauthorized Run B)
        resp_denied = self.client.get(
            f"/api/evaluations/compare?run_ids={self.run_a.id},{self.run_b.id}",
            headers=self.headers_a
        )
        self.assertEqual(resp_denied.status_code, 404)

        # 3. Admin compares Run A, Run B, and Baseline -> ALLOWED
        resp_admin = self.client.get(
            f"/api/evaluations/compare?run_ids={self.run_a.id},{self.run_b.id},{self.baseline.id}",
            headers=self.admin_headers
        )
        self.assertEqual(resp_admin.status_code, 200)
        self.assertEqual(len(resp_admin.json()["runs"]), 3)

if __name__ == "__main__":
    unittest.main()
