# Current Build Pathway

Last Updated: 2026-06-14
Status: active — Chunk Seven next
Owner: Adam Goodwin

## Purpose

Live build route from current state to shipped product. Keep chunks small, timestamped, and easy to resume.

## Required Work Pattern

For ordinary scoped work:

1. Check `git status --short`.
2. Read `AGENTS.md`.
3. Use `docs/context-map.md` when context routing is unclear.
4. Inspect only the specific files, errors, or docs needed for the task.
5. Run targeted validation after the change.

For material or risk-triggering work:

1. Read `START_HERE.md`.
2. Run `bash scripts/governance-preflight.sh`.
3. Review `docs/standards/README.md` and `docs/policy/durable-development-engineering-policy.md`.
4. Capture timestamp with `date -Iseconds`.
5. Work in the smallest complete chunk that can be reviewed safely.

## Active Path

| Step | Status | Timestamp | Notes |
|------|--------|-----------|-------|
| Chunk One — governance baseline | Complete | 2026-06-14 | Docs filled, plan updated, memory note saved |
| Chunk Two — app shell | Complete | 2026-06-14 | Backend health endpoint live; five-tab shell renders; start.sh launches both |
| Chunk Three — Ask interface | Complete | 2026-06-14 | POST /ask live; query/path/explain modes; sessions saved |
| Chunk Four — readable map | Complete | 2026-06-14 | GET /graph/summary live; hub-and-spoke map; drill-down; inspect panel; filters; path tracing |
| Chunk Five — decision ledger | Complete | 2026-06-14 | POST/GET/PATCH /decisions; Decisions tab; Map badges |
| Chunk Six — recommendation queue | Complete | 2026-06-14 | POST/GET/PATCH /recommendations; Ollama synthesis; Recommendations tab |
| Chunk Seven — steady work mode | Active | — | Next |
| Chunk Seven — steady work mode | Planned | — | |
| Chunk Eight — approved actions | Planned | — | |
| Chunk Nine — GitHub packaging | Planned | — | |

---

## Chunk One - Product And Governance Baseline

Status: **complete** — 2026-06-14

Completion target: Draft complete

Budget class: Small

Objective: Fill the cockpit repo docs with the product boundary, architecture, agent/model/prompt/tool controls, and risk register. Update the plan to reflect the governance override.

Acceptance criteria:

- [x] `README.md` has product story and safety model
- [x] `docs/architecture.md` has component map, data flow, dependencies, state layout
- [x] `docs/current-build-pathway.md` has all 9 chunks
- [x] `docs/agent-inventory.md` has AG-001 through AG-004 with autonomy levels
- [x] `docs/model-registry.md` has M-001 (Ollama) and M-002 (Claude dev)
- [x] `docs/prompt-register.md` has P-001 through P-007 with template paths
- [x] `docs/tool-permission-matrix.md` has full read/write/execute boundaries
- [x] `docs/risks/risk-register.md` has R-001 through R-008
- [x] Plan (PLAN-GFY-001) updated to v0.2.0 with governance override noted
- [x] Memory note saved: governance_level:1 / risk_tier:low are intentional owner overrides

Validation: document review — all placeholder templates replaced with cockpit-specific content.

---

## Chunk Two - Single App Shell

Status: **complete** — 2026-06-14

Completion target: Draft complete

Budget class: Medium

Objective: Scaffold backend and frontend, confirm the app starts locally, create a single desktop launcher, establish the five-tab shell.

Inputs:

- `docs/architecture.md`
- `docs/tool-permission-matrix.md`
- Graphify `graph.json` at `/home/adamgoodwin/code/Tools/graphify/workspace/out/graph.json`

Outputs:

- `backend/` — FastAPI app with health endpoint and graph-load endpoint
- `frontend/` — React/Vite app with five empty tabs: Ask, Map, Decisions, Recommendations, Work Queue
- `scripts/start.sh` — single command to start backend + frontend
- Desktop launcher or README quick-start that opens the app
- Old Navigator/Strategy/Manager launchers marked deprecated or routed to cockpit note

Acceptance criteria:

- [x] `uvicorn` starts backend on localhost:8000; `/health` returns 200
- [x] `npm run dev` starts frontend; cockpit shell loads in browser
- [x] Five tabs render (empty content is fine)
- [x] `scripts/start.sh` starts both without error
- [x] No secrets or private workspace paths hardcoded

Validation:

- Manual: open browser, confirm five tabs visible
- Manual: backend `/health` returns JSON
- `git status --short` — only new scaffold files

Stop condition: stop before deep graph loading or model behavior. Tabs can be empty shells.

Known gaps:

- Graph loading not yet wired
- Ollama adapter not yet present
- Desktop launcher deferred: Adam wants a single `.desktop` launcher file so the cockpit is easy to open without a terminal. Create this when the cockpit is first usable end-to-end (target: after Chunk Three). Launcher should call `scripts/start.sh` and open `http://localhost:5173` in the browser.

---

## Chunk Three - Ask Interface

Status: **complete** — 2026-06-14

Completion target: Task complete

Budget class: Medium

Objective: Wire real question-answering into the Ask tab using Graphify CLI.

Inputs:

- Loaded `graph.json`
- `docs/prompt-register.md` (P-001)
- `docs/agent-inventory.md` (AG-001)

Outputs:

- Backend endpoint `POST /ask` — selects graphify query/path/explain, runs CLI, returns answer + evidence
- Frontend Ask tab — question input, answer rendering, evidence node list, follow-up buttons that fire real requests
- Session transcript saved to `workspace/state/sessions/`

Acceptance criteria:

- [x] Broad question returns graph-backed answer with evidence nodes
- [x] Relationship question (`path`) returns path result
- [x] Focused explain question returns node explanation
- [x] Follow-up buttons run new requests (not clipboard-copy)
- [x] Session saved to state

Validation:

- Ask "what projects are in this workspace?" — confirm answer renders
- Ask "how are X and Y related?" — confirm path answer
- Check `workspace/state/sessions/` for saved transcript

Stop condition: stop before Ollama synthesis. Graph-only answers are sufficient for Chunk Three.

---

## Chunk Four - Readable Map

Status: **complete** — 2026-06-14

Completion target: Draft complete

Budget class: Medium

Objective: Replace raw graph dump with a clustered, drill-down project-level map in the Map tab.

Inputs:

- Loaded `graph.json`
- Cytoscape.js

Outputs:

- Backend endpoint `GET /graph/summary` — returns project/cluster-level nodes and edges
- Frontend Map tab — Cytoscape.js render, click-to-inspect side panel, filters by type/theme/decision, "why connected?" between selected nodes

Acceptance criteria:

- [x] Map renders at project level (not raw file dump)
- [x] Click node opens side panel with summary
- [x] Filter controls work (by type, theme, or decision status)
- [x] Map is non-blank and responsive on desktop
- [x] Large graph does not freeze the browser (test with full workspace graph)

Stop condition: stop before full file-level expansion if performance is uncertain.

---

## Chunk Five - Decision Ledger

Status: **complete** — 2026-06-14

Completion target: Task complete

Budget class: Medium

Objective: Let Adam classify workspace areas and persist decisions that influence map display and recommendation ranking.

Inputs:

- `docs/architecture.md` (Decision record schema)
- `docs/tool-permission-matrix.md`

Outputs:

- Backend endpoints: `POST /decisions`, `GET /decisions`, `PATCH /decisions/{id}`
- `workspace/state/decisions.json`
- Frontend Decisions tab — classification controls, decision history, edit/retire
- Map tab: node color or badge driven by decision status

Acceptance criteria:

- [x] Create, edit, and retire a decision
- [x] Reload app and confirm persistence
- [x] Map reflects decision badges/colors

Stop condition: stop before action execution. Decision records are read and write; no workspace mutation triggered by them.

---

## Chunk Six - Recommendation Queue

Status: **complete** — 2026-06-14

Completion target: Draft complete

Budget class: Medium

Objective: Turn Ollama output into structured recommendation cards with evidence, confidence, risk, and accept/reject/defer controls.

Inputs:

- `docs/prompt-register.md` (P-002 through P-004)
- `docs/agent-inventory.md` (AG-002)
- `docs/model-registry.md` (M-001)
- Decision records from Chunk Five

Outputs:

- Backend endpoint `POST /recommendations/generate` — Ollama-backed recommendation generation
- Structured recommendation records in `workspace/state/recommendations/`
- Frontend Recommendations tab — card list, accept/reject/defer buttons, evidence inspection links

Acceptance criteria:

- [x] Generate "next best build" recommendation
- [x] Generate "archive candidates" recommendation
- [x] Cards show evidence, confidence, risk
- [x] Accept/reject/defer saves status to record
- [x] No action is triggered by generating or displaying a card

Stop condition: stop at reviewable cards. No action execution in this chunk.

---

## Chunk Seven - Steady Work Mode

Status: **planned**

Completion target: Draft complete

Budget class: Large

Objective: Run bounded, non-destructive analysis missions in the background while Adam is away.

Inputs:

- `docs/agent-inventory.md` (AG-003)
- `docs/prompt-register.md` (P-005, P-006)
- Recommendation queue from Chunk Six

Outputs:

- Mission selection UI in Work Queue tab (or dedicated panel)
- Background job status and progress log
- Generated recommendation cards (writes to state only)
- Safe cancellation

Acceptance criteria:

- [ ] Run one short mission (e.g., "find archive candidates")
- [ ] Mission writes recommendation cards only
- [ ] No file mutations outside `workspace/state/`
- [ ] Cancel button stops the job cleanly

Stop condition: stop before approved action execution. Output is cards only.

---

## Chunk Eight - Approved Actions

Status: **planned**

Completion target: Draft complete

Budget class: Large

Objective: Create an approval-gated action queue where accepted recommendations can become executed workspace changes.

Inputs:

- `docs/agent-inventory.md` (AG-004)
- `docs/tool-permission-matrix.md`
- `docs/architecture.md` (Action queue record schema)
- Accepted recommendations from Chunk Six

Outputs:

- Backend endpoint `POST /actions/{id}/dry-run` and `POST /actions/{id}/execute`
- Action queue records in `workspace/state/action-queue/`
- Frontend Work Queue tab — dry-run preview, approve button, execution report, rollback note
- Execution report written to action record

Acceptance criteria:

- [ ] Dry-run preview works before execution
- [ ] Approve button required before execution (no auto-execute)
- [ ] Execution report written to action record
- [ ] Destructive and external actions remain disabled

Stop condition: stop before GitHub publishing or public release.

---

## Chunk Nine - GitHub Packaging

Status: **planned**

Completion target: Release ready

Budget class: Strategic

Objective: Prepare the cockpit for public sharing on GitHub.

Outputs:

- Public-safe `README.md` with screenshots and "why this exists" story
- Demo graph (no private workspace data)
- Clean install and run instructions for Linux first
- `LICENSE` confirmed
- `.gitignore` reviewed — no private paths, graphs, or secrets committed
- `.github/workflows/` CI (lint, tests)
- All private workspace paths removed from public docs where inappropriate

Acceptance criteria:

- [ ] Clean clone + setup test passes
- [ ] Tests pass
- [ ] No private graph data or secrets committed
- [ ] README works for a new user
- [ ] GitHub release plan reviewed by Adam before publishing

Stop condition: stop at owner approval before creating or publishing a public repository.

---

## Timestamp Rule

Use ISO-style timestamps for work notes, handoffs, decisions, exceptions, and validation records:

```bash
date -Iseconds
```

## Validation Log

| Timestamp | Command | Result | Notes |
|-----------|---------|--------|-------|
| 2026-06-14T10:00:00-06:00 | Document review — Chunk One | Pass | All placeholder docs replaced with cockpit-specific content |
| 2026-06-14 | Backend smoke test — GET /health | Pass | 200 {"status":"ok","version":"0.1.0"} |
| 2026-06-14 | Frontend typecheck — tsc --noEmit | Pass | Zero errors |
| 2026-06-14 | POST /ask query mode | Pass | Evidence nodes returned, session saved |
| 2026-06-14 | POST /ask path mode (FastAPI→health) | Pass | 2-hop path returned |
| 2026-06-14 | POST /ask explain mode (FastAPI) | Pass | Node detail + 3 connections returned |
| 2026-06-14 | Frontend typecheck after Ask tab — tsc --noEmit | Pass | Zero errors |
| 2026-06-14 | GET /graph/summary (cold) | Pass | 9 nodes, 7 edges; 1s first load |
| 2026-06-14 | GET /graph/summary (cached) | Pass | 75ms subsequent calls |
| 2026-06-14 | GET /graph/summary?project=agents | Pass | 11 sub-projects, 12 edges, 255ms |
| 2026-06-14 | Map tab renders — top-level hub view | Pass | agents at center, Applications connected, outer ring for small projects |
| 2026-06-14 | Map tab drill-down into agents | Pass | 11 sub-projects in ring layout, breadcrumb updated |
| 2026-06-14 | Map inspect panel | Pass | Stats, code%, progress bar, drill-down and path buttons |
| 2026-06-14 | Frontend typecheck after Map tab — tsc --noEmit | Pass | Zero errors |
| 2026-06-14 | POST /decisions (invest, agents) | Pass | Record created with id, timestamps, status=active |
| 2026-06-14 | PATCH /decisions/{id} (rationale update) | Pass | updated_at refreshed, field updated |
| 2026-06-14 | PATCH /decisions/{id} (retire + reactivate) | Pass | Status toggled correctly |
| 2026-06-14 | GET /decisions | Pass | Returns array; empty before first write |
| 2026-06-14 | Persistence check — decisions.json | Pass | File written to workspace/state/decisions.json |
| 2026-06-14 | Frontend typecheck after Decisions tab — tsc --noEmit | Pass | Zero errors |
| 2026-06-14 | GET /recommendations (empty) | Pass | Returns empty array |
| 2026-06-14 | POST /recommendations/generate (next-build) | Pass | Ollama phi4:latest returned title, summary, evidence, confidence=0.75 |
| 2026-06-14 | POST /recommendations/generate (archive-candidates) | Pass | Structured card returned |
| 2026-06-14 | PATCH /recommendations/{id} (accept) | Pass | Status updated, file persisted |
| 2026-06-14 | Frontend typecheck after Recommendations tab — tsc --noEmit | Pass | Zero errors |
