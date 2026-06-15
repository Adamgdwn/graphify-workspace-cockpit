# Roadmap

Last Updated: 2026-06-15T10:23:52-06:00
Owner: Adam Goodwin

## Done — Chunks 1–19 (all complete as of 2026-06-15)

- **Chunk One** — Governance baseline: docs, risk register, agent inventory, prompt register, tool permission matrix
- **Chunk Two** — App shell: FastAPI backend, React/Vite frontend, six-tab cockpit, `start.sh` launcher
- **Chunk Three** — Ask interface: graph-backed Q&A via `graphify query/path/explain`, Ollama synthesis, session transcripts
- **Chunk Four** — Readable map: clustered Cytoscape.js view, drill-down, click-to-inspect panel, type/theme/decision filters
- **Chunk Five** — Decision ledger: persistent classifications, map badges, accept/edit/retire
- **Chunk Six** — Recommendation queue: Ollama-backed cards, accept/reject/defer, evidence inspection
- **Chunk Seven** — Steady work mode: bounded background missions, progress log, cancel
- **Chunk Eight** — Approved actions: dry-run gate, explicit confirmation, execution report, rollback note
- **Chunk Nine** — GitHub packaging: env-var layer, Dockerfile, docker-compose, demo graph, clean README, CI
- **Chunk Ten** — Network-ready deployment: API key auth, Caddy HTTPS proxy, graph upload API, responsive layout, Windows Docker guide
- **Chunk Eleven** — Shared state: Supabase storage backend, cross-device sync, `created_by` identity, named graphs, org settings
- **Chunk Twelve** — Real graph foundation: live `graph.json` (533 nodes, 645 edges), `demo_mode` flag, dismissible banner, full tab validation
- **Chunk Thirteen** — Demo polish and UX quality: empty states, export buttons, responsive audit, graph stats in Settings, `Ctrl+K` shortcut, god node gold ring, keyboard and mobile UX
- **Chunk Fourteen** — Cloud knowledge base connectors: SharePoint + OneNote OAuth, sync engine, background sync, cloud node visual distinction
- **Chunk Fifteen** — Hardening, polish, and help: rate limiting (slowapi, 60/min), session pruning (50 max), `POST /graph/rebuild`, `ErrorBoundary` per tab, `HelpModal`, graph rebuild in Settings
- **Chunk Sixteen** — Knowledge base cluster selector: `GET/PUT /cluster-selection`, source + cluster toggles in Settings, cluster-filtered graph context for Ask and Recommendations, Map source chip
- **Chunk Seventeen** — In-cockpit AI assistant: floating draggable/resizable overlay panel, `POST /chat` SSE streaming, cluster-aware graph context, "X nodes used" chip, localStorage persistence, Settings → AI Assistant section
- **Chunk Eighteen** — Overlap analysis: cross-cluster semantic edge panel, pair highlighting on the Map, task creation from overlap evidence
- **Chunk Nineteen** — Signal/noise filtering and LLM triage: same-name detection, similarity chips, `POST /overlap/triage`, verdict badges, and triage-aware task creation

## Now

The 19-chunk build pathway is complete. The next planned path is decision-flow
polish: making the existing surfaces feel like one continuous decision tool
rather than six adjacent tabs.

The cockpit is a working local-first decision surface with:

- Graph-backed Q&A, interactive map, decision ledger, recommendation queue, and action log
- Floating AI assistant available in every tab
- Knowledge base cluster selector for focused graph context
- Overlap analysis with duplicate/reference/related triage
- Cloud connector sync (SharePoint + OneNote)
- Cross-device shared state via Supabase
- API key auth, Caddy HTTPS, Docker deployment, rate limiting, and session pruning

Planned decision-flow chunks:

- **Chunk Twenty** — Decision-flow foundation: align decision vocabulary and introduce active cockpit context
- **Chunk Twenty-One** — Evidence navigation: click Ask and Recommendation evidence into focused Map context
- **Chunk Twenty-Two** — Map mode polish: group dense Map controls into Explore / Trace / Overlap / Review modes
- **Chunk Twenty-Three** — Overlap triage workflow: persist untriaged, triaged, task-created, and dismissed states
- **Chunk Twenty-Four** — Decision command center: surface pending recommendations, dry-run actions, untriaged overlaps, and graph freshness
- **Chunk Twenty-Five** — Confidence and shipped evidence: focused tests and demo-path validation

Additional candidates for follow-on work:

- End-to-end test suite (Playwright or Vitest + MSW)
- Graph rebuild UI polish (progress streaming, error reporting)
- Ask and Chat response formatting (markdown rendering for model output)
- Mobile layout refinements below 768px

## Strategic Direction

The cockpit is the knowledge backbone of Adam's AI-native operating system.

```
Layer 1 — Knowledge Extraction
  Graphify CLI + graph.json
  Reads repos, docs, and workspace structure
  Produces a semantic workspace graph

Layer 2 — Decision Intelligence (this cockpit)
  Answers questions, maps relationships, proposes recommendations
  Records human decisions, accepted recommendations, approved actions
  Exports durable governed artifacts through /actions?format=uaos

Layer 3 — Mission Execution
  User AI Operating System (UAOS)
  Reads cockpit artifacts through the handoff contract
  Proposes and executes policy-gated missions
```

## Non-Goals (standing)

- Autonomous commits, pushes, or destructive actions
- Editing arbitrary source files from the UI
- Making decisions on the user's behalf
- Replacing Codex or Claude as a coding assistant
- Public client access without a separate governance decision
- Whole-workspace semantic re-extraction from the UI
