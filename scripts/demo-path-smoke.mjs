#!/usr/bin/env node

import { execFile } from "node:child_process";
import { access } from "node:fs/promises";
import { isAbsolute } from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const apiUrl = (process.env.API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const frontendUrl = (process.env.FRONTEND_URL ?? "http://localhost:5173").replace(/\/$/, "");
const askQuestion = process.env.SMOKE_ASK_QUESTION ?? "What projects are in this workspace?";
const smokeApiKey = process.env.SMOKE_API_KEY ?? process.env.API_KEY ?? "";

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
        ...(smokeApiKey ? { "X-API-Key": smokeApiKey } : {}),
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

async function fetchStatus(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Number(process.env.SMOKE_TIMEOUT_MS ?? 15000));
  try {
    const response = await fetch(`${apiUrl}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(smokeApiKey ? { "X-API-Key": smokeApiKey } : {}),
        ...(options.headers ?? {}),
      },
    });
    const text = await response.text();
    return { status: response.status, ok: response.ok, text };
  } finally {
    clearTimeout(timeout);
  }
}

async function findChromium() {
  const windowsCandidates = process.platform === "win32"
    ? [
        "chrome.exe",
        "msedge.exe",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
        "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
      ]
    : [];
  const candidates = [
    process.env.CHROMIUM_BIN,
    ...windowsCandidates,
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (isAbsolute(candidate) || candidate.includes("/") || candidate.includes("\\")) {
      try {
        await access(candidate);
        return candidate;
      } catch {
        continue;
      }
    }
    try {
      const lookup = process.platform === "win32" ? "where.exe" : "which";
      const { stdout } = await execFileAsync(lookup, [candidate]);
      return stdout.trim().split(/\r?\n/)[0] || candidate;
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
  pass("backend health", `graph_configured=${Boolean(health.graph_configured)}`);

  if (!health.graph_configured) {
    const runtime = await fetchJson("/runtime/status");
    if (runtime?.state !== "not_ready") throw new Error(`expected not_ready for fresh instance, got ${runtime?.state}`);
    if (runtime?.warnings?.[0]?.code !== "NO_GRAPH") throw new Error("fresh instance did not report NO_GRAPH");
    pass("fresh instance readiness", runtime.summary ?? "No workspace graph yet");

    const settings = await fetchJson("/settings");
    if (settings?.graph_configured !== false) throw new Error("settings did not report graph_configured=false");
    pass("settings empty graph", settings.graph_name ?? "No graph yet");

    const graphs = assertArray(await fetchJson("/graphs"), "graphs");
    pass("available graphs", `${graphs.length} instance graph${graphs.length === 1 ? "" : "s"} found`);

    const ask = await fetchStatus("/ask", {
      method: "POST",
      body: JSON.stringify({ question: askQuestion, mode: "query" }),
    });
    if (ask.status !== 503 || !ask.text.includes("workspace graph")) {
      throw new Error(`Ask empty-state response was unexpected: HTTP ${ask.status}: ${ask.text.slice(0, 120)}`);
    }
    pass("Ask empty state", "reports no workspace graph yet");

    const recommendations = assertArray(await fetchJson("/recommendations"), "recommendations");
    pass("recommendation queue", `${recommendations.length} records readable`);

    const actions = assertArray(await fetchJson("/actions"), "actions");
    pass("work queue actions", `${actions.length} records readable`);

    const decisions = assertArray(await fetchJson("/decisions"), "decisions");
    pass("decision ledger", `${decisions.length} records readable`);

    const overlap = await fetchJson("/graph/overlap-report");
    const overlapGroups = assertArray(overlap?.groups, "overlap.groups");
    pass("overlap report", `${overlapGroups.length} groups readable`);
    return;
  }

  if (!health.graph_loaded) {
    throw new Error(`configured graph did not load: ${health.graph_error ?? "unknown error"}`);
  }

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
    "Current Map Recommendations",
    "Untriaged Overlaps",
    "Active Graph",
  ];
  const health = await fetchJson("/health");
  if (!health.graph_configured) {
    requiredText.push("No graph yet");
  }

  const missing = requiredText.filter((text) => !stdout.includes(text));
  if (missing.length) throw new Error(`missing frontend text: ${missing.join(", ")}`);
  pass("frontend command shell", `${requiredText.length} labels rendered`);
}

async function main() {
  console.log(`Workspace cockpit smoke check`);
  console.log(`API_URL=${apiUrl}`);
  console.log(`FRONTEND_URL=${frontendUrl}`);
  console.log(`SMOKE_API_KEY=${smokeApiKey ? "set" : "unset"}`);

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
