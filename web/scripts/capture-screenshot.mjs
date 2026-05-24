#!/usr/bin/env node
// Capture a deterministic screenshot of the dashboard for docs/screenshots/dashboard.png.
//
// Usage: from repo root, `cd web && npm run screenshot`
// Requires the Vite dev server build artifacts; this script spawns its own
// `vite preview` server against the existing `dist/` build, so run `npm run build` first.

import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..", "..");
const WEB_ROOT = resolve(__dirname, "..");
const OUT_DIR = resolve(REPO_ROOT, "docs", "screenshots");
const OUT_FILE = resolve(OUT_DIR, "dashboard.png");
const PORT = Number(process.env.SCREENSHOT_PORT ?? 5273);

const TODAY = new Date().toISOString().slice(0, 10);
const HOURS_AGO = (h) =>
  new Date(Date.now() - h * 3600 * 1000).toISOString().slice(0, 19);

const PROJECTS = [
  { cwd: "/Users/demo/code/orbital-cli", name: "orbital-cli" },
  { cwd: "/Users/demo/code/lighthouse-api", name: "lighthouse-api" },
  { cwd: "/Users/demo/code/portfolio-site", name: "portfolio-site" },
];

function session(overrides) {
  return {
    session_id: "sess-0000",
    project_dir: PROJECTS[0].cwd,
    cwd: PROJECTS[0].cwd,
    start_ts: HOURS_AGO(2),
    end_ts: HOURS_AGO(1),
    title: "Untitled",
    first_prompt: "",
    last_prompt: "",
    tasks: {},
    user_msg_count: 0,
    input_tokens: 0,
    output_tokens: 0,
    cache_create_tokens: 0,
    cache_read_tokens: 0,
    billable_tokens: 0,
    total_tokens: 0,
    incomplete_count: 0,
    completed_count: 0,
    ...overrides,
  };
}

function task(id, subject, status = "in_progress") {
  return { task_id: id, subject, description: "", status };
}

const SESSIONS = [
  session({
    session_id: "01k5c4xa-orbital-router",
    cwd: PROJECTS[0].cwd,
    project_dir: PROJECTS[0].cwd,
    start_ts: HOURS_AGO(2),
    end_ts: HOURS_AGO(1),
    title: "Wire up the new router with deferred imports",
    first_prompt:
      "Refactor the router so route modules are imported lazily — the cold-start budget is 80ms and we're at 140ms.",
    last_prompt: "Looks good, let's also add a regression test for the lazy path.",
    tasks: {
      t1: task("t1", "Split route registry into eager + lazy buckets", "in_progress"),
      t2: task("t2", "Add cold-start benchmark to CI", "pending"),
    },
    user_msg_count: 14,
    input_tokens: 18_500,
    output_tokens: 6_200,
    cache_read_tokens: 42_000,
    billable_tokens: 66_700,
    total_tokens: 66_700,
    incomplete_count: 2,
    completed_count: 1,
  }),
  session({
    session_id: "01k5b9zd-lighthouse-jobs",
    cwd: PROJECTS[1].cwd,
    project_dir: PROJECTS[1].cwd,
    start_ts: HOURS_AGO(5),
    end_ts: HOURS_AGO(3),
    title: "Background job retries — exponential backoff",
    first_prompt:
      "Our retry policy retries every 30s forever. Switch to exponential backoff capped at 1h and surface a dead-letter queue.",
    last_prompt: "Ship it — I'll handle the migration in a follow-up.",
    tasks: {
      t3: task("t3", "Replace fixed-interval retry with exponential", "completed"),
      t4: task("t4", "Add DLQ table + admin view", "completed"),
    },
    user_msg_count: 22,
    input_tokens: 24_100,
    output_tokens: 9_800,
    cache_read_tokens: 71_300,
    billable_tokens: 105_200,
    total_tokens: 105_200,
    incomplete_count: 0,
    completed_count: 2,
  }),
  session({
    session_id: "01k5a2qb-portfolio-darkmode",
    cwd: PROJECTS[2].cwd,
    project_dir: PROJECTS[2].cwd,
    start_ts: HOURS_AGO(8),
    end_ts: HOURS_AGO(7),
    title: "Dark mode tokens + system-preference detection",
    first_prompt:
      "Add a dark theme. Use CSS custom properties so we can swap palettes without touching components.",
    last_prompt: "Great — please also persist the user override in localStorage.",
    tasks: {
      t5: task("t5", "Persist override in localStorage", "in_progress"),
    },
    user_msg_count: 9,
    input_tokens: 6_400,
    output_tokens: 3_100,
    billable_tokens: 9_500,
    total_tokens: 9_500,
    incomplete_count: 1,
    completed_count: 3,
  }),
  session({
    session_id: "01k59lkp-orbital-flags",
    cwd: PROJECTS[0].cwd,
    project_dir: PROJECTS[0].cwd,
    start_ts: HOURS_AGO(26),
    end_ts: HOURS_AGO(25),
    title: "Migrate feature flags to OpenFeature",
    first_prompt:
      "Swap our hand-rolled feature-flag client for OpenFeature with a LaunchDarkly provider.",
    last_prompt: "Tests are green, opening the PR.",
    tasks: {},
    user_msg_count: 18,
    input_tokens: 31_200,
    output_tokens: 12_400,
    cache_read_tokens: 88_900,
    billable_tokens: 132_500,
    total_tokens: 132_500,
    incomplete_count: 0,
    completed_count: 4,
  }),
  session({
    session_id: "01k58hh1-lighthouse-tracing",
    cwd: PROJECTS[1].cwd,
    project_dir: PROJECTS[1].cwd,
    start_ts: HOURS_AGO(30),
    end_ts: HOURS_AGO(29),
    title: "OTel tracing on the ingest pipeline",
    first_prompt:
      "Instrument the ingest workers with OpenTelemetry — spans for parse, validate, enqueue.",
    last_prompt: "",
    tasks: {
      t6: task("t6", "Add otel-collector to docker-compose", "completed"),
      t7: task("t7", "Document sampling defaults in README", "pending"),
    },
    user_msg_count: 11,
    input_tokens: 14_600,
    output_tokens: 5_900,
    cache_read_tokens: 30_200,
    billable_tokens: 50_700,
    total_tokens: 50_700,
    incomplete_count: 1,
    completed_count: 1,
  }),
  session({
    session_id: "01k57e4w-portfolio-og",
    cwd: PROJECTS[2].cwd,
    project_dir: PROJECTS[2].cwd,
    start_ts: HOURS_AGO(50),
    end_ts: HOURS_AGO(49),
    title: "Dynamic OG images for blog posts",
    first_prompt: "Generate per-post OG cards using @vercel/og at build time.",
    last_prompt: "Merged.",
    tasks: {},
    user_msg_count: 6,
    input_tokens: 4_800,
    output_tokens: 2_200,
    billable_tokens: 7_000,
    total_tokens: 7_000,
    incomplete_count: 0,
    completed_count: 0,
  }),
];

const TOTAL_BILLABLE = SESSIONS.reduce((n, s) => n + s.billable_tokens, 0);
const TOTAL_OPEN = SESSIONS.reduce((n, s) => n + s.incomplete_count, 0);

const PROJECT_MAP = Object.fromEntries(
  PROJECTS.map((p) => [
    p.cwd,
    {
      cwd: p.cwd,
      name: p.name,
      github_url: `https://github.com/demo/${p.name}`,
      augment_status: "indexed",
      session_count: SESSIONS.filter((s) => s.cwd === p.cwd).length,
      open_tasks: SESSIONS.filter((s) => s.cwd === p.cwd).reduce(
        (n, s) => n + s.incomplete_count,
        0,
      ),
    },
  ]),
);

const DASHBOARD = {
  start: TODAY,
  end: TODAY,
  range_label: "today",
  is_today_only: true,
  is_single_day: true,
  sessions: SESSIONS,
  projects: PROJECT_MAP,
  project_index: Object.fromEntries(
    PROJECTS.map((p) => [p.name, [p.cwd, "indexed"]]),
  ),
  today_usage: {
    input: 49_000,
    output: 19_100,
    cache_create: 0,
    cache_read: 113_300,
    billable: 181_400,
    total: 181_400,
    cache_hit_pct: 62,
    session_count: 3,
  },
  week_usage: {
    input: 99_600,
    output: 39_600,
    cache_create: 0,
    cache_read: 232_400,
    billable: TOTAL_BILLABLE,
    total: TOTAL_BILLABLE,
    cache_hit_pct: 60,
    session_count: SESSIONS.length,
  },
  range_usage: {
    input: 49_000,
    output: 19_100,
    cache_create: 0,
    cache_read: 113_300,
    billable: 181_400,
    total: 181_400,
    cache_hit_pct: 62,
    session_count: 3,
  },
  total_open: TOTAL_OPEN,
  known_sids: SESSIONS.map((s) => s.session_id),
};

const TODOS = {
  todos: [
    { name: "Triage cold-start regression report", status: "In progress", due: TODAY, url: "https://notion.so/x", project: "orbital-cli", source: "claude" },
    { name: "Draft RFC for retry backoff", status: "Not started", due: null, url: "https://notion.so/x", project: "lighthouse-api", source: "claude" },
    { name: "Write release notes for v0.4", status: "Not started", due: null, url: "https://notion.so/x", project: "lighthouse-api", source: "claude" },
    { name: "Pick fonts for the redesign", status: "Not started", due: null, url: "https://notion.so/x", project: "portfolio-site", source: "claude" },
  ],
  source: "cache",
  fetched_at: HOURS_AGO(1),
};

const SUBSCRIPTION = {
  rate_limits: {
    five_hour: { used_percentage: 38, resets_at: Math.floor(Date.now() / 1000) + 3 * 3600, reset_at: null },
    seven_day: { used_percentage: 61, resets_at: Math.floor(Date.now() / 1000) + 4 * 86400, reset_at: null },
    seven_day_opus: null,
    seven_day_sonnet: null,
  },
  cost: { total_cost_usd: 18.42 },
};

async function waitForServer(url, timeoutMs = 30_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {
      // not ready
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`server ${url} did not become ready within ${timeoutMs}ms`);
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });

  const previewBin = resolve(WEB_ROOT, "node_modules", ".bin", "vite");
  const server = spawn(
    previewBin,
    ["preview", "--port", String(PORT), "--strictPort", "--host", "127.0.0.1"],
    { cwd: WEB_ROOT, stdio: ["ignore", "pipe", "inherit"] },
  );
  server.stdout.on("data", () => {}); // silence

  try {
    await waitForServer(`http://127.0.0.1:${PORT}/`);

    const browser = await chromium.launch();
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 2,
      reducedMotion: "reduce",
    });
    const page = await context.newPage();

    await page.route("**/api/dashboard*", (route) =>
      route.fulfill({ json: DASHBOARD, headers: { "Cache-Control": "no-store" } }),
    );
    await page.route("**/api/todos", (route) =>
      route.fulfill({ json: TODOS, headers: { "Cache-Control": "no-store" } }),
    );
    await page.route("**/api/search*", (route) => route.fulfill({ json: [] }));
    await page.route("**/api/subscription-usage", (route) =>
      route.fulfill({ json: SUBSCRIPTION }),
    );
    await page.route("**/api/events", (route) =>
      route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
        body: ": keepalive\n\n",
      }),
    );

    await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { level: 3 }).first().waitFor();
    await page.evaluate(() => document.fonts && document.fonts.ready);
    await page.waitForTimeout(400);

    await page.screenshot({ path: OUT_FILE, fullPage: false });
    console.log(`wrote ${OUT_FILE}`);

    await browser.close();
  } finally {
    server.kill("SIGTERM");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
