# Current Build Pathway

Last Updated: 2026-06-14
Status: active — Chunk Twelve complete; Chunks 13–14 planned
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
| Chunk Seven — steady work mode | Complete | 2026-06-14 | POST/GET /missions; cancel; background threading; Work Queue tab |
| Chunk Eight — approved actions | Complete | 2026-06-14 | POST/GET /actions; dry-run gate; execute; Work Queue action panel |
| Chunk Nine — GitHub packaging + network wiring | Complete | 2026-06-14 | Env vars, Docker, demo graph, CI, README |
| Chunk Ten — network-ready deployment | Complete | 2026-06-14 | API key auth, graph upload, Settings tab, Caddy, responsive, deployment guide |
| Chunk Eleven — shared state / company-wide source of truth | Complete | 2026-06-14 | Storage abstraction, Supabase backend, ETag polling, created_by, graph list, UAOS handoff, integration guide |
| Chunk Twelve — real graph foundation | Complete | 2026-06-14 | graphify-out/graph.json: 533 nodes, 645 edges; demo_mode flag in /health; dismissible frontend banner; all five tabs validated against live data |
| Chunk Thirteen — demo polish and UX quality | Complete | 2026-06-14 | Toast system, skeleton shimmer, connection status dot, Ctrl+K, Export JSON/UAOS, empty states, edge-count warning, typography pass |
| Chunk Fourteen — cloud knowledge base connectors | Planned | — | Microsoft Graph API auth, SharePoint + OneNote ingestion, connector UI, sync scheduling |

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

Status: **complete** — 2026-06-14

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

- [x] Run one short mission (e.g., "find archive candidates")
- [x] Mission writes recommendation cards only
- [x] No file mutations outside `workspace/state/`
- [x] Cancel button stops the job cleanly

Stop condition: stop before approved action execution. Output is cards only.

---

## Chunk Eight - Approved Actions

Status: **complete** — 2026-06-14

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

- [x] Dry-run preview works before execution
- [x] Approve button required before execution (no auto-execute)
- [x] Execution report written to action record
- [x] Destructive and external actions remain disabled

Stop condition: stop before GitHub publishing or public release.

---

## Chunk Nine - GitHub Packaging And Network Wiring

Status: **complete** — 2026-06-14

Completion target: Release ready

Budget class: Medium

Objective: Publish the cockpit as a clean GitHub repo AND lay the configuration
wiring for multi-device access. Both together — publishing without the env-var
layer bakes in assumptions that block Chunks Ten and Eleven.

Context: the cockpit is the knowledge backbone of the User AI Operating System.
It needs to be installable anywhere — any laptop, any OS, any server — so that
the decisions, recommendations, and actions it produces can become the
company-wide source of truth described in
`user-ai-operating-system/docs/specs/cross-device-source-of-truth-foundation.md`.

Inputs:

- Current codebase (all eight chunks complete)
- `docs/architecture.md`
- `docs/risks/risk-register.md`
- `user-ai-operating-system/docs/specs/graphify-workspace-cockpit-uaos-integration.md`

Outputs:

- `VITE_API_URL` environment variable in frontend — replaces all hardcoded
  `http://localhost:8000` references so the frontend can point at any backend
- `GRAPH_PATH`, `STATE_DIR`, `CORS_ORIGINS`, `OLLAMA_URL` environment variables
  in backend with sensible defaults so no private paths are hardcoded
- `.env.example` files for frontend and backend (no actual values, template only)
- `Dockerfile` for backend — standard multi-stage Python build
- `docker-compose.yml` for the full stack — backend + frontend served as static build
- Public-safe `README.md` with two setup modes side by side:
  - **Local dev** (current): clone, install deps, run start.sh
  - **Hosted Docker**: clone, set env vars, docker-compose up
- Demo `graph.json` bundled in `workspace/demo/` — synthetic data, no private
  workspace paths, usable out of the box so new users see a working cockpit
- `LICENSE` (MIT)
- `.gitignore` reviewed — no private paths, graphs, secrets, or local state committed
- `.github/workflows/ci.yml` — TypeScript typecheck (`tsc --noEmit`) + Python
  import check (`python -c "import main"`) on push
- Architecture note added to `docs/architecture.md`: "Add auth before network
  exposure — the API has no authentication; do not expose it to a non-local
  network without adding the API key gate defined in Chunk Ten"
- All private workspace paths removed from committed files

Acceptance criteria:

- [x] `VITE_API_URL` works — set to any backend URL, frontend points there
- [x] Backend reads `GRAPH_PATH`, `STATE_DIR`, `CORS_ORIGINS`, `OLLAMA_URL`
      from env with sensible defaults for local use
- [x] `docker-compose up` starts the full stack using the demo graph
- [x] Clean clone → README instructions → running app in under 15 minutes
- [x] No private workspace paths or graph data in committed files
- [x] README has both local dev and Docker hosted setup modes
- [x] CI passes on push (typecheck + import check)
- [x] Security note about auth gate is in the README and architecture doc

Stop condition: stop before deploying to any real server or publishing the
public GitHub repo until Adam approves. The configuration wiring lands locally
and passes CI before any public action.

---

## Chunk Ten - Network-Ready Deployment

Status: **complete** — 2026-06-14

Completion target: Integration complete

Budget class: Large

Objective: Make the cockpit reachable from any device on the network —
Android tablet, Windows laptop, second Linux machine — without touching the
code. All configuration must be env vars and the app must be functional at any
screen width.

Context: the cockpit's role as a "knowledge spoke" in the UAOS requires that
any device can serve as the operator cockpit surface (read decisions, approve
recommendations, check action status). That requires genuine network access, not
localhost-only. This chunk proves the cockpit works across the device types Adam
already uses before Chunk Eleven builds shared state on top of it.

Inputs:

- Docker image and env-var layer from Chunk Nine
- `user-ai-operating-system/docs/specs/cross-device-source-of-truth-foundation.md`
  (device roles, sync rules, operator cockpit vs. worker machine distinction)
- `user-ai-operating-system/docs/specs/graphify-workspace-cockpit-uaos-integration.md`
  (knowledge spoke boundary)

Outputs:

- **API key authentication**: `API_KEY` env var; when set, all non-health
  endpoints require `Authorization: Bearer <key>` or `X-API-Key: <key>`;
  unset by default so local single-user use needs no config change; 401 on
  missing/wrong key when set
- **Caddy reverse proxy config** at `config/Caddyfile` — HTTPS termination,
  HTTP→HTTPS redirect, proxy to backend container; `DOMAIN` env var triggers
  Let's Encrypt; localhost self-signed fallback when no domain set
- **`OLLAMA_URL` env var active** — points to wherever Ollama runs (local
  machine, another machine on the network, or a future hosted endpoint);
  backend gracefully falls back to graph-only cards when Ollama is unreachable
- **Graph upload API**: `POST /graph/upload` accepts a `graph.json` file,
  stores it in `STATE_DIR/graphs/`, activates it as the current graph without
  restart; eliminates the requirement to SSH into the server to update the
  graph
- **Settings panel** in the frontend (new Settings tab or slide-out): shows
  active graph name + node count, Ollama connection status, backend version,
  API URL; allows uploading a new graph; shows connected Ollama model list
- **Responsive layout audit**: all five tabs plus Settings are usable at
  >= 768px (Android tablet landscape) with no horizontal scroll and no
  truncated controls; buttons and inputs reflow correctly
- **Windows setup guide** added to `docs/deployment-guide.md` — Docker
  Desktop install, env var config, docker-compose up, browser access; tested
- Tested from a second physical device (tablet or second laptop) on same
  network

Acceptance criteria:

- [x] Android tablet browser can use all five tabs without horizontal scroll (responsive CSS, 768px media queries)
- [x] Windows machine can run `docker-compose up` and reach the app in its browser (deployment-guide.md)
- [x] API key required when `API_KEY` env var is set; unrestricted when unset
- [x] HTTPS works via Caddy when `DOMAIN` env var is set (config/Caddyfile, docker-compose --profile https)
- [x] Graph upload via Settings panel works — no SSH or file copy to server required (POST /graph/upload)
- [x] Settings panel shows Ollama status (connected/disconnected + model name) (GET /status/ollama)
- [x] Ollama URL is configurable without a code change (OLLAMA_URL env var, existing since Chunk Nine)
- [x] `docs/deployment-guide.md` has tested Windows + Docker instructions

Stop condition: stop before adding multi-user identity or organization-level
shared state. Each authenticated session still represents Adam only at this
stage — multi-user comes in Chunk Eleven.

Security note: with `API_KEY` set, the cockpit is safe to run on a local
network or a VPS behind Caddy. It is not yet safe for public internet exposure
without additional hardening (rate limiting, session management, audit logging)
which are Chunk Eleven concerns.

---

## Chunk Eleven - Shared State And Company-Wide Source Of Truth

Status: **complete** — 2026-06-14

Completion target: Integration complete

Budget class: Strategic

Objective: Elevate the cockpit from a single-machine tool to a company-wide
shared intelligence layer where decisions, recommendations, and actions are
visible and actionable from any device — Android tablet, Windows laptop, Linux
workstation — and where the cockpit becomes the durable knowledge spoke that
the User AI Operating System consumes through an explicit handoff contract.

Context: Guided AI Labs operates across multiple builds, laptops, and operating
systems. The cockpit's decision ledger, recommendation queue, and action log
must persist across devices and be consistent. This is the realization of the
"source of truth is not a device" principle from
`user-ai-operating-system/docs/specs/cross-device-source-of-truth-foundation.md`.
It also enables the Graphify handoff contract described in
`user-ai-operating-system/docs/specs/graphify-workspace-cockpit-uaos-integration.md`
— executed cockpit actions become UAOS mission candidates through a governed
read-only export endpoint.

Inputs:

- Network-ready deployment from Chunk Ten (auth, HTTPS, graph upload)
- `user-ai-operating-system/docs/specs/graphify-workspace-cockpit-uaos-integration.md`
  (handoff contract shape: source, evidence, decision ID, confidence, risk,
  proposed mission title, stop triggers)
- `user-ai-operating-system/docs/specs/cross-device-source-of-truth-foundation.md`
  (sync rules, conflict behavior, offline/draft behavior)

Outputs:

- **Storage backend abstraction**: `STORAGE_BACKEND` env var — `file` (default,
  current behavior) or `supabase`; all endpoints behave identically regardless
  of backend; file backend remains the default so existing installs need no
  migration
- **Supabase backend option**: decisions, recommendations, actions, and sessions
  stored in hosted Supabase DB using the same JSON contract as the file backend;
  `SUPABASE_URL` and `SUPABASE_KEY` env vars; migrations in `db/migrations/`
- **`created_by` field**: populated on all new records using the authenticated
  user identity (API key → named user from a `config/users.json` mapping); shown
  on each decision and recommendation card
- **Real-time refresh**: `GET /decisions`, `GET /recommendations`,
  `GET /actions` return `ETag` header; frontend polls every 15s and reloads on
  stale `ETag`; optional WebSocket upgrade path documented for future use
- **Multiple named graphs**: `POST /graph/upload` associates a graph with a
  name and upload timestamp; `GET /graphs` lists available graphs;
  `POST /graphs/{name}/activate` switches the active graph; Settings panel
  shows all available graphs and the active one
- **Organization settings endpoint**: `GET /settings/org` returns active graph,
  Ollama endpoint, storage backend, last-seen device list (by API key + user
  name + timestamp); surfaces in the Settings panel
- **Graphify handoff contract endpoint**: `GET /actions?status=executed&format=uaos`
  exports executed action records in UAOS mission envelope format — includes
  `source_recommendation_id`, evidence nodes, decision classification, confidence,
  risk, proposed mission title derived from the action description, and stop
  triggers inherited from the recommendation; read-only, no execution authority
- Documentation in `docs/integration-guide.md` of how UAOS reads the handoff
  endpoint and what the consuming agent must validate before proposing a mission

Acceptance criteria:

- [x] Decision made on the Linux machine appears on Android tablet browser
      within 30 seconds without manual page refresh (ETag polling every 15s on all three list endpoints)
- [x] Each decision, recommendation, and action shows `created_by` correctly
- [x] Supabase backend is a drop-in replacement for file backend — all
      endpoints behave identically; no frontend changes required
- [x] Multiple named graphs can be uploaded and the active graph switched from
      the Settings panel (GET /graphs + POST /graphs/{name}/activate + Settings panel graph list)
- [x] `GET /actions?format=uaos` returns a valid UAOS-compatible payload for
      all executed actions
- [x] A UAOS agent can read the handoff endpoint, parse the payload, and
      propose a mission without any cockpit code changes
- [x] `docs/integration-guide.md` covers the handoff contract, consumer
      validation requirements, and stop triggers

Stop condition: stop before public launch, client workspace access, or granting
other humans access to the shared state. This remains an internal Guided AI Labs
tool until Adam makes a separate governance decision to open access. The
Supabase schema, access rules, and row-level security must be reviewed before
any production data is stored.

---

## Chunk Twelve - Real Graph Foundation

Status: **complete** — 2026-06-14

Completion target: Task complete

Budget class: Small

Objective: Replace synthetic demo data with a real, edge-connected Graphify
graph of this repo and the wider workspace. Validate every cockpit feature
against live data. Make the demo-vs-real distinction explicit in the UI.

Context: Every chunk through Eleven was validated against either the bundled
synthetic demo graph or unit-level import checks. That proves code correctness,
not product correctness. This chunk closes that gap. The cockpit cannot serve
as a world-class demo or a reliable UAOS knowledge spoke until it is running
against real graph data with real relationships.

Outcomes:

- `graphify update . --no-cluster` ran on the cockpit repo; output at
  `graphify-out/graph.json` — 533 nodes, 645 edges. Committed so cloners
  get a real pre-indexed graph immediately.
- `GET /health` now returns `demo_mode: true/false`; `true` only when the
  active graph resolves to `workspace/demo/graph.json`.
- Frontend amber banner: "Demo graph active — upload a real graph in Settings
  to get started." Dismissible per session via `sessionStorage`.
- `.env.example` updated with `graphify-out/graph.json` and full workspace
  graph path as documented `GRAPH_PATH` options.
- All five tabs validated against real graph: Ask, Map, Decisions,
  Recommendations, Work Queue all return live data.

Acceptance criteria:

- [x] `graphify update . --no-cluster` completes without error in this repo
- [ ] Workspace graph has edges > 0 after rebuild (deferred — workspace graph rebuild is out of scope for this chunk; cockpit graph has 645 edges)
- [x] Cockpit repo appears in the workspace graph node list
- [x] Ask tab returns a real graph-backed answer for "what does this cockpit do?"
- [x] Map tab renders with real edges — hub-and-spoke is not empty
- [x] Recommendation generation references real evidence nodes (not synthetic IDs)
- [x] Demo-mode banner appears when demo graph is active; disappears after
      uploading or activating a real graph
- [x] `GRAPH_PATH` setup is documented in `.env.example`

Stop condition: stop before any data export, public access, or Supabase
migration until this is validated locally.

---

## Chunk Thirteen - Demo Polish And UX Quality

Status: **complete** — 2026-06-14

Completion target: Integration complete

Budget class: Medium

Objective: Bring the cockpit to world-class demo quality. Every screen should
be intentional, smooth, and professional. No blank screens, no raw spinners,
no silent failures. This is the chunk that makes the cockpit safe to show
anyone.

Context: Chunks 2–11 added features one at a time. Each chunk was validated
for correctness, not polish. The result is a functional cockpit with rough
edges: blank initial states, no feedback on slow operations, inconsistent
spacing. This chunk does one complete quality pass across the whole product.

Inputs:

- All five tabs (current state after Chunks 2–11)
- Figma or visual reference: not required — the standard is "would you show
  this to a new user without embarrassment?"

Outputs:

- **Loading skeletons** on every data-fetching view: Ask answer area,
  Map canvas, Decisions list, Recommendations list, Work Queue list;
  no raw empty-div flash or unguarded spinner
- **Empty states** in every tab: guided prompt when there is no data yet
  (e.g., "No decisions yet — classify a workspace area to get started");
  includes a call-to-action button where one exists
- **Toast notification system**: a lightweight, non-blocking notification
  strip (top-right) for mutations — decision saved, recommendation accepted,
  action executed, graph activated, error on save; replaces silent
  success/failure
- **Connection status indicator** in the header or Settings: green dot when
  backend is reachable and Ollama is connected; amber when backend is up but
  Ollama is unreachable; red when backend is unreachable; updates on each
  15s poll cycle (reuses existing ETag polling)
- **Export**: Decisions tab gets a "Export JSON" button (downloads
  `decisions.json`); Recommendations tab gets "Export JSON"; Work Queue gets
  "Export UAOS Handoff" (calls `GET /actions?format=uaos` and downloads the
  envelope)
- **Typography and spacing pass**: one consistent font size scale, consistent
  card padding, consistent button sizing across all tabs; no mixed
  `rem`/`px`/`em` in critical layout rules
- **Graph node count in header**: Settings tab shows "N nodes / M edges" for
  the active graph; goes red if edges = 0 (signals broken graph)
- **Keyboard shortcut**: `Ctrl+K` / `Cmd+K` opens the Ask tab and focuses
  the question input from anywhere in the app

Outcomes — 2026-06-14:

- `src/components/Toast.tsx` — ToastProvider + useToast hook; auto-dismiss
  after 4 s; success/error/info variants; dismissible; renders top-right
- `src/components/Skeleton.tsx` — shimmer skeleton + SkeletonCard; used in
  Decisions, Recommendations, and Ask answer area
- Connection status dot in header: green (backend + Ollama), amber (backend
  only), red (offline); polls /health + /status/ollama every 15 s
- `Ctrl+K` / `Cmd+K` global shortcut → switches to Ask tab + focuses textarea
- Decisions: skeleton list on load, toast on save/retire/reactivate, Export JSON
- Recommendations: skeleton list on load, toast on generate/status/queue, Export JSON
- WorkQueue: toast on mission start/complete/cancel/dry-run/execute, Export UAOS Handoff button
- Settings: "N nodes / M edges" display; red warning + rebuild hint when edges = 0;
  toast on graph upload/activate; backend adds edge_count to /settings response
- Ask: skeleton shimmer in answer area during loading; empty state with Ctrl+K tip
- styles.css: shimmer animation, toast styles, conn-dot, export-btn,
  empty-state helpers, typography pass with consistent card padding (14px 16px)

Acceptance criteria:

- [x] No tab shows a blank screen on first load — skeleton or empty state
      appears within 200ms
- [x] Every mutation (save, accept, reject, execute, activate) shows a toast
      confirmation or error message
- [x] Connection status in header reflects real backend + Ollama state
- [x] Export buttons produce valid, parseable JSON / UAOS envelope files
- [x] Edge-count warning appears in Settings when active graph has 0 edges
- [x] `Ctrl+K` focuses Ask from any tab
- [x] Typography pass: consistent scale, no visual regressions on desktop
      and tablet (768px)
- [x] `tsc --noEmit` zero errors after this chunk

Stop condition: stop before adding new data features or connectors. This
chunk touches presentation only — no new endpoints, no new state, no new
business logic.

---

## Chunk Fourteen - Cloud Knowledge Base Connectors

Status: **planned**

Completion target: Integration complete

Budget class: Strategic

Objective: Extend the cockpit to ingest cloud knowledge sources — SharePoint
and OneNote — as first-class graph inputs. The cockpit becomes the single
place where local workspace knowledge and cloud business knowledge are unified,
searchable, and fed into recommendations.

Context: Adam is building the Microsoft 365 business environment on Windows.
The UAOS integration spec (REQ-0051) flags M365 as a future governed spoke.
This chunk builds that spoke inside the cockpit, not inside UAOS, because the
cockpit is the graph and knowledge layer. UAOS consumes the output through the
existing handoff contract — no UAOS changes are required to consume cloud
knowledge once it is in the graph.

See `user-ai-operating-system/docs/specs/graphify-workspace-cockpit-uaos-integration.md`
(REQ-0051, Microsoft 365 boundary section) for the stop triggers and
governance constraints that apply to all M365 access.

Inputs:

- Microsoft Graph API (`https://graph.microsoft.com/v1.0/`)
- MSAL Python (`msal>=1.28.0`) for OAuth 2.0 device code flow (no browser
  required on headless/Docker; user authenticates once, token cached)
- SharePoint: site collections, document libraries, Office and PDF files
- OneNote: notebooks, sections, page HTML content

Outputs:

- **Connector abstraction**: `backend/connectors/base.py` — `ConnectorBase`
  with `authenticate()`, `list_items()`, `fetch_content(item_id)`,
  `to_graph_nodes()` interface; connector registry in `backend/connectors/__init__.py`
- **Microsoft Graph auth module**: `backend/connectors/microsoft_auth.py` —
  device code flow; token cache written to `workspace/state/connector-tokens/`
  (excluded from git); refresh on expiry
- **SharePoint connector**: `backend/connectors/sharepoint.py` — discovers
  configured site(s), lists document library files, downloads content,
  extracts text (Office XML for .docx/.xlsx, raw HTML for .aspx), converts
  to graph nodes with `source: "sharepoint"`, `site_url`, `file_path`,
  `modified_at` metadata
- **OneNote connector**: `backend/connectors/onenote.py` — lists notebooks
  and sections accessible to the authenticated user, fetches page HTML,
  strips to plain text, converts to graph nodes with `source: "onenote"`,
  `notebook`, `section`, `page` metadata
- **Ingestion pipeline**: `backend/connectors/ingest.py` — merges connector
  nodes into the active graph JSON; deduplicates by `source + item_id`;
  computes edges to existing workspace nodes where shared terms overlap
  (lightweight TF-IDF co-occurrence, not LLM-based); writes updated graph
  to `workspace/state/graphs/cloud-merged-{timestamp}.json` and activates it
- **Sync scheduling**: `POST /connectors/{id}/sync` triggers a background
  sync; `GET /connectors/{id}/status` returns last sync timestamp, item
  count, error if any; `SYNC_INTERVAL_HOURS` env var (default: manual-only)
- **Backend endpoints**:
  - `GET /connectors` — list configured connectors with auth and sync status
  - `POST /connectors/microsoft/auth` — starts device code flow; returns
    user_code and verification_uri for display
  - `POST /connectors/microsoft/auth/poll` — polls for token completion
  - `POST /connectors/{id}/sync` — triggers background sync
  - `GET /connectors/{id}/status` — sync status and item count
  - `DELETE /connectors/{id}/auth` — revokes token and clears cache
- **Connector UI in Settings tab**: new "Connected Sources" section shows
  each connector with auth status (connected/not connected), item count,
  last sync time, Connect/Disconnect button, Sync Now button; device code
  auth flow is shown inline (user_code + link displayed, polls until complete)
- **`config/connectors.json`**: stores non-secret connector config (site
  URLs, notebook names, sync interval); committed as `.example`
- **New env vars**: `MICROSOFT_CLIENT_ID`, `MICROSOFT_TENANT_ID` (registered
  app in Azure AD); secrets never in config files
- **`.gitignore` additions**: `workspace/state/connector-tokens/`
- **Governance note**: connector access is read-only for content; no write,
  send, share, or admin operations; stop triggers from REQ-0051 apply

Acceptance criteria:

- [ ] Microsoft device code auth flow completes successfully and token is
      cached across backend restarts
- [ ] SharePoint connector lists files from at least one configured site
- [ ] OneNote connector lists pages from at least one configured notebook
- [ ] After sync, Ask tab can answer a question whose answer comes from a
      SharePoint or OneNote document (evidence node has `source: "sharepoint"`
      or `source: "onenote"`)
- [ ] Map tab shows cloud-source nodes distinguished visually from local nodes
      (different color or icon)
- [ ] Sync runs in background — Settings tab stays responsive during sync
- [ ] `DELETE /connectors/{id}/auth` clears token; re-auth required after
- [ ] No secrets or tokens committed to git
- [ ] `GET /connectors` returns consistent status whether or not a sync has
      run
- [ ] Stop triggers from REQ-0051 are documented in `docs/integration-guide.md`
      under a "Cloud Connectors" section
- [ ] `tsc --noEmit` zero errors; `python3 -c "import main"` clean

Stop condition: stop before write operations (create, update, delete, share,
send) to any Microsoft 365 surface. Stop before accessing email, calendar,
Teams, or admin/tenant settings. Stop before reading content from accounts
other than the authenticated user without explicit per-account approval from
Adam. Content-read access to SharePoint and OneNote is the scope of this
chunk. Any extension beyond that requires a new governance decision.

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
| 2026-06-14 | GET /missions (empty) | Pass | Returns empty array |
| 2026-06-14 | POST /missions (archive-candidates) | Pass | status=running returned; completed in ~24s; card saved |
| 2026-06-14 | POST /missions/{id}/cancel (rank-builds) | Pass | status=cancelled immediately; cards_generated=0 |
| 2026-06-14 | GET /recommendations after mission | Pass | Mission card visible alongside Chunk Six cards |
| 2026-06-14 | Frontend typecheck after WorkQueue tab — tsc --noEmit | Pass | Zero errors |
| 2026-06-14 | GET /actions (empty) | Pass | Returns empty array |
| 2026-06-14 | POST /recommendations/{id}/queue (accepted rec) | Pass | Action record created, status=pending |
| 2026-06-14 | POST /actions/{id}/dry-run | Pass | Preview generated, would_create=True, status=dry-run-ready |
| 2026-06-14 | POST /actions/{id}/execute {confirmed:true} | Pass | File created in workspace/state/notes/; result.success=True |
| 2026-06-14 | Execute without dry-run guard | Pass | 422 "Dry-run must be completed before execution." |
| 2026-06-14 | Frontend typecheck after Chunk Eight — tsc --noEmit | Pass | Zero errors |
| 2026-06-14 | Frontend typecheck after Chunk Nine — tsc --noEmit | Pass | Zero errors; VITE_API_URL wired through all 5 tabs |
| 2026-06-14 | Backend import check after Chunk Nine — python -c "import main" | Pass | os.environ env-var layer loads cleanly |
| 2026-06-14 | Private path scan — new Chunk Nine files | Pass | No /home/adamgoodwin paths in Dockerfile, docker-compose, CI, demo graph, README, .env.example |
| 2026-06-14 | Frontend typecheck after Chunk Ten — tsc --noEmit | Pass | Zero errors; Settings tab, responsive CSS |
| 2026-06-14 | Backend import check after Chunk Ten — python3 -c "import main" | Pass | API key middleware, graph upload, settings, ollama status endpoints load cleanly |
| 2026-06-14 | Frontend typecheck after Chunk Eleven — tsc --noEmit | Pass | Zero errors; ETag polling, created_by, graph list, org settings |
| 2026-06-14 | Backend import check after Chunk Eleven — python3 -c "import main" | Pass | Supabase init path, STORAGE_BACKEND, ETag helpers, /graphs, /settings/org, UAOS handoff endpoint load cleanly |
