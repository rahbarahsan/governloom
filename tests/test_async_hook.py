import asyncio
import json

import httpx
import pytest

from governloom.api import create_app
from governloom.async_hook import AsyncRuntimeHook
from governloom.contract import prepare_event
from governloom.hook import MonitoringUnavailable, PolicyViolation
from governloom.monitoring import Monitor, MonitorPolicy
from governloom.schemas import Application


def test_async_boundaries_task_receipts_batch_partial_replay_and_unavailable(workbench):
    app = workbench.create_application(Application(name="Async AI", purpose="Async service", owner="Test", expected_behavior="Deny write and withhold output"))
    monitor = Monitor(workbench)
    monitor.policy(app["id"], MonitorPolicy(name="Async boundaries", actor="Test", rationale="Explicit enforcement",
        rules=[dict(id="tools", name="Denied tool", detector="tool_allowlist", phase="tool", allowed=["search"], action="block", mitigation="Deny"),
               dict(id="confidence", name="Uncertainty", detector="metric_threshold", phase="output", metric="confidence", comparator="lt", threshold=.8, action="block", mitigation="Withhold")]))
    key = monitor.issue_key(app["id"], "async", "Test")["key"]
    scope = dict(task_type="vision", model_version="model-1", application_version="app-1")
    async def scenario():
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(workbench.store)))
        async with client:
            async with AsyncRuntimeHook("http://127.0.0.1", key, mode="enforce", client=client) as hook:
                calls = []
                async def target(value):
                    calls.append(value)
                    return {"confidence": value}
                blocked_tool = hook.wrap_tool(target, tool_name="write", **scope)
                with pytest.raises(PolicyViolation):
                    await blocked_tool(.1)
                assert not calls
                wrapped = hook.wrap(target, **scope, output_mapper=lambda value: {"metrics": value})
                with pytest.raises(PolicyViolation) as withheld:
                    await wrapped(.1)
                assert calls == [.1] and withheld.value.receipt["phase"] == "output"
                async def emit_and_read(identifier, confidence):
                    receipt = await hook.emit(enforce=False, **scope, trace_id=identifier, phase="output", metrics={"confidence": confidence})
                    await asyncio.sleep(0)
                    assert hook.last_receipt["event_id"] == receipt["event_id"]
                    return receipt["action"]
                assert await asyncio.gather(emit_and_read("risk", .2), emit_and_read("clear", .9)) == ["block", "allow"]
            async with AsyncRuntimeHook("http://127.0.0.1", key, client=client) as observe:
                fields = {**scope, "trace_id": "batch", "phase": "output", "metrics": {"confidence": .9}}
                bodies = [prepare_event(**{**fields, "event_id": "batch-1"}), prepare_event(**{**fields, "event_id": "batch-2"})]
                first = await observe.emit_batch(bodies)
                assert [item["status"] for item in first["results"]] == [200, 200]
                replay = await observe.emit_batch(bodies)
                assert all(item["receipt"]["duplicate"] for item in replay["results"])
                partial = await observe.emit_batch([{**bodies[0], "metrics": {"confidence": .1}}, {**fields, "event_id": "batch-3"}])
                assert [item["status"] for item in partial["results"]] == [409, 200]
                assert "text" not in json.dumps(partial["results"][0])
            denied = await client.post("http://127.0.0.1/api/runtime/events/batch", json={"events": bodies}, headers={"Authorization": "Bearer invalid"})
            assert denied.status_code == 401
            enforced = await client.post("http://127.0.0.1/api/runtime/events/batch", json={"events": [{**bodies[0], "client_mode": "enforce"}]}, headers={"Authorization": "Bearer " + key})
            assert enforced.status_code == 422 and "input" not in json.dumps(enforced.json())
        async def unavailable(event):
            raise MonitoringUnavailable("Explicit outage")
        async with AsyncRuntimeHook("http://127.0.0.1", key, transport=unavailable, on_unavailable="continue") as continuing:
            assert (await continuing.emit(**scope, trace_id="outage", phase="output"))["action"] == "unavailable"
            assert continuing.unavailable_count == 1
    asyncio.run(scenario())
