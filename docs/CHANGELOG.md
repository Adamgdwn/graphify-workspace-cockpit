# Changelog

All notable changes to the Graphify Workspace Cockpit are recorded here.
Entries follow the chunk build sequence. Each entry covers what was added,
changed, or fixed in that chunk.

---

## Relationship Map Second Video Readiness (2026-06-21)

### Added
- Map-local Semantic Analysis run/rerun flow with status polling and Evidence-layer refresh.
- Semantic-link inspector options for canonicalize, bridge/reference, compare, keep separate, and dismiss decisions.
- `Explain next steps with AI` for clicked semantic links, passing exact endpoints, repos, paths, scores, signals, and options to the floating assistant.
- 15,000 visible-node Evidence cap with scope warnings.

### Changed
- Semantic overlap defaults now emphasize an actionable queue instead of dense raw similarity.
- Workspace Scope profile estimates now report selected source files and default-ignored paths without broad 10,000-file cap confusion.
- Duplicate/waste semantic copy now frames links as decision candidates rather than assuming one canonical home.

### Fixed
- Saved-scope rebuilds now allow explicitly included child folders under excluded parent paths.
- Running semantic analysis no longer shows a stale red "not run" alert while work is in progress.

## Chunk Thirty — Decision Packet View (2026-06-15)

### Added
- `GET /decision-packets/recommendations/{rec_id}` read-only endpoint for recommendation decision packets
- Expandable Decision Packet panel in Recommendation cards
- Markdown copy/export and JSON export for decision packets

### Changed
- Overlap-created recommendations now retain overlap metadata and triage dossier details for future packet review
- Recommendation packets combine evidence provenance, overlap dossier, action plan, related decisions, queued action state, and the existing approval gate

## Chunk Twenty-Nine — Recommendation Action Plans (2026-06-15)

### Added
- Optional `action_plan` on recommendations with canonical target, sources, concrete steps, conservative savings, risks, acceptance criteria, rollback, and open questions
- Implementation Brief sections in Recommendations and Work Queue
- Dry-run note content now includes richer action-plan context when present

## Chunk Twenty-Eight — Overlap Evidence Dossier (2026-06-15)

### Added
- Structured overlap triage dossier: why it matters, per-side purpose, similarities, differences, canonicality signals, and open questions
- Full path context under overlap pair labels in the Map panel

## Chunk Twenty-Seven — Node Provenance Inspector (2026-06-15)

### Added
- Full-graph node inspector provenance: repo, container, path, source location, symbol, kind, language, origin, root, id, purpose, metadata, and safe source excerpt

## Chunk Twenty-Six — Final Owner UI Readiness Sweep (2026-06-15)

### Added
- Final live browser walkthrough evidence across all seven tabs: Command, Ask, Map, Decisions, Recommendations, Work Queue, Settings
- Browser check for real Ask submission returning `Evidence nodes`

### Changed
- Closed the decision-flow polish path as integration complete without adding speculative product-code changes
- Updated `START_HERE.md` and `docs/current-build-pathway.md` to reflect the close-out state

## Chunk Twenty-Five — Confidence and Shipped Evidence (2026-06-15)

### Added
- `scripts/demo-path-smoke.mjs` — dependency-free live smoke check for backend health, graph summary, Ask evidence, decision/recommendation/action queues, overlap report, and rendered Command shell labels
- `docs/demo-path-checklist.md` — manual demo path for Command → Ask → Evidence → Map → Decision → Recommendation → Work Queue
- Demo readiness instructions in `docs/runbook.md`

### Changed
- Updated `docs/video-script-prompt.md` for the seven-tab workflow, Command-first demo path, overlap review workflow, current graph facts, and smoke evidence command

## Chunk Twenty-Four — Decision Command Center (2026-06-15)

### Added
- `Command` tab as the first cockpit tab
- Attention cards for pending recommendations, accepted-not-queued recommendations, dry-run-ready actions, untriaged overlaps, graph freshness, and semantic freshness
- Direct navigation from Command cards into the relevant tab or Map context

## Chunk Twenty-Three — Overlap Triage Workflow (2026-06-15)

### Added
- Durable overlap workflow records with statuses: untriaged, triaged, task-created, dismissed
- Status filters plus dismiss/restore workflow in the Map overlap panel
- Persisted task-created state after creating a recommendation from an overlap pair
- Restored triage verdicts from durable overlap records when Map loads

## Chunk Twenty-Two — Map Mode Polish (2026-06-15)

### Added
- Explicit Map modes: Explore, Trace, Overlap, Review
- Trace mode arms summary path tracing
- Overlap mode opens the semantic overlap workflow
- Review mode groups graph view, type, source, and edge-layer controls

## Chunk Twenty-One — Evidence Navigation (2026-06-15)

### Added
- Clickable Ask evidence nodes that navigate into focused Map context
- Clickable Recommendation evidence chips that navigate into focused Map context
- Map focus notices and soft warnings for missing evidence targets

### Changed
- Backend default CORS now supports both `localhost` and `127.0.0.1` dev origins

## Chunk Twenty — Decision-Flow Foundation (2026-06-15)

### Added
- Shared frontend decision metadata in `frontend/src/domain/decision.ts`
- App-level active cockpit context in `frontend/src/domain/cockpitContext.ts`

### Changed
- Decision vocabulary aligned across docs, UI, and backend expectations
- Legacy or unknown saved classifications render safely and normalize to `monitor` when edited

## Chunk Nineteen — Signal/Noise Filtering + LLM Triage (2026-06-15)

### Added
- Layer 1 heuristics: `sameName` flag per edge pair (basename comparison), `sameNameCount` per group, groups with same-name pairs sorted first and badged `≡ N`, same-name pair rows highlighted amber
- Similarity filter chips (70 / 80 / 85 / 90%) — filter on `maxSimilarity` so groups with any high-confidence pair stay visible
- "Same-name" toggle chip to isolate filename-matched groups
- `filteredGroups` useMemo derived from `overlapGroups`, used by both panel JSX and `triageAll()`
- `POST /overlap/triage` — LLM triage endpoint: accepts group data, builds structured prompt with same-name hint, calls Ollama `phi4:latest`, returns `{verdict, confidence, reason, action, model}`
- `TriageResult` interface and triage state (`triageResults`, `triaging`) in Map component
- "Triage" per-group button and "Triage All" toolbar button
- Verdict badge (colour-coded red/amber/gray/neutral) with confidence %, reason, and "Next step" action for **all** verdict types
- Task button verb reflects triage verdict: "Task: Merge →", "Task: Review →", "Task: Document →"
- `triage_verdict`, `triage_action`, `triage_confidence` optional fields on `CreateOverlapRecommendationRequest`; backend uses them for verdict-specific task title prefix and `proposed_action`

### Fixed
- **Highlight/fade bug**: `edge.faded { opacity: 0.03 }` was overridden by the later `edge.semantic-edge { opacity: 0.7 }` rule (equal specificity, last-wins). Added `edge.semantic-edge.faded { opacity: 0.03 }` as a two-class selector to win on specificity.
- **Clear regression**: After clearing a highlighted pair, all 1,988 edges snapped back to 70% opacity simultaneously. Fixed via `sem-browse` browse mode (opacity 0.22) — active whenever the Overlap panel is open but no pair is highlighted.

---

## Chunk Eighteen — Overlap Analysis + Actionable Consolidation (2026-06-14)

### Added
- Cross-cluster semantic edge filtering: isolates the 1,988 cross-repo edges from the 14,501 total; cross-edges are the ones where source and target nodes belong to different clusters
- `overlapGroups` useMemo: groups cross-edges by cluster pair, computes `edgeCount`, `avgSimilarity`, `topPairs` (top 6 by similarity), sorts by edge count
- Overlap Analysis panel in Map tab — toggled by "Overlap (N)" toolbar button
- "Highlight" button per group — dims all non-matching semantic edges on the Cytoscape canvas, brightens the selected pair; "Clear" restores browse mode
- `POST /recommendations/from-overlap` — creates a `mode: "duplicates"` recommendation from overlap evidence without requiring LLM
- "Create Task →" button per group — fires recommendation endpoint and shows ✓ confirmation
- `GET /graph/overlap-report` — server-side overlap computation (reference; frontend computes client-side)
- Real data finding: 14 cluster pairs, 1,988 edges; top pair is AI_BOOTSTRAP.md ↔ docs (771 edges, 80% avg)

---

## Chunk Seventeen — In-Cockpit AI Assistant (2026-06-14)

### Added
- Floating draggable/resizable `AICopilot` overlay panel rendered at App root — visible in every tab without navigation
- Collapsed state: 48×48px circular "AI" button; drag to reposition anywhere on screen; click to expand
- Expanded state: full chat panel with drag-to-move header and bottom-right resize handle
- `POST /chat` — SSE streaming endpoint using Ollama `/api/chat`; cluster-filtered graph nodes prepended as system context
- `GET /chat-config` and `PUT /chat-config` — persist `{system_prompt, model}` to `workspace/state/chat-config.json`
- `_prune_chat_sessions()` — prunes `workspace/state/chat-sessions/` to ≤50 on startup
- "X nodes used" chip on each assistant message shows how many graph nodes were in context
- Panel position, size, and expanded state persisted in `localStorage` (`copilot_pos`, `copilot_size`, `copilot_expanded`)
- Settings → "AI Assistant" section: editable system prompt textarea + model input + Save button

### Design decision
Original plan called for a Chat tab (sixth nav tab). Changed during implementation to a floating overlay panel so the assistant is available without leaving the current tab.

---

## Chunk Sixteen — Knowledge Base Cluster Selector (2026-06-14)

### Added
- `GET /cluster-selection` and `PUT /cluster-selection` — persist active source + cluster toggles
- Source toggles and cluster toggles in Settings → Knowledge Sources panel with select-all/deselect-all
- Cluster-filtered graph context layer for `POST /ask` and recommendation generation
- Map source chip ("X of Y sources active") with click-to-navigate to Settings

---

## Chunk Fifteen — Hardening, Polish, and Help (2026-06-14)

### Added
- Rate limiting via slowapi — 60 req/min per IP; `/health` exempt
- `POST /graph/rebuild` and `GET /graph/rebuild/status` — background graph rebuild with progress tracking
- `ErrorBoundary` per tab — tab errors no longer crash the whole app
- `HelpModal` — `?` header button with keyboard shortcuts, feature guide, and quick-start tips
- Graph rebuild button and token savings estimate in Settings
- `graph_stats` in `/settings/org` response (node count, edge count, last-modified)
- God node gold ring (top-5 nodes by edge weight highlighted in Map)

### Changed
- Session pruning: Ask sessions pruned to ≤50 on startup (was unbounded)

---

## Chunk Fourteen — Cloud Knowledge Base Connectors (2026-06-14)

### Added
- SharePoint + OneNote OAuth connector sync engine
- Background sync from cloud knowledge bases into the graph
- Cloud-source nodes visually distinguished from local nodes in Map
- Sync status and "Sync Now" button in Settings → Connected Sources

---

## Chunk Thirteen — Demo Polish and UX Quality (2026-06-14)

### Added
- Empty states in every tab with guided prompts
- Export JSON buttons in Decisions, Recommendations, and Work Queue tabs
- Graph node/edge count in Settings header
- `Ctrl+K` / `Cmd+K` global shortcut → switches to Ask tab and focuses textarea
- Responsive layout audit — all tabs usable at ≥768px (Android tablet landscape)

### Changed
- Button sizing, card padding, and visual consistency pass across all tabs
- Map: god node gold ring (top hub nodes highlighted)

---

## Chunk Twelve — Real Graph Foundation (2026-06-14)

### Added
- Live `graph.json` from real workspace: 533 nodes, 645 edges
- `demo_mode` flag in `/health` response
- Dismissible demo banner in frontend (stored in `sessionStorage`)
- Core tabs validated against live graph data; Settings validates graph and service status

---

## Chunk Eleven — Shared State / Cross-Device Sync (2026-06-14)

### Added
- Supabase storage backend option for decisions, recommendations, and actions
- Cross-device real-time sync when Supabase is configured
- `created_by` identity field on all records
- Multiple named graphs per organization
- Org settings panel in Settings tab
- `GET /actions?format=uaos` UAOS handoff export endpoint

---

## Chunk Ten — Network-Ready Deployment (2026-06-14)

### Added
- API key authentication gate (`API_KEY` env var; `Authorization: Bearer` or `X-API-Key` header)
- HTTPS via Caddy reverse proxy (`docker-compose --profile https`)
- Graph upload API (`POST /graph/upload`) — no SSH required
- Responsive layout for Android tablet (≥768px media queries)
- Windows Docker Desktop setup guide
- Configurable Ollama URL via `OLLAMA_URL` env var

---

## Chunk Nine — GitHub Packaging (2026-06-14)

### Added
- Environment variable layer (`GRAPH_PATH`, `STATE_DIR`, `CORS_ORIGINS`, `OLLAMA_URL`, `VITE_API_URL`)
- `Dockerfile` and `docker-compose.yml`
- Demo graph with three fictional projects (`cockpit`, `knowledge-hub`, `automation`)
- Clean README (local dev + hosted Docker modes)
- CI on push (GitHub Actions)
- Auth warning in docs

---

## Chunk Eight — Approved Actions (2026-06-14)

### Added
- `POST /actions` and `GET /actions` — action queue records
- Dry-run preview (`GET /actions/{id}/dry-run`) before any execution
- `POST /actions/{id}/execute` — explicit approval gate; writes result + rollback note

---

## Chunk Seven — Steady Work Mode (2026-06-14)

### Added
- `POST /missions` and `GET /missions` — bounded background analysis missions
- Background threading for mission execution
- Progress log per mission
- `POST /missions/{id}/cancel`

---

## Chunk Six — Recommendation Queue (2026-06-14)

### Added
- `POST /recommendations` and `GET /recommendations` — Ollama-backed recommendation cards
- Accept / reject / defer controls in Recommendations tab
- Evidence node inspection links

---

## Chunk Five — Decision Ledger (2026-06-14)

### Added
- `POST /decisions` and `GET /decisions` — persistent decision classifications
- `PATCH /decisions/{id}` — edit or retire a decision
- Map tab badges driven by decision status

---

## Chunk Four — Readable Map (2026-06-14)

### Added
- Cytoscape.js project-level graph view with hub-and-spoke layout
- Click-to-inspect side panel with node summary
- Filters by type, theme, and decision status
- "Why connected?" path tracing between selected nodes
- On-demand drill-down to file level

---

## Chunk Three — Ask Interface (2026-06-14)

### Added
- `POST /ask` — graph-backed Q&A via `graphify query/path/explain`
- Optional Ollama synthesis for natural language answers
- Evidence node list and follow-up question suggestions
- Session transcripts saved to `workspace/state/sessions/`

---

## Chunk Two — App Shell (2026-06-14)

### Added
- FastAPI backend with `/health` endpoint
- React/Vite TypeScript frontend
- Five-tab cockpit shell (Ask, Map, Decisions, Recommendations, Work Queue)
- `scripts/start.sh` launcher (uvicorn + Vite)

---

## Chunk One — Governance Baseline (2026-06-14)

### Added
- `docs/` structure: architecture, risk register, agent inventory, prompt register, tool permission matrix, roadmap, vision, domain language, context map
- `project-control.yaml` with risk tier and governance level
- `docs/standards/` and `docs/policy/` governance documents
- `AI_BOOTSTRAP.md` and `START_HERE.md`
