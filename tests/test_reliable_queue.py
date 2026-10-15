import time
import uuid
import unittest
from unittest.mock import MagicMock, patch
import redis

from backend.src.queue.redis_queue import RedisAuditQueue
from backend.src.worker.processor import AuditTaskProcessor
from backend.src.db.models import AuditJob, AuditStatus
from backend.src.db.database import Base, SessionLocal, engine


class TestReliableQueueLifecycleMemory(unittest.TestCase):
    """
    Unit Tests for the Reliable Queue Lifecycle using In-Memory Fallback.
    Labels: [MOCK / LOCAL IN-MEMORY FALLBACK]
    """

    def setUp(self):
        self.queue = RedisAuditQueue(
            redis_url="redis://invalid_host:9999/0",
            queue_name=f"test_memory_queue_{uuid.uuid4().hex[:8]}",
            redis_required=False,
            processing_timeout=1,
            max_attempts=3
        )
        self.queue.clear()

    def test_atomic_dequeue_and_in_flight_tracking(self):
        job_id = "test_job_101"
        self.queue.enqueue_audit(job_id)
        self.assertEqual(self.queue.get_queue_length(), 1)
        self.assertEqual(self.queue.get_processing_length(), 0)

        # Dequeue moves item to in-flight processing list
        dequeued = self.queue.dequeue_audit(timeout=1, worker_id="worker_test_1")
        self.assertEqual(dequeued, job_id)
        self.assertEqual(self.queue.get_queue_length(), 0)
        self.assertEqual(self.queue.get_processing_length(), 1)

    def test_acknowledgement_removes_from_processing(self):
        job_id = "test_job_102"
        self.queue.enqueue_audit(job_id)
        self.queue.dequeue_audit(timeout=1, worker_id="worker_test_1")
        self.assertEqual(self.queue.get_processing_length(), 1)

        # Acknowledge after outcome persistence
        self.queue.acknowledge(job_id, worker_id="worker_test_1")
        self.assertEqual(self.queue.get_processing_length(), 0)
        self.assertEqual(self.queue.get_queue_length(), 0)

    def test_worker_crash_stale_job_recovery(self):
        job_id = "test_job_crash_103"
        self.queue.enqueue_audit(job_id)
        dequeued = self.queue.dequeue_audit(timeout=1, worker_id="crashed_worker")
        self.assertEqual(dequeued, job_id)
        self.assertEqual(self.queue.get_processing_length(), 1)

        # Worker crashes! (never calls acknowledge)
        # Immediate recovery with 0s threshold simulates timeout expiry
        recovered = self.queue.recover_stale_jobs(timeout_seconds=0, max_attempts=3)
        self.assertIn(job_id, recovered)

        # Job is recovered back to the pending queue
        self.assertEqual(self.queue.get_queue_length(), 1)
        self.assertEqual(self.queue.get_processing_length(), 0)

    def test_heartbeat_prevents_premature_stale_recovery(self):
        job_id = "test_job_heartbeat_104"
        self.queue.enqueue_audit(job_id)
        self.queue.dequeue_audit(timeout=1, worker_id="active_worker")

        # Worker records heartbeat
        hb_success = self.queue.record_heartbeat(job_id, worker_id="active_worker")
        self.assertTrue(hb_success)

        # Job should NOT be recovered if timeout is large (e.g. 10s)
        recovered = self.queue.recover_stale_jobs(timeout_seconds=10, max_attempts=3)
        self.assertEqual(len(recovered), 0)
        self.assertEqual(self.queue.get_processing_length(), 1)

    def test_max_attempts_moves_to_dead_letter_queue(self):
        job_id = "test_job_dlq_105"
        self.queue.enqueue_audit(job_id)
        self.queue.dequeue_audit(timeout=1, worker_id="worker_fail")

        # Simulate job having exhausted attempts (max_attempts=3)
        self.queue._memory_attempts[job_id] = 3

        # Stale recovery detects exhausted attempts and routes to DLQ
        self.queue.recover_stale_jobs(timeout_seconds=0, max_attempts=3)
        self.assertEqual(self.queue.get_queue_length(), 0)
        self.assertEqual(self.queue.get_processing_length(), 0)
        self.assertEqual(self.queue.get_dlq_length(), 1)
        self.assertIn(job_id, self.queue.get_dlq_items())

    def test_explicit_move_to_dead_letter(self):
        job_id = "test_job_explicit_dlq_106"
        self.queue.enqueue_audit(job_id)
        self.queue.dequeue_audit(timeout=1, worker_id="worker_fatal")

        moved = self.queue.move_to_dead_letter(job_id, reason="fatal_syntax_error", worker_id="worker_fatal")
        self.assertTrue(moved)
        self.assertEqual(self.queue.get_processing_length(), 0)
        self.assertEqual(self.queue.get_dlq_length(), 1)
        self.assertIn(job_id, self.queue.get_dlq_items())


class TestReliableQueueLiveRedis(unittest.TestCase):
    """
    Integration Tests for the Reliable Queue Lifecycle using Real Redis on localhost:6379.
    Labels: [LIVE REDIS INTEGRATION]
    """

    @classmethod
    def setUpClass(cls):
        try:
            r = redis.Redis(host="localhost", port=6379, socket_timeout=1.0)
            r.ping()
            cls.redis_available = True
        except Exception:
            cls.redis_available = False

    def setUp(self):
        if not self.redis_available:
            self.skipTest("Live Redis server unavailable on localhost:6379. Skipping live Redis test.")
        self.queue_name = f"test_live_queue_{uuid.uuid4().hex[:8]}"
        self.queue = RedisAuditQueue(
            redis_url="redis://localhost:6379/0",
            queue_name=self.queue_name,
            redis_required=True,
            processing_timeout=1,
            max_attempts=3
        )
        self.queue.clear()

    def tearDown(self):
        if self.redis_available:
            self.queue.clear()

    def test_live_atomic_brpoplpush_and_acknowledgement(self):
        job_id = f"live_job_{uuid.uuid4().hex[:6]}"
        self.queue.enqueue_audit(job_id)
        self.assertEqual(self.queue.get_queue_length(), 1)
        self.assertEqual(self.queue.get_processing_length(), 0)

        # Dequeue atomically moves from queue_name to queue_name:processing
        dequeued = self.queue.dequeue_audit(timeout=2, worker_id="live_worker_1")
        self.assertEqual(dequeued, job_id)
        self.assertEqual(self.queue.get_queue_length(), 0)
        self.assertEqual(self.queue.get_processing_length(), 1)

        # Heartbeat update in Redis
        hb = self.queue.record_heartbeat(job_id, worker_id="live_worker_1")
        self.assertTrue(hb)

        # Acknowledge removes from processing
        self.queue.acknowledge(job_id, worker_id="live_worker_1")
        self.assertEqual(self.queue.get_processing_length(), 0)

    def test_live_worker_crash_stale_recovery(self):
        job_id = f"live_crash_job_{uuid.uuid4().hex[:6]}"
        self.queue.enqueue_audit(job_id)
        self.queue.dequeue_audit(timeout=2, worker_id="live_crashed_worker")
        self.assertEqual(self.queue.get_processing_length(), 1)

        # Stale recovery with 0s threshold re-enqueues back to pending queue
        recovered = self.queue.recover_stale_jobs(timeout_seconds=0, max_attempts=3)
        self.assertIn(job_id, recovered)
        self.assertEqual(self.queue.get_queue_length(), 1)
        self.assertEqual(self.queue.get_processing_length(), 0)

    def test_live_dlq_on_max_attempts(self):
        job_id = f"live_dlq_job_{uuid.uuid4().hex[:6]}"
        self.queue.enqueue_audit(job_id)
        self.queue.dequeue_audit(timeout=2, worker_id="live_worker_retries")

        # Set attempts to max_attempts (3)
        self.queue._redis_client.hset(self.queue.attempts_key, job_id, 3)

        # Stale recovery routes to DLQ
        self.queue.recover_stale_jobs(timeout_seconds=0, max_attempts=3)
        self.assertEqual(self.queue.get_processing_length(), 0)
        self.assertEqual(self.queue.get_dlq_length(), 1)
        self.assertIn(job_id, self.queue.get_dlq_items())


class TestIdempotencyAndDuplicatePrevention(unittest.TestCase):
    """
    Tests ensuring duplicate job processing is prevented and at-least-once delivery is safe.
    Labels: [IDEMPOTENCY / AT-LEAST-ONCE SEMANTICS]
    """

    def test_processor_skips_already_completed_job(self):
        session = MagicMock()
        mock_job = MagicMock()
        mock_job.status = AuditStatus.COMPLETED
        mock_job.request_id = "req_123"

        with patch("backend.src.db.repositories.AuditRepository.get_audit", return_value=mock_job):
            # When processor receives a job already COMPLETED in DB, it returns True without re-running LangGraph
            with patch("backend.src.graph.workflow.app.invoke") as mock_graph_invoke:
                success = AuditTaskProcessor.process_audit_job(session, "completed_audit_id", worker_id="worker_x")
                self.assertTrue(success)
                mock_graph_invoke.assert_not_called()

    def test_processor_skips_already_failed_job(self):
        session = MagicMock()
        mock_job = MagicMock()
        mock_job.status = AuditStatus.FAILED
        mock_job.request_id = "req_456"

        with patch("backend.src.db.repositories.AuditRepository.get_audit", return_value=mock_job):
            with patch("backend.src.graph.workflow.app.invoke") as mock_graph_invoke:
                success = AuditTaskProcessor.process_audit_job(session, "failed_audit_id", worker_id="worker_x")
                self.assertTrue(success)
                mock_graph_invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
