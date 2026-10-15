import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.src.db.database import Base
from backend.src.db.models import EvaluationRun, EvaluationRunStatus
from backend.src.db.evaluation_repository import EvaluationRepository

class TestEvaluationDatabaseLayer(unittest.TestCase):
    """Unit tests for EvaluationRun persistence and EvaluationRepository."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = self.SessionLocal()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_create_and_get_run(self):
        run = EvaluationRepository.create_run(
            self.session,
            run_name="Test Benchmark Run",
            model_name="gpt-4o",
            dataset_version="v1"
        )
        self.assertIsNotNone(run.id)
        self.assertEqual(run.status, EvaluationRunStatus.QUEUED)
        self.assertEqual(run.run_name, "Test Benchmark Run")
        self.assertEqual(run.dataset_version, "v1")
        self.assertEqual(run.dataset_type, "MANUALLY_CURATED")

        retrieved = EvaluationRepository.get_run(self.session, run.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, run.id)
        self.assertEqual(retrieved.model_name, "gpt-4o")

    def test_mark_running(self):
        run = EvaluationRepository.create_run(self.session, run_name="Running Test")
        updated = EvaluationRepository.mark_running(self.session, run.id)
        self.assertEqual(updated.status, EvaluationRunStatus.RUNNING)
        self.assertIsNotNone(updated.started_at)

    def test_save_run_results(self):
        run = EvaluationRepository.create_run(self.session, run_name="Completed Test")
        EvaluationRepository.mark_running(self.session, run.id)

        metrics = {
            "finding_precision": 0.85,
            "finding_recall": 0.90,
            "finding_f1": 0.87,
            "evidence_support_rate": 0.95
        }
        summary = {"cases_evaluated": 6}
        discrepancies = [{"case_id": "case_001", "failure_type": "FALSE_POSITIVE"}]

        completed = EvaluationRepository.save_run_results(
            session=self.session,
            run_id=run.id,
            metrics=metrics,
            summary=summary,
            discrepancies=discrepancies,
            duration_ms=4500,
            case_count=6
        )

        self.assertEqual(completed.status, EvaluationRunStatus.COMPLETED)
        self.assertEqual(completed.duration_ms, 4500)
        self.assertEqual(completed.metrics["finding_f1"], 0.87)
        self.assertEqual(len(completed.discrepancies), 1)
        self.assertIsNotNone(completed.completed_at)

    def test_mark_failed(self):
        run = EvaluationRepository.create_run(self.session, run_name="Failed Test")
        failed = EvaluationRepository.mark_failed(self.session, run.id, error_message="Dataset file not found")
        self.assertEqual(failed.status, EvaluationRunStatus.FAILED)
        self.assertEqual(failed.error_message, "Dataset file not found")
        self.assertIsNotNone(failed.completed_at)

    def test_list_runs_with_filtering(self):
        EvaluationRepository.create_run(self.session, run_name="Run 1", model_name="gpt-4o", dataset_version="v1")
        EvaluationRepository.create_run(self.session, run_name="Run 2", model_name="gpt-4o-mini", dataset_version="v2")

        all_runs = EvaluationRepository.list_runs(self.session)
        self.assertEqual(len(all_runs), 2)

        v1_runs = EvaluationRepository.list_runs(self.session, dataset_version="v1")
        self.assertEqual(len(v1_runs), 1)
        self.assertEqual(v1_runs[0].run_name, "Run 1")

        mini_runs = EvaluationRepository.list_runs(self.session, model_name="gpt-4o-mini")
        self.assertEqual(len(mini_runs), 1)
        self.assertEqual(mini_runs[0].model_name, "gpt-4o-mini")

if __name__ == "__main__":
    unittest.main()
