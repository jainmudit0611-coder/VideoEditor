import unittest
from fastapi.testclient import TestClient

from backend.src.api.server import app
from backend.src.db.database import Base, engine, SessionLocal
from backend.src.db.models import User, UserRole, EvaluationRun, EvaluationRunStatus
from backend.src.db.user_repository import UserRepository
from backend.src.services.auth_service import AuthService
from backend.src.security.passwords import hash_password

class TestEvaluationAuthorizationSecurity(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        self.db = SessionLocal()

        self.db.query(EvaluationRun).delete()
        self.db.query(User).delete()
        self.db.commit()

        self.user_a = UserRepository.create_user(
            self.db,
            email="eval_user_a@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="Eval User A",
            role=UserRole.USER
        )
        self.token_a = AuthService.create_token_for_user(self.user_a)

        self.user_b = UserRepository.create_user(
            self.db,
            email="eval_user_b@brandguardian.ai",
            password_hash=hash_password("Pass123456"),
            display_name="Eval User B",
            role=UserRole.USER
        )
        self.token_b = AuthService.create_token_for_user(self.user_b)

        self.admin = UserRepository.create_user(
            self.db,
            email="eval_admin@brandguardian.ai",
            password_hash=hash_password("AdminPass123!"),
            display_name="Eval Admin",
            role=UserRole.ADMIN
        )
        self.token_admin = AuthService.create_token_for_user(self.admin)

        # Baseline run created by admin
        self.baseline_run = EvaluationRun(
            id="baseline-run-uuid-001",
            run_name="Baseline Run 1",
            status=EvaluationRunStatus.COMPLETED,
            is_baseline=True,
            created_by=self.admin.id,
            case_count=6,
            metrics={},
            summary={},
            discrepancies=[]
        )
        self.db.add(self.baseline_run)

        # Private run created by User A
        self.private_run_a = EvaluationRun(
            id="private-run-uuid-001",
            run_name="Private Run A",
            status=EvaluationRunStatus.COMPLETED,
            is_baseline=False,
            created_by=self.user_a.id,
            case_count=6,
            metrics={},
            summary={},
            discrepancies=[]
        )
        self.db.add(self.private_run_a)
        self.db.commit()

    def tearDown(self):
        try:
            self.db.query(EvaluationRun).delete()
            self.db.query(User).delete()
            self.db.commit()
        except Exception:
            pass
        self.db.close()
        Base.metadata.drop_all(bind=engine)


    def test_user_cannot_create_official_baseline_rejected_403(self):
        res = self.client.post(
            "/api/evaluations/runs",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"is_baseline": True}
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Administrative privileges required", res.json()["detail"])

    def test_admin_can_create_official_baseline(self):
        res = self.client.post(
            "/api/evaluations/runs",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            json={"is_baseline": True}
        )
        self.assertEqual(res.status_code, 202)
        data = res.json()
        self.assertTrue(data["is_baseline"])

    def test_user_can_view_official_baseline(self):
        res = self.client.get(
            f"/api/evaluations/runs/{self.baseline_run.id}",
            headers={"Authorization": f"Bearer {self.token_a}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], self.baseline_run.id)

    def test_user_cannot_view_another_users_private_run_rejected_404(self):
        res = self.client.get(
            f"/api/evaluations/runs/{self.private_run_a.id}",
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_user_cannot_compare_with_unauthorized_private_run(self):
        # User B attempts to compare baseline with User A's private run
        res = self.client.get(
            f"/api/evaluations/compare?run_ids={self.baseline_run.id},{self.private_run_a.id}",
            headers={"Authorization": f"Bearer {self.token_b}"}
        )
        self.assertEqual(res.status_code, 404)

    def test_admin_can_view_any_run_and_compare(self):
        res = self.client.get(
            f"/api/evaluations/runs/{self.private_run_a.id}",
            headers={"Authorization": f"Bearer {self.token_admin}"}
        )
        self.assertEqual(res.status_code, 200)

        compare_res = self.client.get(
            f"/api/evaluations/compare?run_ids={self.baseline_run.id},{self.private_run_a.id}",
            headers={"Authorization": f"Bearer {self.token_admin}"}
        )
        self.assertEqual(compare_res.status_code, 200)

    def test_run_creation_payload_cannot_spoof_created_by(self):
        res = self.client.post(
            "/api/evaluations/runs",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={
                "is_baseline": False,
                "created_by": self.admin.id  # Attempt to spoof creator
            }
        )
        self.assertEqual(res.status_code, 202)
        run_id = res.json()["id"]
        run_record = self.db.query(EvaluationRun).filter_by(id=run_id).first()

        self.assertEqual(run_record.created_by, self.user_b.id)

if __name__ == "__main__":
    unittest.main()

