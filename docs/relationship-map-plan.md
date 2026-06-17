# Relationship Map Plan

Last Updated: 2026-06-17T17:25:02-06:00
Status: active plan - relationship-map restart and next implementation slices
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

Completed foundations:

- `Scope` is now its own top-level tab for drive/folder/workspace selection.
- `Generate Map` saves scope, rebuilds, activates the scoped graph, and opens
  the `Map` tab.
- `Map` is focused on exploration; it no longer embeds the scope picker.
- Broad graphs are protected by a browser-safe cap for Evidence/full graph
  mode.
- `/graph/summary` no longer collapses a broad `/home/adamgoodwin/code` scope
  into one giant `code` node. It now derives top-level groups from relative
  source paths when scope metadata is too broad.
- Summary nodes expose physical connection counts and mark zero-link visible
  groups as gaps.
- The current active graph opens as groups such as `agents`, `Applications`,
  `Tools`, and `Workspace Docs`.

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

The latest fix prevents the one-dot collapse, but the broad workspace map still
needs a clearer decision surface for relationships. In particular, broad maps
cannot rely on full Evidence mode because `/graph/full` is capped for browser
safety, and the existing Overlap workflow still expects Evidence/full graph in
some cases.

## Next Implementation Slices

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

Goal: make overlap useful on broad maps without requiring a 5,000-node full
graph payload.

Expected behavior:

- Add or reuse a server-side overlap summary that works on visible summary
  groups.
- Overlap mode should show pair cards or edges for likely duplicated,
  reference, or related areas at the group/module level.
- The UI should not ask the browser to render the full evidence graph just to
  start overlap review.

Likely files:

- `backend/main.py`
- `frontend/src/tabs/Map.tsx`
- overlap status or recommendation routes only if needed
- backend tests covering broad overlap summary behavior

### Slice 3 - Gap Triage

Goal: make gaps actionable instead of merely orange badges.

Expected behavior:

- Gap details should distinguish "truly isolated", "hidden by low-signal
  filters", "missing semantic extraction", and "root-level docs only" when the
  data supports it.
- Gap panels should offer natural next actions such as drill in, ask about this
  area, mark as monitor/archive, or generate a recommendation.

### Slice 4 - Decision Overlay

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
5. Start with Slice 1 unless Adam redirects.

Avoid loading the long historical plans unless investigating a regression:

- `docs/workspace-scope-and-signal-plan.md`
- `docs/stabilization-plan.md`
- `docs/current-build-pathway.md`
- `docs/handover.md`
