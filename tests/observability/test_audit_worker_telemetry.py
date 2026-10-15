import json
import logging
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.src.db.database import Base
from backend.src.db.models import AuditJob, AuditStatus, AuditStage
from backend.src.db.repositories import AuditRepository
from backend.src.queue.redis_queue import RedisAuditQueue
from backend.src.worker.processor import AuditTaskProcessor
from backend.src.worker.worker import WorkerDaemon
from backend.src.observability.events import ObservabilityEvent
from backend.src.observability.structured_logger import StructuredJsonFormatter, get_logger
from backend.src.observability.correlation import clear_correlation_context


class TestAuditWorkerTelemetry(unittest.TestCase):
    """
    Tests correlation flow across Audit creation, Queue, Worker execution,
    and Retry telemetry.
    """

    def setUp(self):
        clear_correlation_context()
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Capture structured logs
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setFormatter(StructuredJsonFormatter())
        
        # Attach to root / processors
        for name in ["brand-guardian-queue", "brand-guardian-worker", "brand-guardian-worker-processor"]:
            l = get_logger(name)
            l.setLevel(logging.INFO)
            l.addHandler(self.handler)

    def tearDown(self):
        self.session.close()
        clear_correlation_context()

    def _get_logged_events(self):
        output = self.log_stream.getvalue().strip()
        events = []
        for line in output.split("\n"):
            if line.strip():
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
        return events

    def test_audit_creation_preserves_request_id(self):
        """Verifies AuditJob model and repository persist the correlation request_id."""
        job = AuditRepository.create_audit(
            session=self.session,
            video_url="https://www.youtube.com/watch?v=demo123",
            request_id="req_test_init_001"
        )
        self.assertEqual(job.request_id, "req_test_init_001")

        retrieved = AuditRepository.get_audit(self.session, job.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.request_id, "req_test_init_001")
        self.assertEqual(retrieved.to_dict()["request_id"], "req_test_init_001")

    def test_queue_emits_enqueue_and_dequeue_events(self):
        """Verifies RedisAuditQueue emits structured events on enqueue and dequeue."""
        queue = RedisAuditQueue(queue_name="test_obs_queue", redis_required=False)
        queue.clear()

        queue.enqueue_audit("audit_test_queue_01")
        item = queue.dequeue_audit(timeout=1)
        self.assertEqual(item, "audit_test_queue_01")

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]

        self.assertIn("queue_enqueue", event_names)
        self.assertIn("queue_dequeue", event_names)

        # Check queue_enqueue details
        enqueue_event = next(e for e in events if e.get("event") == "queue_enqueue")
        self.assertEqual(enqueue_event.get("audit_id"), "audit_test_queue_01")
        self.assertIn("duration_ms", enqueue_event)

    @patch("backend.src.worker.processor.compliance_graph.invoke")
    def test_worker_processor_sets_correlation_and_emits_lifecycle(self, mock_invoke):
        """Verifies AuditTaskProcessor correlates worker_id, audit_id, and request_id."""
        mock_invoke.return_value = {
            "final_status": "PASS",
            "final_report": "All tests passed",
            "compliance_results": [],
            "citations": [],
            "verification_results": {"overall_status": "VERIFIED"},
            "iteration_count": 0,
            "visual_observations": [],
            "is_degraded_vision_mode": False,
            "timing_metrics": {"verifier_time": 0.1}
        }

        job = AuditRepository.create_audit(
            session=self.session,
            video_url="https://www.youtube.com/watch?v=valid123",
            request_id="req_worker_test_99"
        )

        success = AuditTaskProcessor.process_audit_job(
            session=self.session,
            audit_id=job.id,
            worker_id="test_worker_instance_42"
        )
        self.assertTrue(success)

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]

        self.assertIn("worker_job_received", event_names)
        self.assertIn("worker_job_completed", event_names)
        self.assertIn("audit_completed", event_names)

        # Check correlation identifiers on worker_job_completed event
        complete_event = next(e for e in events if e.get("event") == "worker_job_completed")
        self.assertEqual(complete_event.get("audit_id"), job.id)
        self.assertEqual(complete_event.get("worker_id"), "test_worker_instance_42")
        self.assertEqual(complete_event.get("request_id"), "req_worker_test_99")
        self.assertIn("duration_ms", complete_event)

    @patch("backend.src.worker.processor.compliance_graph.invoke")
    def test_worker_retry_observability_on_transient_error(self, mock_invoke):
        """Verifies transient failures emit worker_job_retry event with attempt metadata."""
        mock_invoke.side_effect = ConnectionError("Azure rate limit 503 Service Unavailable")

        job = AuditRepository.create_audit(
            session=self.session,
            video_url="https://www.youtube.com/watch?v=retrytest",
            request_id="req_retry_001"
        )

        with patch("backend.src.queue.redis_queue.audit_queue.enqueue_audit"):
            success = AuditTaskProcessor.process_audit_job(
                session=self.session,
                audit_id=job.id,
                worker_id="worker_retry_test"
            )
        self.assertFalse(success)

        events = self._get_logged_events()
        event_names = [e.get("event") for e in events]

        self.assertIn("worker_job_retry", event_names)
        retry_event = next(e for e in events if e.get("event") == "worker_job_retry")
        self.assertEqual(retry_event.get("audit_id"), job.id)
        self.assertEqual(retry_event.get("attempt"), 1)
        self.assertEqual(retry_event.get("error_code"), "TRANSIENT_ERROR")

    def test_worker_daemon_initializes_unique_id(self):
        """Verifies WorkerDaemon generates a unique worker_id containing hostname and pid."""
        daemon1 = WorkerDaemon()
        daemon2 = WorkerDaemon()
        self.assertTrue(daemon1.worker_id.startswith("worker_"))
        self.assertNotEqual(daemon1.worker_id, daemon2.worker_id)


if __name__ == "__main__":
    unittest.main()
