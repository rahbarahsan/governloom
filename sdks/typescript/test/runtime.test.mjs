import assert from "node:assert/strict";
import {createServer} from "node:http";
import {test} from "node:test";
import {RuntimeHook, PolicyViolation, MonitoringUnavailable} from "../dist/index.js";

test("real HTTP boundary blocks before tools, withholds after inference, batches stable IDs and denies redirect", async () => {
  const received = []; let behavior = "normal";
  const server = createServer(async (request, response) => {
    let text = ""; for await (const chunk of request) text += chunk;
    const body = JSON.parse(text); received.push(body);
    if (behavior === "redirect") {response.writeHead(302, {Location: "http://127.0.0.1:1/leak"}); response.end(); return;}
    if (behavior === "offline") {response.writeHead(503); response.end(); return;}
    response.setHeader("Content-Type", "application/json");
    const receipt = event => ({event_id: event.event_id, action: ["output", "tool"].includes(event.phase) ? "block" : "allow", checks: []});
    response.end(JSON.stringify(body.events ? {schema_version: 1, results: body.events.map(event => ({event_id: event.event_id, status: 200, receipt: receipt(event)}))} : receipt(body)));
  });
  await new Promise(done => server.listen(0, "127.0.0.1", done));
  const endpoint = `http://127.0.0.1:${server.address().port}`;
  const scope = {task_type: "vision", model_version: "real-http-contract", application_version: "test"};
  try {
    const hook = new RuntimeHook(endpoint, "gl_test", {mode: "enforce"});
    let calls = 0;
    await assert.rejects(hook.wrapTool(async () => {calls++;}, scope, "write")(), PolicyViolation);
    assert.equal(calls, 0);
    await assert.rejects(hook.wrap(async () => {calls++; return {confidence: .1};}, scope, {output: value => ({metrics: {confidence: value.confidence}})})(), PolicyViolation);
    assert.equal(calls, 1); assert.equal(received.at(-1).phase, "output");
    const observe = new RuntimeHook(endpoint, "gl_test");
    const result = await observe.emitBatch([{...scope, trace_id: "batch", phase: "output", event_id: "stable-id"}]);
    assert.equal(result.results[0].event_id, "stable-id");
    await assert.rejects(hook.emitBatch([{...scope, trace_id: "batch", phase: "output"}]), /observe/);
    behavior = "redirect";
    await assert.rejects(observe.emit({...scope, trace_id: "redirect", phase: "output"}), error => error instanceof MonitoringUnavailable && error.status === 302 && !error.retryable);
    behavior = "offline";
    const continuing = new RuntimeHook(endpoint, "gl_test", {onUnavailable: "continue"});
    assert.equal((await continuing.emit({...scope, trace_id: "outage", phase: "output"})).action, "unavailable");
    assert.equal(continuing.unavailableCount, 1);
  } finally {await new Promise(done => server.close(done));}
});
