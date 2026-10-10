"""Async Python integration; install governloom[async] for the httpx transport."""
import contextvars
import functools
import inspect
import json
import time

from .hook import MonitoringUnavailable, PolicyViolation, RuntimeHook, retry_delay
from .monitoring import ActionAcknowledgment, Heartbeat, RuntimeEvent
from .schemas import uid


class AsyncRuntimeHook(RuntimeHook):
    def __init__(self, endpoint, key, *, client=None, **options):
        import httpx
        self._receipt = contextvars.ContextVar("governloom_async_receipt", default=None)
        super().__init__(endpoint, key, **options)
        self.client = client or httpx.AsyncClient(timeout=self.timeout, follow_redirects=False, trust_env=False)
        self.owns_client = client is None

    @property
    def last_receipt(self):
        return self._receipt.get()

    @last_receipt.setter
    def last_receipt(self, value):
        self._receipt.set(value)

    async def _request(self, path, body):
        import httpx
        try:
            async with self.client.stream("POST", self.endpoint + path, content=json.dumps(body).encode(),
                headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"},
                follow_redirects=False, timeout=self.timeout) as response:
                if response.status_code != 200:
                    status = response.status_code
                    raise MonitoringUnavailable(f"Collector rejected request (HTTP {status})", retryable=status in (408, 429) or status >= 500,
                        status_code=status, retry_after_seconds=retry_delay(response.headers.get("Retry-After")))
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 1_000_000:
                        raise MonitoringUnavailable("Collector receipt exceeds size limit", retryable=False)
                return json.loads(data)
        except (httpx.HTTPError, ValueError):
            raise MonitoringUnavailable("Collector unavailable or invalid JSON response") from None

    async def emit(self, *, enforce=True, **fields):
        event = RuntimeEvent(**{**fields, "client_mode": self.mode}).model_dump(mode="json")
        try:
            receipt = await self.transport(event)
            if not isinstance(receipt, dict) or receipt.get("action") not in ("allow", "flag", "review", "block") or receipt.get("event_id") != event["event_id"]:
                raise MonitoringUnavailable("Collector returned an invalid receipt", retryable=False)
            self.last_receipt = receipt
        except MonitoringUnavailable:
            self.unavailable_count += 1
            self.last_receipt = {"action": "unavailable", "event_id": event["event_id"], "checks": []}
            if self.on_unavailable == "raise":
                raise
            return self.last_receipt
        if enforce and self.mode == "enforce" and receipt["action"] == "block":
            raise PolicyViolation(receipt)
        return receipt

    async def heartbeat(self, **fields):
        return await self._request("/api/runtime/heartbeats", Heartbeat(**fields).model_dump(mode="json"))

    async def acknowledge_action(self, **fields):
        return await self._request("/api/runtime/actions", ActionAcknowledgment(**fields).model_dump(mode="json"))

    async def emit_batch(self, events):
        if self.mode != "observe" or not 1 <= len(events) <= 100:
            raise ValueError("Batch delivery requires observe mode and 1..100 events")
        bodies = [RuntimeEvent(**{**event, "client_mode": "observe"}).model_dump(mode="json") for event in events]
        return await self._request("/api/runtime/events/batch", {"events": bodies})

    def wrap(self, function, *, task_type, model_version, application_version, input_mapper=None, output_mapper=None, environment="production"):
        context = {"task_type": task_type, "model_version": model_version, "application_version": application_version, "environment": environment}
        async def mapped(mapper, *args, **kwargs):
            result = mapper(*args, **kwargs) if mapper else {}
            return await result if inspect.isawaitable(result) else result
        @functools.wraps(function)
        async def monitored(*args, **kwargs):
            trace_id = uid()
            before = await mapped(input_mapper, *args, **kwargs)
            await self.emit(**{**before, **context, "trace_id": trace_id, "phase": "input"})
            started = time.perf_counter()
            try:
                result = await function(*args, **kwargs)
            except Exception as error:
                try:
                    await self.emit(enforce=False, **context, trace_id=trace_id, phase="error", error_type=type(error).__name__, metrics={"latency_ms": (time.perf_counter() - started) * 1000})
                except MonitoringUnavailable:
                    pass
                raise
            after = await mapped(output_mapper, result)
            after = {**after, "metrics": {**after.get("metrics", {}), "latency_ms": (time.perf_counter() - started) * 1000}}
            await self.emit(**{**after, **context, "trace_id": trace_id, "phase": "output"})
            return result
        return monitored

    def wrap_tool(self, function, *, tool_name, task_type, model_version, application_version, environment="production"):
        @functools.wraps(function)
        async def monitored(*args, **kwargs):
            await self.emit(trace_id=uid(), phase="tool", tool_name=tool_name, task_type=task_type,
                model_version=model_version, application_version=application_version, environment=environment)
            return await function(*args, **kwargs)
        return monitored

    async def aclose(self):
        if self.owns_client:
            await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
