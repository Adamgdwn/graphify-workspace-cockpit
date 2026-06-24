# Relationship Map Plan

Last Updated: 2026-06-23T09:57:48-06:00
Status: automatic graph escalation drafted; owner verification next
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

Owner sign-off 2026-06-19: Adam reviewed the multi-repo Evidence comparison map
(Timeshare-Connect / vector-conversion-tool / mermaid-tool with cross-repo
semantic links) and called it "video ready." The path is owner-approved;
remaining work is polish/tuning, not a rebuild. Same-day: shipped constant
on-screen-size repo labels (commit `995adc3`) and refreshed the canonical
workspace graph (35,637 → 41,881 nodes). The original Graphify token-saving
workflow was verified intact and additive to the cockpit.

Polish note 2026-06-20T13:40:39-06:00: semantic overlay visibility is now
actionability-first. Raw semantic matches can remain stored, but bright green
Evidence links are filtered/ranked for cross-folder or cross-repo decision
signals: duplicate/waste, gap, drift risk, shared pattern, intentional
reference, or cross-app similarity. The video script now includes this semantic
evolution beat and recording pointers for raw-vs-actionable counts.

Polish note 2026-06-20T13:57:24-06:00: bright semantic Evidence edges now have
a direct inspector. Clicking a semantic edge highlights both endpoints and
shows the practical "so what": insight kind, actionability score, similarity,
decision signals, endpoints, repos, and a trace-from-source action. Overlap
cards also show the same actionability signals when LLM triage has not supplied
richer evidence yet.

Polish note 2026-06-20T14:09:52-06:00: semantic zero-state copy now separates
"raw edges exist but do not cross the boundary" from "boundary candidates
failed the actionability score." In the current Applications evidence scope,
the 14 matching raw semantic edges are same-container/local links, so hiding
them is correct; the UI should not imply that real cross-folder candidates were
discarded by an overly strict score.

Polish note 2026-06-20T14:16:50-06:00: physical/structural map edges are
slightly brighter in both Overview and Evidence, with selected-node connections
using a stronger pale-blue highlight so pullback shots still read clearly.

Polish note 2026-06-20T14:25:31-06:00: map render overlays now clear on
interrupted render cleanup and have a small watchdog, preventing hot reloads or
mid-render state changes from leaving the Evidence map stuck behind "Rendering
map" after Cytoscape has already produced a graph or error state.

Polish note 2026-06-20T14:38:21-06:00: the single-repo semantic zero-state was
mostly stale cache identity, not an overly strict actionability threshold. The
backend now stamps semantic edges with a graph fingerprint, clears stale
semantic caches on graph upload/activation, and exposes stale/current metadata
so the Map can tell Adam to rerun Semantic Analysis for the current repo/scope
instead of implying the filter rejected valid current edges.

Polish note 2026-06-20T16:49:22-06:00: the video shoot exposed two operator
clarity gaps. The Map now distinguishes "Semantic Analysis has not run for this
map" from "semantic edges were filtered out," and recommendation cards now carry
active-map identity in their context so the UI can split Current Map, Other Map,
and System recommendations instead of showing one global pending pile.

Polish note 2026-06-20T21:43:48-06:00: Workspace Scope summary cards now use
the current checked folder selection for estimated files and default-ignored
files instead of the inspected root totals, so draft scopes do not keep showing
the broad 10,000-file cap after Adam selects a narrower folder.

Polish note 2026-06-20T21:55:27-06:00: two-repo review exposed a label/source
metadata issue rather than a failed scoped generation. Evidence graphs below
the old 600-node multi-repo fast-layout threshold skipped repo label nodes, so
multi-repo Evidence now uses the preset comparison layout whenever more than
one repo is visible. `/graph/full` also resolves duplicate relative filenames
per node source root, preventing same-name files in different repos from
showing the wrong root or excerpt. The active semantic cache for the tested
two-repo map had 21,008 stored edges, 7,426 visible raw matches, and 966 raw
cross-repo matches; remaining UX work is to let Map run/rerun semantic analysis
for the current scope directly instead of routing Adam to Settings.

Polish note 2026-06-20T22:30:05-06:00: semantic actionability is now stricter
about "so what?" signal. The Map keeps raw semantic matches available, but the
bright Evidence layer demotes shared repo scaffolding, copied governance docs,
generic symbols, extractor vocabulary, and density-only similarity. In the
current Governed Agent Lab / chuwi-optimizer scope, the simulated promotion set
falls from hundreds of cross-repo candidates to 5 code-concept links (`loop`
and `memory`), which is a better default for decision-grade overlap review.

Night closeout 2026-06-20T23:00:14-06:00: Adam shot the video and called out the
core project thesis: turn data into information, then information into
knowledge. The relationship-map polish run is boxed up and pushed through
`aa69140 Tighten semantic actionability filter`. Today's practical lesson is
that a scope with zero bright semantic links can be correct when raw matches do
not clear a decision-grade "so what?" gate. The next useful product follow-up is
to let Map run or rerun Semantic Analysis for the current scope directly, so the
operator does not have to leave the map and infer cache state from Settings.

Polish note 2026-06-21T15:08:06-06:00: the Map-local Semantic button now starts
or reruns Semantic Analysis when the active map has no usable semantic cache, a
stale cache, or mostly out-of-scope stored edges. It polls the existing backend
semantic pass, shows progress in the Map toolbar, refreshes semantic edges and
summary overlap after completion, and only behaves as a show/hide overlay once
current usable semantic edges exist.

Polish note 2026-06-21T15:20:08-06:00: Workspace Scope profile estimates no
longer let default-ignored bulk consume the bounded file-count budget. The
backend now treats default-ignored directories such as `.git`, `node_modules`,
and generated output folders as ignored paths without descending into their
contents, and the Profile cards label the values as estimated source files and
default-ignored paths. A direct check against this repo now reports 138 source
files and 18 default-ignored paths instead of the old 10,000-file cap behavior.

Polish note 2026-06-21T15:32:50-06:00: Evidence/full graph rendering now caps
at 15,000 visible nodes. The Scope tab warns before generation when the current
selection's source-file estimate approaches or exceeds that cap, and the Map
toolbar shows the exact generated visible-node count against the 15,000 cap
after generation. The saved-scope rebuild path also now lets explicit child
folder includes win over excluded parent paths, fixing the top-right
"Saved workspace scope has no included directories to scan" toast for valid
child-folder selections.

Polish note 2026-06-21T16:22:15-06:00: semantic generation now treats
actionability as the product boundary. The Map-run semantic pass sends the
current visible Evidence node ids, low-signal state, and knowledge lens state
to the backend; the backend scopes to visible signal nodes by default, raises
the default threshold to 0.86, keeps only mutual top-12 semantic neighbors, and
caps stored candidate edges at 50,000. Old broad semantic caches without the
current edge-policy version are withheld from `/graph/semantic-edges` and
reported as stale metadata; the live million-edge cache now returns 0 served
edges with `legacy_edge_count=1,082,041` so the Map prompts for a fresh
actionable rerun instead of loading the flood.

Polish note 2026-06-21T16:44:10-06:00: semantic overlap review now has a
second, stricter product boundary. The Map still stores candidate semantic
edges, but the default visible overlay is capped to a small readability
backbone, highlighted overlap pairs get their own bounded edge view, and the
Overlap panel opens on a top-action queue instead of every filtered pair.
`Triage Queue` now runs only that visible queue unless Adam explicitly switches
to `Show All`. `/graph/overlap-summary` adds actionability score, insight kind,
and decision signals so the in-cockpit assistant receives a ranked semantic
action queue and should answer with merge/bridge/compare/dismiss options rather
than generic similarity narration.

Polish note 2026-06-21T18:34:52-06:00: clicked semantic Evidence links now read
more like decision briefs. The semantic-link inspector adds signal-aware
options such as canonicalize, bridge, compare, document, dismiss, or choose a
source of truth, and the drawer body scrolls independently so endpoint and
provenance details no longer squeeze the "what can I do with this?" summary.

Polish note 2026-06-21T19:11:03-06:00: semantic-link explanations now escalate
cleanly into next-step reasoning. The inspector treats duplicate/waste as a
candidate decision rather than assuming one canonical home, publishes a precise
semantic-link active context with endpoints, repos, paths, scores, signals, and
options, and adds `Explain next steps with AI` to open the assistant with a
prompt that compares merge/canonicalize, bridge/reference, compare,
keep-separate, and dismiss choices.

Night closeout 2026-06-21T19:34:50-06:00: Adam reviewed the improved semantic
knowledge layer with options and called it "second video ready." The relationship
map is boxed for the night as a decision-grade semantic layer: Map can run the
analysis, stale/broad caches are withheld, visible semantic links are actionable
and readable, overlap defaults to a top action queue, clicked links explain their
endpoints and options, and the AI assistant can reason from the exact selected
semantic link. Next work should be owner review/recording or very small copy/UI
tuning only if the next pass exposes it.

Windows closeout 2026-06-21T20:01:05-06:00: the final semantic-link inspector
commit is pulled into the Windows build and the native launcher path is now
usable for recording. The Windows launcher can start the cockpit from
`launcher\launch-cockpit.bat`, and `launcher\restart-cockpit.bat` refreshes the
backend/frontend listeners after pulls or code changes. Live verification on
Windows passed backend tests, frontend build, launcher restart, runtime health,
Ollama model detection, current semantic cache checks, and overlap summary
loading. This is a good stop point for an owner-recorded Windows perspective
video.

Implementation note 2026-06-23T09:24:27-06:00: automatic graph escalation is
now drafted for owner verification. Workspace map generation can make a quick
local Ollama routing decision and, when `GRAPH_ESCALATION_ENABLED=true` plus a
configured `GRAPH_ESCALATION_BACKEND` are present, run elevated Graphify
`extract --no-cluster` instead of local `update --no-cluster`. The same
scope-filter, merge, activation, and semantic-cache clearing path is preserved.
Default behavior remains local-only.

Closeout note 2026-06-23T09:57:48-06:00: the escalation work is boxed up in
`docs/session-handoff-2026-06-23.md`, `docs/handover.md`, ADR-009, and the
Windows `01 Work Tracking` ledger. Validation passed for backend tests,
backend compile, frontend typecheck/build, diff whitespace, and
`graphify update . --no-cluster` (1,765 nodes, 3,400 edges). Live elevated
provider execution remains the owner-verification step once credentials are
configured.

Shutdown handoff 2026-06-18T22:45:26-06:00: see
`docs/session-handoff-2026-06-18.md` for the compact restart packet. Slices 1-5,
the video intent recenter, the multi-repo Evidence grid fix, and inert repo
labels are implemented and pushed. Adam's next useful step is hands-on review:
verify the labels, semantic links, and comparison layout against real
two-project selections, then tune the clear-map defaults based on what is
actually confusing.

Closeout note 2026-06-18T17:37:36-06:00: this plan is the active continuation
plan after `START_HERE.md`. The scope-focus examples used for smoke testing
are not product fixtures. Slices 1-5 now give the Map a broad relationship
layer, broad-safe overlap review, gap triage, a file-importance knowledge
lens, and a first decision overlay.

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
- File nodes now carry explicit `importance_tier` and `importance_reason`
  metadata, and the Map has a `Knowledge` lens for anchors, interfaces, and
  important boundary nodes.
- A static `Importance Criteria Table` tab now sits between `Scope` and `Map`
  to show how file importance is ranked and why files are shown, held, hidden,
  or excluded.
- Summary groups and full/drilldown nodes now carry a compact decision overlay
  derived from active decisions, relevant recommendations, and queued actions.
  Map nodes glow by primary decision classification, and selected node details
  show the related decision context.
- Semantic overlay display is actionability-first: raw stored matches are
  filtered into bright Evidence links only when they carry a pragmatic
  cross-folder or cross-repo reason.
- Clicking a bright semantic Evidence edge opens a semantic-link inspector with
  the "so what" signals used to rank and admit the connection.

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
loading full Evidence mode, make gap triage actionable, separate file
importance from raw file inclusion, and surface existing decisions plus
follow-up work directly in the map.

The remaining practical blocker is owner review on real broad workspaces after
the Map-local Semantic Analysis UX change. The decision overlay, importance
classifier, semantic overlap triage, and multi-repo layout should continue to be
tuned so the cockpit keeps the clean Graphify map intent while still preserving
the richer decision tools now built around it.

## Video Intent Recenter

Status: captured 2026-06-18T22:30:02-06:00 from Adam's reference video,
`Graphify + Obsidian + Claude Code = CHEAT CODE`.

The reference intent is not to build a literal file browser, nor to make the
map visually exhaustive. The useful core is:

- Graphify turns a repository, codebase, or document corpus into a knowledge
  graph of concepts, communities, and relationships.
- The graph is a map for an AI assistant: it should answer what exists, how
  concepts relate, where source evidence lives, and why a topic matters without
  forcing the assistant to scan everything.
- Source documents and files are evidence behind the map. They should be
  linked, inspectable, and retrievable, but they should not dominate the first
  view unless they are important boundaries or source-of-truth materials.
- Imported/generated knowledge should be staged. The operator should be able to
  keep it isolated, bring it into a scoped folder, harvest selected parts, or
  redistribute it deliberately.
- The clear look matters because the value is orientation. The default map
  should communicate the few important areas and high-signal relationships
  first, then let Adam progressively reveal communities, concepts, source docs,
  decisions, and raw evidence.

Graphify Workspace Cockpit should use that same principle without requiring
Obsidian as the runtime. The cockpit can keep Scope, Map, Decisions,
Recommendations, Work Queue, semantic overlap, gap triage, importance ranking,
and the AI assistant, but those features should orbit a clean Graphify-first
map. Next UI tuning should therefore prefer:

- staged map levels: workspace or repo groups first, then communities/concepts,
  then evidence files
- visible source links and provenance in the inspector instead of many source
  files on the canvas
- semantic overlays that explain high-signal overlap, gaps, drift, or shared
  patterns, not dense raw similarity clouds
- multi-repo comparison layouts that show projects beside each other with
  cross-repo semantic links as the primary added signal
- operator choices that mirror staging options: isolate, include as folder,
  harvest selected knowledge, or redistribute intentionally
- calm defaults with optional detail, so richer features remain available
  without replacing the simple map Adam originally wanted

## Next Implementation Slices

### Map-Local Semantic Analysis UX

Status: task complete 2026-06-21T15:08:06-06:00.

Owner-reported issue: enabling semantic connections from Settings was
cumbersome, especially after changing workspace folders. The Map already knows
when semantic analysis is missing, stale, or out of scope, so the Semantic
button should run the semantic pass directly instead of sending Adam to
Settings.

Delivered behavior:

- `Map` reuses the existing `POST /graph/semantic-pass`,
  `/graph/semantic-pass/status`, `/graph/semantic-edges`, and
  `/graph/overlap-summary` backend contract.
- The Semantic button reads `Run Semantic` or `Rerun Semantic` when the active
  map has no usable cache, a stale cache, or mostly out-of-scope stored edges.
- When a run starts from the Map, the toolbar shows semantic progress, the Map
  keeps Adam on the current surface, and toasts/focus notices report start,
  failure, and completion.
- On completion, the Map refreshes stored semantic edges, refreshes summary
  overlap, clears the full graph cache so Evidence reloads, and turns the
  semantic overlay on.
- Once current usable semantic edges exist, the same button remains a normal
  show/hide layer toggle.
- Map and Overlap copy now points back to the Semantic control instead of
  instructing Adam to go to Settings.

Validation:

- `bash scripts/governance-preflight.sh`: passed with 0 warnings
- `source "$HOME/.nvm/nvm.sh" && npm --prefix frontend run typecheck`: passed
- `source "$HOME/.nvm/nvm.sh" && npm --prefix frontend run build`: passed

Follow-up watch point:

- Owner should verify the live workflow against a freshly switched workspace
  scope. If progress feels too quiet, add a compact inline semantic status panel
  near the toolbar without changing the backend contract.

### Owner Review Tuning - June 20 Semantic And Recording Polish

Status: task complete 2026-06-20T23:00:14-06:00.

Goal: make the video/demo map easier to read and make semantic links more
truthful, actionable, and map-specific after Adam's live testing and recording
session.

Delivered behavior:

- Physical/structural map edges are brighter, and selected-node connections
  highlight more clearly for zoomed-out recording shots.
- Interrupted Evidence renders clean themselves up instead of leaving the map
  stuck behind "Rendering map".
- Semantic cache identity is explicit. Map can tell Adam when Semantic Analysis
  has not run for the active graph/scope instead of implying all current edges
  were filtered out.
- Semantic edge saving uses the correct helper path again.
- Recommendation context is map-specific, enabling Current Map, Other Map, and
  System recommendation separation.
- Workspace Scope estimated-file and default-ignore summary cards now follow
  the checked folder selection instead of stale inspected-root totals.
- Multi-repo Evidence uses the comparison layout whenever more than one repo is
  visible, and `/graph/full` resolves duplicate relative filenames per source
  root.
- Semantic actionability now demotes generic shared scaffolding and only
  promotes bright Evidence links with a practical "so what?" reason.

Validation:

- `source "$HOME/.nvm/nvm.sh" && npm --prefix frontend run typecheck`: passed
- `source "$HOME/.nvm/nvm.sh" && npm --prefix frontend run build`: passed
- `git diff --check`: passed
- Live two-repo semantic scorer simulation after tightening: 7,426 raw visible
  semantic matches, 966 boundary candidates, 5 promoted actionable links
  centered on `loop` and `memory`.

Follow-up watch point:

- Owner verification should confirm the stricter semantic actionability filter
  still feels honest and useful after the Map-local rerun control refreshes a
  newly selected scope.

### Owner Review Tuning - Multi-Repo Evidence Layout

Status: task complete 2026-06-18T22:36:01-06:00.

Owner-reported issue: a two-repo selection still rendered Evidence as a
left-to-right grid of file nodes instead of a clear comparison map. That
violated the video-intent recenter because the first visual read looked like an
inventory dump instead of two projects with relationships.

Delivered behavior:

- Fast full-graph Evidence mode now computes repo/container comparison
  positions before Cytoscape is created and passes those positions into the
  initial preset layout.
- The fast path no longer runs an additional layout pass after initialization,
  preventing Cytoscape's default grid from winning the first paint.
- Multi-repo Evidence now adds inert repo name labels above the comparison
  regions so Adam can identify which project each cluster belongs to without
  selecting individual nodes.
- The render spinner still clears through the same fast-path
  `requestAnimationFrame` plus timeout finalization, so broad two-repo maps
  stay responsive without falling back to grid packing.

Validation:

- `source /home/adamgoodwin/.nvm/nvm.sh && npm --prefix frontend run typecheck`:
  passed
- `git diff --check`: passed
- `rm -rf frontend/dist && source /home/adamgoodwin/.nvm/nvm.sh && npm --prefix frontend run build`:
  passed
- repo-label follow-up `source /home/adamgoodwin/.nvm/nvm.sh && npm --prefix frontend run typecheck`:
  passed
- repo-label follow-up `git diff --check`: passed
- repo-label follow-up `rm -rf frontend/dist && source /home/adamgoodwin/.nvm/nvm.sh && npm --prefix frontend run build`:
  passed
- repo-label follow-up `graphify update . --no-cluster`: rebuilt 1,615 nodes
  and 117,521 edges

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

Goal: make overlap useful on broad maps without requiring a 15,000-node full
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

Status: task complete 2026-06-18T17:14:07-06:00.

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

Delivered behavior:

- `backend/workspace_scope.py` now classifies every graph node with
  `importance_tier` values of `anchor`, `interface`, `important`, `evidence`,
  `hidden`, or `excluded`, plus an `importance_reason`.
- Source-of-truth files, governance/architecture docs, configuration
  boundaries, rationale nodes, public API/data boundaries, migrations,
  workspace-owned contract declarations, runtime entry points, and
  high-signal tests stay visible as knowledge.
- Dependency type declarations such as `node_modules/@types/react/index.d.ts`,
  generated type shims, ambient `*.d.ts`, lockfiles, fixtures, mocks,
  snapshots, test data, and generated paths are hidden from default knowledge
  surfaces.
- `/graph/summary` and `/graph/full` expose `importance_counts`; `/graph/full`
  accepts `knowledge_only=true` to return only workspace knowledge nodes while
  preserving existing Evidence and Low Signal modes.
- `Map` now has a `Knowledge` control that can open a stricter full graph even
  when broad Evidence is capped. Selected node details show both Signal and
  Importance badges and explanations.
- A static top-level `Importance Criteria Table` tab was added between `Scope`
  and `Map`, with rank, tier, default-map behavior, Knowledge lens behavior,
  examples, and reason labels.
- The Evidence button explicitly clears Knowledge mode, Low Signal clears
  Knowledge mode, and turning off Knowledge on an oversized broad scope returns
  safely to Overview instead of loading the capped Evidence payload.

Validation:

- `bash scripts/governance-preflight.sh`: passed with 0 warnings
- `backend/.venv/bin/python -m pytest tests/test_workspace_scope.py tests/test_graphify_service.py -q`:
  35 passed
- `backend/.venv/bin/python -m pytest tests -q`: 75 passed
- `backend/.venv/bin/python -m compileall backend`: passed, with noisy
  virtualenv listing
- `source ~/.nvm/nvm.sh && npm --prefix frontend run typecheck`: passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run build`: passed
- post-table follow-up `source ~/.nvm/nvm.sh && npm --prefix frontend run build`:
  passed

Follow-up watch point:

- The classifier is intentionally heuristic. After Adam reviews a real broad
  workspace map, tune edge cases where an implementation file should become an
  interface or where a project-specific generated/dependency path is still
  visible.

### Slice 5 - Decision Overlay

Status: task complete 2026-06-18T17:37:36-06:00.

Goal: make decisions visible on the relationship map.

Expected behavior:

- Existing decision classifications should appear on summary groups and
  drilldown nodes.
- Selected node details should show relevant decisions, recommendations, and
  queued actions.
- The map should help decide what to invest in, merge, document, archive, or
  leave alone.

Delivered behavior:

- `/graph/summary` now derives a compact `decision_overlay` for each summary
  group from active decisions, non-rejected recommendations, and queued actions.
  Group overlays aggregate child node ids, labels, repos, clusters, source
  roots, and paths so a decision on `app-a` can light up the `app-a` group.
- `/graph/full` attaches the same overlay shape to drilldown/full nodes. Node
  matching includes exact ids/labels/repos/clusters first and path containment
  for file or project paths.
- `backend/map_decision_overlay.py` owns the pure overlay matching and compact
  record shaping, while `backend/main.py` only loads current records and
  attaches overlay payloads to graph responses.
- Summary cache keys include an overlay state hash, so newly recorded
  decisions, recommendations, or actions do not stay hidden behind a stale
  summary response.
- `Map` now uses backend `decision_overlay.decision_classification` for summary
  and full-node decision glows, with the existing local decision fetch retained
  as a fallback while saving new gap decisions.
- Selected summary groups and full nodes now show a `Decision Context` block
  with matched decisions, recommendations, queued actions, and compact next
  action text.

Validation:

- `bash scripts/governance-preflight.sh`: passed with 0 warnings
- `backend/.venv/bin/python -m pytest tests/test_graphify_service.py::test_graph_map_decision_overlay_marks_summary_and_full_nodes -q`:
  1 passed
- `backend/.venv/bin/python -m pytest tests/test_graphify_service.py -q`:
  25 passed
- `backend/.venv/bin/python -m pytest tests -q`: 76 passed
- `backend/.venv/bin/python -m compileall -q -x 'backend/.venv|__pycache__' backend`:
  passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run typecheck`: passed
- `source ~/.nvm/nvm.sh && npm --prefix frontend run build`: passed
- `git diff --check`: passed
- `graphify update . --no-cluster`: rebuilt 1,589 nodes and 80,369 edges

Follow-up watch point:

- Overlay matching is intentionally compact and heuristic. After Adam reviews a
  real broad workspace, tune cases where a decision should inherit into a
  module/file node or where recommendation evidence is too broad.

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
4. Read `docs/session-handoff-2026-06-21.md`.
5. Read this file: `docs/relationship-map-plan.md`.
6. Start with the second-video recording/review path, or tiny semantic-link copy
   tuning only if Adam redirects.

Avoid loading the long historical plans unless investigating a regression:

- `docs/workspace-scope-and-signal-plan.md`
- `docs/stabilization-plan.md`
- `docs/current-build-pathway.md`
- `docs/handover.md`
