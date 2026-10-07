"""Provider-independent Python hook for predictions, outcomes and tool calls."""

import functools
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .monitoring import RuntimeEvent
from .schemas import uid


class MonitoringUnavailable(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A collector redirect must never forward an ingestion credential.
        return None


class PolicyViolation(RuntimeError):
    def __init__(self, receipt):
        super().__init__("Runtime policy requested a block; inspect the associated GovernLoom alert")
        self.receipt = receipt


class RuntimeHook:
    def __init__(self, endpoint, key, *, mode="observe", timeout_seconds=1, on_unavailable="raise", transport=None):
        parsed = urlsplit(endpoint)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Specify an HTTP(S) collector base URL without credentials/query/fragment")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Remote collectors require HTTPS")
        if mode not in ("observe", "enforce") or on_unavailable not in ("raise", "continue"):
            raise ValueError("Specify observe/enforce mode and raise/continue availability behavior")
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 30:
            raise ValueError("Hook timeout must be positive and at most 30 seconds")
        if not isinstance(key, str) or not key.startswith("gl_") or "\n" in key or "\r" in key:
            raise ValueError("Use a GovernLoom ingestion key")
        self.endpoint = endpoint.rstrip("/")
        self.key = key
        self.mode = mode
        self.timeout = timeout_seconds
        self.on_unavailable = on_unavailable
        self.transport = transport or self._send
        self.opener = build_opener(NoRedirect())
        self.last_receipt = None
        self.unavailable_count = 0

    def _send(self, event):
        request = Request(self.endpoint + "/api/runtime/events", data=json.dumps(event).encode("utf-8"),
                          headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}, method="POST")
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise MonitoringUnavailable("Collector did not accept the event")
                payload = response.read(1_000_001)
                if len(payload) > 1_000_000:
                    raise MonitoringUnavailable("Collector receipt exceeds the size limit")
                return json.loads(payload)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            # Never include URL credentials, event text or target output in errors.
            raise MonitoringUnavailable(f"Collector request failed ({type(exc).__name__})") from None

    def emit(self, *, enforce=True, **fields):
        event = RuntimeEvent(**{**fields, "client_mode": self.mode}).model_dump(mode="json")
        try:
            receipt = self.transport(event)
            if not isinstance(receipt, dict) or receipt.get("action") not in ("allow", "flag", "review", "block") or receipt.get("event_id") != event["event_id"]:
                raise MonitoringUnavailable("Collector returned an invalid receipt")
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

    def wrap(self, function, *, task_type, model_version, application_version, input_mapper=None, output_mapper=None, environment="production"):
        """Mappers explicitly select telemetry; images/arrays are never auto-uploaded."""
        context = {"task_type": task_type, "model_version": model_version,
                   "application_version": application_version, "environment": environment}

        @functools.wraps(function)
        def monitored(*args, **kwargs):
            trace_id = uid()
            before = input_mapper(*args, **kwargs) if input_mapper else {}
            self.emit(**{**before, **context, "trace_id": trace_id, "phase": "input"})
            started = time.perf_counter()
            try:
                result = function(*args, **kwargs)
            except Exception as exc:
                try:
                    self.emit(enforce=False, **context, trace_id=trace_id, phase="error", error_type=type(exc).__name__,
                              metrics={"latency_ms": (time.perf_counter() - started) * 1000})
                except MonitoringUnavailable:
                    pass
                raise
            latency = (time.perf_counter() - started) * 1000
            after = output_mapper(result) if output_mapper else {}
            after = {**after, "metrics": {**after.get("metrics", {}), "latency_ms": latency}}
            self.emit(**{**after, **context, "trace_id": trace_id, "phase": "output"})
            return result

        return monitored

    def wrap_tool(self, function, *, tool_name, task_type, model_version, application_version, environment="production"):
        @functools.wraps(function)
        def monitored(*args, **kwargs):
            self.emit(trace_id=uid(), phase="tool", tool_name=tool_name, task_type=task_type,
                      model_version=model_version, application_version=application_version, environment=environment)
            return function(*args, **kwargs)
        return monitored
