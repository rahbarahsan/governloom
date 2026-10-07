import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { createConnection } from "node:net";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const python = resolve(
  root,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const directory = resolve(root, "data", `gif-capture-${Date.now()}`);
await mkdir(directory, { recursive: true });
const environment = {
  ...process.env,
  GOVERNLOOM_DB: `sqlite:///${resolve(directory, "demo.db").replaceAll("\\", "/")}`,
};
const children = [];
let browser;
const pause = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

async function occupied(port) {
  return new Promise((resolve) => {
    const socket = createConnection({ host: "127.0.0.1", port });
    socket.on("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.on("error", () => resolve(false));
  });
}

function start(executable, args, cwd = root) {
  const child = spawn(executable, args, {
    cwd,
    env: environment,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });
  child.diagnostic = "";
  child.stderr.on("data", (chunk) => {
    child.diagnostic += chunk;
  });
  child.on("error", (error) => {
    child.diagnostic += error.message;
  });
  children.push(child);
  return child;
}

async function ready(url, child) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null)
      throw new Error(child.diagnostic);
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      /* Process still starting. */
    }
    await pause(100);
  }
  throw new Error(`Startup timeout: ${url}\n${child.diagnostic}`);
}

async function request(path) {
  const response = await fetch(`http://127.0.0.1:8000/api${path}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

try {
  if ((await occupied(8000)) || (await occupied(5173)))
    throw new Error(
      "Capture requires free ports 8000 and 5173; stop existing local servers first.",
    );
  const api = start(python, [
    "-m",
    "uvicorn",
    "governloom.api:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
  ]);
  const vite = start(
    process.execPath,
    [
      resolve(root, "web/node_modules/vite/bin/vite.js"),
      "--host",
      "127.0.0.1",
      "--port",
      "5173",
      "--strictPort",
    ],
    resolve(root, "web"),
  );
  start(python, ["-m", "governloom.cli", "worker"]);
  await Promise.all([
    ready("http://127.0.0.1:8000/api/health", api),
    ready("http://127.0.0.1:5173", vite),
  ]);
  browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 },
    reducedMotion: "reduce",
    timezoneId: "UTC",
  });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const scenes = [];
  async function capture(caption, duration_ms, locator) {
    if (locator)
      await locator.evaluate((element) => {
        const top = element.getBoundingClientRect().top + window.scrollY;
        window.scrollTo(0, Math.max(0, top - 40));
      });
    else await page.evaluate(() => window.scrollTo(0, 0));
    await page.evaluate(() => document.fonts.ready);
    const file = `${String(scenes.length + 1).padStart(2, "0")}.png`;
    await page.screenshot({
      path: resolve(directory, file),
      animations: "disabled",
    });
    scenes.push({ caption, duration_ms, file });
    console.log(`Captured ${scenes.length}: ${caption}`);
  }

  await page.goto("http://127.0.0.1:5173");
  await page.getByRole("button", { name: "Load no-key demo" }).click();
  await expect(
    page.getByRole("heading", { name: "Northstar support · demo" }),
  ).toBeVisible();
  const application = (await request("/applications"))[0];
  await capture("Load fictional sources and 40 unreviewed fixtures", 1800);
  const source = page
    .locator(".source-row")
    .filter({ hasText: "billing-v2.md" });
  await source.locator("summary").click();
  await capture(
    "Inspect current source content and its immutable hash",
    1800,
    source,
  );

  await page.getByRole("button", { name: /02.*datasets/i }).click();
  await page
    .getByLabel("Reviewer name")
    .fill("Recorded demo (scripted fixture acceptance)");
  const candidate = (
    await request(`/applications/${application.id}/cases`)
  ).find(
    (item) => item.category === "answerable" && item.group_id === "billing",
  );
  const exactQuestion = new RegExp(
    `^${candidate.question.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`,
  );
  await page
    .locator(".case-item")
    .filter({ has: page.locator("span").filter({ hasText: exactQuestion }) })
    .click();
  await page.locator(".case-editor .evidence summary").first().click();
  await capture(
    "Review a candidate against its quoted policy passage",
    2400,
    page.locator(".review-layout"),
  );
  await page.getByRole("button", { name: "Save & approve" }).click();
  await expect(page.getByRole("status")).toContainText("Case revision saved");
  await capture(
    "Record an attributed approval and a new case revision",
    1600,
    page.locator(".review-layout"),
  );
  await page
    .getByRole("button", { name: /Approve remaining 39 cases/ })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Remaining candidates approved",
  );
  await page.getByRole("button", { name: "Publish approved dataset" }).click();
  await expect(page.getByText("Version 1 · 40 approved cases")).toBeVisible();
  await capture(
    "Freeze 40 approved cases with a dataset checksum",
    2000,
    page.locator(".dataset-row").first(),
  );
  await page.getByRole("button", { name: "Evaluate v1" }).click();
  await capture("Select a held-out sample and a bounded local target", 1600);

  async function evaluate(target) {
    await page.getByLabel("Target", { exact: true }).selectOption(target);
    await page.getByRole("button", { name: "Queue evaluation" }).click();
    await expect(page.getByRole("status")).toContainText("Evaluation queued");
    const run = (await request(`/runs?application_id=${application.id}`))[0];
    await expect
      .poll(async () => (await request(`/runs/${run.id}`)).status, {
        timeout: 20_000,
      })
      .toBe("completed");
    await page
      .getByRole("button", { name: new RegExp(`${run.id.slice(0, 8)}$`) })
      .click();
    await expect(
      page
        .locator("main > .content .panel")
        .filter({
          has: page.getByRole("heading", {
            name: `Run · ${target.replaceAll("_", " ")}`,
            exact: true,
          }),
        })
        .locator(".badge.completed"),
    ).toBeVisible();
    return run;
  }
  const clean = await evaluate("clean");
  const runPanel = () =>
    page.locator(".panel").filter({ has: page.locator(".run-progress") });
  await capture(
    "Clean run: separate metric scores, skips and unavailable checks",
    2200,
    runPanel(),
  );
  const faulty = await evaluate("invalid_citation");
  await capture(
    "Faulty run: 10 citation-consistency failures",
    2000,
    runPanel(),
  );
  await page.getByLabel("Baseline run").selectOption(clean.id);
  await page.getByLabel("Candidate run").selectOption(faulty.id);
  await page.getByRole("button", { name: "Compare selected runs" }).click();
  await expect(page.locator(".comparison .badge.compatible")).toBeVisible();
  await capture(
    "Compare the same 20 held-out cases with compatible evaluators",
    2600,
    page.locator(".comparison"),
  );
  await page
    .getByRole("button", { name: "Inspect findings & evidence" })
    .click();
  await expect(page.locator(".findings article")).toHaveCount(10);
  const finding = page.locator(".findings article").first();
  await capture(
    "Inspect the observed answer, invalid citation and expected behavior",
    2400,
    finding,
  );
  await finding.locator(".metric-findings summary").first().click();
  await finding.locator(".evidence summary").first().click();
  await expect(finding.locator("mark").first()).toBeVisible();
  await capture(
    "Follow a failed check back to frozen source evidence",
    2800,
    finding.locator(".metric-findings"),
  );
  if (errors.length) throw new Error(errors.join("\n"));
  await writeFile(
    resolve(directory, "manifest.json"),
    JSON.stringify({ schema_version: 1, scenes }, null, 2),
  );
  await new Promise((resolvePromise, reject) => {
    const encoder = spawn(
      python,
      [
        resolve(root, "scripts/encode_demo.py"),
        resolve(directory, "manifest.json"),
        "--output",
        resolve(root, "docs/media/demo.gif"),
      ],
      { cwd: root, windowsHide: true, stdio: "inherit" },
    );
    encoder.on("error", reject);
    encoder.on("exit", (code) =>
      code === 0
        ? resolvePromise()
        : reject(new Error(`GIF encoder exited ${code}`)),
    );
  });
  console.log(`Capture artifacts: ${directory}`);
} finally {
  await browser?.close();
  for (const child of children) if (child.exitCode === null) child.kill();
}
