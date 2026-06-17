# Workspace Scope and Signal Plan

Last Updated: 2026-06-17T11:09:43-06:00
Status: active plan - Chunk 6 task complete; Chunk 7 next
Owner: Adam Goodwin

## Purpose

Graphify Workspace Cockpit is not meant to be a literal file browser. It is a
token-saving build intelligence tool: it should help identify overlaps, gaps,
important build insights, and useful future-build context across Adam's active
workspaces.

The current failure mode is that "workspace graph" can be interpreted as
"every file as a visible node." That creates visual noise, wastes context, and
buries the actual product value. The next build path fixes the scope model
before adding more analysis.

## Current Evidence

Observed on 2026-06-16:

- The active local graph is
  `/home/adamgoodwin/code/agents/graphify-workspace-cockpit/graphify-out/graph.json`.
- That graph contains only the cockpit repo: about 1,314 nodes and 39,199 links.
- `workspace/state/scan-dirs.json` is missing, so the backend rebuild path falls
  back to scanning only the current repo with `graphify update . --no-cluster`.
- A broader workspace graph exists at
  `/home/adamgoodwin/code/Tools/graphify/workspace/out/graph.json`, but the
  cockpit is not currently using it as an active scoped graph.
- The existing Settings "Local Repositories" control is a flat manual path list.
  It is not a folder tree selector and it does not provide include/exclude
  defaults for generated, secret-like, dependency, cache, or low-signal files.
- Chunk 1 is task complete as of 2026-06-17T08:55:48-06:00:
  `POST /workspace-scope/inspect` returns a read-only tree summary for a parent
  folder, applies default exclusions with visible reasons, reports secret-like
  paths by presence only, detects repo/project boundaries, and keeps child repo
  expansion bounded. Backend tests cover `.git`, `node_modules`,
  `graphify-out`, `workspace/state`, and secret-like paths without returning
  file contents.
- Chunk 2 is task complete as of 2026-06-17T09:08:55-06:00:
  Settings now has a Workspace Scope panel that loads any saved profile,
  accepts a parent folder path, calls `POST /workspace-scope/inspect`, displays
  a bounded tree with include/exclude toggles, shows count/default-exclusion
  evidence, and saves the profile through `PUT /workspace-scope` so it survives
  refresh.
- Chunk 3 is task complete as of 2026-06-17T10:28:17-06:00:
  `POST /graph/rebuild` now prefers a saved workspace scope profile when one
  exists, scans only de-duplicated included roots, skips explicitly excluded
  roots, filters generated/dependency/cache/state/secret-like graph nodes out
  of the produced scoped graph, annotates kept nodes with source-root and scope
  metadata, activates `graphify-out/merged-graph.json`, and clears stale
  semantic edges when the active graph identity changes. With no saved scope,
  the existing local repo fallback remains in place. This chunk guarantees
  filtered cockpit graph output; adding a Graphify ignore-file handshake for
  stricter pre-index pruning remains a later hardening improvement.
- Chunk 4 is task complete as of 2026-06-17T10:42:36-06:00:
  nodes now receive explicit `signal_tier` and `signal_reason` values, scoped
  rebuild output persists those values, `/graph/summary` and default
  `/graph/full` responses hide evidence/hidden low-signal nodes, API responses
  include signal counts plus hidden/excluded-node counts, and the Map toolbar
  has an opt-in Low Signal layer that temporarily reloads evidence/hidden
  nodes.
- Post-Chunk 4 warning cleanup is task complete as of
  2026-06-17T10:48:34-06:00: FastAPI startup now uses lifespan instead of
  deprecated `on_event`, backend test dependencies include `httpx2` for the
  current Starlette TestClient path, and Vite build output is split into
  bounded React/vendor/Cytoscape chunks. Validation passed with backend tests
  using `-W error` and frontend production build without the prior chunk-size
  warning.
- Chunk 5 is task complete as of 2026-06-17T11:04:05-06:00:
  Map summary mode is now the default first experience, top-level summary
  groups prefer workspace scope repo/project metadata, drilldown groups a
  selected repo/project into root/module summaries, full graph clustering and
  overlap reporting use repo/project identity for cross-repo readability, and
  the Map labels the summary layer as Overview with selected repo/module badges.
- Chunk 6 is task complete as of 2026-06-17T11:09:43-06:00:
  Ask evidence is enriched and filtered against the active scoped/signal-aware
  graph, chat and recommendation prompts receive a compact workspace scope
  context packet, overlap reporting ignores low-signal hidden nodes, and
  recommendation cards surface included groups, hidden/excluded context, and
  rough token-saving evidence.

## Target Mental Model

The user selects a parent folder, usually something like:

```text
/home/adamgoodwin/code
```

The cockpit discovers child folders and repositories as a tree:

```text
code/
  agents/
    graphify-workspace-cockpit/
    New Build Agent/
  Applications/
    Clean_pdf_build/
    Timeshare-Connect/
  Tools/
    graphify/
  01 Work Tracking/
  Infrastructure/
```

The default map is a workspace/repo/project map, not a file map. Files are
evidence and drilldown material unless they are high-signal enough to surface.

## Product Principles

1. Scope before scan.
   The user must be able to choose what part of the folder tree is in scope
   before a rebuild creates a large graph.

2. Repos and project folders are first-class.
   The overview map should show repos, project areas, and important modules.
   Individual files should appear mainly in drilldown, evidence panels, Ask
   answers, and overlap packets.

3. Exclude before indexing when safe.
   Generated output, dependency directories, caches, build artifacts, local
   state, and secret-like files should be excluded before Graphify runs.

4. Hide low-signal nodes by default.
   Some files may be useful evidence but do not deserve visible default nodes.
   The map should hide them by default while keeping counts and a way to inspect
   them when needed.

5. Explain the filter.
   Operators should see why a folder or file class was excluded, hidden, or
   shown. No mystery pruning.

6. Preserve reversibility.
   Exclusions and signal filters are configuration, not destructive mutations.
   The cockpit must not delete workspace files.

7. Protect tokens.
   Ask, chat, recommendations, and overlap triage should consume compact scoped
   context packets, not raw graph dumps or all visible files.

## Scope Builder Requirements

### Parent Folder Selection

Add a "Workspace Scope" control under Settings.

Minimum first version:

- Text input for parent folder path.
- "Inspect Folder" action that returns a safe tree summary.
- Display child folders/repos with include/exclude toggles.
- Save scope profile to local state.
- Rebuild graph from the saved profile.

Later version:

- Native folder picker where browser/launcher capabilities allow it.
- Named profiles such as "All Code", "Agents Only", "Applications Only",
  "Tools Only", and "Video Demo".

### Tree Granularity

Default tree depth should stop at repo/project boundaries.

Recommended hierarchy:

1. Parent root.
2. Top-level grouping folders.
3. Repos/projects detected by `.git`, package manifests, Python project files,
   README/project docs, or Graphify-compatible markers.
4. Optional second-level project modules only after expansion.

Do not render every file in the tree by default.

### Include / Exclude States

Each tree item should have a tri-state:

- `included`
- `excluded`
- `partial`

The tree should also show:

- estimated file count
- estimated included count
- detected repo/project type
- warning badges for large/generated/noisy areas
- reason for default exclusion

### Default Exclusions

Exclude these before graph generation:

- dependency folders: `node_modules/`, `.venv/`, `venv/`, `.pnpm-store/`
- build outputs: `dist/`, `build/`, `.next/`, `out/`, `coverage/`
- caches: `.cache/`, `.pytest_cache/`, `__pycache__/`, `.ruff_cache/`
- VCS internals: `.git/`
- generated Graphify output: `graphify-out/`, `graphify-out/cache/`
- cockpit local state: `workspace/state/`
- binary/media bulk unless explicitly included
- secret-like and environment files: `.env*`, `*.pem`, `*.key`, files or paths
  containing `secret`, `credential`, `password`, `private-key`, `api-key`,
  `api_key`, `access_token`, `refresh_token`, or `token`

Do not print, summarize, index, or commit secret values. If a secret-like file
is detected, only report presence and exclusion reason.

### Low-Signal Defaults

Hide or demote these from the default map, even if they remain in the evidence
graph:

- generated type files such as `_vercel-types.ts`, `next-env.d.ts`,
  `vite-env.d.ts`
- lockfiles unless they are directly relevant to dependency analysis
- empty or tiny `__init__.py` files
- barrel files with only re-exports
- one-line config shims
- fixture files below the signal threshold
- duplicated generated API wrappers
- files with very low degree and no semantic uniqueness

Important caveat: size alone must not decide importance. A small file can be
high-signal if it is a central config, auth boundary, entrypoint, migration,
policy, prompt, contract, or source-of-truth document.

## Signal Model

Each node should receive a `signal_tier`:

- `overview`: visible in default workspace/repo map
- `important`: visible in focused repo/module maps
- `evidence`: hidden by default but usable in Ask, citations, drilldown, and
  recommendation packets
- `hidden`: excluded from visual map unless the user enables low-signal nodes
- `excluded`: not scanned or not loaded

Suggested scoring inputs:

- graph degree and weighted degree
- cross-repo or cross-module edge count
- semantic uniqueness or overlap strength
- file role: entrypoint, route, model, schema, migration, policy, prompt,
  README, architecture doc, test, generated file, fixture, cache, dependency
- source path class
- content size and meaningful identifier density
- recent owner decisions or recommendation references

The initial version can be heuristic. The important part is to make it explicit,
inspectable, and easy to tune.

## Graph Pipeline

### Step 1: Discover

Backend endpoint:

```text
POST /workspace-scope/inspect
```

Input:

```json
{ "root": "/home/adamgoodwin/code", "max_depth": 3 }
```

Output:

- root metadata
- child tree
- repo/project detection
- default include/exclude suggestion
- exclusion reasons
- estimated file counts

This endpoint is read-only.

### Step 2: Save Scope

Backend endpoint:

```text
PUT /workspace-scope
GET /workspace-scope
```

Persist to:

```text
workspace/state/workspace-scope.json
```

Shape:

```json
{
  "root": "/home/adamgoodwin/code",
  "profile_name": "All Code",
  "included_paths": [
    "/home/adamgoodwin/code/agents",
    "/home/adamgoodwin/code/Applications",
    "/home/adamgoodwin/code/Tools"
  ],
  "excluded_paths": [
    "/home/adamgoodwin/code/.codex",
    "/home/adamgoodwin/code/.claude"
  ],
  "exclude_patterns": [
    "node_modules/",
    ".git/",
    "graphify-out/",
    "workspace/state/",
    ".env*"
  ],
  "signal": {
    "hide_low_signal": true,
    "show_generated": false,
    "min_visible_signal": "important"
  }
}
```

### Step 3: Rebuild

Backend endpoint can reuse:

```text
POST /graph/rebuild
```

But rebuild should prefer the saved workspace scope profile when present.

Recommended behavior:

1. Generate a scoped scan manifest from `workspace-scope.json`.
2. Run Graphify on included project roots or an approved parent root with
   generated ignore rules.
3. Merge per-root graphs into a single active graph.
4. Add cockpit metadata:
   - source root
   - source root name
   - repo/project name
   - scope profile
   - signal tier
   - exclusion/hide reason where applicable
5. Activate the generated scoped graph.
6. Clear stale semantic edges if the graph identity changed.

### Step 4: Render

Map default view should use aggregated graph levels:

1. Workspace overview: repos/projects as nodes.
2. Repo/project view: modules and important files.
3. Evidence view: selected file/node details.
4. Low-signal view: opt-in, temporary layer.

Do not show every evidence node in the default map.

## Token-Saving Behavior

The scope system should reduce token use in three ways:

1. Smaller active graph.
   Exclude irrelevant roots and generated/dependency/state folders before graph
   generation.

2. Smaller visible graph.
   Hide low-signal nodes by default and aggregate repo/module relationships.

3. Smaller AI context.
   Ask, chat, recommendations, and overlap triage should receive scoped packets:
   active scope, top entities, strongest edges, relevant evidence nodes, and
   explicit omissions.

The cockpit should always answer "why this context?" and "what was left out?"
well enough for the operator to trust the answer.

## Implementation Chunks

### Chunk 1: Scope Data Model and Read-Only Inspect Endpoint

Goal: Add backend support for inspecting a parent folder safely without
rebuilding the graph.

Files likely to change:

- `backend/config.py`
- `backend/state_store.py`
- `backend/main.py` or a new `backend/routes/workspace_scope.py`
- `backend/workspace_scope.py`
- tests under `tests/`

Acceptance:

- Inspecting `/home/adamgoodwin/code` returns a tree summary, not file contents.
- Default exclusions are applied and explained.
- Secret-like paths are presence-only and excluded.
- Tests cover `.git`, `node_modules`, `graphify-out`, `workspace/state`, and
  secret-like paths.

Status: task complete on 2026-06-17T08:55:48-06:00.

Evidence:

- Added `backend/workspace_scope.py` for safe path classification, bounded tree
  inspection, repo/project detection, default exclusion reasons, and
  presence-only secret-like path reporting.
- Added `backend/routes/workspace_scope.py` and wired
  `POST /workspace-scope/inspect` into the FastAPI app without expanding
  `backend/main.py` route logic.
- Added `tests/test_workspace_scope.py` for default exclusions, child repo
  boundary behavior, endpoint response shape, missing-root validation, and
  no secret content leakage.
- Smoke inspected `/home/adamgoodwin/code` with `max_depth=3`; the endpoint
  returned a bounded tree summary and reported secret-like env paths by name
  only.
- Validation passed: governance preflight, `backend/.venv/bin/python -m pytest
  tests`, targeted backend compileall, `npm run typecheck`, and `npm run build`
  through local nvm. Existing FastAPI/Starlette deprecation warnings and the
  existing Vite chunk-size warning remain non-blocking.

### Chunk 2: Settings Workspace Scope UI

Goal: Replace flat manual scan directories with an understandable parent-folder
tree workflow.

Files likely to change:

- `frontend/src/tabs/Settings.tsx`
- `frontend/src/styles.css`
- frontend API types if extracted

Acceptance:

- User can enter a parent folder and inspect its child tree.
- User can include/exclude top-level groups and repos.
- UI clearly shows excluded/noisy/default-hidden categories.
- Saved scope survives refresh.

Status: task complete on 2026-06-17T09:08:55-06:00.

Evidence:

- Added `GET /workspace-scope` and `PUT /workspace-scope` to persist a
  normalized scope profile in `workspace/state/workspace-scope.json` through the
  existing atomic JSON state writer.
- Added scope profile validation that keeps included/excluded paths inside the
  selected root, normalizes root/path values, carries default exclude patterns,
  and preserves low-signal defaults for the later signal model.
- Updated Settings with a Workspace Scope panel above Rebuild Graph: saved
  profile summary, parent-folder input, Inspect Folder action, profile name
  field, bounded tree rows, include/exclude checkboxes, default exclusion
  reasons, estimated counts, default exclude pattern display, and Save Scope.
- Kept the existing Local Repositories list and current rebuild behavior
  visible for compatibility; scoped rebuild remains Chunk 3.
- Validation passed: governance preflight, `backend/.venv/bin/python -m pytest
  tests/test_workspace_scope.py`, full `backend/.venv/bin/python -m pytest
  tests`, targeted backend compileall, `npm --prefix frontend run typecheck`,
  `npm --prefix frontend run build`, live `GET /workspace-scope`, live
  `POST /workspace-scope/inspect`, and a Chromium Settings smoke that rendered
  the Workspace Scope panel, inspected the cockpit repo, and confirmed counts
  plus default excludes appeared. Existing FastAPI/Starlette deprecation
  warnings and the existing Vite chunk-size warning remain non-blocking.

### Chunk 3: Scoped Rebuild Engine

Goal: Make rebuild use the saved workspace scope instead of defaulting to the
cockpit repo.

Files likely to change:

- `backend/services/graphify_service.py`
- `backend/main.py` rebuild range or a route module
- `backend/workspace_scope.py`
- `tests/`

Acceptance:

- With no saved scope, current demo/local behavior remains safe.
- With saved scope, rebuild scans only included roots.
- Excluded paths and default ignore classes do not appear in generated graph
  metadata.
- Active graph updates to the scoped merged graph.

Status: task complete on 2026-06-17T10:28:17-06:00.

Evidence:

- Added scoped rebuild orchestration that loads `workspace-scope.json`,
  calculates de-duplicated scan roots, skips explicitly excluded roots, runs
  Graphify only against included roots, filters produced graph JSON, and
  activates the scoped `graphify-out/merged-graph.json`.
- Added graph filtering in `backend/workspace_scope.py` so default noisy classes
  such as `graphify-out/`, `.env*`, dependency folders, caches, media bulk, and
  `workspace/state/` are removed from the cockpit-owned active graph even if the
  upstream Graphify command emitted them.
- Added source-root metadata (`scope_profile`, `source_root`,
  `source_root_name`, `repo_project_name`, `signal_tier`) to kept nodes so
  later map/signal work can group by selected repo/project roots.
- Updated graph file lookup and semantic source windows to consider saved
  workspace scope roots, not just the cockpit repo or old manual scan dirs.
- Cleared stale semantic edges when rebuild activation changes the active graph
  path.
- Validation passed: governance preflight, `backend/.venv/bin/python -m pytest
  tests/test_graphify_service.py -q`, `backend/.venv/bin/python -m pytest
  tests/test_workspace_scope.py -q`, full `backend/.venv/bin/python -m pytest
  tests`, targeted backend compileall, `npm --prefix frontend run typecheck`,
  `npm --prefix frontend run build`, `git diff --check`, and
  `graphify update . --no-cluster` (`1,423 nodes`, `2,703 edges`). Existing
  FastAPI/Starlette deprecation warnings and the existing Vite chunk-size
  warning remain non-blocking.

### Chunk 4: Signal Tiers and Low-Signal Filtering

Goal: Add node scoring/tiering so default maps stop showing inconsequential
files.

Files likely to change:

- backend graph normalization/full/summary paths
- `frontend/src/tabs/Map.tsx`
- tests for signal tiering

Acceptance:

- Nodes receive `signal_tier`.
- Default Map hides `hidden` and low-signal evidence nodes.
- UI shows counts for hidden/excluded nodes.
- Operator can temporarily show low-signal nodes.

Status: task complete on 2026-06-17T10:42:36-06:00.

Evidence:

- Added explicit signal tier classification in `backend/workspace_scope.py`,
  covering source-of-truth files, entrypoints/important path roles, connector
  workspace items, ordinary evidence files, generated type shims, lockfiles,
  package markers, and fixture/mock paths.
- Scoped rebuild filtering now annotates kept nodes with `signal_tier` and
  `signal_reason`; noisy/generated/secret-like nodes still remain excluded from
  the active graph.
- `/graph/summary` and default `/graph/full` now use visible tiers
  (`overview`, `important`) by default and return `signal_counts`,
  `hidden_node_count`, and scoped `excluded_node_count` so the operator can see
  what was left out.
- `/graph/full?include_low_signal=true` restores evidence and hidden nodes for
  temporary inspection without changing the saved scope or graph files.
- Map now shows hidden low-signal and scoped excluded counts in the toolbar,
  provides a Low Signal toggle, and displays each selected full-graph node's
  signal tier/reason in the inspector.
- Validation passed: governance preflight, `backend/.venv/bin/python -m pytest
  tests/test_workspace_scope.py -q`, `backend/.venv/bin/python -m pytest
  tests/test_graphify_service.py -q`, targeted connector compatibility test,
  full `backend/.venv/bin/python -m pytest tests`, targeted backend
  compileall, `npm --prefix frontend run typecheck`, and
  `npm --prefix frontend run build`. The previously noted FastAPI/Starlette
  and Vite chunk-size warnings were addressed in the post-Chunk 4 warning
  cleanup.

### Chunk 5: Workspace Overview Map

Goal: Make the first Map experience repo/project-level, with drilldown into
modules and evidence.

Acceptance:

- Parent folder selection yields a workspace overview.
- Repos/projects are visible as the primary nodes.
- Cross-repo edges and semantic overlap are readable.
- Clicking a repo/project shows important modules and evidence, not a pile of
  tiny files.

Status: task complete on 2026-06-17T11:04:05-06:00.

Evidence:

- Updated `/graph/summary` so top-level summary nodes use scoped
  `source_root` / `repo_project_name` metadata when present, making saved parent
  folder scopes render as repo/project overview nodes instead of first-folder
  file clusters.
- Updated project drilldown so clicking a repo/project returns root/module
  summary nodes such as `(root)`, `src`, `backend`, or `docs`; evidence remains
  aggregated into meaningful groups rather than visible as a pile of tiny file
  nodes.
- Updated full graph node metadata, the source selector, and backend semantic
  overlap grouping to use repo/project cluster identity so cross-repo overlap is
  readable after a workspace-scoped rebuild.
- Map now opens in Overview mode by default, labels the raw graph mode as
  Evidence, preserves friendly breadcrumb labels for path-backed repo keys, and
  shows whether a selected summary node is a repo/project or module.
- Added backend contract tests for workspace overview grouping, repo/project
  drilldown, and full-graph repo clustering.

### Chunk 6: Insight Workflows Use Scope

Goal: Ensure Ask, AI assistant, recommendations, overlap, and gap detection use
the scoped/signal-aware graph.

Acceptance:

- Ask and chat cite scoped evidence.
- Overlap analysis prioritizes cross-repo/project overlap, not generated files.
- Recommendations explain included context and major exclusions.
- Gap/overlap/insight cards are framed around build decisions and token savings.

Status: task complete on 2026-06-17T11:09:43-06:00.

Evidence:

- Added scoped Ask evidence enrichment so Graphify query evidence is matched
  back to the active visible graph, annotated with repo/source-root/signal
  metadata, and filtered away when it only points at hidden low-signal files.
- Added a shared scope context packet for chat, recommendation generation, and
  steady missions. The packet names the active scope, included repo/module
  groups, explicit exclusions, default noisy-path filters, hidden/excluded
  counts, and a rough token-saving estimate.
- Recommendation and overlap-generated cards now persist that scope context, and
  the Recommendations tab shows a compact context strip with included groups,
  hidden/excluded counts, and token-saving estimate.
- Backend overlap reporting now applies signal tiers and ignores hidden
  low-signal nodes, so generated/lockfile-style content does not create default
  cross-repo overlap groups.
- Added backend contract tests for scoped Ask evidence, graph-context scope
  framing, and low-signal overlap filtering.

### Chunk 7: Video-Readiness Smoke Pass

Goal: Validate the workflow Adam needs to show.

Acceptance:

- Select `/home/adamgoodwin/code`.
- Exclude noisy folders in the tree.
- Rebuild a scoped graph.
- Show workspace overview.
- Drill into one repo/project.
- Show semantic overlap between meaningful project areas.
- Demonstrate hidden low-signal node counts.
- Ask one question that returns a compact scoped answer.

## Non-Goals

- Do not index the entire home directory by default.
- Do not turn the cockpit into a full filesystem browser.
- Do not expose secret values.
- Do not delete user files.
- Do not make low-signal filtering irreversible.
- Do not run live Supabase migrations as part of this plan.
- Do not broaden hosted auth or deployment scope unless Adam explicitly asks.

## Startup Instructions For Next Session

To continue tomorrow:

1. `git status --short`
2. Read `AGENTS.md`.
3. Read `START_HERE.md`.
4. Read this document only: `docs/workspace-scope-and-signal-plan.md`.
5. Start with Chunk 5 unless Adam redirects.

Avoid loading `docs/current-build-pathway.md` and long historical sections of
`docs/stabilization-plan.md` unless investigating a regression.
