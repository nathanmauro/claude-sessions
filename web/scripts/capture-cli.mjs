#!/usr/bin/env node
// Render the CLI screenshot as a faux terminal using Playwright + the
// agent-sessions-web Chromium install. Run from repo root:
//   node web/scripts/capture-cli.mjs
//
// Lives in web/scripts/ (not docs/screenshots/) so Node can resolve
// @playwright/test from web/node_modules. We use HTML/CSS instead of
// `freeze`/`vhs` because freeze 0.2.2 hits "ERROR  No input" on every
// invocation we tried and `vhs` would add another brew dep.

import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..", "..");
const OUT_FILE = resolve(REPO_ROOT, "docs", "screenshots", "cli.png");
const DEMO_SCRIPT = resolve(REPO_ROOT, "docs", "screenshots", "_demo-ls.sh");

const raw = execFileSync("bash", [DEMO_SCRIPT], { encoding: "utf8" });
const lines = raw.replace(/\n+$/, "").split("\n");

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

const renderedLines = lines
  .map((line) => {
    const safe = escapeHtml(line);
    if (safe.startsWith("$ ")) return `<span class="prompt">$</span><span class="cmd">${safe.slice(1)}</span>`;
    return safe;
  })
  .join("\n");

const html = `<!doctype html>
<html><head><meta charset="utf-8"><title>cli</title>
<style>
  html, body { margin: 0; padding: 0; background: #14161a; }
  body { padding: 24px; }
  .term {
    max-width: 1100px;
    background: #1a1d23;
    border-radius: 10px;
    box-shadow: 0 24px 48px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.06);
    overflow: hidden;
    font-family: "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace;
  }
  .titlebar {
    display: flex;
    align-items: center;
    padding: 10px 14px;
    background: linear-gradient(180deg, #2a2e36 0%, #22262d 100%);
    border-bottom: 1px solid rgba(0,0,0,0.4);
  }
  .dot { width: 12px; height: 12px; border-radius: 50%; margin-right: 6px; }
  .dot.r { background: #ff5f57; }
  .dot.y { background: #febc2e; }
  .dot.g { background: #28c840; }
  .title {
    margin-left: 14px;
    color: #8b8f98;
    font-size: 12px;
    letter-spacing: 0.02em;
  }
  pre {
    margin: 0;
    padding: 20px 24px 24px;
    color: #d6d9df;
    font-size: 13px;
    line-height: 1.55;
    white-space: pre;
  }
  .prompt { color: #5ec2a8; margin-right: 4px; }
  .cmd { color: #e6e9ef; }
</style></head><body>
  <div class="term">
    <div class="titlebar">
      <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
      <span class="title">agent-sessions — zsh — 130×16</span>
    </div>
    <pre>${renderedLines}</pre>
  </div>
</body></html>`;

const tmpHtml = resolve(REPO_ROOT, ".tmp-cli.html");
writeFileSync(tmpHtml, html);

mkdirSync(dirname(OUT_FILE), { recursive: true });

const { chromium } = await import("@playwright/test");
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1180, height: 360 },
  deviceScaleFactor: 2,
});
const page = await context.newPage();
await page.goto(`file://${tmpHtml}`);
await page.waitForLoadState("networkidle");
const term = page.locator(".term");
await term.screenshot({ path: OUT_FILE });
await browser.close();

import { unlinkSync } from "node:fs";
try { unlinkSync(tmpHtml); } catch {}

console.log(`wrote ${OUT_FILE}`);
