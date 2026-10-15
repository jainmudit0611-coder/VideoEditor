import unittest
from backend.src.queue.redis_queue import RedisAuditQueue

class TestQueueLayer(unittest.TestCase):
    def test_enqueue_and_dequeue_local_dev_fallback(self):
        # Force fallback memory queue for isolated testing (REDIS_REQUIRED=False)
        queue_dev = RedisAuditQueue(
            redis_url="redis://invalid_host_for_test:9999/0",
            redis_required=False
        )
        audit_id_1 = "audit_uuid_100"
        audit_id_2 = "audit_uuid_200"

        queue_dev.enqueue_audit(audit_id_1)
        queue_dev.enqueue_audit(audit_id_2)

        self.assertGreaterEqual(queue_dev.get_queue_length(), 2)

        dequeued_1 = queue_dev.dequeue_audit(timeout=1)
        self.assertEqual(dequeued_1, audit_id_1)

        dequeued_2 = queue_dev.dequeue_audit(timeout=1)
        self.assertEqual(dequeued_2, audit_id_2)

        empty_pop = queue_dev.dequeue_audit(timeout=1)
        self.assertIsNone(empty_pop)

    def test_redis_required_production_failure(self):
        # Production mode (REDIS_REQUIRED=True) with invalid Redis server must raise RuntimeError
        with self.assertRaises(RuntimeError) as ctx:
            RedisAuditQueue(
                redis_url="redis://invalid_host_for_test:9999/0",
                redis_required=True
            )
        self.assertIn("REDIS_REQUIRED is True", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
