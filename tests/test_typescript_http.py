import json
import os
import shutil
import subprocess

import pytest

from governloom.monitoring import Monitor, MonitorPolicy
from governloom.schemas import Application


def test_typescript_sdk_against_real_collector(workbench, tmp_path):
    from examples.common import ROOT
    from examples.processes import Processes
    sdk = ROOT / "sdks/typescript/dist/index.js"
    if not sdk.exists() or not shutil.which("node"):
        pytest.skip("Build the optional Node SDK; its CI job runs this integration")
    app = workbench.create_application(Application(name="Node model", purpose="Cross-language event contract", owner="Test", expected_behavior="Deny write"))
    monitor = Monitor(workbench)
    monitor.policy(app["id"], MonitorPolicy(name="Tools", actor="Test", rationale="Enforcement before side effect",
        rules=[dict(id="tools", name="Tool boundary", detector="tool_allowlist", phase="tool", allowed=["search"], action="block", mitigation="Deny write")]))
    key = monitor.issue_key(app["id"], "node", "Test")["key"]
    code = """import assert from 'node:assert/strict';
import {RuntimeHook,PolicyViolation,prepareEvent} from './sdks/typescript/dist/index.js';
const scope={task_type:'custom',model_version:'node-1',application_version:'test'};
const hook=new RuntimeHook(process.env.TEST_ENDPOINT,process.env.TEST_KEY,{mode:'enforce'});
let called=false;
await assert.rejects(hook.wrapTool(async()=>{called=true},scope,'write')(),PolicyViolation);
assert.equal(called,false);
const observe=new RuntimeHook(process.env.TEST_ENDPOINT,process.env.TEST_KEY);
const events=[1,2].map(n=>prepareEvent({...scope,phase:'output',trace_id:'node-batch',event_id:'node-'+n,metrics:{prediction:n}}));
const first=await observe.emitBatch(events); const second=await observe.emitBatch(events);
assert.ok(first.results.every(row=>row.status===200)); assert.ok(second.results.every(row=>row.receipt.duplicate));
console.log('Node SDK actual collector: denied tool and exact batch replay pass');
"""
    with Processes(tmp_path / "logs") as processes:
        endpoint = processes.start("governloom.api:app", {"GOVERNLOOM_DB": workbench.store.url}, readiness="/api/health")
        result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", code], cwd=ROOT,
            env={**os.environ, "TEST_ENDPOINT": endpoint, "TEST_KEY": key}, timeout=20, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    assert len(monitor.events(app["id"])["events"]) == 3
    assert len(monitor.alerts(app["id"])) == 1
