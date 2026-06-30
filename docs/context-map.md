# Context Map

Document type: project context routing map
Status: current
Owner: Adam Goodwin
Audience: coding agents, human coders, reviewers, and project owners

## Purpose

This file keeps agent context loads small, deliberate, and recoverable.

The repository remembers. Agents rent context. Use this map to decide what to
load first, what to load by task type, and what to avoid unless the task needs
it.

## Always Load

- `AGENTS.md` or the active agent instruction file
- `START_HERE.md` for material work, unclear scope, or changes to the active plan
- `project-control.yaml` when risk, governance level, controls, or required docs matter

Keep these files compact. They should route to durable docs, not duplicate them.

## Load By Task

| Task | Load First |
|---|---|
| Graphify CNS speed/function planning, hot-path context packets, or next chunks | `docs/2026-06-29 - Graphify Quantum Speed Execution Plan.md` |
| CNS API contract, write lanes, or Graphify integration boundaries | `docs/specs/2026-06-29 - Graphify Function Boundary And Speed Doctrine.md`, then `docs/specs/2026-06-28 - Graphify CNS Connectome Contract.md` (20D) |
| GAIL OS GraphFact extraction pipeline spec or accepted emitters | `docs/specs/2026-06-28 - GAIL Graph Fact Import Boundary.md` (20E) |
| CNS endpoint list, query patterns, or SLA table | `docs/specs/2026-06-28 - Graphify Endpoint Family Map.md` |
| Current plan, chunking, validation, or handoff | `docs/2026-06-29 - Graphify Quantum Speed Execution Plan.md` for CNS/API/store/speed work; `docs/relationship-map-plan.md` for Map/UI work; use `docs/workspace-scope-and-signal-plan.md` only for completed scope/signal evidence; use `docs/stabilization-plan.md` only for completed stabilization evidence; use `docs/current-build-pathway.md` only for archived build history |
| Relationship map, physical connections, overlap, gaps, and decision overlay | `docs/relationship-map-plan.md` |
| Workspace scope, folder tree selection, repo inclusion/exclusion, low-signal filtering, token-saving graph context | `docs/workspace-scope-and-signal-plan.md` |
| Fast restart after clearing or compaction | `AGENT_QUICKSTART.md` |
| Source routing without generated output | `docs/ARCHITECTURE_MAP.md`, then `docs/FILE_SUMMARIES.md` |
| Known issues or owner-review gates | `docs/KNOWN_ISSUES.md`, then relevant sections of `docs/stabilization-plan.md` |
| Engineering standards map | `docs/standards/README.md` |
| Context windows, token budgets, compaction, scoped reads, or handoffs | `docs/standards/context-hygiene-standard.md` |
| Durable implementation, design quality, testing discipline, or AI coding fundamentals | `docs/policy/durable-development-engineering-policy.md` |
| Use-case controls, risk tier, governance level, or owner decisions | `docs/standards/engineering-governance-by-use-case.md` |
| Completion labels, Definition of Shipped, release evidence, or finish reports | `docs/standards/ship-ready-engineering-standard.md` |
| Historical Phase 3 framing or cross-repo integration background | `docs/2026-06-27 - next-phase-builder-wishlist.md` — historical after the 2026-06-29 boundary/speed reset |
| Architecture decisions or system shape | `docs/2026-06-24 - architecture.md` and relevant ADRs |
| Domain terms or naming | `docs/2026-06-15 - domain-language.md` |
| Deployment, release, rollback, or environment changes | `docs/2026-06-24 - deployment-guide.md`, `docs/2026-06-26 - runbook.md`, and release standards |
| Agent autonomy, tools, prompts, models, or permissions | `docs/2026-06-24 - agent-inventory.md`, `docs/2026-06-24 - model-registry.md`, `docs/2026-06-14 - prompt-register.md`, and `docs/2026-06-24 - tool-permission-matrix.md` |

## Search Before Loading

- long audit reports
- old pathway history below the current active chunk
- logs, generated reports, and command output
- exported manifests
- archived plans or superseded briefs
- `backend/main.py` broad ranges; search for route/helper names first

Use `rg` or targeted file excerpts before opening long files.

## Avoid Unless Needed

- `.git/`
- `.venv/`, `venv/`, `node_modules/`, and dependency caches
- build output, coverage, and generated artifacts
- `graphify-out/` and `graphify-out/cache/`
- `workspace/state/`
- ignored Graphify output
- secrets and environment files
- large transcripts or pasted chat histories

Do not print, summarize, index, or commit secrets.

## Work Packet Reminder

For meaningful work, define:

- goal
- budget class: Tiny, Small, Medium, Large, or Strategic
- context to load first
- files or folders to avoid unless needed
- constraints and non-goals
- done-when checks
- handoff location

Tiny edits may use an inline version of this packet. Large or strategic work
should record the packet in the active plan named by `START_HERE.md`, an ADR, or
a short handoff note.

## Maintenance

Update this file when the repo's routing paths change or when agents repeatedly
load the wrong material. Keep it short enough to read at startup when context
routing is unclear.
