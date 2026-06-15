#!/usr/bin/env node

import { execFile } from "node:child_process";
import { access } from "node:fs/promises";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const apiUrl = (process.env.API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const frontendUrl = (process.env.FRONTEND_URL ?? "http://127.0.0.1:5173").replace(/\/$/, "");
const askQuestion = process.env.SMOKE_ASK_QUESTION ?? "What projects are in this workspace?";

const checks = [];

function pass(name, detail = "") {
  checks.push({ name, ok: true, detail });
  console.log(`PASS ${name}${detail ? ` - ${detail}` : ""}`);
}

function fail(name, detail) {
  checks.push({ name, ok: false, detail });
  console.error(`FAIL ${name}${detail ? ` - ${detail}` : ""}`);
}

async function fetchJson(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Number(process.env.SMOKE_TIMEOUT_MS ?? 15000));
  try {
    const response = await fetch(`${apiUrl}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers ?? {}),
      },
    });
    const text = await response.text();
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${text.slice(0, 180)}`);
    }
    return text ? JSON.parse(text) : null;
  } finally {
    clearTimeout(timeout);
  }
}

async function findChromium() {
  const candidates = [
    process.env.CHROMIUM_BIN,
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (candidate.includes("/")) {
      try {
        await access(candidate);
        return candidate;
      } catch {
        continue;
      }
    }
    try {
      await execFileAsync("which", [candidate]);
      return candidate;
    } catch {
      // Keep searching.
    }
  }
  return null;
}

function assertArray(value, name) {
  if (!Array.isArray(value)) throw new Error(`${name} is not an array`);
  return value;
}

async function checkBackendContract() {
  const health = await fetchJson("/health");
  if (health?.status !== "ok") throw new Error(`unexpected health status ${health?.status}`);
  pass("backend health", `demo_mode=${Boolean(health.demo_mode)}`);

  const summary = await fetchJson("/graph/summary");
  const summaryNodes = assertArray(summary?.nodes, "summary.nodes");
  if (summaryNodes.length === 0) throw new Error("graph summary returned no nodes");
  pass("graph summary", `${summary.total_nodes ?? summaryNodes.length} nodes available`);

  const ask = await fetchJson("/ask", {
    method: "POST",
    body: JSON.stringify({ question: askQuestion, mode: "query" }),
  });
  const evidence = assertArray(ask?.evidence, "ask.evidence");
  if (!ask?.answer || evidence.length === 0) throw new Error("Ask did not return an answer with evidence");
  pass("Ask evidence", `${evidence.length} evidence nodes for "${askQuestion}"`);

  const recommendations = assertArray(await fetchJson("/recommendations"), "recommendations");
  pass("recommendation queue", `${recommendations.length} records readable`);

  const actions = assertArray(await fetchJson("/actions"), "actions");
  pass("work queue actions", `${actions.length} records readable`);

  const decisions = assertArray(await fetchJson("/decisions"), "decisions");
  pass("decision ledger", `${decisions.length} records readable`);

  const overlap = await fetchJson("/graph/overlap-report");
  const overlapGroups = assertArray(overlap?.groups, "overlap.groups");
  pass("overlap report", `${overlapGroups.length} groups readable`);
}

async function checkFrontendShell() {
  const chromium = await findChromium();
  if (!chromium) {
    throw new Error("Chromium not found. Set CHROMIUM_BIN to run the browser smoke check.");
  }

  const { stdout } = await execFileAsync(chromium, [
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--dump-dom",
    frontendUrl,
  ], { maxBuffer: 8 * 1024 * 1024 });

  const requiredText = [
    "Graphify Workspace Cockpit",
    "Command Center",
    "Ask",
    "Map",
    "Decisions",
    "Recommendations",
    "Work Queue",
    "Settings",
    "Pending Recommendations",
    "Untriaged Overlaps",
    "Active Graph",
  ];

  const missing = requiredText.filter((text) => !stdout.includes(text));
  if (missing.length) throw new Error(`missing frontend text: ${missing.join(", ")}`);
  pass("frontend command shell", `${requiredText.length} labels rendered`);
}

async function main() {
  console.log(`Demo path smoke check`);
  console.log(`API_URL=${apiUrl}`);
  console.log(`FRONTEND_URL=${frontendUrl}`);

  try {
    await checkBackendContract();
  } catch (error) {
    fail("backend contract", error instanceof Error ? error.message : String(error));
  }

  try {
    await checkFrontendShell();
  } catch (error) {
    fail("frontend command shell", error instanceof Error ? error.message : String(error));
  }

  const failed = checks.filter((check) => !check.ok);
  if (failed.length) {
    console.error(`\n${failed.length} smoke check(s) failed.`);
    process.exit(1);
  }

  console.log(`\n${checks.length} smoke checks passed.`);
}

main();
