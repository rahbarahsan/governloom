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


def test_installed_node_tarball_observes_discovered_tool_policy(workbench, tmp_path):
    from examples.common import ROOT
    from examples.processes import Processes
    from governloom.discovery import Discovery, DiscoveryImport, Confirmation, CalibrationRequest, Activation
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm or not (ROOT/"sdks/typescript/dist/index.js").exists():
        pytest.skip("Build the optional Node SDK first; SDK CI runs this consumer")
    app = workbench.create_application(Application(name="Installed Node tool consumer", purpose="Discover permissions", owner="Owner", expected_behavior="Observe tool attempts"))
    service = Discovery(workbench)
    rows = [{"sample_id": index, "tool_name": "search" if index%2 else "write", "model_version": "node-v1", "application_version": "node-app-v1",
             "split": "calibration" if index<4 else "held_out"} for index in range(8)]
    draft = service.create(app["id"], DiscoveryImport(actor="owner", traces=rows))
    confirmation = service.confirm(app["id"], draft["id"], Confirmation(actor="owner", expected_checksum=draft["checksum"], task_type="custom",
        purpose="Review tool attempts", rationale="Owner confirms read-only permissions", mappings=draft["analysis"]["mappings"], allowed_tools=["search"]))
    plan = service.calibrate(app["id"], CalibrationRequest(actor="owner", confirmation_id=confirmation["id"]))
    service.activate(app["id"], plan["id"], Activation(actor="owner", expected_policy_id=None, acknowledge_limitations=True, rationale="Review flags"))
    key = Monitor(workbench).issue_key(app["id"], "node-consumer", "owner")["key"]
    environment = {**os.environ, "npm_config_cache": str(tmp_path/"npm-cache")}
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    packed = subprocess.run([npm, "pack", "--json", "--pack-destination", str(tmp_path)], cwd=ROOT/"sdks/typescript",
                            env=environment, capture_output=True, text=True, timeout=30, creationflags=flags)
    assert packed.returncode == 0, packed.stderr
    tarball = tmp_path/json.loads(packed.stdout)[0]["filename"]
    consumer = tmp_path/"consumer"
    consumer.mkdir()
    (consumer/"package.json").write_text('{"private":true,"type":"module"}', encoding="utf-8")
    installed = subprocess.run([npm, "install", "--offline", "--ignore-scripts", "--no-audit", "--no-fund", "--package-lock=false", str(tarball)],
                               cwd=consumer, env=environment, capture_output=True, text=True, timeout=30, creationflags=flags)
    assert installed.returncode == 0, installed.stderr
    (consumer/"check.mjs").write_text("""import assert from 'node:assert/strict';
import {RuntimeHook} from '@governloom/runtime';
const hook=new RuntimeHook(process.env.TEST_ENDPOINT,process.env.TEST_KEY);
const context={task_type:'custom',model_version:'node-v1',application_version:'node-app-v1',trace_id:'installed-node'};
const clear=await hook.emit({...context,phase:'tool',tool_name:'search'});
const flag=await hook.emit({...context,phase:'tool',tool_name:'write'});
assert.equal(clear.action,'allow');assert.equal(flag.action,'flag');
assert.equal(flag.checks[0].control_reference.control_id,'tools.permissions');
assert.ok(flag.checks[0].control_reference.references.some(row=>row.reference==='LLM06:2025'));
console.log('Installed Node tarball: discovered policy, clear/flag and frozen references pass');
""", encoding="utf-8")
    with Processes(tmp_path/"logs") as processes:
        endpoint = processes.start("governloom.api:app", {"GOVERNLOOM_DB": workbench.store.url}, readiness="/api/health")
        checked = subprocess.run([shutil.which("node"), "check.mjs"], cwd=consumer,
            env={**environment, "TEST_ENDPOINT": endpoint, "TEST_KEY": key}, capture_output=True, text=True, timeout=30, creationflags=flags)
        assert checked.returncode == 0, checked.stderr
    assert len(Monitor(workbench).incidents(app["id"])) == 1
