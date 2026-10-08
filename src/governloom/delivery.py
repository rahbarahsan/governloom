"""Bounded, in-memory observation delivery. Never performs inline enforcement."""

import json
import math
import random
import threading
import time
from collections import deque

from .hook import MonitoringUnavailable, RuntimeHook
from .monitoring import RuntimeEvent
from .schemas import uid


class ObservationHook(RuntimeHook):
    def __init__(self, endpoint, key, *, queue_size=256, max_queue_bytes=1_000_000,
                 max_age_seconds=30, max_attempts=4, backoff_seconds=0.1, **kwargs):
        if kwargs.get("mode", "observe") != "observe":
            raise ValueError("Background observation cannot enforce a policy")
        kwargs.pop("mode", None)
        super().__init__(endpoint, key, mode="observe", **kwargs)
        if not isinstance(queue_size, int) or not 1 <= queue_size <= 10000:
            raise ValueError("Queue size must be 1..10000")
        if not isinstance(max_queue_bytes, int) or not 1 <= max_queue_bytes <= 64_000_000:
            raise ValueError("Queue byte bound must be 1..64000000")
        if not math.isfinite(max_age_seconds) or not 0 < max_age_seconds <= 300:
            raise ValueError("Maximum event age must be positive and at most 300 seconds")
        if not isinstance(max_attempts, int) or not 1 <= max_attempts <= 10:
            raise ValueError("Attempt bound must be 1..10")
        if not math.isfinite(backoff_seconds) or not 0 <= backoff_seconds <= 30:
            raise ValueError("Backoff must be 0..30 seconds")
        self.capacity, self.byte_bound = queue_size, max_queue_bytes
        self.max_age, self.max_attempts, self.backoff = max_age_seconds, max_attempts, backoff_seconds
        self.condition = threading.Condition()
        self.queue = deque()
        self.bytes_pending = 0
        self.inflight = False
        self.closed = False
        self.stop = threading.Event()
        self.counters = {name: 0 for name in ("emitted", "queued", "accepted", "dropped", "failed", "retries", "expired", "auth_failed", "rate_limited", "invalid")}
        self.worker = threading.Thread(target=self._run, name="governloom-observation", daemon=True)
        self.worker.start()

    @property
    def stats(self):
        with self.condition:
            return {**self.counters, "pending": len(self.queue) + int(self.inflight), "bytes_pending": self.bytes_pending,
                    "worker_alive": self.worker.is_alive(), "closed": self.closed}

    def emit(self, *, enforce=True, **fields):
        event = RuntimeEvent(**{**fields, "client_mode": "observe"}).model_dump(mode="json")
        # Freeze ID, timestamp, text and metrics once. Only RAM holds transient text.
        payload = json.dumps(event, ensure_ascii=False, allow_nan=False).encode("utf-8")
        with self.condition:
            self.counters["emitted"] += 1
            reason = "closed" if self.closed else "overflow" if (len(self.queue) + int(self.inflight) >= self.capacity or
                self.bytes_pending + len(payload) > self.byte_bound) else None
            if reason:
                self.counters["dropped"] += 1
                return {"action": "dropped", "event_id": event["event_id"], "reason": reason}
            self.queue.append((payload, time.monotonic()))
            self.bytes_pending += len(payload)
            self.counters["queued"] += 1
            self.condition.notify()
        return {"action": "queued", "event_id": event["event_id"], "trace_id": event["trace_id"]}

    def _deliver(self, payload, started):
        for attempt in range(self.max_attempts):
            if self.stop.is_set():
                return "dropped"
            if time.monotonic() - started >= self.max_age:
                return "expired"
            try:
                event = json.loads(payload)
                receipt = self.transport(event)
                if not isinstance(receipt, dict) or receipt.get("event_id") != event["event_id"] or receipt.get("action") not in ("allow", "flag", "review", "block"):
                    raise MonitoringUnavailable("Invalid collector receipt", retryable=False)
                with self.condition:
                    self.last_receipt = receipt
                return "accepted"
            except MonitoringUnavailable as exc:
                with self.condition:
                    if exc.status_code == 401:
                        self.counters["auth_failed"] += 1
                    elif exc.status_code == 429:
                        self.counters["rate_limited"] += 1
                    elif exc.status_code in (400, 409, 422) or not exc.retryable:
                        self.counters["invalid"] += 1
                if not exc.retryable or attempt + 1 == self.max_attempts:
                    return "failed"
                delay = max(self.backoff * 2 ** attempt * random.uniform(0.75, 1.25), exc.retry_after_seconds or 0)
                remaining = self.max_age - (time.monotonic() - started)
                if delay >= remaining:
                    return "expired"
                with self.condition:
                    self.counters["retries"] += 1
                if self.stop.wait(delay):
                    return "dropped"
            except Exception:
                # Custom transport failures are counted, with no sensitive diagnostics.
                return "failed"
        return "failed"

    def _run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.queue or self.stop.is_set())
                if self.stop.is_set() and not self.queue:
                    return
                payload, started = self.queue.popleft()
                self.inflight = True
            outcome = self._deliver(payload, started)
            with self.condition:
                self.counters[outcome] += 1
                self.bytes_pending -= len(payload)
                self.inflight = False
                self.condition.notify_all()

    def close(self, drain_seconds=5):
        if not math.isfinite(drain_seconds) or not 0 <= drain_seconds <= 300:
            raise ValueError("Drain deadline must be 0..300 seconds")
        deadline = time.monotonic() + drain_seconds
        with self.condition:
            self.closed = True
            while (self.queue or self.inflight) and time.monotonic() < deadline:
                self.condition.wait(max(0, deadline - time.monotonic()))
            self.stop.set()
            while self.queue:
                payload, _ = self.queue.popleft()
                self.counters["dropped"] += 1
                self.bytes_pending -= len(payload)
            self.condition.notify_all()
        self.worker.join(timeout=max(0, deadline - time.monotonic()))
        # An in-flight HTTP request cannot be cancelled; its configured timeout
        # bounds the default transport. Expose it instead of claiming a drain.
        return self.stats

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class HeartbeatReporter:
    """Independent cadence; cumulative counters and a new boot ID per process."""
    def __init__(self, hook, agent_id, *, interval_seconds=30):
        if not math.isfinite(interval_seconds) or not 0 < interval_seconds <= 86400:
            raise ValueError("Heartbeat interval must be positive and at most one day")
        self.hook, self.agent_id, self.interval = hook, agent_id, interval_seconds
        self.boot_id, self.sequence = uid(), 1
        from .monitoring import Heartbeat
        Heartbeat(agent_id=agent_id, boot_id=self.boot_id, sequence=1)
        self.sent, self.failures = 0, 0
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self._run, name="governloom-heartbeat", daemon=True)
        self.worker.start()

    def _run(self):
        from .monitoring import Heartbeat
        body = None
        while not self.stop.is_set():
            if body is None:
                stats = self.hook.stats
                body = Heartbeat(agent_id=self.agent_id, boot_id=self.boot_id, sequence=self.sequence,
                    counters={name: stats[name] for name in self.hook.counters.keys() | {"pending"}}).model_dump(mode="json")
            try:
                self.hook.heartbeat(**body)
                self.sent += 1
                self.sequence += 1
                body = None
            except MonitoringUnavailable:
                self.failures += 1
                # Preserve the same sequence/body until acceptance is known.
            if self.stop.wait(self.interval):
                return

    def close(self, timeout_seconds=2):
        if not math.isfinite(timeout_seconds) or not 0 <= timeout_seconds <= 30:
            raise ValueError("Heartbeat shutdown timeout must be 0..30 seconds")
        self.stop.set()
        self.worker.join(timeout_seconds)
        return {"sent": self.sent, "failures": self.failures, "worker_alive": self.worker.is_alive()}
