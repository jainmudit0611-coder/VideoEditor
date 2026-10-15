import os
import sys
import time
import socket
import uuid
import logging
import signal

from backend.src.config import settings
from backend.src.db.database import SessionLocal, init_db
from backend.src.queue.redis_queue import audit_queue
from backend.src.worker.processor import AuditTaskProcessor
from backend.src.observability import (
    log_event,
    ObservabilityEvent,
    get_logger,
    set_correlation_context,
)

logger = get_logger("brand-guardian-worker")

class WorkerDaemon:
    """
    Background Task Worker Daemon that polls the Redis Audit Queue and processes video compliance audits.
    """
    def __init__(self, worker_id: str = None):
        self.running = True
        host = socket.gethostname().split(".")[0]
        self.worker_id = worker_id or f"worker_{host}_{os.getpid()}_{uuid.uuid4().hex[:6]}"
        self._last_stale_check: float = 0.0
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        log_event(
            logger,
            ObservabilityEvent.WORKER_SHUTDOWN,
            message=f"Received shutdown signal ({signum}). Gracefully stopping worker {self.worker_id}...",
            worker_id=self.worker_id
        )
        self.running = False

    def check_stale_jobs(self) -> list:
        """Periodically inspects processing queue and recovers stale/abandoned jobs."""
        now = time.time()
        if now - self._last_stale_check > 30.0:
            self._last_stale_check = now
            try:
                recovered = audit_queue.recover_stale_jobs()
                if recovered:
                    logger.info(f"Worker {self.worker_id} recovered {len(recovered)} stale job(s): {recovered}")
                return recovered
            except Exception as e_rec:
                logger.warning(f"Worker {self.worker_id} stale job recovery check error: {e_rec}")
        return []

    def run_single_loop(self) -> bool:
        """
        Executes a single dequeue and process iteration.
        Returns True if a job was processed, False otherwise.
        """
        set_correlation_context(worker_id=self.worker_id)
        self.check_stale_jobs()
        try:
            audit_id = audit_queue.dequeue_audit(timeout=2, worker_id=self.worker_id)
        except RuntimeError as e_redis:
            logger.warning(f"Redis queue dequeue error (REDIS_REQUIRED={audit_queue.redis_required}): {e_redis}")
            time.sleep(2.0)
            try:
                audit_queue.reconnect()
            except Exception:
                pass
            return False

        if not audit_id:
            return False

        logger.info(f"Dequeued job audit_id={audit_id}. Starting execution on {self.worker_id}...")
        session = SessionLocal()
        try:
            success = AuditTaskProcessor.process_audit_job(session, audit_id, worker_id=self.worker_id)
            if success:
                audit_queue.acknowledge(audit_id, worker_id=self.worker_id)
            return True
        except Exception as e:
            logger.error(f"Unhandled error processing audit_id={audit_id}: {e}")
            return False
        finally:
            session.close()

    def start(self):
        """Starts the infinite background worker polling loop."""
        init_db()
        log_event(
            logger,
            ObservabilityEvent.WORKER_STARTED,
            message=f"Initializing Brand Guardian AI Background Task Worker: worker_id={self.worker_id}",
            worker_id=self.worker_id
        )
        if audit_queue.redis_required and not audit_queue.is_redis_available:
            logger.warning("Worker starting with REDIS_REQUIRED=True but Redis connection is unavailable. Will attempt reconnection during polling loop.")

        logger.info(f"Worker {self.worker_id} actively listening for audit jobs in Redis queue...")

        while self.running:
            try:
                processed = self.run_single_loop()
                if not processed:
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Worker loop exception: {e}")
                time.sleep(1.0)

        log_event(
            logger,
            ObservabilityEvent.WORKER_SHUTDOWN,
            message=f"Worker daemon {self.worker_id} stopped cleanly.",
            worker_id=self.worker_id
        )

if __name__ == "__main__":
    daemon = WorkerDaemon()
    daemon.start()
