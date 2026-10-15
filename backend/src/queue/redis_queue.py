import json
import time
import queue
import logging
from typing import Optional, List, Dict, Any
import redis
from backend.src.config import settings
from backend.src.observability import (
    log_event,
    ObservabilityEvent,
    get_logger,
)
from backend.src.observability.redaction import sanitize_url

logger = get_logger("brand-guardian-queue")


class RedisAuditQueue:
    """
    Production-Reliable Redis Task Queue for Asynchronous Multimodal Audit Jobs.

    Lifecycle & Delivery Semantics:
    -------------------------------
    - At-Least-Once Delivery: Jobs are never deleted from Redis upon dequeue. Instead,
      an atomic queue transfer (BRPOPLPUSH) moves the job from the pending queue to a
      dedicated processing list (in-flight state).
    - Idempotency & Duplicate Prevention: Consumers must treat job execution as idempotent.
      If a worker crashes or processing times out before acknowledgement, the job is
      re-queued. Downstream consumers verify whether the job has already been persisted
      (e.g., status COMPLETED or FAILED in DB) before re-executing.
    - Heartbeat Leases: Active workers record heartbeats for in-flight jobs.
    - Stale Job Recovery: Jobs in the processing list exceeding the configured processing
      timeout without heartbeats are automatically recovered and re-queued.
    - Dead-Letter Queue (DLQ): If a job exhausts its maximum attempt threshold, it is
      atomically transferred from the processing list to the DLQ, preserving diagnostic context.
    - Safe Acknowledgement: A job is only removed from the processing queue after its outcome
      has been confirmed and persisted by the database repository.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        queue_name: str = "brand_guardian_audit_queue",
        redis_required: Optional[bool] = None,
        processing_timeout: Optional[int] = None,
        max_attempts: Optional[int] = None,
    ):
        self.queue_name = queue_name
        self.processing_queue_name = f"{queue_name}:processing"
        self.dlq_name = f"{queue_name}:dlq"
        self.in_flight_key = f"{queue_name}:in_flight"
        self.attempts_key = f"{queue_name}:attempts"

        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_required = redis_required if redis_required is not None else settings.REDIS_REQUIRED
        self.processing_timeout = processing_timeout or getattr(settings, "QUEUE_PROCESSING_TIMEOUT_SECONDS", 300)
        self.max_attempts = max_attempts or getattr(settings, "MAX_RETRIES", 3)

        self._redis_client: Optional[redis.Redis] = None

        # Local in-memory fallback state (used when REDIS_REQUIRED=False and Redis is offline)
        self._memory_queue: queue.Queue = queue.Queue()
        self._memory_processing: Dict[str, Dict[str, Any]] = {}
        self._memory_attempts: Dict[str, int] = {}
        self._memory_dlq: List[str] = []
        self._memory_dlq_metadata: Dict[str, Dict[str, Any]] = {}

        self.is_redis_available: bool = False
        self._connect()

    @property
    def redis_required(self) -> bool:
        """Returns True if Redis is mandatory for this queue instance."""
        return self._redis_required

    @redis_required.setter
    def redis_required(self, value: bool):
        self._redis_required = value

    def _connect(self):
        """Attempts to connect to Redis server."""
        safe_url = sanitize_url(self.redis_url)
        try:
            client = redis.Redis.from_url(
                self.redis_url,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                decode_responses=False
            )
            client.ping()
            self._redis_client = client
            self.is_redis_available = True
            logger.info(f"Connected to reliable Redis queue: {self.queue_name} ({safe_url})")
        except Exception as e:
            self.is_redis_available = False
            log_event(
                logger,
                ObservabilityEvent.QUEUE_UNAVAILABLE,
                level=logging.ERROR if self._redis_required else logging.WARNING,
                message=f"Redis connection failed: {e}",
                queue_name=self.queue_name,
                redis_required=self._redis_required
            )
            if self._redis_required:
                logger.error(f"CRITICAL: Redis connection failed ({e}) and REDIS_REQUIRED is True!")
                raise RuntimeError(f"Redis connection failed ({e}) and REDIS_REQUIRED is True.")
            else:
                logger.warning(f"Redis server unavailable ({e}). Falling back to internal memory queue (local dev mode).")

    def reconnect(self):
        """Re-initializes connection attempt to Redis."""
        self._connect()

    def enqueue_audit(self, audit_id: str) -> bool:
        """
        Pushes an audit_id into the pending FIFO queue.
        Returns True on success, raises RuntimeError if Redis is required and offline.
        """
        t0 = time.time()
        if self.is_redis_available and self._redis_client:
            try:
                self._redis_client.rpush(self.queue_name, audit_id)
                dur_ms = int((time.time() - t0) * 1000)
                log_event(
                    logger,
                    ObservabilityEvent.QUEUE_ENQUEUE,
                    message=f"Enqueued audit_id={audit_id} to Redis queue: {self.queue_name}",
                    audit_id=audit_id,
                    queue_name=self.queue_name,
                    queue_backend="redis",
                    duration_ms=dur_ms
                )
                return True
            except Exception as e:
                self.is_redis_available = False
                log_event(
                    logger,
                    ObservabilityEvent.QUEUE_UNAVAILABLE,
                    level=logging.ERROR,
                    message=f"Failed to enqueue audit {audit_id} to Redis: {e}",
                    audit_id=audit_id,
                    queue_name=self.queue_name
                )
                if self._redis_required:
                    logger.error(f"CRITICAL: Failed to enqueue audit {audit_id} to Redis and REDIS_REQUIRED is True!")
                    raise RuntimeError(f"Failed to enqueue audit {audit_id} to Redis queue: {e}")
                logger.error(f"Failed to enqueue to Redis ({e}), pushing to fallback memory queue.")

        if self._redis_required:
            logger.error(f"CRITICAL: Cannot enqueue audit {audit_id}: Redis is unavailable and REDIS_REQUIRED is True!")
            raise RuntimeError(f"Cannot enqueue audit {audit_id}: Redis is unavailable and REDIS_REQUIRED is True.")

        self._memory_queue.put(audit_id)
        dur_ms = int((time.time() - t0) * 1000)
        log_event(
            logger,
            ObservabilityEvent.QUEUE_ENQUEUE,
            message=f"Enqueued audit_id={audit_id} to Memory queue.",
            audit_id=audit_id,
            queue_name=self.queue_name,
            queue_backend="memory",
            duration_ms=dur_ms
        )
        return True

    def dequeue_audit(self, timeout: int = 2, worker_id: Optional[str] = None) -> Optional[str]:
        """
        Atomically dequeues an audit_id from the pending queue into the processing queue.
        Guarantees that the job is never lost if the worker crashes immediately after dequeue.
        """
        t0 = time.time()
        worker = worker_id or "unknown_worker"

        if self.is_redis_available and self._redis_client:
            try:
                # Atomic transfer: pop from tail of queue_name, push to head of processing_queue_name
                raw_val = self._redis_client.brpoplpush(
                    self.queue_name,
                    self.processing_queue_name,
                    timeout=timeout
                )
                if raw_val:
                    audit_id = raw_val.decode("utf-8") if isinstance(raw_val, bytes) else str(raw_val)

                    # Track in-flight processing metadata
                    now = time.time()
                    in_flight_data = {
                        "worker_id": worker,
                        "started_at": now,
                        "heartbeat_at": now,
                    }
                    pipe = self._redis_client.pipeline()
                    pipe.hset(self.in_flight_key, audit_id, json.dumps(in_flight_data))
                    pipe.hincrby(self.attempts_key, audit_id, 1)
                    pipe.execute()

                    dur_ms = int((time.time() - t0) * 1000)
                    log_event(
                        logger,
                        ObservabilityEvent.QUEUE_DEQUEUE,
                        message=f"Atomically dequeued audit_id={audit_id} to processing queue ({worker}).",
                        audit_id=audit_id,
                        worker_id=worker,
                        queue_name=self.queue_name,
                        processing_queue=self.processing_queue_name,
                        queue_backend="redis",
                        duration_ms=dur_ms
                    )
                    return audit_id
                return None
            except Exception as e:
                self.is_redis_available = False
                log_event(
                    logger,
                    ObservabilityEvent.QUEUE_UNAVAILABLE,
                    level=logging.ERROR if self._redis_required else logging.WARNING,
                    message=f"Redis dequeue failed: {e}",
                    queue_name=self.queue_name
                )
                if self._redis_required:
                    logger.error(f"CRITICAL: Redis dequeue failed ({e}) and REDIS_REQUIRED is True!")
                    raise RuntimeError(f"Redis dequeue failed ({e}) and REDIS_REQUIRED is True.")
                logger.warning(f"Redis dequeue failed ({e}), checking fallback memory queue.")

        if self._redis_required:
            logger.error("CRITICAL: Cannot dequeue audit: Redis is unavailable and REDIS_REQUIRED is True!")
            raise RuntimeError("Cannot dequeue audit: Redis is unavailable and REDIS_REQUIRED is True.")

        # Memory Fallback Dequeue
        try:
            audit_id = self._memory_queue.get(timeout=timeout)
            now = time.time()
            attempts = self._memory_attempts.get(audit_id, 0) + 1
            self._memory_attempts[audit_id] = attempts
            self._memory_processing[audit_id] = {
                "worker_id": worker,
                "started_at": now,
                "heartbeat_at": now,
                "attempts": attempts,
            }
            dur_ms = int((time.time() - t0) * 1000)
            log_event(
                logger,
                ObservabilityEvent.QUEUE_DEQUEUE,
                message=f"Dequeued audit_id={audit_id} from Memory queue to processing store.",
                audit_id=audit_id,
                worker_id=worker,
                queue_name=self.queue_name,
                queue_backend="memory",
                duration_ms=dur_ms
            )
            return audit_id
        except queue.Empty:
            return None

    def record_heartbeat(self, audit_id: str, worker_id: Optional[str] = None) -> bool:
        """
        Updates the in-flight processing timestamp to prevent the job from being classified as stale.
        """
        now = time.time()
        worker = worker_id or "unknown_worker"

        if self.is_redis_available and self._redis_client:
            try:
                raw_info = self._redis_client.hget(self.in_flight_key, audit_id)
                if raw_info:
                    info = json.loads(raw_info.decode("utf-8") if isinstance(raw_info, bytes) else str(raw_info))
                    info["heartbeat_at"] = now
                    if worker_id:
                        info["worker_id"] = worker
                    self._redis_client.hset(self.in_flight_key, audit_id, json.dumps(info))
                    # Also refresh worker heartbeat lease (30 second TTL)
                    self._redis_client.setex(f"{self.queue_name}:worker:{worker}", 30, str(now))
                    return True
                return False
            except Exception as e:
                logger.warning(f"Failed to record Redis heartbeat for {audit_id}: {e}")
                return False

        if audit_id in self._memory_processing:
            self._memory_processing[audit_id]["heartbeat_at"] = now
            if worker_id:
                self._memory_processing[audit_id]["worker_id"] = worker
            return True
        return False

    def acknowledge(self, audit_id: str, worker_id: Optional[str] = None):
        """
        Acknowledges complete processing of a job.
        Atomically removes the job from the processing list and clears tracking keys.
        Must only be invoked after the final job outcome has been persisted to the DB.
        """
        if self.is_redis_available and self._redis_client:
            try:
                pipe = self._redis_client.pipeline()
                pipe.lrem(self.processing_queue_name, 1, audit_id)
                pipe.hdel(self.in_flight_key, audit_id)
                pipe.hdel(self.attempts_key, audit_id)
                pipe.execute()
                log_event(
                    logger,
                    ObservabilityEvent.QUEUE_ACKNOWLEDGED,
                    message=f"Acknowledged and removed audit_id={audit_id} from processing queue.",
                    audit_id=audit_id,
                    worker_id=worker_id,
                    queue_name=self.queue_name
                )
                return
            except Exception as e:
                logger.error(f"Error acknowledging audit_id={audit_id} in Redis: {e}")

        # Memory Fallback Acknowledgement
        self._memory_processing.pop(audit_id, None)
        self._memory_attempts.pop(audit_id, None)
        log_event(
            logger,
            ObservabilityEvent.QUEUE_ACKNOWLEDGED,
            message=f"Acknowledged and removed audit_id={audit_id} from memory processing store.",
            audit_id=audit_id,
            worker_id=worker_id,
            queue_name=self.queue_name
        )

    def move_to_dead_letter(
        self,
        audit_id: str,
        reason: str = "max_attempts_exceeded",
        worker_id: Optional[str] = None
    ) -> bool:
        """
        Moves an exhausted or permanently failing job from the processing queue to the Dead-Letter Queue (DLQ).
        """
        metadata = {
            "audit_id": audit_id,
            "reason": reason,
            "moved_at": time.time(),
            "worker_id": worker_id or "system",
        }

        if self.is_redis_available and self._redis_client:
            try:
                pipe = self._redis_client.pipeline()
                pipe.lrem(self.processing_queue_name, 1, audit_id)
                pipe.rpush(self.dlq_name, audit_id)
                pipe.hset(f"{self.dlq_name}:metadata", audit_id, json.dumps(metadata))
                pipe.hdel(self.in_flight_key, audit_id)
                pipe.execute()

                log_event(
                    logger,
                    ObservabilityEvent.QUEUE_DEAD_LETTER,
                    level=logging.ERROR,
                    message=f"Moved audit_id={audit_id} to DLQ ({self.dlq_name}): reason={reason}",
                    audit_id=audit_id,
                    worker_id=worker_id,
                    dlq_name=self.dlq_name,
                    reason=reason
                )
                return True
            except Exception as e:
                logger.error(f"Failed to move audit {audit_id} to Redis DLQ: {e}")
                return False

        # Memory Fallback DLQ
        self._memory_processing.pop(audit_id, None)
        self._memory_dlq.append(audit_id)
        self._memory_dlq_metadata[audit_id] = metadata
        log_event(
            logger,
            ObservabilityEvent.QUEUE_DEAD_LETTER,
            level=logging.ERROR,
            message=f"Moved audit_id={audit_id} to Memory DLQ: reason={reason}",
            audit_id=audit_id,
            worker_id=worker_id,
            dlq_name=self.dlq_name,
            reason=reason
        )
        return True

    def recover_stale_jobs(
        self,
        timeout_seconds: Optional[int] = None,
        max_attempts: Optional[int] = None
    ) -> List[str]:
        """
        Scans in-flight jobs in the processing queue. If a job has been inactive
        (no heartbeat update) for longer than timeout_seconds, it is either:
        1. Transferred to the Dead-Letter Queue if attempts >= max_attempts, or
        2. Atomically re-queued back to the pending queue for another worker to process.

        Returns a list of recovered audit IDs.
        """
        timeout = timeout_seconds if timeout_seconds is not None else self.processing_timeout
        max_att = max_attempts if max_attempts is not None else self.max_attempts
        now = time.time()
        recovered: List[str] = []

        if self.is_redis_available and self._redis_client:
            try:
                # Read all items currently in processing list
                raw_items = self._redis_client.lrange(self.processing_queue_name, 0, -1)
                for raw_item in raw_items:
                    audit_id = raw_item.decode("utf-8") if isinstance(raw_item, bytes) else str(raw_item)
                    raw_info = self._redis_client.hget(self.in_flight_key, audit_id)

                    is_stale = False
                    last_active = now

                    if raw_info:
                        try:
                            info = json.loads(raw_info.decode("utf-8") if isinstance(raw_info, bytes) else str(raw_info))
                            last_active = info.get("heartbeat_at", info.get("started_at", 0))
                            if (now - last_active) >= timeout:
                                is_stale = True
                        except Exception:
                            is_stale = True
                    else:
                        # Orphan item in processing list without metadata
                        is_stale = True

                    if is_stale:
                        # Fetch total attempts
                        raw_att = self._redis_client.hget(self.attempts_key, audit_id)
                        attempts = int(raw_att) if raw_att else 1

                        if attempts >= max_att:
                            self.move_to_dead_letter(
                                audit_id,
                                reason=f"stale_timeout_exceeded_{timeout}s_attempts_{attempts}"
                            )
                        else:
                            # Re-queue back to pending queue
                            pipe = self._redis_client.pipeline()
                            pipe.lrem(self.processing_queue_name, 1, audit_id)
                            pipe.rpush(self.queue_name, audit_id)
                            pipe.hdel(self.in_flight_key, audit_id)
                            pipe.execute()

                            log_event(
                                logger,
                                ObservabilityEvent.QUEUE_STALE_RECOVERED,
                                level=logging.WARNING,
                                message=f"Recovered stale job audit_id={audit_id} (inactive for {int(now - last_active)}s). Re-enqueued.",
                                audit_id=audit_id,
                                queue_name=self.queue_name,
                                attempt=attempts,
                                max_attempts=max_att
                            )
                            recovered.append(audit_id)
                return recovered
            except Exception as e:
                logger.error(f"Error during Redis stale job recovery: {e}")
                return recovered

        # Memory Fallback Stale Recovery
        stale_ids = []
        for audit_id, info in list(self._memory_processing.items()):
            last_active = info.get("heartbeat_at", info.get("started_at", 0))
            if (now - last_active) >= timeout:
                stale_ids.append(audit_id)

        for audit_id in stale_ids:
            attempts = self._memory_attempts.get(audit_id, 1)
            if attempts >= max_att:
                self.move_to_dead_letter(
                    audit_id,
                    reason=f"stale_timeout_exceeded_{timeout}s_attempts_{attempts}"
                )
            else:
                self._memory_processing.pop(audit_id, None)
                self._memory_queue.put(audit_id)
                log_event(
                    logger,
                    ObservabilityEvent.QUEUE_STALE_RECOVERED,
                    level=logging.WARNING,
                    message=f"Recovered stale memory job audit_id={audit_id}. Re-enqueued.",
                    audit_id=audit_id,
                    queue_name=self.queue_name,
                    attempt=attempts,
                    max_attempts=max_att
                )
                recovered.append(audit_id)

        return recovered

    def get_queue_length(self) -> int:
        """Returns total pending items waiting in queue."""
        if self.is_redis_available and self._redis_client:
            try:
                return self._redis_client.llen(self.queue_name)
            except Exception:
                if self._redis_required:
                    raise RuntimeError("Failed to query Redis queue length and REDIS_REQUIRED is True.")
        return self._memory_queue.qsize()

    def get_processing_length(self) -> int:
        """Returns total in-flight jobs currently being processed."""
        if self.is_redis_available and self._redis_client:
            try:
                return self._redis_client.llen(self.processing_queue_name)
            except Exception:
                if self._redis_required:
                    raise RuntimeError("Failed to query Redis processing queue length and REDIS_REQUIRED is True.")
        return len(self._memory_processing)

    def get_dlq_length(self) -> int:
        """Returns total jobs in the Dead-Letter Queue."""
        if self.is_redis_available and self._redis_client:
            try:
                return self._redis_client.llen(self.dlq_name)
            except Exception:
                if self._redis_required:
                    raise RuntimeError("Failed to query Redis DLQ length and REDIS_REQUIRED is True.")
        return len(self._memory_dlq)

    def get_dlq_items(self) -> List[str]:
        """Returns all job IDs currently in the DLQ."""
        if self.is_redis_available and self._redis_client:
            try:
                raw_items = self._redis_client.lrange(self.dlq_name, 0, -1)
                return [r.decode("utf-8") if isinstance(r, bytes) else str(r) for r in raw_items]
            except Exception:
                return []
        return list(self._memory_dlq)

    def clear(self):
        """Flushes pending, processing, and DLQ queues (for test isolation)."""
        if self.is_redis_available and self._redis_client:
            try:
                self._redis_client.delete(
                    self.queue_name,
                    self.processing_queue_name,
                    self.dlq_name,
                    self.in_flight_key,
                    self.attempts_key,
                    f"{self.dlq_name}:metadata"
                )
            except Exception:
                pass
        with self._memory_queue.mutex:
            self._memory_queue.queue.clear()
        self._memory_processing.clear()
        self._memory_attempts.clear()
        self._memory_dlq.clear()
        self._memory_dlq_metadata.clear()


# Global queue singleton instance
audit_queue = RedisAuditQueue()
