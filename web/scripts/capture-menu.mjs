#!/usr/bin/env node
// Render the menubar screenshot as a faux macOS menubar + dropdown using
// Playwright. We mock it (instead of driving the real rumps app via
// AppleScript) because:
//   1. AppleScript automation is flaky and PII-heavy.
//   2. The dropdown content is structural (running / recent / projects)
//      and easy to reproduce faithfully.
//
// Mirrors agent_sessions/menu/app.py::_build_menu.
//
// Run from repo root:  node web/scripts/capture-menu.mjs

import { mkdirSync, writeFileSync, unlinkSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "..", "..");
const OUT_FILE = resolve(REPO_ROOT, "docs", "screenshots", "menubar.png");

const running = [
  { age: "1h", project: "orbital-cli", title: "Wire up the new router with deferred imports" },
  { age: "3h", project: "lighthouse-api", title: "Background job retries — exponential backoff" },
];

const projects = [
  { name: "orbital-cli", count: 4 },
  { name: "lighthouse-api", count: 3 },
  { name: "portfolio-site", count: 5 },
  { name: "intent-workspace", count: 2 },
  { name: "claude-sessions", count: 6 },
];

function esc(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

const runningRows = running
  .map(
    (r) =>
      `<div class="row running"><span class="dot"></span><span class="age">${esc(r.age)}</span>` +
      `<span class="proj">[${esc(r.project)}]</span> <span class="title">${esc(r.title)}</span></div>`,
  )
  .join("\n");

const projectRows = projects
  .map(
    (p) =>
      `<div class="row submenu"><span class="title">${esc(p.name)} (${p.count})</span><span class="chev">▸</span></div>`,
  )
  .join("\n");

const html = `<!doctype html>
<html><head><meta charset="utf-8"><title>menu</title>
<style>
  html, body { margin: 0; padding: 0; background: #d8d4cc; }
  body {
    padding: 0 36px 48px;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
    background: linear-gradient(180deg, #c9c3b8 0%, #e1ddd5 100%);
  }
  .menubar {
    height: 26px;
    background: rgba(245, 243, 239, 0.88);
    backdrop-filter: blur(20px);
    display: flex;
    align-items: center;
    padding: 0 14px;
    border-bottom: 1px solid rgba(0,0,0,0.08);
    margin: 0 -36px 0;
    font-size: 13px;
    color: #1d1d1f;
  }
  .menubar .apple { font-weight: 600; margin-right: 18px; }
  .menubar .app-name { font-weight: 600; margin-right: 18px; }
  .menubar .menu { color: #1d1d1f; margin-right: 16px; }
  .menubar .spacer { flex: 1; }
  .menubar .status { display: flex; gap: 14px; color: #1d1d1f; align-items: center; }
  .menubar .badge {
    background: rgba(0,0,0,0.04);
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    border: 1px solid rgba(0,0,0,0.06);
  }
  .menubar .badge.active { color: #1d6f42; }
  .anchor { position: relative; height: 0; }
  .dropdown {
    position: absolute;
    top: 6px;
    right: 60px;
    width: 420px;
    background: rgba(248, 246, 242, 0.96);
    backdrop-filter: blur(30px);
    border-radius: 8px;
    box-shadow: 0 12px 36px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.08);
    padding: 5px 0;
    font-size: 13px;
    color: #1d1d1f;
  }
  .section { padding: 4px 14px; color: #8a8a8e; font-size: 11px; letter-spacing: 0.02em; }
  .row {
    padding: 4px 14px;
    display: flex;
    align-items: center;
    gap: 6px;
    line-height: 1.35;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .row.submenu { justify-content: space-between; padding-right: 12px; }
  .row.highlight {
    background: linear-gradient(180deg, #4a89ec 0%, #2f6fd1 100%);
    color: white;
    border-radius: 4px;
    margin: 0 4px;
    padding-left: 10px;
    padding-right: 10px;
  }
  .dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #34c759;
    box-shadow: 0 0 6px rgba(52, 199, 89, 0.6);
    margin-right: 2px;
  }
  .age { color: #6e6e73; font-variant-numeric: tabular-nums; min-width: 22px; }
  .proj { color: #8a8a8e; }
  .title { color: #1d1d1f; overflow: hidden; text-overflow: ellipsis; }
  .row.highlight .age, .row.highlight .proj, .row.highlight .title { color: white; }
  .sep { height: 1px; background: rgba(0,0,0,0.1); margin: 5px 10px; }
  .chev { color: #8a8a8e; }
</style></head><body>
  <div class="menubar">
    <span class="apple"></span>
    <span class="app-name">Finder</span>
    <span class="menu">File</span><span class="menu">Edit</span><span class="menu">View</span><span class="menu">Go</span>
    <span class="spacer"></span>
    <span class="status">
      <span class="badge active">CC${running.length}</span>
      <span>🔋</span><span>📶</span><span>🔍</span><span>9:41 AM</span>
    </span>
  </div>
  <div class="anchor">
    <div class="dropdown">
      <div class="section">— Running (${running.length}) —</div>
${runningRows}
      <div class="sep"></div>
      <div class="section">— Recent —</div>
${projectRows}
      <div class="sep"></div>
      <div class="row"><span class="title">Refresh</span></div>
      <div class="row"><span class="title">Quit</span></div>
    </div>
  </div>
</body></html>`;

const tmpHtml = resolve(REPO_ROOT, ".tmp-menu.html");
writeFileSync(tmpHtml, html);
mkdirSync(dirname(OUT_FILE), { recursive: true });

const { chromium } = await import("@playwright/test");
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1200, height: 520 },
  deviceScaleFactor: 2,
});
const page = await context.newPage();
await page.goto(`file://${tmpHtml}`);
await page.waitForLoadState("networkidle");
await page.screenshot({ path: OUT_FILE, fullPage: false });
await browser.close();
try { unlinkSync(tmpHtml); } catch {}
console.log(`wrote ${OUT_FILE}`);
