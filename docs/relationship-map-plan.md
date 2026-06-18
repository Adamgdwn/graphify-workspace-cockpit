# Relationship Map Plan

Last Updated: 2026-06-18T16:56:04-06:00
Status: boxed for context clear - scope/relationship fixes complete; next active work is Slice 4 file-importance and workspace knowledge lens before Slice 5 decision overlay
Owner: Adam Goodwin

## Purpose

This is the active continuation plan. Keep it short enough to read at restart.

Graphify Workspace Cockpit should provide a decision-grade relationship map,
not a literal file browser and not a single folder summary dot. The map should
help Adam see:

- physical workspace structure: folders, repos, projects, modules, and files
  where useful
- connections: which areas are linked by imports, references, docs, shared
  concepts, and workflow relationships
- overlaps: where multiple places appear to solve or describe the same thing
- gaps: important folders or projects with weak or missing relationships
- decisions: what has already been classified, accepted, deferred, or queued

The map exists to save tokens and make better build decisions. Files are
evidence and drilldown material unless they are high-signal enough to be visible
as first-class nodes.

## Current State

Closeout note 2026-06-18T16:56:04-06:00: this plan is the active continuation
plan after `START_HERE.md`. The scope-focus examples used for smoke testing
are not product fixtures. Adam's latest owner direction is that workspace-scale
maps need an explicit file-importance model so dependency/type/generated noise
does not crowd out the real decision and knowledge surface.

Completed foundations:

- `Scope` is now its own top-level tab for drive/folder/workspace selection.
- `Generate Map` saves scope, rebuilds, activates the scoped graph, and opens
  the `Map` tab.
- `Map` is focused on exploration; it no longer embeds the scope picker.
- Broad graphs are protected by a browser-safe cap for Evidence/full graph
  mode.
- `Map` now verifies that the active generated graph matches the saved
  workspace scope before rendering. If scope changed without regeneration, it
  offers a direct `Generate Map` recovery action instead of showing a stale
  broad map.
- Single-included-path scopes under the Evidence cap open directly into the
  expanded Evidence map. The behavior is path-generic; no selected repo name is
  hard-coded into the scope or map flow.
- `/graph/summary` no longer collapses a broad `/home/adamgoodwin/code` scope
  into one giant `code` node. It now derives top-level groups from relative
  source paths when scope metadata is too broad.
- Summary nodes expose physical connection counts and mark zero-link visible
  groups as gaps.
- The current active graph opens as groups such as `agents`, `Applications`,
  `Tools`, and `Workspace Docs`.
- Working states across the cockpit now use a shared, color-matched spinning
  nuclear/radiation indicator so background processing is visually obvious.
- Overlap copy now distinguishes "Semantic overlay is off" from "semantic
  edges exist, but no cross-repo overlap edges are visible in the current
  scope/source filters."

Historical evidence lives in `docs/workspace-scope-and-signal-plan.md`.
Completed stabilization evidence lives in `docs/stabilization-plan.md`.
Original 0-to-1 build history lives in `docs/current-build-pathway.md` and
`docs/handover.md`.

## Product Intent

The operator should be able to select a workspace, generate a map, and then
answer:

1. What are the major areas in this workspace?
2. Which areas are physically or semantically connected?
3. Which areas overlap enough to review, merge, document, archive, or keep
   separate?
4. Which important areas are disconnected or under-explained?
5. What decisions have already been made about an area?
6. What should I inspect next without dumping the entire graph into a model?

## Immediate Problem

The map is only partway to that product intent.

The latest fixes prevent stale scope maps, make broad Overlap usable without
loading full Evidence mode, and make gap triage actionable.

Owner review found the next practical blocker: at large workspace scale, the
map can still feel like a raw technical artifact dump. File inclusion is
folder-first and signal-tiered, but it does not yet expose a clear enough
importance model for deciding which files matter across major projects.
Dependency type files, generated type shims, fixtures, lockfiles, ordinary leaf
source, and other low-signal evidence need better separation from decision
anchors and cross-project contracts.

Decision overlay remains important, but it will be more useful after the map
can reliably show workspace knowledge instead of every runnable implementation
detail.

## Next Implementation Slices

### Scope Focus Fix - Single Repo Generation

Status: completed 2026-06-18T07:49:36-06:00.

Owner-reported issue: after selecting one repo in `Scope`, `Map` still showed
the last generated broad workspace map. Expected behavior is a fully expanded
repo map minus exclusions.

Delivered behavior:

- Generated scoped graphs now store `included_paths` and `excluded_paths` in
  graph metadata, and `/graph/summary` returns that active scope metadata.
- `Map` compares the saved scope profile with active graph metadata before
  rendering. Stale generated graphs route back to `Scope` instead of drawing a
  misleading broad map.
- When the saved scope has exactly one included path and the visible graph is
  below the Evidence cap, `Map` opens in expanded Evidence mode.
- Follow-up fix: when Adam selects or saves a scope and lands on `Map` before
  the active graph metadata matches it, the empty state can start the scoped
  rebuild directly and refresh the map after completion.
- Follow-up fix: `Scope` now separates the saved profile from the current draft
  checkbox selection. Changing selected folders shows a `Draft` state and
  derives a neutral profile name from the selected path unless Adam manually
  edits the name.
- Visual follow-up: Map, Scope, Ask, Dashboard, Decisions, Recommendations,
  Work Queue, and Settings now share the same working indicator for page-level
  loading, rebuild, generation, and analysis states.

Validation:

- `backend/.venv/bin/python -m pytest tests/test_graphify_service.py tests/test_workspace_scope.py -q`:
  34 passed
- `backend/.venv/bin/python -m pytest tests -q`: 74 passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run typecheck`: passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run build`: passed
- `git diff --check`: passed
- `graphify update . --no-cluster`: rebuilt 1,528 nodes and 53,427 edges
- live scoped rebuild for a one-repo selection: active metadata matched the
  saved one-repo scope and rendered under the Evidence cap
- final closeout validation after the shared working indicator:
  frontend typecheck passed, frontend production build passed,
  `git diff --check` passed, and `graphify update . --no-cluster` rebuilt
  1,538 nodes and 64,197 edges

### Slice 1 - Broad Summary Relationship Layer

Status: completed 2026-06-17T17:25:02-06:00.

Goal: make the default Overview visibly relational at broad workspace scale.

Delivered behavior:

- Overview edges should represent aggregated physical relationships between
  visible groups.
- Edge weight should reflect the number or strength of visible underlying
  physical links.
- Gap groups should be visibly distinct and explain why they are considered
  gaps.
- Selecting a group should show top connected groups, gap status, and useful
  drilldown actions.

Implementation notes:

- `backend/main.py` now aggregates broad summary relationships as undirected
  visible group-to-group physical edges, exposes per-node `connections`,
  `connection_count`, `connection_weight`, `is_gap`, and `gap_reason`.
- `frontend/src/tabs/Map.tsx` shows gap badges and a selected-node Connected
  Groups list with relationship weights and click-to-focus navigation.
- `frontend/src/styles.css` styles gap states and relationship rows in the map
  inspector.
- `tests/test_graphify_service.py` covers broad path-derived grouping,
  undirected relationship weights, connection lists, and gap metadata.

Validation:

- `backend/.venv/bin/python -m pytest tests/test_graphify_service.py -q`:
  21 passed
- `backend/.venv/bin/python -m pytest tests -q`: 72 passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run typecheck`: passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run build`: passed
- active graph summary inspection at `min_weight=1`: 23,192 visible nodes,
  9 groups, 5 relationship edges; `Applications` has 4 connected groups and
  relationship weight 83; `Workspace Docs` is marked as a gap
- `git diff --check`: passed
- `graphify update . --no-cluster`: rebuilt 1,510 nodes and 45,537 edges

### Slice 2 - Broad Overlap Without Full Evidence Mode

Status: completed 2026-06-17T17:33:47-06:00.

Goal: make overlap useful on broad maps without requiring a 5,000-node full
graph payload.

Delivered behavior:

- Add or reuse a server-side overlap summary that works on visible summary
  groups.
- Overlap mode should show pair cards or edges for likely duplicated,
  reference, or related areas at the group/module level.
- The UI should not ask the browser to render the full evidence graph just to
  start overlap review.

Implementation notes:

- `backend/main.py` now exposes `/graph/overlap-summary`, which reads stored
  semantic edges server-side, applies the active source/cluster and signal
  filters, and groups overlap pairs using the same visible summary grouping as
  `/graph/summary`.
- `frontend/src/tabs/Map.tsx` now opens Overlap in summary mode when Evidence
  view is capped, fetches summary-level overlap pairs, and keeps the existing
  triage/recommendation workflow available for those pairs.
- Summary overlap cards can highlight the two visible Overview groups without
  requiring raw full-graph nodes or semantic edge rendering.
- `frontend/src/styles.css` labels summary-level overlap panels.
- `tests/test_graphify_service.py` covers broad summary overlap grouping and
  confirms excluded low-signal semantic edges are ignored.

Validation:

- `backend/.venv/bin/python -m pytest tests/test_graphify_service.py -q`:
  22 passed
- `backend/.venv/bin/python -m pytest tests -q`: 73 passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run typecheck`: passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run build`: passed
- active graph overlap-summary inspection: endpoint returned cleanly with
  0 stored summary overlap pairs because the current semantic-edge store is
  empty
- `git diff --check`: passed
- `graphify update . --no-cluster`: rebuilt 1,516 nodes and 48,144 edges

### Slice 3 - Gap Triage

Status: completed 2026-06-18T07:37:04-06:00.

Goal: make gaps actionable instead of merely orange badges.

Delivered behavior:

- Gap details should distinguish "truly isolated", "hidden by low-signal
  filters", "missing semantic extraction", and "root-level docs only" when the
  data supports it.
- Gap panels should offer natural next actions such as drill in, ask about this
  area, mark as monitor/archive, or generate a recommendation.

Implementation notes:

- `backend/main.py` now classifies summary gap nodes as `root_level_docs_only`,
  `hidden_by_low_signal_filters`, `missing_semantic_extraction`, or
  `truly_isolated`, with gap detail, evidence, and action hints attached to
  each summary node.
- `frontend/src/tabs/Map.tsx` now renders a Gap Triage section in the selected
  summary-node inspector, can open low-signal Evidence mode for filter-hidden
  gaps, copies a targeted Ask prompt, and creates or updates Monitor/Archive
  decisions through the existing decisions API.
- `frontend/src/styles.css` adds compact inspector styling for the triage
  panel and action grid.
- `tests/test_graphify_service.py` covers all four backend gap classifications.

Validation:

- `backend/.venv/bin/python -m pytest tests/test_graphify_service.py -q`:
  23 passed
- `backend/.venv/bin/python -m pytest tests -q`: 74 passed
- `backend/.venv/bin/python -m compileall backend`: passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run typecheck`: passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run build`: passed
- `git diff --check`: passed

### Slice 4 - File Importance And Workspace Knowledge Lens

Status: planned.

Goal: make workspace-scale maps show decision-grade knowledge instead of noisy
raw file evidence.

Expected behavior:

- Add or formalize an importance model such as `anchor`, `interface`,
  `important`, `evidence`, `hidden`, and `excluded`.
- Default broad workspace maps should prioritize source-of-truth docs,
  architecture/governance docs, ADRs, runbooks, API routes/contracts, schemas,
  migrations, prompts, package manifests, deployment/config boundaries, auth
  and storage boundaries, public interfaces, and high-signal tests.
- Default broad workspace maps should demote or hide dependency declarations,
  dependency type packages, most generated or ambient `*.d.ts` files, lockfiles,
  fixtures, mocks, snapshots, test data, build output, caches, and ordinary leaf
  implementation files unless graph degree or path role makes them important.
- Single-repo Evidence can still expose richer implementation detail; broad
  workspace mode should act more like a knowledge and decision map.
- Node details should explain why a file is visible or hidden, for example
  "source-of-truth doc", "public API boundary", "generated type shim",
  "dependency type declaration", "fixture evidence", or "connected
  implementation node".
- Add a `Workspace Knowledge` or equivalent preset/lens that hides dependency,
  generated, fixture, and ordinary leaf evidence more aggressively than
  Evidence mode.

Implementation notes:

- Start from `backend/workspace_scope.py` signal tiering and
  `frontend/src/tabs/Map.tsx` controls.
- Treat known generated type shims and dependency type declaration paths as
  low-signal by default.
- Decide whether arbitrary `*.d.ts` files should be `hidden` by default or
  `interface` when they define workspace-owned public contracts.
- Preserve secrets, generated output, and dependency folders as excluded where
  the source path can be resolved under an excluded path.
- Add tests that cover dependency type declarations, workspace-owned contract
  type definitions, generated shims, and broad-map visibility counts.

### Slice 5 - Decision Overlay

Status: planned after file-importance/workspace-knowledge slice.

Goal: make decisions visible on the relationship map.

Expected behavior:

- Existing decision classifications should appear on summary groups and
  drilldown nodes.
- Selected node details should show relevant decisions, recommendations, and
  queued actions.
- The map should help decide what to invest in, merge, document, archive, or
  leave alone.

## Non-Goals

- Do not render every file by default.
- Do not remove the browser cap for broad Evidence/full graph mode.
- Do not index the home directory by default.
- Do not expose secret values.
- Do not delete workspace files.
- Do not run live Supabase migrations.
- Do not broaden hosted auth or deployment scope unless Adam explicitly asks.

## Startup Instructions

For the next coding session:

1. `git status --short`
2. Read `AGENTS.md`.
3. Read `START_HERE.md` only as the top-level router.
4. Read this file: `docs/relationship-map-plan.md`.
5. Start with File Importance And Workspace Knowledge Lens unless Adam
   redirects.

Avoid loading the long historical plans unless investigating a regression:

- `docs/workspace-scope-and-signal-plan.md`
- `docs/stabilization-plan.md`
- `docs/current-build-pathway.md`
- `docs/handover.md`
