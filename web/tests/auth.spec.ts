import { spawn, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

const root = resolve("..");
const python = resolve(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const password = "browser-test-only passphrase 42";

test("named sign-in, scoped viewer, reviewer disposition and logout", async ({page, request}) => {
  const port = await new Promise<number>(done => { const socket = createServer(); socket.listen(0, "127.0.0.1", () => { const address = socket.address() as {port: number}; socket.close(() => done(address.port)); }); });
  const endpoint = `http://127.0.0.1:${port}`;
  const db = `sqlite:///${resolve(root, "data", `browser-auth-${Date.now()}.db`).replaceAll("\\", "/")}`;
  const env = {...process.env, GOVERNLOOM_DB: db, GOVERNLOOM_AUTH_MODE: "operators", GOVERNLOOM_ALLOWED_ORIGINS: endpoint};
  let server: ChildProcess | undefined;
  await new Promise<void>((done, reject) => {
    const child = spawn(python, ["-m", "governloom.cli", "--db", db, "bootstrap-admin", "admin", "--password-stdin"], {cwd: root, env, windowsHide: true});
    child.on("error", reject); child.on("exit", code => code === 0 ? done() : reject(new Error("Bootstrap failed")));
    child.stdin.end(password + "\n");
  });
  try {
    server = spawn(python, ["-m", "uvicorn", "governloom.api:app", "--host", "127.0.0.1", "--port", String(port)], {cwd: root, env, windowsHide: true, stdio: "ignore"});
    server.on("error", () => {});
    await expect.poll(async () => { try { return (await request.get(endpoint + "/api/health")).status(); } catch { return 0; } }).toBe(200);
    const session = await (await request.post(endpoint + "/api/auth/login", {data: {username: "admin", password}})).json();
    const adminHeaders = {Authorization: "Bearer " + session.token};
    const application = await (await request.post(endpoint + "/api/applications", {headers: adminHeaders, data: {name: "Scoped vision", purpose: "Vision test", owner: "Test", expected_behavior: "Review risk"}})).json();
    for (const role of ["viewer", "reviewer"]) {
      expect((await request.post(endpoint + "/api/auth/users", {headers: adminHeaders, data: {username: role, password, role, application_ids: [application.id]}})).status()).toBe(201);
    }
    const prefix = endpoint + `/api/applications/${application.id}`;
    expect((await request.post(prefix + "/detector-profiles", {headers: adminHeaders, data: {name: "CI distribution control", actor: "spoofed", kind: "distribution_shift", task_type: "vision", environment: "test", model_version: "test-v1", application_version: "test-v1", metric: "confidence", reference: Array(20).fill(.8), window_size: 20, calibration: {dataset_sha256: "a".repeat(64), labels_sha256: "b".repeat(64), label_provenance: "engineering", description: "Software fixture, not measured model quality", calibration_groups: ["cal"], held_out_groups: ["held"], true_positives: 1, false_positives: 0, true_negatives: 1, false_negatives: 0}}})).status()).toBe(201);
    await request.post(prefix + "/monitor-policy", {headers: adminHeaders, data: {name: "Low confidence", actor: "spoofed", rationale: "Test", rules: [{id: "confidence", name: "Review confidence", detector: "metric_threshold", metric: "confidence", comparator: "lt", threshold: .6, action: "review", mitigation: "Inspect prediction"}]}});
    const key = await (await request.post(prefix + "/ingest-keys", {headers: adminHeaders, data: {name: "service", actor: "spoofed"}})).json();
    await request.post(endpoint + "/api/runtime/events", {headers: {Authorization: "Bearer " + key.key}, data: {trace_id: "browser-auth", phase: "output", task_type: "vision", model_version: "test-v1", application_version: "test-v1", metrics: {confidence: .2}}});
    await page.goto(endpoint);
    await page.getByLabel("Username", {exact: true}).fill("viewer"); await page.getByLabel("Password", {exact: true}).fill(password); await page.getByRole("button", {name: "Sign in", exact: true}).click();
    await expect(page.getByText("Signed in as")).toContainText("viewer");
    await expect(page.getByRole("button", {name: "Create ingestion key"})).toBeDisabled();
    await page.locator(".detector-profiles").getByText("CI distribution control · awaiting review", {exact: true}).click();
    await expect(page.getByRole("button", {name: "Approve detector evidence"})).toBeDisabled();
    await page.locator(".runtime-incident").getByText("Assign or review incident", {exact: true}).click();
    await expect(page.locator(".runtime-incident").getByRole("button", {name: "Save incident disposition"})).toBeDisabled();
    await expect(page.getByLabel("Monitoring operator")).toHaveValue("viewer");
    expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain("go_");
    await page.getByRole("button", {name: "Sign out", exact: true}).click();
    await expect(page.getByRole("button", {name: "Sign in", exact: true})).toBeVisible();
    await page.getByLabel("Username", {exact: true}).fill("reviewer"); await page.getByLabel("Password", {exact: true}).fill(password); await page.getByRole("button", {name: "Sign in", exact: true}).click();
    await page.locator(".detector-profiles").getByText("CI distribution control · awaiting review", {exact: true}).click();
    await page.getByLabel("Detector approval rationale").fill("Reviewed the software fixture and its explicit limitations");
    await page.getByRole("button", {name: "Approve detector evidence"}).click();
    await expect(page.locator(".detector-profiles").getByText("CI distribution control · approved", {exact: true})).toBeVisible();
    const incident = page.locator(".runtime-incident");
    await incident.getByText("Assign or review incident", {exact: true}).click();
    await incident.getByLabel("Incident owner").fill("reviewer");
    await incident.getByLabel("Incident disposition").selectOption("acknowledged");
    await incident.getByLabel("Incident rationale").fill("Investigating the actual event evidence");
    await incident.getByRole("button", {name: "Save incident disposition"}).click();
    await expect(page.getByText("Incident ownership and disposition recorded.")).toBeVisible();
    const audit = await (await request.get(prefix + "/review-events", {headers: adminHeaders})).json();
    expect(audit.some((r: {actor: string; action: string}) => r.actor === "reviewer" && r.action === "runtime_incident_review")).toBeTruthy();
    await page.reload();
    await expect(page.getByRole("button", {name: "Sign in", exact: true})).toBeVisible();
  } finally {
    if (server && server.exitCode === null) { server.kill(); await new Promise<void>(done => { server!.once("exit", () => done()); setTimeout(done, 5000); }); }
  }
});
