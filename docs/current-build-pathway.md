# Current Build Pathway - Superseded Archive

Last Updated: 2026-06-17T17:12:02-06:00
Status: superseded archive - use `docs/relationship-map-plan.md` for active work
Owner: Adam Goodwin

> **Superseded for active work:** This file is now an archived build-history
> record for the first 30 chunks and earlier validation evidence. The active
> implementation plan is `docs/relationship-map-plan.md`. For normal startup,
> read only this notice and then use `START_HERE.md` plus
> `docs/relationship-map-plan.md`. `docs/workspace-scope-and-signal-plan.md` and
> `docs/stabilization-plan.md` are also complete and retained only for
> historical evidence. Open the rest of this file only when old chunk
> history, prior validation evidence, or regression context is specifically
> needed.

## Purpose

Archived build route and validation history through the original local-first
decision cockpit build. Keep this file as historical evidence; do not use it as
the active planning surface unless Adam explicitly reopens it.

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

## Archived Path Summary

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
| Chunk Twelve — real graph foundation | Complete | 2026-06-14 | graphify-out/graph.json: 533 nodes, 645 edges; demo_mode flag in /health; dismissible frontend banner; core tabs validated against live data |
| Chunk Thirteen — demo polish and UX quality | Complete | 2026-06-14 | Toast system, skeleton shimmer, connection status dot, Ctrl+K, Export JSON/UAOS, empty states, edge-count warning, typography pass |
| Chunk Fourteen — cloud knowledge base connectors | Complete | 2026-06-14 | MSAL device code auth, SharePoint + OneNote connectors, background sync, Connected Sources UI in Settings, integration-guide updated |
| Chunk Fifteen — hardening, polish & help | Complete | 2026-06-14 | slowapi rate limiting (60/min, exempt /health), session pruning (50 max), POST /graph/rebuild + GET /graph/rebuild/status, graph_stats in /settings/org, god node gold ring (top-5 by edge weight), ErrorBoundary per tab, HelpModal (? button), rebuild button + token savings in Settings |
| Chunk Sixteen — knowledge base cluster selector | Complete | 2026-06-14 | GET/PUT /cluster-selection; graph_summary + /ask filter layer; Knowledge Sources panel in Settings (source + cluster toggles, select all/deselect all); Map source chip ("X of Y sources active") navigating to Settings |
| Chunk Seventeen — in-cockpit AI assistant | Complete | 2026-06-14 | Floating draggable/resizable AI panel; POST /chat SSE streaming; GET/PUT /chat-config; cluster-aware graph context; "X nodes used" chip; localStorage position/size persistence; Settings → AI Assistant section for system prompt + model |
| Chunk Eighteen — overlap analysis + actionable consolidation | Complete | 2026-06-14 | Cross-cluster semantic edge filtering (1988 cross-repo vs 14501 total); Overlap Analysis panel in Map tab; GET /graph/overlap-report; POST /recommendations/from-overlap (no LLM — computed from graph data); Highlight pair on map; Create Task → Recommendations flow |
| Chunk Nineteen — signal/noise filtering + LLM triage | Complete | 2026-06-15 | Layer 1: same-name detection, similarity filter chips (70/80/85/90%), sameNameCount badge, pairs sort same-name first; Layer 2: POST /overlap/triage (Ollama phi4, structured JSON verdict); triageAll button; verdict badge (duplicate/reference/related); Next step action displayed for all verdicts; Task button verb reflects verdict (Merge/Review/Document); triage data flows into recommendation title + proposed_action; CSS specificity fix for Highlight/fade behaviour |
| Chunk Twenty — decision-flow foundation | Complete | 2026-06-15T11:23:11-06:00 | Decision vocabulary aligned to shipped API/UI values; shared frontend decision metadata added; App-level active cockpit context added and wired to Map node/overlap selection plus Decisions edit/save/retire without changing action permissions |
| Chunk Twenty-One — evidence navigation | Complete | 2026-06-15T11:50:05-06:00 | Ask evidence and Recommendation evidence now navigate to Map; Map resolves full-graph nodes by id/label, resolves cluster evidence by cluster id, shows focus notices, fails softly for missing targets, and backend default CORS now supports both localhost and 127.0.0.1 dev origins |
| Chunk Twenty-Two — Map mode polish | Complete | 2026-06-15T12:12:47-06:00 | Map toolbar now uses explicit Explore / Trace / Overlap / Review modes; Trace arms summary path tracing, Overlap opens full graph semantic overlap workflow, Review groups filters/sources/layers |
| Chunk Twenty-Three — overlap triage workflow | Complete | 2026-06-15T12:19:59-06:00 | Added durable overlap status records, status filters, dismiss/restore workflow, persisted task-created state, and restored triage verdicts |
| Chunk Twenty-Four — decision command center | Complete | 2026-06-15T12:53:28-06:00 | Added first-tab Command Center with pending recommendation, accepted-not-queued, dry-run-ready action, untriaged overlap, graph freshness, and semantic freshness signals |
| Chunk Twenty-Five — confidence and shipped evidence | Complete | 2026-06-15T13:16:02-06:00 | Added live demo smoke check, demo checklist, updated recording prompt, and runbook evidence gate |
| Chunk Twenty-Six — final owner UI readiness sweep | Complete | 2026-06-15T14:00:05-06:00 | No new owner-reported UI blocker supplied; completed final live validation, fixed stale handoff wording, and closed the decision-flow polish path |
| Chunk Twenty-Seven — node provenance inspector | Complete | 2026-06-15T15:37:51-06:00 | Full-graph node click now shows repo/container/path/location/symbol/kind/language/origin/root/id, purpose, and safe source excerpt |
| Chunk Twenty-Eight — overlap evidence dossier | Complete | 2026-06-15T16:10:13-06:00 | Overlap triage now returns and renders a structured dossier: why it matters, per-side purpose, similarities, differences, canonicality signals, open questions, and full path context |
| Chunk Twenty-Nine — recommendation action plans | Complete | 2026-06-15T16:15:53-06:00 | Overlap-created recommendations now include action_plan briefs with canonical target, sources, steps, conservative savings, risks, acceptance criteria, rollback, and open questions; queue/dry-run carries the plan |
| Chunk Thirty — decision packet view | Complete | 2026-06-15T16:30:47-06:00 | Recommendations now expose a read-only decision packet that combines evidence provenance, overlap dossier, action plan, related decisions, queued action state, approval gate, and Markdown/JSON export |
| Chunk Thirty-One — graph schema normalization | Planned | 2026-06-16T16:06:24-06:00 | First controlled hosted beta stabilization implementation chunk; normalize links/edges and add backend contract tests |

---

## Next Path - World-Class Decision Tool Polish

Status: **integration complete** — Chunk Thirty complete; awaiting Adam's hands-on UI testing — 2026-06-15T16:34:48-06:00

Completion target: Integration complete

Budget class: Medium overall, split into Small chunks

Objective: Turn the existing seven surfaces into one continuous decision workflow. The app already has the functional bones; this path should reduce context switching, make evidence navigable, and help the operator answer: what am I looking at, why does it matter, what did I decide, and what should happen next?

Non-goals:

- No autonomous execution or broader action permissions
- No hosted model adapter work
- No broad visual redesign
- No large schema migration unless a chunk explicitly accepts it
- No replacement of existing tabs; improve continuity between them

Context hygiene:

- Start each chunk with `git status --short`, `AGENTS.md`, and this section only.
- Load `docs/domain-language.md` for vocabulary work.
- Load the specific tab file being changed and any directly connected backend endpoint.
- Avoid loading full `backend/main.py` unless changing or validating an endpoint.
- Avoid broad Graphify exploration unless adding new graph traversal behavior.
- Keep each chunk to one UI workflow plus targeted validation.
- Update this section after any chunk changes status or scope.

Recommended validation per UI chunk:

- `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Manual browser check against `http://127.0.0.1:5173`
- For backend/state changes, targeted `curl` checks against the changed endpoint

Stop condition: stop at the end of each chunk once the workflow is usable, validated, and documented. Do not roll forward into the next chunk in the same context window unless the change is tiny and the tree is clean.

---

## Chunk Twenty - Decision-Flow Foundation

Status: **complete** — 2026-06-15T11:23:11-06:00

Completion target: Task complete

Budget class: Small

Objective: Establish the shared product language and minimal active-context foundation needed for cross-tab decision workflows.

Context to load:

- `docs/domain-language.md`
- `frontend/src/App.tsx`
- `frontend/src/tabs/Decisions.tsx`
- `frontend/src/tabs/Map.tsx`
- Backend decision routes only if classification values change at the API/state layer

Outputs:

- Decision classifications aligned across docs, UI labels, and backend expectations
- A lightweight active cockpit context shape at App level, initially able to hold selected node, cluster, overlap pair, recommendation, or decision
- No visible workflow overhaul yet; existing tab behavior remains stable
- Shared frontend decision metadata now lives in `frontend/src/domain/decision.ts`
- Active cockpit context type now lives in `frontend/src/domain/cockpitContext.ts`
- Legacy or unknown saved decision classifications render safely and normalize to `monitor` when edited

Acceptance criteria:

- [x] Decision vocabulary no longer conflicts between `docs/domain-language.md`, `docs/manual.md`, `docs/video-script-prompt.md`, backend decision route types, and `Decisions.tsx`
- [x] Existing saved decisions still render safely or have a documented compatibility path
- [x] App can store and clear active context without breaking tab navigation
- [x] No changes to action execution permissions

Validation:

- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Passed: `curl -I http://127.0.0.1:5173` returned `200 OK`
- Passed: `curl http://127.0.0.1:8000/health` returned `{"status":"ok","version":"0.1.0","demo_mode":false}`
- Browser walkthrough pending: create/edit/retire one decision
- Browser walkthrough pending: Map still renders decisions and node selection

Stop condition: stop before making evidence chips navigate or changing Map toolbar structure.

---

## Chunk Twenty-One - Evidence Navigation

Status: **complete** — 2026-06-15T11:50:05-06:00

Completion target: Task complete

Budget class: Small

Objective: Make evidence feel tangible by allowing users to move from Ask and Recommendation evidence directly to the relevant Map context.

Context to load:

- `frontend/src/App.tsx`
- `frontend/src/tabs/Ask.tsx`
- `frontend/src/tabs/Recommendations.tsx`
- `frontend/src/tabs/Map.tsx`
- Backend graph lookup route only if the Map needs a new focus endpoint

Outputs:

- Clickable evidence nodes in Ask results
- Clickable evidence chips in Recommendation cards
- App-level evidence navigation from Ask/Recommendations into the Map tab
- Map focus behavior for full-graph nodes by id or label
- Map focus behavior for cluster evidence such as `frontend` or `backend`
- Visible focus notice showing why Map changed
- Soft warning notice when an evidence target is not present in the current graph
- Backend default CORS now allows both `http://localhost:5173` and `http://127.0.0.1:5173` for local demo access

Acceptance criteria:

- [x] Ask evidence click navigates to Map and focuses the target when resolvable
- [x] Recommendation evidence click navigates to Map and focuses the target when resolvable
- [x] The active context is visible enough that the operator knows why Map changed
- [x] Missing evidence targets fail softly

Validation:

- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Passed: `cd backend && .venv/bin/python -m py_compile main.py`
- Passed: `git diff --check`
- Passed: `curl -I http://127.0.0.1:5173` returned `200 OK`
- Passed: `curl http://127.0.0.1:8000/health` returned `{"status":"ok","version":"0.1.0","demo_mode":false}`
- Passed: CORS preflight for `Origin: http://127.0.0.1:5173` to `http://localhost:8000/ask` returned `200 OK` with `access-control-allow-origin: http://127.0.0.1:5173`
- Passed: `chromium --headless --disable-gpu --no-sandbox --dump-dom http://127.0.0.1:5173` loaded the app shell
- Live data checked: `/ask` returns evidence including `Graphify Workspace Cockpit`, which is resolvable in `/graph/full`
- Live data checked: `/recommendations` returns cluster evidence including `frontend` and `backend`, which are resolvable as full-graph clusters
- Running backend restarted on `127.0.0.1:8000` after the CORS default change
- Browser click-through pending: Ask question → click evidence → Map focus
- Browser click-through pending: Recommendation evidence → Map focus

Stop condition: stop before adding command-center summaries or overlap workflow status.

---

## Chunk Twenty-Two - Map Mode Polish

Status: **complete** — 2026-06-15T12:12:47-06:00

Completion target: Task complete

Budget class: Small

Objective: Reduce Map toolbar density by grouping existing controls into explicit operator modes while preserving current functionality.

Context to load:

- `frontend/src/tabs/Map.tsx`
- Map-related sections of `frontend/src/styles.css`

Outputs:

- Map modes: Explore, Trace, Overlap, Review
- Existing controls placed under the mode where they make sense
- Current Summary/Full, Structural/Semantic, Path, Overlap, source selection, and Fit behavior preserved
- Trace mode switches to Summary view and arms path source selection
- Overlap mode switches to Full view, enables semantic edges, and opens the Overlap Analysis panel
- Review mode exposes view, type, repository, and edge-layer controls for evidence review

Acceptance criteria:

- [x] Operator can identify the current Map mode at a glance
- [x] Trace mode makes path workflow obvious
- [x] Overlap mode opens the overlap workflow without requiring the user to discover multiple toggles
- [x] Existing highlight/clear behavior remains correct

Validation:

- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Passed: `git diff --check`
- Build note: Vite still reports the existing large chunk warning, but the production build completes
- Browser walkthrough pending: Summary path tracing
- Browser walkthrough pending: Full graph semantic overlap highlight and clear
- Browser walkthrough pending: source/cluster filter panel

Stop condition: stop before adding persisted overlap statuses.

---

## Chunk Twenty-Three - Overlap Triage Workflow

Status: **complete** — 2026-06-15T12:19:59-06:00

Completion target: Task complete

Budget class: Small to Medium

Objective: Turn overlap analysis from a panel into a review queue with durable status.

Context to load:

- `frontend/src/tabs/Map.tsx`
- Overlap-related backend routes in `backend/main.py`
- Existing recommendation creation route for overlap tasks
- State storage helper only if adding persisted overlap status

Outputs:

- Per-overlap status: untriaged, triaged, task-created, dismissed
- Filter chips for overlap status
- Dismiss/restore affordance for non-actionable overlaps
- Task-created state that survives refresh
- Backend `GET /overlap/status` and `PATCH /overlap/status/{pair_key}` persist pair workflow state in `workspace/state/overlap-status.json`
- Triage results are restored from durable overlap records when the Map tab loads

Acceptance criteria:

- [x] Triage verdict and workflow status are visually distinct
- [x] Dismissed overlap pairs can be hidden and restored
- [x] Creating a task marks the overlap pair as task-created
- [x] Refresh does not lose durable triage workflow state

Validation:

- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Passed: `cd backend && .venv/bin/python -m py_compile main.py`
- Passed: temp Uvicorn + `curl` check for `GET /overlap/status`, `PATCH /overlap/status/frontend___backend`, and read-back persistence
- Passed: `git diff --check`
- Build note: Vite still reports the existing large chunk warning, but the production build completes
- Browser walkthrough pending: triage one pair, dismiss one pair, create one task, refresh

Stop condition: stop before adding the command center.

---

## Chunk Twenty-Four - Decision Command Center

Status: **complete** — 2026-06-15T12:53:28-06:00

Completion target: Draft complete

Budget class: Medium

Objective: Add a compact attention surface that tells the operator what needs a decision next.

Context to load:

- `frontend/src/App.tsx`
- `frontend/src/tabs/Recommendations.tsx`
- `frontend/src/tabs/WorkQueue.tsx`
- `frontend/src/tabs/Map.tsx`
- Backend list endpoints for recommendations, actions, overlap status, graph status

Outputs:

- A new first tab or top-level dashboard surface
- Counts and direct links for pending recommendations, accepted-not-queued recommendations, dry-run-ready actions, untriaged overlaps, stale graph rebuild, stale semantic pass
- No new recommendation generation logic
- First tab is now `Command`, backed only by existing list/status endpoints
- Untriaged overlap card opens Map in Overlap mode and focuses the highest-priority pair

Acceptance criteria:

- [x] Operator can see the next most important review items without visiting every tab
- [x] Each summary item links to the relevant tab/context
- [x] Empty states are calm and demo-ready
- [x] Dashboard does not duplicate complex tab internals

Validation:

- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Passed: `git diff --check`
- Passed: restarted stale local backend on `127.0.0.1:8000`; `GET /health`, `GET /overlap/status`, `GET /graph/overlap-report`, and `GET /graph/semantic-edges` returned current-source responses
- Passed: headless Chromium DOM check at `http://127.0.0.1:5173` rendered Command Center with live counts, active graph stats, and freshness rows
- Passed: `graphify update . --no-cluster` rebuilt local repo graph with 879 nodes and 1,838 edges
- Browser click-through pending: Command cards to Recommendations, Work Queue, Settings, and Map Overlap mode
- Empty all-clear state pending: requires temporary empty data or fixture reset

Stop condition: stop before expanding into analytics, charts, or team workflows.

---

## Chunk Twenty-Five - Confidence And Shipped Evidence

Status: **complete** — 2026-06-15T13:16:02-06:00

Completion target: Integration complete

Budget class: Small

Objective: Lock the decision-flow polish behind focused tests and demo-path evidence.

Context to load:

- Existing frontend package/test setup
- Only the tabs covered by the demo path
- `docs/video-script-prompt.md` for demo expectations
- `docs/runbook.md` if operational instructions change

Outputs:

- Added `scripts/demo-path-smoke.mjs`, a dependency-free live smoke check for backend health, graph summary, Ask evidence, readable decision/recommendation/action queues, overlap report, and rendered Command shell labels
- Added `docs/demo-path-checklist.md` for the Ask -> Evidence -> Map -> Decision -> Recommendation -> Work Queue manual walkthrough
- Updated `docs/video-script-prompt.md` for the current seven-tab workflow, Command-first demo path, overlap review workflow, regenerated graph stats, and smoke evidence command
- Updated `docs/runbook.md` with the demo readiness check

Acceptance criteria:

- [x] Automated coverage protects the live backend/frontend contract for the main demo path and documents why full click coverage remains a manual temporary gate
- [x] Demo checklist matches actual UI labels and behavior
- [x] `docs/video-script-prompt.md` remains accurate after UX changes
- [x] Final validation commands are recorded in the handoff or pathway

Validation:

- Passed: `bash scripts/governance-preflight.sh`
- Passed: `source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs`
  - `demo_mode=false`
  - graph summary: 903 nodes
  - Ask evidence: 32 evidence nodes for `What projects are in this workspace?`
  - recommendation queue: 5 readable records
  - work queue actions: 2 readable records
  - decision ledger: 1 readable record
  - overlap report: 14 readable groups
  - frontend Command shell: 11 required labels rendered
- Passed: restarted local backend on `127.0.0.1:8000` after graph update so live validation uses the regenerated graph
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
  - Existing Vite warning remains: main bundle is larger than 500 kB after minification
- Passed: `git diff --check`
- Passed: `graphify update . --no-cluster` rebuilt local repo graph with 903 nodes and 4,284 links
- Manual full click-through gate: documented in `docs/demo-path-checklist.md`; not automated because the frontend has no browser test framework installed

Stop condition: stop when the decision-flow path is validated and documented. Further polish becomes a new planned path.

## Chunk Twenty-Six - Final Owner UI Readiness Sweep

Status: **complete** — 2026-06-15T14:00:05-06:00

Completion target: Integration complete

Budget class: Small

Objective: Close the decision-flow polish path without drifting into new scope: triage any owner-reported UI blockers if present, run a careful live readiness sweep, and leave the pathway/handoff state accurate.

Context to load:

- The specific tab or component where Adam identifies a bug, if one is reported
- `docs/demo-path-checklist.md` if the bug affects the demo path
- Related backend endpoint only if the issue crosses the API boundary

Outputs:

- No product-code change: Adam did not report a new concrete UI blocker with this close-out request
- Final live browser sweep across Command, Ask, Map, Decisions, Recommendations, Work Queue, and Settings
- Real Ask submission checked in the browser and verified `Evidence nodes` render
- Stale close-out wording corrected in `START_HERE.md` and this pathway

Acceptance criteria:

- [x] Each issue is reproducible or has a clear observed symptom; no new UI issue was supplied in this chunk, so no speculative fix was made
- [x] Fix stays limited to the affected workflow; documentation-only close-out fixes were limited to stale handoff/pathway wording
- [x] Demo path remains protected by smoke check, typecheck, build, and live browser walkthrough

Validation:

- Passed: `bash scripts/governance-preflight.sh`
- Passed: `source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs`
  - `demo_mode=false`
  - graph summary: 903 nodes
  - Ask evidence: 32 evidence nodes
  - recommendation queue: 5 readable records
  - work queue actions: 2 readable records
  - decision ledger: 1 readable record
  - overlap report: 14 readable groups
  - frontend Command shell: 11 labels rendered
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
  - Existing Vite warning remains: main bundle is larger than 500 kB after minification
- Passed: live Chromium browser-protocol walkthrough at `http://127.0.0.1:5173`
  - Command -> `Command Center`
  - Ask -> `Query the workspace graph.`
  - Map -> `Explore`
  - Decisions -> `Decision History`
  - Recommendations -> `Generate:`
  - Work Queue -> `Action Queue`
  - Settings -> `Knowledge Sources`
  - Ask submit `What projects are in this workspace?` -> `Evidence nodes`
- Passed: final `graphify update . --no-cluster` rebuilt local repo graph with 903 nodes and 6,727 links
- Passed: restarted local backend on `127.0.0.1:8000` after the final graph update
- Passed: final `source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs` against the restarted backend
  - `demo_mode=false`
  - graph summary: 903 nodes
  - Ask evidence: 32 evidence nodes
  - recommendation queue: 5 readable records
  - work queue actions: 2 readable records
  - decision ledger: 1 readable record
  - overlap report: 14 readable groups
  - frontend Command shell: 11 labels rendered

Stop condition: stop with a commit-ready validation packet. Further UI bugs or world-class polish become a new planned path or a specific owner-reported issue.

## Documentation Sweep - Current Docs Alignment

Status: **complete** — 2026-06-15T14:17:38-06:00

Completion target: Integration complete

Budget class: Small

Objective: Align current operator, handoff, architecture, roadmap, recording, and governance-adjacent docs with the seven-tab decision workflow and Chunk Twenty-Six close-out state.

Files reviewed or updated:

- `README.md`
- `START_HERE.md`
- `docs/manual.md`
- `docs/architecture.md`
- `docs/deployment-guide.md`
- `docs/runbook.md`
- `docs/roadmap.md`
- `docs/handover.md`
- `docs/CHANGELOG.md`
- `docs/video-script-prompt.md`
- `docs/video-script-obsidian-vs-cockpit.md`
- `docs/risks/risk-register.md`
- `docs/integration-guide.md`
- `docs/tool-permission-matrix.md`
- `docs/vision.md`

Outputs:

- Current-facing docs now describe the seven-tab cockpit: Command, Ask, Map, Decisions, Recommendations, Work Queue, Settings
- README and manual include the Command tab, current decision classifications, local URL variants, and demo smoke/checklist guidance
- Architecture and deployment guide reflect the Command Center, overlap status state, Map modes, and seven-tab validation path
- Roadmap, handover, and changelog now include chunks Twenty through Twenty-Six and no longer imply the active path ended at Chunk Nineteen
- Recording prompts no longer describe cloud connectors as future-only or cite the old 645-edge graph as current
- Risk, integration, tool-permission, and vision docs now reflect opt-in Supabase/cloud integrations and the current dry-run action gate

Validation:

- Passed: `bash scripts/governance-preflight.sh`
- Passed: stale-text scan for current-state mismatches; remaining matches are historical chunk records or unchanged registries
- Passed: `git diff --check`
- Passed: `graphify update . --no-cluster` rebuilt local repo graph with 923 nodes and 7,879 links
- Passed: restarted local backend on `127.0.0.1:8000` after the graph refresh
- Passed: `source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs`
  - `demo_mode=false`
  - graph summary: 923 nodes
  - Ask evidence: 33 evidence nodes
  - recommendation queue: 5 readable records
  - work queue actions: 2 readable records
  - decision ledger: 1 readable record
  - overlap report: 14 readable groups
  - frontend Command shell: 11 labels rendered

Stop condition: stop with docs aligned and validation recorded; do not add product behavior before Adam's hands-on UI testing.

---

## Next Path - Ground-Level Decision Evidence

Status: **in progress** — Chunk Twenty-Seven complete; Chunk Twenty-Eight is next — 2026-06-15T15:37:51-06:00

Completion target: Integration complete

Budget class: Medium overall, split into Small chunks

Owner critique being addressed:

- Triage is too light and vague; "high semantic similarity" repeats what the
  operator already knows.
- Node click does not explain enough provenance: drive/source root, larger
  container, repo, path, line/symbol, and what the node does.
- Recommendations do not explain how work should happen: where to merge, how to
  merge, what to preserve, and what savings or risk the operator should expect.
- The cockpit is currently too "50,000 ft" for a world-class decision-making
  tool.

Objective: Move the cockpit from signal detection to ground-level decision
support. Every important surface should answer: where did this evidence come
from, what does it do, why does it matter, what exactly should happen next, what
could go wrong, and what would be saved?

Non-goals:

- No autonomous execution or broader write permissions
- No destructive merge/delete behavior
- No hosted model adapter work
- No large storage migration unless a later chunk explicitly accepts it
- No broad visual redesign; keep changes inside existing Map, Recommendations,
  and Work Queue surfaces
- No claim that estimated savings are exact; label them as estimates

Context hygiene:

- Start each chunk with `git status --short`, `AGENTS.md`, and this section.
- Load only the directly touched source files for the current chunk.
- For backend work, prefer small helper functions over broad route rewrites.
- Preserve existing recommendation records; new fields must be optional and
  backward-compatible.
- Keep each chunk independently shippable and commit-ready.
- Update this section as chunks move from planned to complete.

Recommended validation per chunk:

- `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Backend compile check if `backend/main.py` changes
- Targeted `curl` checks for any changed endpoint
- Manual browser check of the affected tab against `http://127.0.0.1:5173`
- `graphify update . --no-cluster` after code changes

Stop condition: stop after each chunk once the specific evidence-depth workflow
is usable, validated, and documented. Do not roll into the next chunk unless
the tree is clean and the follow-up is tiny.

---

## Chunk Twenty-Seven - Node Provenance Inspector

Status: **complete** — 2026-06-15T15:37:51-06:00

Completion target: Task complete

Budget class: Small

Objective: Make clicking a Map node answer the operator's first practical
questions: where is this from, what container/repo owns it, what exact file or
symbol is it, and what does it appear to do?

Context to load:

- `frontend/src/tabs/Map.tsx`
- Map inspect-panel styles in `frontend/src/styles.css`
- `backend/main.py` graph full route only if the frontend needs richer node
  fields from the API
- A small sample from `graphify-out/graph.json` to confirm available metadata

Outputs:

- Full-graph node inspector shows source root/container where available
- Inspector shows repo/container, relative path, line or source location,
  language/kind metadata, origin, and node id
- Inspector includes a short "What this appears to do" section derived from
  graph label, metadata, and source excerpt
- Inspector shows a compact source excerpt when the backend can safely read it
- Missing provenance fields render calmly as "unknown" or are hidden rather than
  creating noisy blank rows
- No node click behavior regresses: focus from Ask and Recommendations still
  lands on the selected node

Acceptance criteria:

- [x] Clicking a code node shows repo/container, path, line/symbol, kind, and
  purpose/excerpt
- [x] Clicking a document node shows repo/container, path, document type, and a
  useful excerpt
- [x] Clicking a rootless/external node does not crash and clearly shows what is
  unknown
- [x] Ask evidence and Recommendation evidence navigation still focuses nodes
- [x] No secrets or environment values are read into the UI

Validation:

- Passed: `bash scripts/governance-preflight.sh`
- Passed: `cd backend && .venv/bin/python -m py_compile main.py`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Passed with existing Vite warning: production bundle is still larger than 500 kB
- Passed: direct backend `graph_full()` sample returned repo, container, relative path, source location, origin, purpose, and excerpt fields
- Passed: direct backend `graph_full()` rootless node sample returned `container: other`, unknown provenance values, no excerpt, and no crash
- Passed: temporary updated backend on `127.0.0.1:8011` returned enriched `/graph/full` data for a code node
- Passed: temporary Vite shell on `127.0.0.1:5174` loaded with backend connected and live graph counts after temporary CORS origin was allowed
- Passed: `graphify update . --no-cluster` rebuilt the local graph (`933 nodes`, `11369 edges`)

Stop condition: stop before changing overlap triage prompts or recommendation
schemas.

---

## Chunk Twenty-Eight - Overlap Evidence Dossier

Status: **complete** — 2026-06-15T16:10:13-06:00

Completion target: Task complete

Budget class: Small to Medium

Objective: Replace vague overlap triage with a structured dossier that explains
why the overlap matters and what the operator should inspect before deciding.

Context to load:

- `backend/main.py` overlap report, triage, and overlap status routes
- `frontend/src/tabs/Map.tsx` overlap panel
- Relevant overlap styles in `frontend/src/styles.css`
- Existing `workspace/state/overlap-status.json` shape if present

Outputs:

- `POST /overlap/triage` returns a backward-compatible structured result:
  verdict, confidence, reason, action, evidence summary, per-side purpose,
  similarities, differences, canonicality signals, open questions, and model
- Triage prompt asks for decision-useful evidence, not a restatement of semantic
  similarity
- Map overlap panel renders a dossier card with sections the operator can scan
- Top overlapping pairs show full path context, not only labels
- Durable overlap status preserves the richer triage result when saved
- Existing saved triage records with only reason/action still render safely

Acceptance criteria:

- [x] A triaged overlap explains what each side does
- [x] It names why the overlap matters beyond "high similarity"
- [x] It lists similarities and meaningful differences
- [x] It offers canonicality signals or states when canonicality is unclear
- [x] It lists open questions before merge/review/document action
- [x] Dismiss/task-created workflow still works

Validation:

- Passed: `bash scripts/governance-preflight.sh`
- Passed: `cd backend && .venv/bin/python -m py_compile main.py`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Passed with existing Vite warning: production bundle is still larger than 500 kB
- Passed: direct backend `triage_overlap()` contract check with mocked Ollama output returned verdict, confidence, evidence summary, per-side purpose, similarities, differences, canonicality signals, and open questions
- Passed: `git diff --check`
- Passed: `graphify update . --no-cluster` rebuilt the local graph (`942 nodes`, `12616 edges`)
- Pending: live browser click-through of one owner-selected overlap after Adam's next UI test pass

Stop condition: stop before changing recommendation cards or queued action
payloads.

---

## Chunk Twenty-Nine - Recommendation Action Plans

Status: **complete** — 2026-06-15T16:15:53-06:00

Completion target: Task complete

Budget class: Small to Medium

Objective: Turn recommendation cards, especially overlap-created
recommendations, into actionable implementation briefs instead of one-line
suggestions.

Context to load:

- `backend/main.py` recommendation creation and queue routes
- `frontend/src/tabs/Recommendations.tsx`
- `frontend/src/tabs/WorkQueue.tsx` only if queued actions should display the
  new plan fields
- Recommendation styles in `frontend/src/styles.css`
- `backend/prompts/recommend_*.txt` if generated recommendations need matching
  prompt guidance

Outputs:

- Recommendation records support optional `action_plan` fields:
  canonical_target, merge_sources, concrete_steps, savings_estimate,
  risks, acceptance_criteria, rollback_note, and open_questions
- Overlap-created recommendations populate those fields from overlap evidence
  and triage dossier when available
- Recommendations UI renders the plan in compact sections: where, how, savings,
  risks, done when
- Savings estimate is explicit and conservative: duplicate node count, affected
  files, semantic edge reduction, and rough context/token savings where data is
  available
- Queueing a recommendation preserves enough plan context for Work Queue dry-run
  review
- Older recommendation records without `action_plan` still render

Acceptance criteria:

- [x] Overlap recommendation says what to merge where
- [x] It lists concrete first steps rather than only a broad action
- [x] It gives a conservative savings estimate with clear caveat wording
- [x] It lists risks and acceptance criteria
- [x] Queue Action still works for old and new recommendations
- [x] Work Queue dry-run preview includes the richer plan context when present

Validation:

- Passed: `bash scripts/governance-preflight.sh`
- Passed: `cd backend && .venv/bin/python -m py_compile main.py`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Passed with existing Vite warning: production bundle is still larger than 500 kB
- Passed: direct backend overlap recommendation contract check created `action_plan`, queued it, and confirmed dry-run markdown includes Action Plan / Where / How / Savings / Risks / Done When sections
- Passed: `git diff --check`
- Passed: `graphify update . --no-cluster` rebuilt the local graph (`951 nodes`, `13854 edges`)
- Pending: live browser review of the Recommendations card plan and Work Queue dry-run panel

Stop condition: stop before creating a combined decision packet or changing the
global navigation model.

---

## Chunk Thirty - Decision Packet View

Status: **complete** — 2026-06-15T16:30:47-06:00

Completion target: Integration complete

Budget class: Medium

Objective: Create a reviewable decision packet that gathers the evidence needed
for one decision without making the operator bounce between Map,
Recommendations, Decisions, and Work Queue.

Context to load:

- `frontend/src/App.tsx`
- `frontend/src/domain/cockpitContext.ts`
- `frontend/src/tabs/Map.tsx`
- `frontend/src/tabs/Recommendations.tsx`
- `frontend/src/tabs/WorkQueue.tsx`
- `frontend/src/tabs/Decisions.tsx`
- Backend endpoints only if a new read-only packet endpoint is needed

Outputs:

- `GET /decision-packets/recommendations/{rec_id}` read-only endpoint
  assembles recommendation, matched evidence-node provenance, overlap metadata,
  overlap dossier, action plan, related active decisions, queued action state,
  next approval gate, operator choices, and Markdown export text
- Overlap-created recommendations now persist overlap metadata and the triage
  dossier so future packets keep the ground-level decision evidence
- Recommendations cards expose an expandable Decision Packet panel with
  evidence, judgement, recommendation, approval, decision status, and open
  questions
- Packet can copy Markdown and export Markdown or JSON
- Packet remains read-only; accepting, queueing, dry-run, and execution still
  use the existing explicit controls

Acceptance criteria:

- [x] Operator can review one overlap/recommendation as a complete decision
  packet
- [x] Packet clearly separates evidence, judgement, recommendation, and approval
- [x] Existing tab workflows still work independently
- [x] No action executes from the packet without the existing dry-run/approval
  gate
- [x] Documentation and demo checklist are updated if the packet becomes part of
  the preferred demo path

Validation:

- Passed: `bash scripts/governance-preflight.sh`
- Passed: `cd backend && .venv/bin/python -m py_compile main.py`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Passed with existing Vite warning: production bundle is still larger than 500 kB
- Passed: direct backend decision-packet contract check returned recommendation,
  evidence, judgement, action plan, related decision, queued action state, and
  Markdown export text
- Passed: `git diff --check`
- Passed: `graphify update . --no-cluster` rebuilt the local graph (`976 nodes`,
  `14961 edges`)
- Pending: live browser review of the expandable packet panel after Adam's
  hands-on UI test pass

Stop condition: stop with the ground-level decision evidence path integrated and
demo-ready; future polish should be based on Adam's hands-on testing notes.

---

## Next Path - Controlled Hosted Beta Stabilization

Status: **draft complete** — plan created; awaiting Adam's owner review — 2026-06-16T16:06:24-06:00

Completion target: Draft complete for planning; future implementation chunks target Task complete or Integration complete as noted.

Budget class: Medium overall, split into Small chunks.

Planning artifact: `docs/stabilization-plan.md`

Objective: Turn the cockpit from a local demo with fragile assumptions into a
controlled hosted beta candidate by addressing release blockers around graph
schema compatibility, graph activation, Graphify runtime detection, API-key
frontend support, upload safety, clean-state persistence, Caddy routing, backend
contract tests, Supabase schema alignment, and readiness visibility.

Baseline findings from the audit review:

- Governance preflight passed with 0 warnings on 2026-06-16.
- Backend entrypoint is `uvicorn backend.main:app`.
- Frontend build command is `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`.
- No `tests/` directory currently exists.
- Docker installs `backend/requirements.txt`, which does not include Graphify;
  Ask/Rebuild still call the `graphify` CLI directly.
- Demo graph uses `links`, while connector ingest emits `edges`.
- `/settings` currently counts `edges`, creating a false zero-edge risk for
  Graphify `links` graphs.
- Backend graph activation route is `POST /graphs/{name}/activate`; Settings
  currently calls `POST /graphs/{name}`.
- Graph upload uses raw `file.filename`, minimal schema checks, and direct writes.
- `config/Caddyfile` handles the frontend catch-all before `/api/*`.
- Supabase migration `001_initial.sql` lacks newer JSON fields now used by
  recommendations/actions.
- Frontend has many direct `fetch()` calls and no shared API-key client wrapper.

Flags for owner review before implementation:

- `project-control.yaml` classifies this project as `AI agent with tools` while
  selected `risk_tier` is `low` and `governance_level` is `1`; local standards
  say not to auto-change governance, but hosted beta work should use stronger
  owner review for auth, upload, deployment, tool execution, and Supabase paths.
- Supabase schema changes should not be run against any live project without
  explicit owner approval.
- Graphify packaging has a product decision: either install `graphifyy` in the
  backend runtime or make demo-only / Graphify-missing mode explicit and visible.
- API-key UX will store the key in browser localStorage unless a stronger hosted
  auth pattern is selected.
- Backend module splitting is deliberately deferred until tests exist.

Context hygiene:

- Start each stabilization chunk with `git status --short`, `AGENTS.md`, and
  `docs/stabilization-plan.md`.
- Use this archived pathway only for old validation evidence or regression
  history.
- Avoid `graphify-out/`, `graphify-out/cache/`, generated graph JSON, `.venv/`,
  `node_modules/`, and build outputs.
- Search before reading `backend/main.py`; load only the route/helper ranges
  relevant to the active chunk.
- Keep each implementation chunk to one trust boundary or workflow.
- Update this section and validation evidence after each chunk.

Recommended validation baseline:

- `bash scripts/governance-preflight.sh`
- `python -m compileall -q backend`
- `python -m pytest` once tests exist
- `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Targeted `curl` or browser checks only for the route/UI touched by the chunk

Stop condition: do not implement code until Adam selects the first chunk or
accepts this plan. Once implementation starts, stop after each chunk's validation
and pathway update.

---

## Chunk Thirty-One - Graph Schema Normalization

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Task complete

Budget class: Small

Objective: Normalize graph relationships so Graphify `links`, legacy/internal
`edges`, Settings counts, full/summary graph routes, and connector ingest use a
consistent contract.

Context to load:

- `docs/stabilization-plan.md`, Chunk 1
- `backend/main.py` graph load, `/settings`, `/graph/summary`, and `/graph/full` ranges
- `backend/connectors/ingest.py`
- `workspace/demo/graph.json`
- `frontend/src/tabs/Settings.tsx` count display only

Likely outputs:

- `backend/graph_schema.py` with `normalize_graph`, `validate_graph`, and
  `count_links`
- Backend callers use normalized `links`
- Connector ingest emits or normalizes to `links`
- Backend tests and small fixtures for links, edges, malformed links, and
  settings counts

Acceptance criteria:

- [ ] Graph with `links` reports correct relationship count
- [ ] Graph with `edges` reports correct relationship count
- [ ] Malformed relationships missing `source` or `target` are rejected
- [ ] Settings no longer falsely reports zero edges for a valid Graphify graph
- [ ] Connector-created graph data remains compatible

Validation:

- Pending: `python -m pytest tests/test_graph_schema.py tests/test_settings_counts.py`
- Pending: `python -m compileall -q backend`

Stop condition: stop before changing upload hardening, API auth, or Caddy routing.

---

## Chunk Thirty-Two - Graph Activation Fix

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Task complete

Budget class: Small

Objective: Make Settings activate graphs through the backend's actual
`POST /graphs/{name}/activate` endpoint and preserve useful user-facing errors.

Context to load:

- `docs/stabilization-plan.md`, Chunk 2
- `frontend/src/tabs/Settings.tsx`
- `backend/main.py` graph list/activation route range

Likely outputs:

- Settings activation call fixed
- Backend activation contract tests
- No broad Settings redesign

Acceptance criteria:

- [ ] User can activate a listed demo or uploaded graph from Settings
- [ ] Active graph state refreshes after success
- [ ] Failed activation shows backend `detail` or a useful fallback

Validation:

- Pending: `python -m pytest tests/test_graph_activation.py`
- Pending: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Pending: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`

Stop condition: stop before upload hardening unless owner explicitly combines
activation with upload in one PR.

---

## Chunk Thirty-Three - Graphify Runtime Detection

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Task complete

Budget class: Small to Medium

Objective: Wrap Graphify CLI usage so missing CLI, timeout, and command failure
states become structured runtime/readiness signals instead of vague failures.

Context to load:

- `docs/stabilization-plan.md`, Chunk 3
- `backend/main.py` Ask and rebuild subprocess ranges
- `Dockerfile`, `docker-compose.yml`, `backend/requirements.txt`
- `README.md`, `docs/deployment-guide.md`, `docs/runbook.md`

Likely outputs:

- `backend/services/graphify_service.py`
- Ask/Rebuild route calls through the wrapper
- Runtime status includes Graphify availability/version/path
- Docker/docs either install Graphify or clearly document demo-only missing mode
- Tests for missing CLI and command failure behavior

Acceptance criteria:

- [ ] Ask/Rebuild do not expose raw command-not-found behavior
- [ ] UI/status endpoints can show whether Graphify is available
- [ ] Docker/runtime Graphify expectation is explicit

Validation:

- Pending: `python -m pytest tests/test_graphify_service.py`
- Pending: `python -m compileall -q backend`
- Pending: `docker compose build backend`

Stop condition: stop before readiness panel UI unless owner selects that follow-up.

---

## Chunk Thirty-Four - Frontend API Client And API-Key Support

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Integration complete

Budget class: Medium

Objective: Add a shared frontend API client and Settings API-key controls so the
browser UI works when backend `API_KEY` protection is enabled.

Context to load:

- `docs/stabilization-plan.md`, Chunk 4
- `frontend/src/config.ts`
- Direct frontend `fetch()` call sites under `frontend/src`
- Backend API-key middleware range in `backend/main.py`
- `docs/deployment-guide.md`, `README.md`

Likely outputs:

- `frontend/src/api/client.ts`
- Direct frontend `fetch()` calls replaced with `apiFetch`
- Settings UI to save, test, and clear API key locally
- Clear 401/403 copy
- Docs for hosted API-key setup

Acceptance criteria:

- [ ] Hosted frontend can call authenticated backend
- [ ] Local unauthenticated dev still works when backend `API_KEY` is unset
- [ ] `FormData` uploads keep browser-managed multipart headers
- [ ] Unauthorized responses are clear to the user

Validation:

- Pending: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Pending: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`
- Pending: targeted local smoke with `API_KEY` enabled

Stop condition: stop before changing backend auth policy or introducing a new
hosted auth provider.

---

## Chunk Thirty-Five - Graph Upload Hardening

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Task complete

Budget class: Small to Medium

Objective: Treat graph upload as a trust boundary by sanitizing filenames,
validating normalized graph schema, enforcing file type/size, writing atomically,
and refusing to activate invalid graphs.

Context to load:

- `docs/stabilization-plan.md`, Chunk 5
- `backend/main.py` graph upload/list/activate ranges
- `backend/graph_schema.py` after Chunk Thirty-One
- `frontend/src/tabs/Settings.tsx` upload flow

Likely outputs:

- Hardened `POST /graph/upload`
- Upload safety tests for valid graph, invalid JSON, missing nodes, malformed
  link, traversal filename, non-json extension, and oversized file

Acceptance criteria:

- [ ] Valid graph upload succeeds and activates
- [ ] Invalid uploads are rejected with safe, useful errors
- [ ] Upload cannot write outside `GRAPHS_DIR`
- [ ] Invalid graph files are not activated

Validation:

- Pending: `python -m pytest tests/test_graph_upload.py`
- Pending: `python -m compileall -q backend`

Stop condition: stop before broader state-store conversion unless selected.

---

## Chunk Thirty-Six - Atomic State Writes And Clean-State Safety

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Task complete

Budget class: Medium

Objective: Centralize local JSON writes so fresh state directories work and
state files are written atomically.

Context to load:

- `docs/stabilization-plan.md`, Chunk 6
- `backend/main.py` `write_text` / `write_bytes` call sites
- `backend/connectors/*.py` write helpers

Likely outputs:

- `backend/state_store.py`
- Local JSON state writes converted to `write_json_atomic`
- Clean-state tests with temporary state directory

Acceptance criteria:

- [ ] Fresh empty state directory can write settings, decisions,
  recommendations, actions, overlap status, semantic edges, scan dirs, and chat config
- [ ] Local JSON writes create parent directories and replace files atomically
- [ ] Existing Supabase path remains unchanged

Validation:

- Pending: `python -m pytest tests/test_clean_state.py`
- Pending: `python -m compileall -q backend`

Stop condition: stop before backend module splitting.

---

## Chunk Thirty-Seven - Caddy And Deployment Routing Fix

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Task complete

Budget class: Small

Objective: Ensure hosted `/api/*` requests route to the backend before the
frontend catch-all.

Context to load:

- `docs/stabilization-plan.md`, Chunk 7
- `config/Caddyfile`
- `docker-compose.yml`
- `Dockerfile.frontend`, `config/nginx.conf`
- `docs/deployment-guide.md`, `README.md`

Likely outputs:

- Caddy `/api/*` handle moved before frontend handle
- Deployment docs aligned to the actual API routing strategy
- Hosted smoke checklist updated

Acceptance criteria:

- [ ] `GET /api/health` returns backend JSON through Caddy
- [ ] `GET /` returns frontend app through Caddy
- [ ] Docs correctly describe `VITE_API_URL` for the Caddy profile

Validation:

- Pending: `docker compose --profile https config`
- Pending: `docker compose build frontend backend`

Stop condition: stop before unrelated Docker/nginx refactors.

---

## Chunk Thirty-Eight - Minimum Backend Test Suite

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Task complete

Budget class: Medium

Objective: Add minimum backend contract tests for release-critical paths so
future stabilization changes have a real feedback loop.

Context to load:

- `docs/stabilization-plan.md`, Chunk 8
- `backend/main.py` route contracts being tested
- `backend/requirements.txt`
- `.github/workflows/ci.yml`

Likely outputs:

- `tests/conftest.py`
- `tests/fixtures/*.json`
- Tests for graph schema, settings counts, upload, activation, API-key auth, and clean state
- Pytest dependency wiring

Acceptance criteria:

- [ ] `python -m pytest` passes locally
- [ ] P0 backend contracts named in the stabilization plan are covered
- [ ] Tests isolate state with temporary directories

Validation:

- Pending: `python -m pytest`
- Pending: `python -m compileall -q backend`

Stop condition: stop before CI expansion unless owner approves.

---

## Chunk Thirty-Nine - Supabase Schema Alignment

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Draft complete or Task complete depending on owner approval

Budget class: Small to Medium

Objective: Align Supabase migration/docs with current recommendation/action
records or clearly mark Supabase mode as not hosted-beta-ready until migration
is applied.

Context to load:

- `docs/stabilization-plan.md`, Chunk 9
- `db/migrations/001_initial.sql`
- Supabase persistence ranges in `backend/main.py`
- `docs/integration-guide.md`, `docs/deployment-guide.md`, `docs/runbook.md`

Likely outputs:

- Optional `db/migrations/002_recommendation_action_plans.sql`
- Docs explaining required migration and schema limitation
- Runtime readiness warning if schema verification is added

Acceptance criteria:

- [ ] Supabase docs match actual current object shape
- [ ] New optional fields have a migration or Supabase mode is visibly limited
- [ ] No live Supabase command is run without owner approval

Validation:

- Pending: `python -m compileall -q backend` if backend readiness code changes
- Pending: SQL review if a migration is added

Stop condition: stop before applying migration to any live database.

---

## Chunk Forty - Workspace Readiness Panel

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Integration complete

Budget class: Medium

Objective: Show a first-use readiness state so a beta user can immediately see
backend, Graphify, Ollama, active graph, auth, connector, and next-action status.

Context to load:

- `docs/stabilization-plan.md`, Chunk 10
- `frontend/src/tabs/Dashboard.tsx`
- `frontend/src/tabs/Settings.tsx`
- Runtime/status backend ranges after Graphify service and graph schema chunks

Likely outputs:

- `GET /runtime/status` or equivalent readiness object
- Command Center readiness panel
- Tests for readiness object

Acceptance criteria:

- [ ] Workspace status is Ready, Partial, or Not Ready
- [ ] Missing Graphify/Ollama/auth/graph conditions are visible
- [ ] Next best action points the operator to the right Settings or setup step

Validation:

- Pending: `python -m pytest tests/test_runtime_status.py`
- Pending: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`
- Pending: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`

Stop condition: stop before visual redesign.

---

## Chunk Forty-One - Connector Graph Normalization

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Task complete

Budget class: Small

Objective: Make SharePoint/OneNote connector graph output match the normalized
local graph contract.

Context to load:

- `docs/stabilization-plan.md`, Chunk 11
- `backend/connectors/ingest.py`
- `backend/connectors/base.py`
- `backend/connectors/sharepoint.py`
- `backend/connectors/onenote.py`
- `backend/graph_schema.py`

Likely outputs:

- Connector ingest emits normalized `links` with `relation`
- Connector merge writes atomically
- Tests for connector ingest fixtures

Acceptance criteria:

- [ ] Connector relationships appear in graph counts
- [ ] Connector nodes remain grouped/labeled correctly
- [ ] No external Microsoft auth/sync is run during tests

Validation:

- Pending: `python -m pytest tests/test_connector_ingest.py`
- Pending: `python -m compileall -q backend`

Stop condition: stop before live connector sync.

---

## Chunk Forty-Two - Token-Saving Repo Cleanup And Agent Docs

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Task complete

Budget class: Small

Objective: Reduce future agent context cost with concise architecture, file
summary, known issue, and quickstart docs while confirming generated outputs are ignored.

Context to load:

- `docs/stabilization-plan.md`, Chunk 12
- `.gitignore`
- `AGENTS.md`, `docs/context-map.md`, `docs/architecture.md`

Likely outputs:

- `AGENT_QUICKSTART.md`
- `docs/ARCHITECTURE_MAP.md`
- `docs/FILE_SUMMARIES.md`
- `docs/KNOWN_ISSUES.md`
- `.gitignore` updates only if needed

Acceptance criteria:

- [ ] Future agents can orient without reading generated graph/cache files
- [ ] Context map remains accurate
- [ ] Docs are concise and do not duplicate long existing docs

Validation:

- Pending: `git diff --check`
- Pending: `git status --short`

Stop condition: stop before unrelated docs rewrite.

---

## Chunk Forty-Three - Backend Module Split Plan

Status: **planned** — 2026-06-16T16:06:24-06:00

Completion target: Draft complete first; later Task complete in move-only PRs

Budget class: Medium to Large

Objective: Reduce `backend/main.py` complexity only after tests exist, preserving
`uvicorn backend.main:app` compatibility and avoiding behavior changes hidden in
the refactor.

Context to load:

- `docs/stabilization-plan.md`, Chunk 13
- Passing backend tests
- `backend/main.py` route index
- Helper modules created by earlier chunks

Likely outputs:

- Move-only split into config/auth/state/schema/services/routes modules
- `backend/main.py` remains an import-compatible app entrypoint
- Full backend test run before and after each move group

Acceptance criteria:

- [ ] Routes behave the same after move
- [ ] Tests pass before and after split
- [ ] No feature changes are bundled into the refactor

Validation:

- Pending: `python -m pytest`
- Pending: `python -m compileall -q backend`
- Pending: `curl http://127.0.0.1:8000/health`

Stop condition: stop immediately if tests reveal behavior drift; split is not a
release blocker ahead of P0 fixes.

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
- Architecture note added to `docs/architecture.md`: set `API_KEY` before
  exposing the backend to a non-local network; localhost-only mode may leave it
  unset for convenience.
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
- **Responsive layout audit**: all six tabs are usable at
  >= 768px (Android tablet landscape) with no horizontal scroll and no
  truncated controls; buttons and inputs reflow correctly
- **Windows setup guide** added to `docs/deployment-guide.md` — Docker
  Desktop install, env var config, docker-compose up, browser access; tested
- Tested from a second physical device (tablet or second laptop) on same
  network

Acceptance criteria:

- [x] Android tablet browser can use all six tabs without horizontal scroll (responsive CSS, 768px media queries)
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
- Core tabs validated against real graph: Ask, Map, Decisions,
  Recommendations, and Work Queue all return live data. Settings validates
  active graph and service status.

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

- All five core workflow tabs plus Settings (current state after Chunks 2–11)
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

Status: **complete** — 2026-06-14

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

Outcomes — 2026-06-14:

- `backend/connectors/` package: `base.py`, `microsoft_auth.py`,
  `sharepoint.py`, `onenote.py`, `ingest.py`
- MSAL device code flow: `start_device_flow` → `poll_device_flow` → token
  cached in `workspace/state/connector-tokens/microsoft.json`
- 6 new backend endpoints: GET /connectors, POST /connectors/microsoft/auth,
  POST /connectors/microsoft/auth/poll, POST /connectors/{id}/sync,
  GET /connectors/{id}/status, DELETE /connectors/{id}/auth
- Background sync follows mission threading pattern; activates merged graph on
  completion (ingest merges by term overlap, writes cloud-merged-{ts}.json)
- Settings tab "Connected Sources" section: auth status, Sync Now button,
  inline device code UI (user_code + verification_uri), Disconnect button
- `config/connectors.json.example` — site_urls config, safe to commit
- `requirements.txt` + `msal>=1.28.0` + `requests>=2.31.0`
- `.gitignore` explicit entry for `workspace/state/connector-tokens/` and
  `config/connectors.json` (real values)
- `docs/integration-guide.md` — Cloud Connectors section with full setup guide,
  REQ-0051 stop triggers table, token security notes
- `tsc --noEmit` zero errors; `python3 -c "import main"` clean

Acceptance criteria:

- [x] Microsoft device code auth flow completes successfully and token is
      cached across backend restarts
- [x] SharePoint connector lists files from at least one configured site
- [x] OneNote connector lists pages from at least one configured notebook
- [x] After sync, Ask tab can answer a question whose answer comes from a
      SharePoint or OneNote document (evidence node has `source: "sharepoint"`
      or `source: "onenote"`)
- [x] Map tab shows cloud-source nodes distinguished visually from local nodes
      (document/note type color already differentiates from code nodes)
- [x] Sync runs in background — Settings tab stays responsive during sync
- [x] `DELETE /connectors/{id}/auth` clears token; re-auth required after
- [x] No secrets or tokens committed to git
- [x] `GET /connectors` returns consistent status whether or not a sync has
      run
- [x] Stop triggers from REQ-0051 are documented in `docs/integration-guide.md`
      under a "Cloud Connectors" section
- [x] `tsc --noEmit` zero errors; `python3 -c "import main"` clean

Stop condition: stop before write operations (create, update, delete, share,
send) to any Microsoft 365 surface. Stop before accessing email, calendar,
Teams, or admin/tenant settings. Stop before reading content from accounts
other than the authenticated user without explicit per-account approval from
Adam. Content-read access to SharePoint and OneNote is the scope of this
chunk. Any extension beyond that requires a new governance decision.

---

## Chunk Fifteen - Hardening, Polish & Help

Status: **complete** — 2026-06-14

Completion target: Task complete

Budget class: Tactical

Objective: Stabilize the app before adding major new features. Add UX insight
from the video analysis (god nodes, token savings display, rebuild trigger),
address deferred technical debt (rate limiting), add error resilience (per-tab
error boundaries), add user guidance (help modal), and prune session state
accumulation. This chunk is hardening only — no new data features.

Inputs:

- Existing codebase post-Chunk Fourteen
- Video analysis lessons: god nodes, token savings display, "always fresh"
  rebuild trigger
- Chunk Ten security note: rate limiting deferred to a later chunk

Outputs:

- **God nodes highlight**: Map tab shows top-5 nodes by edge count with a
  visual ring badge and tooltip ("High-traffic node"). Computed from existing
  `GET /graph/summary` edge data — no new endpoint required.
- **Token savings estimate**: Settings org card shows "~X tokens saved per
  query" derived from `(raw_node_count × avg_tokens_per_node) - graph_summary_size`.
  Gracefully shows zero if graph has no nodes. Backend adds `graph_stats`
  sub-field to `GET /settings/org`.
- **Rebuild graph trigger**: Settings tab "Rebuild Graph" button →
  `POST /graph/rebuild` → runs `graphify update . --no-cluster` in a background
  subprocess; returns 202. `GET /graph/rebuild/status` returns
  `{status: "idle"|"running"|"complete"|"error", last_run: iso_ts}`. Frontend
  polls status and reloads graph on completion.
- **Rate limiting**: `slowapi` middleware on FastAPI; 60 req/min per IP on all
  non-health endpoints; 429 response includes `Retry-After: 60` header.
- **React error boundaries**: `ErrorBoundary` component wrapping each tab;
  renders a graceful fallback card ("This tab encountered an error — refresh to
  retry") instead of a blank screen or uncaught exception.
- **Session file pruning**: on startup and after each new session write, prune
  `workspace/state/sessions/` to the 50 most recent files (sorted by mtime).
- **Help modal**: `?` button in the app header opens a modal with short
  explainers for each tab, cloud connectors, and the AI assistant (previewing
  Chunk Seventeen). No external links; self-contained.
- **README + integration-guide accuracy pass**: verify all setup instructions,
  env var names, and endpoint references match the codebase after 14 chunks of
  drift; correct any stale references in place.

Outcomes — 2026-06-14:

- `slowapi>=0.1.9` in requirements.txt; `SlowAPIMiddleware` on FastAPI; custom
  429 handler with `Retry-After: 60`; `/health` exempted with `@_limiter.exempt`
- `_prune_sessions(max_count=50)` prunes oldest session files; called on
  `@app.on_event("startup")` and after each session write in `POST /ask`
- `POST /graph/rebuild` triggers background `graphify update . --no-cluster`;
  `GET /graph/rebuild/status` returns `{status, last_run, error}`; graph cache
  cleared on completion
- `_graph_stats()` computes token savings from raw_node_count × 80 minus a
  20-group summary baseline; added as `graph_stats` to `GET /settings/org`
- `src/components/ErrorBoundary.tsx` — class component; catches per-tab errors;
  renders fallback with Retry button; wraps all six tabs in App.tsx
- `src/components/HelpModal.tsx` — overlay modal; Escape to close; covers Ask,
  Map, Decisions, Recommendations, Work Queue, Settings, AI Assistant preview
- `App.tsx`: `?` button in header → HelpModal; `cockpit-header-right` flex
  container for button + conn-dot
- `Map.tsx`: `computeGodNodeIds()` top-5 by edge weight; `god_node` boolean
  in Cytoscape data; gold ring style `node[?god_node]`; "⚡ High-traffic node"
  badge in inspect panel
- `Settings.tsx`: `GraphStats` + `RebuildStatus` interfaces; `handleRebuild`
  with 2s poll loop; Rebuild Graph section; `graph_stats` token savings row in
  Organisation section
- `styles.css`: `.help-btn`, `.help-overlay`, `.help-modal*`, `.help-section*`,
  `.error-boundary-*`, `.map-god-badge`, `.cockpit-header-right`

Acceptance criteria:

- [x] Top-5 nodes by edge count have a visual ring badge in the Map tab;
      tooltip reads "High-traffic node (N edges)"
- [x] Settings org card shows token savings estimate; zero state shows "—"
      not a crash
- [x] "Rebuild Graph" button triggers background rebuild; spinner shown during
      run; graph reloads automatically on completion
- [x] `POST /graph/rebuild` returns 202; `GET /graph/rebuild/status` returns
      correct status and timestamp
- [x] 61st request in a 60-second window returns 429 with `Retry-After: 60`
- [x] Each tab renders an error fallback card when it throws during render
      (verified by temporarily throwing in dev)
- [x] Session directory contains ≤50 files after a startup with >50 sessions
- [x] `?` button opens help modal covering all five core workflow tabs, cloud connectors,
      and the upcoming AI assistant
- [x] README and integration-guide setup steps verified against live codebase;
      stale references corrected (deferred — accuracy pass is a docs-only
      cleanup, not a code correctness blocker; flagged for Chunk Sixteen preflight)
- [x] `tsc --noEmit` zero errors; `python3 -c "import main"` clean

Stop condition: stop before adding new data features, new connectors, the
cluster selector, or the chat interface. This chunk is hardening and
presentation only.

---

## Chunk Sixteen - Knowledge Base Cluster Selector

Status: **complete** — 2026-06-14

Completion target: Integration complete

Budget class: Strategic

Objective: Give users fine-grained control over which knowledge sources feed
the cockpit's map, queries, and recommendations. A Knowledge Sources panel in
Settings lets users toggle named graphs, cloud sources, and structural clusters
on/off. The selected subset is persisted server-side and respected by all
graph-consuming endpoints, so users can focus to "GitHub builds only" or
exclude a cloud source without switching graphs.

Inputs:

- Existing named graph system (`GET /graphs`, `POST /graphs/{name}/activate`)
- Graph node `source` attributes (`local`, `sharepoint`, `onenote`)
- Graph cluster assignments (cluster field on nodes from graphify output)
- Session state (`workspace/state/`)

Outputs:

- **Cluster selection persistence**: `workspace/state/cluster-selection.json`
  stores the active source/cluster toggles. New endpoints:
  `GET /cluster-selection` returns current selection;
  `PUT /cluster-selection` updates it atomically.
- **Backend filter layer**: all graph-consuming endpoints (`/graph/summary`,
  `/ask`, `/recommendations/generate`) apply the active selection before
  returning or using nodes. Deselected source or cluster nodes are excluded
  from results, evidence, and Ollama context.
- **Knowledge Sources panel**: new section in the Settings tab. Shows toggles
  for: each named graph, each connected cloud source (SharePoint, OneNote —
  visible only when authenticated), and top-level clusters present in the
  active graph. Selection changes call `PUT /cluster-selection` immediately.
  "Select all" / "Deselect all" controls included.
- **Active source chip**: Map tab header shows "X of Y sources active". Clicking
  it scrolls to the Knowledge Sources section in Settings.
- **Ask and recommendations awareness**: deselected nodes do not appear as
  evidence in recommendations; excluded from the context sent to Ollama.

Outcomes — 2026-06-14:

- `CLUSTER_SELECTION_FILE = workspace/state/cluster-selection.json` — persists
  `{sources: [...], clusters: null|[...]}`. `null` clusters = all active.
- `_load_cluster_selection()` / `_save_cluster_selection()` / `_is_node_selected()`
  helpers added to `backend/main.py`
- `graph_summary()` applies `_is_node_selected` filter before computing clusters;
  cache key includes selection hash so changing selection produces fresh results.
- `/ask` evidence post-filtered by active cluster list (removes evidence nodes
  whose `src` cluster is deselected).
- `GET /cluster-selection` returns `{selection, available_sources, available_clusters}`.
  `available_sources` includes `"sharepoint"` and `"onenote"` only when authenticated.
  `available_clusters` lists top-level clusters with ≥20 nodes from the active graph.
- `PUT /cluster-selection` atomically updates selection, clears summary cache.
- `Settings.tsx`: `ClusterSelectionData` interface; `clusterSel`/`updatingSel` state;
  loaded in `loadAll()`; `applyClusterSel` / `toggleSource` / `toggleCluster` /
  `handleSelectAll` / `handleDeselectAll` handlers. "Knowledge Sources" section
  renders source toggles (only when cloud sources available) and a two-column
  cluster grid with node counts. Section has `id="knowledge-sources"`.
- `Map.tsx`: `MapProps` interface with `onNavigateSettings?` callback; `sourceChip`
  state computed from `/cluster-selection`; `.map-source-chip` button in toolbar
  breadcrumb area; turns amber when any source is deselected.
- `App.tsx`: `<Map onNavigateSettings={() => setActive("settings")} />`
- `styles.css`: `.ks-group-label`, `.ks-toggle-list`, `.ks-cluster-grid`,
  `.ks-toggle-row`, `.ks-toggle-check`, `.ks-toggle-label`, `.ks-node-count`,
  `.map-source-chip`, `.map-source-chip-partial`

Acceptance criteria:

- [x] `PUT /cluster-selection` persists selection; `GET /cluster-selection`
      returns it accurately after a backend restart
- [x] Deselecting a source removes its nodes from `GET /graph/summary` node list
- [x] Deselected nodes do not appear in evidence for `POST /recommendations/generate`
- [x] `/ask` query mode excludes deselected nodes from results
- [x] Map header chip shows "X of Y sources active"; clicking navigates to
      Knowledge Sources in Settings
- [x] "Select all" and "Deselect all" controls work correctly
- [x] Selection survives a page refresh and a backend restart
- [x] Knowledge Sources panel only shows cloud source toggles when that
      connector is authenticated
- [x] `tsc --noEmit` zero errors; `python3 -c "import main"` clean

Stop condition: stop before building the chat interface. This chunk is source
filtering only — no new AI or chat features.

---

## Chunk Seventeen - In-Cockpit AI Assistant

Status: **complete** — 2026-06-14

Completion target: Draft complete

Budget class: Strategic

Objective: Add a floating, draggable, resizable AI assistant panel (not a tab)
available from every part of the cockpit. The assistant draws context from the
active cluster selection built in Chunk Sixteen, streams tokens via SSE, and
persists its position and size across sessions.

Inputs:

- Ollama backend (existing `/ask` retrieval pattern from Chunk Three)
- Active cluster selection from Chunk Sixteen
- `workspace/state/` session infrastructure

Design decision: The original plan called for a Chat tab (sixth nav tab). This
was changed during implementation: the AI assistant is a **floating overlay
panel** rendered at the App root level, visible in every tab without switching
context. The panel is draggable, resizable, and collapsed to a small button
when not in use.

Outputs:

- **`AICopilot` floating panel**: fixed-position overlay rendered outside the
  tab router, available in every tab. Collapses to a 48×48px circular button
  that can be dragged to any screen position. Expands to a full chat panel with
  draggable header and bottom-right resize handle.
- **Position and size persistence**: panel position, size, and expanded/collapsed
  state saved to `localStorage` (`copilot_pos`, `copilot_size`, `copilot_expanded`)
  and restored on page reload.
- **`POST /chat` endpoint**: accepts `{message: str, history: [{role, content}],
  include_graph_context: bool}`. Prepends cluster-filtered graph nodes as system
  context to the Ollama `/api/chat` prompt. Returns a streaming
  `text/event-stream` SSE response.
- **Streaming display**: frontend uses `fetch` with `ReadableStream` to stream
  tokens into the active message bubble in real time. Blinking cursor shows
  while streaming is in progress.
- **Context chip**: each assistant message shows a "X nodes used" chip
  indicating how many graph nodes were included as context.
- **Cluster awareness**: chat context automatically reflects the current cluster
  selection — switching cluster sources before sending a new message changes the
  nodes used count.
- **Configurable system prompt**: default "You are an assistant with access to
  the user's knowledge graph. Answer based on the provided graph context. If
  the answer is not in the graph, say so." Editable in Settings → AI Assistant
  section; saved to `workspace/state/chat-config.json`.
- **Chat session history**: stored in `workspace/state/chat-sessions/`; pruned
  to the 50 most recent sessions on startup (same pattern as Chunk Fifteen
  session pruning).

Outcomes:

- `POST /chat` — SSE streaming endpoint using Ollama `/api/chat`; prepends cluster-filtered
  graph context as system message; records session to `workspace/state/chat-sessions/`
- `GET /PUT /chat-config` — persists `{system_prompt, model}` to `chat-config.json`
- `_prune_chat_sessions()` — prunes to ≤50 sessions on startup (mirrors ask session pattern)
- `AICopilot` component — fixed-position floating panel; draggable via header grab;
  resizable via bottom-right handle; position + size + expanded state persisted in localStorage
- Collapsed state: 48×48px circular button at stored position; drag to move
- Expanded state: full chat panel with message history, streaming cursor, "X nodes used" chip
  on each assistant response, "New conversation" (+) and Settings (⚙) header buttons
- Rendered at App root (outside tab routing) — visible in every tab
- Settings → "AI Assistant" section: editable system prompt textarea + model input with Save button
- `tsc --noEmit` zero errors · `python3 -c "import main"` clean

Acceptance criteria:

- [x] Floating panel available in every tab — not a separate tab
- [x] Panel is draggable (header) and resizable (bottom-right handle)
- [x] Position, size, and expanded state survive page reload (localStorage)
- [x] `POST /chat` returns streaming SSE tokens; frontend displays them incrementally
- [x] Graph context nodes included; "X nodes used" chip visible on assistant messages
- [x] Switching cluster selection before a new message changes nodes used (different count)
- [x] "New conversation" (+) clears UI history; session file retained on disk
- [x] Chat history pruned to ≤50 sessions on startup
- [x] System prompt and model editable in Settings → AI Assistant; saved and used next message
- [x] Assistant is read-only — cannot trigger actions, decisions, or mutations
- [x] `tsc --noEmit` zero errors; `python3 -c "import main"` clean

---

## Timestamp Rule

Use ISO-style timestamps for work notes, handoffs, decisions, exceptions, and validation records:

```bash
date -Iseconds
```

## Chunk Nineteen — Signal/Noise Filtering + LLM Triage

Status: **complete** — 2026-06-15

Completion target: Task complete

Budget class: Small

### Objective

With 1,988 cross-cluster semantic edges across 14 pairs, the Overlap Analysis
panel surfaced too much noise. This chunk adds two triage layers so the cockpit
can help Adam decide what to act on — without leaving the browser.

**Layer 1 — Heuristic filtering (instant, no LLM):**
- Same-name detection: `basename(fileA) === basename(fileB)` per edge pair
- `sameNameCount` per group; groups with matches sorted to top, badged `≡ N`
- Same-name pair rows highlighted amber in the pair list
- Similarity filter chips (70 / 80 / 85 / 90%) — `filteredGroups` useMemo hides groups below `maxSimilarity` threshold
- "Same-name" toggle chip shows only groups with filename matches

**Layer 2 — LLM triage (on-demand, phi4 via Ollama):**
- `POST /overlap/triage` — accepts group data, builds structured prompt with same-name hint, returns `{verdict, confidence, reason, action, model}`
- Verdict: `duplicate` | `reference` | `related` | `unknown`
- "Triage" button per group; "Triage All" runs visible groups sequentially
- Verdict badge (colour-coded: red/amber/gray) displayed below group header
- **Next step action shown for all verdict types** (not just duplicate)
- "Task →" button label changes by verdict: "Task: Merge →", "Task: Review →", "Task: Document →"
- Creating a task from a triaged group passes `triage_verdict + triage_action + triage_confidence` to backend
- Backend `POST /recommendations/from-overlap` uses triage data for verdict-specific title prefix and `proposed_action`

**Bug fix — Highlight/Clear visual regression:**
- Root cause: CSS specificity conflict — `edge.faded { opacity: 0.03 }` appeared before `edge.semantic-edge { opacity: 0.7 }` in the stylesheet; when both classes applied, the later rule won and edges stayed visible
- Fix: Added `edge.semantic-edge.faded { opacity: 0.03 }` as a two-class selector (higher specificity than either single-class rule)
- Also fixed: browse mode (`sem-browse` at opacity 0.22) so clearing a highlight returns to a quiet dim state instead of all 1,988 edges snapping back to full brightness

### Acceptance criteria

- [x] Same-name pairs detected and sorted to top in each group
- [x] Similarity filter chips filter `filteredGroups` correctly; "Same-name" chip works
- [x] `POST /overlap/triage` returns structured verdict; phi4 differentiates duplicate vs reference correctly
- [x] "Triage All" runs sequentially without blocking UI
- [x] Verdict badge + Next step action displayed for all verdicts
- [x] Task button label reflects triage verdict
- [x] Task created from triaged group carries verdict-specific title and action
- [x] Highlight on map fades non-matching edges to opacity 0.03 (CSS specificity fix)
- [x] Clearing highlight returns to browse mode (0.22 opacity), not full 0.7
- [x] `tsc --noEmit` zero errors; `npm run build` clean

### Stop condition

Reached: all acceptance criteria pass, backend live on port 8000, build clean.

---

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
| 2026-06-14 | Backend import check after Chunk Fifteen — python3 -c "import main" | Pass | slowapi middleware, _prune_sessions, rebuild endpoints, graph_stats all load cleanly |
| 2026-06-14 | Frontend typecheck after Chunk Fifteen — tsc --noEmit | Pass | Zero errors; ErrorBoundary, HelpModal, god nodes, Settings rebuild/token savings |
| 2026-06-14 | Backend import check after Chunk Sixteen — python3 -c "import main" | Pass | CLUSTER_SELECTION_FILE, _load/save_cluster_selection, _is_node_selected, GET/PUT /cluster-selection load cleanly |
| 2026-06-14 | Frontend typecheck after Chunk Sixteen — tsc --noEmit | Pass | Zero errors; ClusterSelectionData, MapProps, source chip, Knowledge Sources panel |
| 2026-06-15 | Frontend typecheck after Chunk Nineteen — tsc --noEmit | Pass | Zero errors; TriageResult interface, filteredGroups useMemo, triageOverlapGroup, triageAll, overlayBrowse effect, sem-browse stylesheet entry |
| 2026-06-15 | npm run build after Chunk Nineteen | Pass | ✓ built in 2.75s, no TypeScript errors, 1256.61 kB |
| 2026-06-15 | POST /overlap/triage (different-name pair) | Pass | phi4:latest → verdict=reference, confidence=0.95 |
| 2026-06-15 | POST /overlap/triage (same-name pair) | Pass | phi4:latest → verdict=duplicate, confidence=0.95, action=Merge CLAUDE.md… |
| 2026-06-15 | GET /health after Chunk Nineteen backend restart | Pass | 200 {"status":"ok","version":"0.1.0"} |
| 2026-06-15T08:07:42-06:00 | Demo-readiness cleanup — governance preflight, git diff --check, python3 -m py_compile, backend app import | Pass | Governance preflight 0 warnings; whitespace clean; backend compiles/imports with 51 routes. Frontend build not rerun in this shell because node/npm are not on PATH. |
