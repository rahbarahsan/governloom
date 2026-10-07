import { spawn, type ChildProcess } from "node:child_process";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

let worker: ChildProcess;
const python = resolve(
  "..",
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);

test.beforeAll(async () => {
  worker = spawn(python, ["-m", "governloom.cli", "worker"], {
    env: process.env,
    windowsHide: true,
  });
  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error("Worker startup timeout")),
      15_000,
    );
    worker.on("error", reject);
    worker.on("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`Worker exited: ${code}`));
    });
    worker.stdout?.on("data", (chunk) => {
      if (String(chunk).includes("worker ready")) {
        clearTimeout(timeout);
        resolve();
      }
    });
  });
});
test.afterAll(() => {
  worker?.kill();
});

test("manual case and trace imports preserve unavailable telemetry", async ({
  page,
  request,
}) => {
  const applications = await (
    await request.get("http://127.0.0.1:8000/api/applications")
  ).json();
  let application = applications.find(
    (app: { name: string }) => app.name === "Manual evidence app",
  );
  if (!application)
    application = await (
      await request.post("http://127.0.0.1:8000/api/applications", {
        data: {
          name: "Manual evidence app",
          purpose: "Support from local text",
          owner: "Browser reviewer",
          expected_behavior: "Answer from evidence",
          model_version: "manual-v1",
        },
      })
    ).json();
  const source = await (
    await request.post(
      `http://127.0.0.1:8000/api/applications/${application.id}/sources`,
      {
        data: {
          document_id: "manual-cafe",
          version: "1",
          filename: "manual.md",
          content: "Café policy: delivery is free.\n",
        },
      },
    )
  ).json();
  const quote = "delivery is free.";
  const start = source.content.indexOf(quote);
  const item = {
    schema_version: 1,
    id: "browser-manual-case",
    application_id: application.id,
    question: "What does delivery cost?",
    category: "answerable",
    expected_behavior: "answer",
    reference_answer: quote,
    references: [
      {
        source_id: source.id,
        start,
        end: start + quote.length,
        quote,
        content_hash: source.content_hash,
      },
    ],
    relevant_source_ids: [source.id],
    provenance: "browser-authored integration label; no independent validation",
    group_id: "delivery-manual",
    split: "held_out",
  };
  await page.goto("/");
  await page.getByLabel("Active application").selectOption(application.id);
  await page.getByLabel("Import cases JSONL").setInputFiles({
    name: "cases.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from(JSON.stringify(item) + "\n"),
  });
  await expect(page.getByRole("status")).toContainText(/cases imported/i);
  await page.getByRole("button", { name: /02.*datasets/i }).click();
  await page.getByLabel("Reviewer name").fill("Manual browser reviewer");
  await page.getByRole("button", { name: "Save & approve" }).click();
  await expect(page.getByRole("status")).toContainText("Case revision saved");
  await page.getByRole("button", { name: "Publish approved dataset" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Immutable dataset published",
  );
  await page.getByRole("button", { name: /01.*applications/i }).click();
  const trace = {
    schema_version: 1,
    case_id: item.id,
    application_version: application.application_version,
    model_version: application.model_version,
    prompt_version: application.prompt_version,
    answer: quote,
    behavior: "answer",
    citations: [source.id],
    retrieved_ids: [source.id],
  };
  await page.getByLabel("Import traces JSONL").setInputFiles({
    name: "traces.jsonl",
    mimeType: "application/x-ndjson",
    buffer: Buffer.from(JSON.stringify(trace) + "\n"),
  });
  await expect(page.getByRole("status")).toContainText(/traces imported/i);
  await page.getByRole("button", { name: /03.*runs/i }).click();
  await page.getByLabel("Target", { exact: true }).selectOption("imported");
  await page
    .getByLabel("Trace batch", { exact: true })
    .selectOption({ index: 1 });
  await page.getByRole("button", { name: "Queue evaluation" }).click();
  await expect(page.getByRole("status")).toContainText("Evaluation queued");
  const runs = await (
    await request.get(
      `http://127.0.0.1:8000/api/runs?application_id=${application.id}`,
    )
  ).json();
  await expect
    .poll(
      async () =>
        (
          await (
            await request.get(`http://127.0.0.1:8000/api/runs/${runs[0].id}`)
          ).json()
        ).status,
    )
    .toBe("completed");
  await page
    .getByRole("button", { name: "Inspect findings & evidence" })
    .click();
  await page
    .getByRole("button", { name: "insufficient evidence", exact: true })
    .click();
  await expect(page.locator(".findings article")).toHaveCount(1);
  await expect(
    page.locator(".metric-findings summary").filter({ hasText: "latency" }),
  ).toContainText("Unavailable");
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Export run traces" }).click(),
  ]);
  expect(download.suggestedFilename()).toContain("traces-v1.jsonl");
});

test("review, freeze, run clean/faulty targets, inspect evidence, compare and reload", async ({
  page,
  request,
}) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Load no-key demo" }).click();
  await expect(
    page.getByRole("heading", { name: "Northstar support · demo" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recommended measurements" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Continue to dataset review" })
    .click();
  await page.getByLabel("Reviewer name").fill("Browser test reviewer");
  await page
    .getByLabel("Question or interaction")
    .fill(
      (await page.getByLabel("Question or interaction").inputValue()) +
        " Please.",
    );
  await page.getByRole("button", { name: "Save & approve" }).click();
  await expect(page.getByRole("status")).toContainText("Case revision saved");
  await page
    .getByRole("button", { name: /Approve remaining 39 cases/ })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Remaining candidates approved",
  );
  await page.getByRole("button", { name: "Publish approved dataset" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Immutable dataset published",
  );
  await expect(page.getByText("Version 1 · 40 approved cases")).toBeVisible();
  await page.getByRole("button", { name: "Evaluate v1" }).click();
  await page.getByRole("button", { name: "Queue evaluation" }).click();
  await expect(page.getByRole("status")).toContainText("Evaluation queued");
  const cleanResponse = await request.get("http://127.0.0.1:8000/api/runs");
  const clean = (await cleanResponse.json())[0];
  await expect
    .poll(
      async () =>
        (
          await (
            await request.get(`http://127.0.0.1:8000/api/runs/${clean.id}`)
          ).json()
        ).status,
    )
    .toBe("completed");
  await expect(
    page.locator("table").first().getByText("completed"),
  ).toBeVisible();
  await page
    .getByLabel("Target", { exact: true })
    .selectOption("invalid_citation");
  await page.getByRole("button", { name: "Queue evaluation" }).click();
  await expect(page.getByRole("status")).toContainText("Evaluation queued");
  const faulty = (
    await (await request.get("http://127.0.0.1:8000/api/runs")).json()
  )[0];
  await expect
    .poll(
      async () =>
        (
          await (
            await request.get(`http://127.0.0.1:8000/api/runs/${faulty.id}`)
          ).json()
        ).status,
    )
    .toBe("completed");
  await page
    .getByRole("button", { name: "Inspect findings & evidence" })
    .click();
  await expect(page.getByText("Known blind spot")).toBeVisible();
  await expect(page.locator(".findings article")).toHaveCount(10);
  await page
    .locator(".findings article")
    .first()
    .locator(".evidence summary")
    .first()
    .click();
  await expect(
    page.locator(".findings article").first().locator("mark").first(),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/findings.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: /02.*datasets/i }).click();
  await page.getByRole("button", { name: "Publish approved dataset" }).click();
  await expect(page.getByText("Version 2 · 40 approved cases")).toBeVisible();
  await page.getByRole("button", { name: /03.*runs/i }).click();
  await page.getByLabel("Baseline run").selectOption(clean.id);
  await page.getByLabel("Candidate run").selectOption(faulty.id);
  await page.getByRole("button", { name: "Compare selected runs" }).click();
  await expect(
    page.getByRole("heading", {
      name: "20 matched cases · 20 baseline / 20 candidate",
    }),
  ).toBeVisible();
  await expect(page.locator(".comparison .badge.compatible")).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/runs.png",
    fullPage: true,
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Northstar support · demo" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /03.*runs/i }).click();
  await expect(page.locator("table").first().locator("tbody tr")).toHaveCount(
    2,
  );
  expect(pageErrors).toEqual([]);
});

test("create application, UTF-8 source import and responsive empty states", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByText("Create an application", { exact: true }).click();
  await page.getByLabel("name", { exact: true }).fill("Browser import app");
  await page
    .getByLabel("purpose", { exact: true })
    .fill("Answer a local policy");
  await page.getByLabel("owner", { exact: true }).fill("Browser reviewer");
  await page
    .getByLabel("expected behavior", { exact: true })
    .fill("Use supplied evidence");
  await page
    .getByRole("button", { name: "Create application", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Browser import app" }),
  ).toBeVisible();
  await page.getByLabel("Document ID", { exact: true }).fill("cafe");
  await page.getByLabel("Source file", { exact: true }).setInputFiles({
    name: "cafe.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("Café policy: delivery is free.\n", "utf8"),
  });
  await page
    .getByRole("button", { name: "Import source", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Versioned source imported",
  );
  await page.getByText("cafe.md", { exact: true }).click();
  await expect(page.locator(".source-text")).toContainText("Café policy");
  await page.getByRole("button", { name: "Generate candidates" }).click();
  await expect(page.getByRole("alert")).toContainText("No structured facts");
  await page.getByRole("button", { name: /02.*datasets/i }).click();
  await expect(page.getByText("No dataset published yet.")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("navigation")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../docs/screenshots/mobile.png",
    fullPage: true,
  });
});
