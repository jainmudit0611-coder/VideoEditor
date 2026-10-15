import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.src.db.database import Base
from backend.src.db.models import EvaluationRunStatus
from backend.src.db.evaluation_repository import EvaluationRepository
from backend.src.services.evaluation_service import EvaluationService

class TestEvaluationServiceLayer(unittest.TestCase):
    """Unit tests for EvaluationService execution and comparison."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = self.SessionLocal()
        self.service = EvaluationService()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_execute_run_lifecycle(self):
        run = EvaluationRepository.create_run(self.session, run_name="Lifecycle Test Run")
        self.assertEqual(run.status, EvaluationRunStatus.QUEUED)

        completed_run = self.service.execute_run(self.session, run.id)
        self.assertIsNotNone(completed_run)
        self.assertEqual(completed_run.status, EvaluationRunStatus.COMPLETED)
        self.assertGreater(completed_run.case_count, 0)
        self.assertIsNotNone(completed_run.duration_ms)
        self.assertIn("finding_precision", completed_run.metrics)
        self.assertIn("finding_recall", completed_run.metrics)
        self.assertIn("finding_f1", completed_run.metrics)
        self.assertIn("case_results", completed_run.summary)

    def test_execute_nonexistent_run(self):
        res = self.service.execute_run(self.session, "invalid_run_id_9999")
        self.assertIsNone(res)

    def test_compare_runs(self):
        run1 = EvaluationRepository.create_run(self.session, run_name="Run A", model_name="gpt-4o")
        run2 = EvaluationRepository.create_run(self.session, run_name="Run B", model_name="gpt-4o-mini")

        metrics1 = {"finding_precision": 0.80, "finding_recall": 0.85, "finding_f1": 0.82}
        metrics2 = {"finding_precision": 0.90, "finding_recall": 0.85, "finding_f1": 0.87}

        EvaluationRepository.save_run_results(self.session, run1.id, metrics1, {}, [], 5000, 6)
        EvaluationRepository.save_run_results(self.session, run2.id, metrics2, {}, [], 4500, 6)

        comparison = EvaluationService.compare_runs([run1, run2])
        self.assertEqual(len(comparison["runs"]), 2)
        self.assertGreater(len(comparison["metrics"]), 0)

        # Check precision delta
        prec_row = next((m for m in comparison["metrics"] if m["key"] == "finding_precision"), None)
        self.assertIsNotNone(prec_row)
        self.assertEqual(prec_row["values"][run1.id], 0.80)
        self.assertEqual(prec_row["values"][run2.id], 0.90)
        self.assertEqual(prec_row["delta"], 0.10)

        # Check metadata difference detection
        model_diff = next((d for d in comparison["differences"] if d["field"] == "Model Name"), None)
        self.assertIsNotNone(model_diff)
        self.assertTrue(model_diff["has_difference"])

if __name__ == "__main__":
    unittest.main()
