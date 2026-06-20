# Start Here

Last Updated: 2026-06-19T18:05:00-06:00
Status: owner sign-off — relationship-map is video-ready; remaining work is polish/tuning, not a rebuild
Owner: Adam Goodwin

## Fast Startup

This file is the official repo-local place to begin after a restart, clear,
compaction, or day handoff. Use it as the lightweight router. Do not load the
historical build log by default.

1. Run `git status --short`.
2. Read `AGENTS.md`.
3. Read `docs/session-handoff-2026-06-18.md` for the latest shutdown note.
4. Read `docs/relationship-map-plan.md`.
5. Start with owner review or post-review tuning unless Adam redirects.
6. Open `docs/workspace-scope-and-signal-plan.md` only for completed scope/signal evidence.
7. Open `docs/stabilization-plan.md` only for completed stabilization evidence.
8. Open `docs/current-build-pathway.md` only when investigating old chunk
   history, validation evidence, or regressions from the original 0-to-1 build.

## State at Pause

Owner sign-off 2026-06-19: Adam reviewed the multi-repo Evidence comparison map
and called it "freaking terrific … video ready." The relationship-map path is
owner-approved; future work is polish/tuning (labels, semantic-edge
explanations, map defaults, ignore tuning), not a rebuild or a new broad slice
unless Adam redirects. Two same-day items: (1) shipped clear-map tuning so
multi-repo region labels hold a constant ~18px on-screen size at any zoom
(commit `995adc3`, pushed); (2) refreshed the canonical cross-repo workspace
graph at `Tools/graphify/workspace/out` (was 7 days stale) with an AST-only
incremental `graphify update`, 35,637 → 41,881 nodes, 0 leakage, backup at
`out/graph.json.bak-2026-06-19`. The original Graphify token-saving workflow was
verified intact: the cockpit consumes the same CLI through a subprocess service
boundary and is additive, not a fork.

Shutdown handoff 2026-06-18T22:45:26-06:00: relationship-map Slices 1-5,
semantic/physical layer fixes, video intent recenter, multi-repo Evidence
layout, and inert repo labels are captured. Latest code is pushed through
`f85f43c Label multi-repo evidence regions`; this shutdown documentation is
the only new repo change in the current closeout. Adam liked the new
multi-repo comparison direction and wants to play with it next; the repo labels
still need visual confirmation after a hard refresh or dev-server restart.
Begin next work with owner review and clear-map tuning, not a broad new slice,
unless Adam redirects.

Continuation closeout 2026-06-18T17:37:36-06:00: today's relationship-map,
scope-focus, working-state polish, semantic-overlap copy fix, file-importance
classifier, `Importance Criteria Table` tab, workspace knowledge lens, decision
overlay, and active plan updates are captured here for restart. Do not treat
any validation repo path used during smoke passes as a hard-coded product
target; the fixes are path-generic.

The first 30 build chunks are complete. The cockpit is a working local-first
decision surface with seven tabs (`Command`, `Ask`, `Map`, `Decisions`,
`Recommendations`, `Work Queue`, `Settings`) plus a floating AI assistant
overlay. The prior decision-tool polish path is integration complete and now
archived in `docs/current-build-pathway.md`.

The controlled hosted beta stabilization path in `docs/stabilization-plan.md`
is complete. Chunk 1 is task complete: graph schema handling now
normalizes `links` and legacy/internal `edges`, Settings counts both shapes
correctly, connector ingest emits canonical `links`, and backend contract tests
exist for this slice. Chunk 2 is task complete: Settings now calls
`POST /graphs/{name}/activate`, backend activation tests cover demo/uploaded
graphs plus useful failures, and launcher-compatible smoke validation passed.
Chunk 3 is task complete: Ask/Rebuild now route through a Graphify service
wrapper, structured Graphify errors and readiness status are exposed in backend
and Settings, and Docker backend build installs `graphifyy`. Chunk 4 is task
complete: frontend backend calls now use a shared API client, Settings can save,
test, and clear the browser-local API key, protected-mode 401/403 copy is
normalized, and authenticated plus unauthenticated smoke validation passed.
Chunk 5 is task complete: graph upload now rejects unsafe names, oversized
files, invalid JSON, missing nodes, malformed links, and invalid activation
candidates; uploaded graphs are normalized and written atomically before
activation. Chunk 6 is task complete: local JSON state writes now use
parent-safe atomic replacement through `backend/state_store.py`, clean empty
state tests cover the main persisted file surfaces, and launcher-compatible
smoke validation passed. Chunk 7 is task complete: Caddy now routes `/api/*`
before the frontend catch-all, strips `/api` before proxying to the backend, and
hosted smoke instructions cover `GET /api/health` plus `GET /`. Chunk 8 is task
complete: backend contract coverage now includes API-key middleware behavior
alongside the graph schema, Settings counts, upload, activation, Graphify
service, connector ingest, and clean-state tests; CI now runs backend pytest,
backend compile checks, frontend typecheck, and frontend production build. Chunk
9 is task complete: Supabase schema alignment now has additive migration
`db/migrations/002_recommendation_action_plans.sql`, backend health/settings
surface `storage.ready` and the required migration when schema columns cannot
be verified, and operator docs document migration order plus live-migration
approval boundaries. Chunk 10 is task complete: Command Center now shows a
compact Workspace Readiness panel backed by `GET /runtime/status`, including
Ready/Partial/Not Ready state, backend, Graphify, Ollama, active graph, auth,
storage, connector status, warnings, and next best action. Chunk 11 is task
complete: SharePoint and OneNote graph nodes now use a shared connector contract
with Graphify-compatible grouping fields, connector ingest normalizes cloud
nodes before merge, and connector relationships are canonical `links` that
appear in graph counts and Map full-graph output. Chunk 12 is task complete:
generated Graphify output is ignored and removed from version control, and
short restart/source-routing docs now help future agents avoid generated output
and stale context. Chunk 13 is task complete: backend configuration, app
construction, API-key middleware, storage readiness, and bounded route groups
for health/runtime, Ask, Decisions, cluster selection, connectors, and chat now
live outside `backend/main.py`; `backend.main:app` remains import-compatible and
the backend contract plus live health/runtime smoke checks passed.

Post-plan owner-reported Map toolbar clarity polish is also task complete:
physical/structural, semantic, overlap, trace, view, type, source, and fit
controls are now visible together, while the top mode presets carry clearer
sublabels and hover/focus explanations. The UI polish commit is
`c27d433 Expose map connection controls`.

Scope-focus follow-up is task complete: if the saved scope and active generated
graph do not match, the `Map` empty state now offers a direct `Generate Map`
recovery action and refreshes after the scoped rebuild completes. `Scope` also
distinguishes saved profiles from unsaved draft selections, so changing folders
shows a `Draft` state with a generic derived profile name until saved.
Working-state polish is task complete: page-level loading, rebuild, generation,
and analysis states now use a shared color-matched spinning nuclear/radiation
indicator across Map, Scope, Ask, Dashboard, Decisions, Recommendations, Work
Queue, and Settings.

The active plan is now `docs/relationship-map-plan.md`: make the Map tab a
decision-grade relationship map that shows physical structure, meaningful
connections, overlaps, gaps, and decisions without requiring a full broad graph
payload in the browser. Relationship-map Slices 1-5 are task complete: the
broad Overview now exposes weighted group-to-group physical relationships,
selected groups show connected groups plus gap metadata, Overlap can open a
summary-level server-side overlap panel without loading capped Evidence/full
graph payloads, gap triage now distinguishes root docs, filter-hidden links,
missing extraction, and true isolation with Map inspector actions, and the Map
now has explicit file importance metadata plus a Workspace Knowledge lens and a
static `Importance Criteria Table` tab between Scope and Map. Summary groups
and drilldown/full nodes now carry a compact decision overlay derived from
active decisions, relevant recommendations, and queued actions; selected node
details show that context in the Map inspector.
Owner-reported scope focus fix is also task complete: generated graphs now
carry included/excluded scope metadata, Map blocks stale generated graphs, and
single-repo scopes under the Evidence cap open directly in expanded Evidence
mode. Scope and Map behavior is path-generic; validation examples should not be
treated as fixed repo targets. Owner review then identified a more immediate
workspace-scale map quality issue: file inclusion needs a clearer importance
model so broad maps show decision-grade knowledge and cross-project contracts
instead of dependency type files, generated shims, fixtures, lockfiles, and
ordinary leaf evidence.
`Slice 4 - File Importance And Workspace Knowledge Lens` and `Slice 5 -
Decision Overlay` are now task complete. A 2026-06-18 video intent recenter is
captured in `docs/relationship-map-plan.md`: keep the cockpit Graphify-first,
use the map as a clean concept/community/source-evidence orientation surface,
and keep richer decision features available without turning the default view
into a file dump or dense similarity cloud. Multi-repo Evidence now uses a
comparison layout and inert repo labels instead of a flat grid. Next work
should start from owner review and targeted clear-map tuning unless Adam names
the next slice.

The completed scope/signal history is retained in
`docs/workspace-scope-and-signal-plan.md`: select a parent folder, represent
repos/projects as a tree, exclude noisy/generated/secret-like paths, hide
low-signal files by default, and keep the cockpit focused on token-saving build
intelligence.

Workspace scope Chunk 1 is task complete as of 2026-06-17T08:55:48-06:00:
`POST /workspace-scope/inspect` now returns a safe read-only tree summary,
applies default exclusion reasons for noisy/generated/state paths, reports
secret-like paths by presence only, and stops expansion at child repo/project
boundaries. Validation passed with backend tests, backend compile checks,
frontend typecheck, and frontend production build. Chunk 2 followed this
backend slice with the Settings Workspace Scope UI.

Workspace scope Chunk 2 is task complete as of 2026-06-17T09:08:55-06:00:
Settings now includes a Workspace Scope panel for parent-folder inspection,
bounded tree counts, include/exclude toggles, visible default-exclusion reasons,
and saved scope profiles through `GET/PUT /workspace-scope`. Validation passed
with governance preflight, backend tests, backend compile checks, frontend
typecheck/build, live workspace-scope API checks, and a Chromium Settings smoke.

Workspace scope Chunk 3 is task complete as of 2026-06-17T10:28:17-06:00:
`POST /graph/rebuild` now prefers a saved workspace scope profile, scans only
de-duplicated included roots, skips explicitly excluded roots, filters noisy,
generated, state, media, and secret-like graph nodes out of the activated
cockpit graph, annotates kept nodes with source-root/scope metadata, activates
the scoped merged graph, and clears stale semantic edges when graph identity
changes. With no saved scope, the existing local repo fallback remains in
place.

Workspace scope Chunk 4 is task complete as of 2026-06-17T10:42:36-06:00:
nodes now receive explicit signal tiers and reasons, default Map graph
responses hide low-signal evidence/hidden nodes, Map shows hidden/excluded
counts, and the operator can temporarily enable the Low Signal layer for
inspection. Post-Chunk 4 warning cleanup is task complete as of
2026-06-17T10:48:34-06:00: FastAPI lifespan, `httpx2` TestClient support, and
Vite manual chunks removed the previously noted backend deprecation and
frontend chunk-size warnings.

Workspace scope Chunk 5 is task complete as of 2026-06-17T11:04:05-06:00:
Map now opens in Overview mode by default, `/graph/summary` uses scoped
repo/project metadata for the parent-folder overview, selected repo/project
drilldown returns root/module summary groups instead of tiny file nodes, and
full graph clustering plus semantic overlap grouping use repo/project identity
for cross-repo readability.

Workspace scope Chunk 6 is task complete as of 2026-06-17T11:09:43-06:00:
Ask evidence is enriched and filtered against the active scoped/signal-aware
graph, chat and recommendation workflows receive compact scope context with
included groups plus hidden/excluded evidence, overlap analysis ignores
low-signal hidden nodes by default, and Recommendation cards show context and
rough token-saving evidence.

Workspace scope Chunk 7 is task complete as of 2026-06-17T11:35:38-06:00:
the video-readiness path was validated against `/home/adamgoodwin/code` with a
saved scoped profile, explicit noisy-folder exclusions, scoped rebuild,
workspace overview, repo/module drilldown, hidden low-signal counts, semantic
overlap groups, and a compact scoped Ask response. The smoke pass also fixed
duplicate raw Graphify node ids during scoped rebuild activation and made
single-repo semantic overlap group by meaningful module areas when community
metadata is absent.

Broad multi-root rebuild follow-up is task complete as of
2026-06-17T12:00:36-06:00: the profile `Adam Code Broad Smoke Scope` selected
`/home/adamgoodwin/code/agents`, `/home/adamgoodwin/code/Applications`,
`/home/adamgoodwin/code/Tools`, and `/home/adamgoodwin/code/Infrastructure`.
`POST /graph/rebuild` completed with four scanned roots after replacing the
brittle Graphify CLI merge step with cockpit-side normalized composition. The
activated graph had 40,835 raw nodes, 71,423 links, zero duplicate node ids,
zero missing link targets, 132 repaired cross-root duplicate ids, and a default
summary grouped into `agents`, `Applications`, `Tools`, and `Infrastructure`.

Browser-freeze follow-up is task complete as of 2026-06-17T12:22:03-06:00:
broad workspace testing showed that Evidence/full graph mode could still request
22,613 visible nodes and slow Zen before the operator could reach Workspace
Scope. `/graph/full` now rejects oversized default payloads with
`413 GRAPH_FULL_TOO_LARGE`, Map disables Evidence, Low Signal, and Overlap modes
when the visible graph is above the browser cap, and Settings shows Workspace
Scope as the first settings card.

Workspace scope Chunk 8 is task complete as of 2026-06-17T14:54:17-06:00:
Map now gates missing/unsafe-broad scopes behind a reusable Generate Workspace
Map picker instead of rendering the broad graph canvas. The same picker is used
from Settings, starts new inspections with no folders selected, offers useful
root suggestions plus exact path fallback, disables default-ignored/noisy rows,
and runs save + scoped rebuild behind a single Generate Map action. Backend
profile validation rejects empty selections, non-directory included paths, and
default-ignored included paths; lockfiles are treated as default low-signal
noise. Validation passed with backend tests, backend compile, frontend
typecheck/build, Graphify update, demo smoke, headless broad-graph Map gate
smoke, and a controlled scoped generate smoke that restored the prior broad
profile/active graph afterward.

Owner UX correction for Chunk 8 is task complete as of
2026-06-17T15:17:51-06:00: the Map startup gate now presents the directory
checkbox tree as the primary visible control, converts root suggestions from a
native dropdown into quick root buttons, keeps an always-present folder panel
while inspection loads, and de-duplicates development-mode inspection requests.
Headless browser verification confirmed the Map startup tree rendered with 60
checkboxes, 47 enabled selectable folder rows, and no startup root-select
dropdown.

Post-restart recovery audit on 2026-06-17T16:27:19-06:00 found the worktree
clean at `aa62169 Open scoped overview after map generation`. That final
follow-up lets the broad workspace Overview open with a browser-cap warning
instead of forcing the picker immediately; Evidence/full graph remains capped.
Local state points at `graphify-out/merged-graph.json`, which parsed cleanly
with 41,391 nodes, 72,717 links, zero duplicate node ids, and zero missing link
targets. Validation passed with backend tests, backend compile, frontend
typecheck/build, state JSON parsing, and `git diff --check`.

Workspace Scope dedicated-tab polish is task complete as of
2026-06-17T16:44:43-06:00: drive/folder/workspace selection and Generate Map now
live in their own top-level `Scope` tab. Generate Map returns to the Map tab
after the scoped rebuild completes. Map no longer embeds the scope picker; when
scope is missing it shows a compact action to open Workspace Scope. Settings
now links to Workspace Scope instead of duplicating the picker. Validation
passed with frontend typecheck/build, headless Chromium tab-flow smoke,
`git diff --check`, and `graphify update . --no-cluster`.

Relationship-map broad-root correction is task complete as of
2026-06-17T17:05:29-06:00: `/graph/summary` now detects when saved scope
metadata would collapse a broad selected folder such as `/home/adamgoodwin/code`
into one `code` node, then derives Overview groups from relative source paths
instead. The current active graph now opens as multiple decision groups
including `agents`, `Applications`, and `Tools`, with root-level files grouped
as `Workspace Docs`. Summary nodes also report visible physical connection
counts and mark zero-link groups as gaps so the map can show connected areas
and disconnected areas in the same view. Validation passed with focused graph
service tests, full backend tests, frontend typecheck/build, active graph
summary inspection, `git diff --check`, and `graphify update . --no-cluster`.

Documentation routing cleanup is task complete as of
2026-06-17T17:12:02-06:00: `AGENTS.md`, `README.md`,
`docs/current-build-pathway.md`, `docs/handover.md`, `docs/FILE_SUMMARIES.md`,
`docs/KNOWN_ISSUES.md`, `docs/vision.md`, and
`docs/standards/context-hygiene-standard.md` now point active continuation to
`docs/workspace-scope-and-signal-plan.md`. `docs/stabilization-plan.md` remains
completed stabilization evidence, and `docs/current-build-pathway.md` plus
`docs/handover.md` remain historical 0-to-1 build evidence unless Adam
explicitly reopens them.

Relationship-map plan split is task complete as of
2026-06-17T17:25:00-06:00: the active next-work document is now the concise
`docs/relationship-map-plan.md`. The long
`docs/workspace-scope-and-signal-plan.md` is marked completed history and should
only be opened for scope/signal evidence or regressions.

Continue with `docs/relationship-map-plan.md`, Slice 5 decision overlay unless
Adam redirects.

Open owner-review flags before future implementation:
- Project is classified as `AI agent with tools` while selected governance is
  low / level 1; do not auto-change governance, but use stronger review for
  hosted beta auth, uploads, deployment, Graphify execution, and Supabase mode.
- Graphify runtime decision is resolved for this pass: Docker/runtime installs
  `graphifyy`, while missing custom runtimes report `GRAPHIFY_MISSING` without
  breaking the rest of the cockpit UI.
- Do not run live Supabase migrations without explicit owner approval; Chunk 9
  added the migration file only.
- API-key browser storage is implemented with localStorage for this beta pass;
  select a stronger hosted auth/session pattern before broader or untrusted
  production exposure.

## Where Things Live

| What | Where |
|------|-------|
| Active relationship map plan | `docs/relationship-map-plan.md` |
| Completed workspace scope + signal history | `docs/workspace-scope-and-signal-plan.md` |
| Completed stabilization plan | `docs/stabilization-plan.md` |
| Archived build history | `docs/current-build-pathway.md` — superseded for startup |
| Architecture + ADRs | `docs/architecture.md` |
| Roadmap and non-goals | `docs/roadmap.md` |
| Full 0→1 build record | `docs/handover.md` |
| Operator manual | `docs/manual.md` |
| Operational runbook | `docs/runbook.md` |
| Context routing map | `docs/context-map.md` |

## To Resume

1. `git status --short` — preserve unrelated work.
2. Confirm this file still names the active plan.
3. Read `docs/relationship-map-plan.md`.
4. Start with Slice 5 decision overlay unless Adam redirects.
5. Load only the files named in that chunk.
6. Use `docs/context-map.md` if routing is still unclear.

## Work Patterns

**Ordinary scoped work:**
1. `git status --short`
2. Read repo-local agent instructions (`AGENTS.md`)
3. Use `docs/context-map.md` when context routing is unclear
4. Inspect only the specific files or errors needed
5. Run targeted validation after the change

**Material or risk-triggering changes:**
1. `bash scripts/governance-preflight.sh`
2. `docs/standards/README.md` → `docs/policy/durable-development-engineering-policy.md`
3. `docs/standards/ship-ready-engineering-standard.md` before declaring complete
4. `date -Iseconds` — timestamp the work
5. Work in the smallest complete chunk that can be reviewed safely

Risk-triggering work: production, deployment, auth, payments, secrets, database
migrations, external side effects, infrastructure, destructive actions, autonomous
tool use, governance changes, release readiness.

## Agent Handoff

Update this file only when the top-level plan or pause state changes. Put
relationship-map progress in `docs/relationship-map-plan.md`. Treat
`docs/workspace-scope-and-signal-plan.md`, `docs/stabilization-plan.md`, and
`docs/current-build-pathway.md` as historical records unless Adam explicitly
asks to reopen them.
