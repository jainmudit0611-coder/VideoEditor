import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.src.db.database import Base
from backend.src.db.models import AuditJob, AuditStatus, AuditStage
from backend.src.db.repositories import AuditRepository

class TestDatabaseLayer(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = self.SessionLocal()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_create_and_get_audit(self):
        job = AuditRepository.create_audit(
            self.session,
            video_url="https://www.youtube.com/watch?v=demo123",
            idempotency_key="idemp_key_001"
        )
        self.assertIsNotNone(job.id)
        self.assertEqual(job.status, AuditStatus.QUEUED)
        self.assertEqual(job.progress, 0)

        retrieved = AuditRepository.get_audit(self.session, job.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.video_url, "https://www.youtube.com/watch?v=demo123")

        idemp_retrieved = AuditRepository.get_audit_by_idempotency_key(self.session, "idemp_key_001")
        self.assertEqual(idemp_retrieved.id, job.id)

    def test_update_status_and_progress(self):
        job = AuditRepository.create_audit(self.session, video_url="https://youtube.com/watch?v=test")
        
        updated = AuditRepository.update_status(
            self.session,
            job.id,
            status=AuditStatus.PROCESSING,
            stage=AuditStage.DOWNLOADING.value,
            progress=15
        )
        self.assertEqual(updated.status, AuditStatus.PROCESSING)
        self.assertEqual(updated.current_stage, AuditStage.DOWNLOADING.value)
        self.assertEqual(updated.progress, 15)
        self.assertIsNotNone(updated.started_at)

        progress_updated = AuditRepository.update_progress(
            self.session,
            job.id,
            progress=55,
            stage=AuditStage.VISION_ANALYSIS.value
        )
        self.assertEqual(progress_updated.progress, 55)
        self.assertEqual(progress_updated.current_stage, AuditStage.VISION_ANALYSIS.value)

    def test_save_result_and_failed(self):
        job = AuditRepository.create_audit(self.session, video_url="https://youtube.com/watch?v=test")

        res_data = {"status": "PASS", "final_report": "# Passed Report"}
        timing = {"download_time": 2.5, "vision_time": 1.2}
        
        saved = AuditRepository.save_result(
            self.session,
            job.id,
            result=res_data,
            timing_metrics=timing,
            iteration_count=1
        )
        self.assertEqual(saved.status, AuditStatus.COMPLETED)
        self.assertEqual(saved.progress, 100)
        self.assertEqual(saved.result["status"], "PASS")
        self.assertIsNotNone(saved.completed_at)

        # Test mark_failed on new job
        job2 = AuditRepository.create_audit(self.session, video_url="https://youtube.com/watch?v=fail")
        failed = AuditRepository.mark_failed(
            self.session,
            job2.id,
            error_code="TEST_ERROR",
            error_message="Test failure message"
        )
        self.assertEqual(failed.status, AuditStatus.FAILED)
        self.assertEqual(failed.error_code, "TEST_ERROR")

    def test_cancel_audit(self):
        job = AuditRepository.create_audit(self.session, video_url="https://youtube.com/watch?v=cancel")
        cancelled = AuditRepository.cancel_audit(self.session, job.id)
        self.assertEqual(cancelled.status, AuditStatus.CANCELLED)

if __name__ == "__main__":
    unittest.main()
