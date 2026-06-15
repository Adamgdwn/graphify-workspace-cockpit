# Architecture Overview

Document ID: ARCH-001
Status: current
Last Updated: 2026-06-15

## Summary

Graphify Workspace Cockpit is a local web application that turns a Graphify `graph.json` into a decision-making surface. The backend exposes graph query, recommendation, decision, action, decision-packet, overlap-review, and AI chat endpoints. The frontend renders a seven-tab cockpit shell (Command, Ask, Map, Decisions, Recommendations, Work Queue, Settings) plus a floating AI assistant overlay that is available in every tab.

## Components

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Backend API | Python FastAPI | Graph query, recommendation, decision, action, decision-packet, overlap-review, chat, and config endpoints |
| Rate Limiter | slowapi | 60 req/min per IP on all endpoints; `/health` exempt |
| Graphify Adapter | Graphify CLI subprocess | Run `graphify query/path/explain` against user-selected `graph.json` |
| Ollama Adapter | Ollama HTTP API | Local model synthesis for Ask, Recommendations, and Chat endpoints (optional — degrades gracefully) |
| Frontend Shell | React/Vite TypeScript | Seven-tab cockpit: Command, Ask, Map, Decisions, Recommendations, Work Queue, Settings |
| Command Center | React tab (`Dashboard.tsx`) | First-screen attention surface for pending recommendations, accepted-not-queued work, dry-run-ready actions, untriaged overlaps, graph freshness, and semantic freshness |
| AICopilot | React component (`AICopilot.tsx`) | Floating draggable/resizable overlay panel; SSE streaming chat; visible in every tab |
| Graph View | Cytoscape.js | Interactive project-level graph, click-to-inspect side panel, on-demand drill-down |
| Cluster Selector | Settings → Knowledge Sources | Source + cluster toggles; filters graph context for Ask, Chat, and Recommendations |
| State Store | JSON files on disk | Decisions, recommendations, actions, sessions, chat sessions, settings, cluster selection |
| Cloud Connectors | SharePoint + OneNote OAuth | Background sync from cloud knowledge bases into the graph |

## Data Flow

1. User loads cockpit → Command Center fetches current recommendations, actions, overlap status, and graph health signals
2. User asks a question (Ask tab) → backend selects graphify tool path, runs CLI with cluster-filtered context, optionally synthesizes with Ollama, returns answer + evidence nodes
3. User inspects map → frontend renders Cytoscape.js at project/cluster level; click expands to file level on demand; source chip shows active source count
4. Model generates recommendation → backend runs Ollama prompt against cluster-filtered graph context, writes structured card to `workspace/state/recommendations/`
5. User reviews decision packet → backend assembles recommendation, evidence-node provenance, overlap dossier, related decisions, queued action state, next approval gate, and Markdown export text without mutating state
6. User accepts recommendation → backend writes action record to `workspace/state/action-queue/`; no execution without explicit approval
7. User approves action → backend runs dry-run preview first, then executes on approval, writes result + rollback note to action record
8. User sends a chat message (AI assistant panel) → backend prepends cluster-filtered graph nodes as system context, streams SSE tokens from Ollama `/api/chat`; frontend displays tokens in real time via `ReadableStream`

No sensitive data flows through the backend. Graph files remain on local disk. Ollama is the only external call in the data path; all other calls are local.

## Boundaries and Non-Goals

- No autonomous commits, pushes, or deletes
- No editing source files from the UI
- No whole-workspace semantic re-extraction from the UI
- File mutations limited to `workspace/state/` except for explicitly approved and dry-run-verified actions
- AI assistant is read-only — it cannot trigger actions, decisions, or mutations

## State File Layout

```
workspace/state/
  decisions.json
  recommendations/          (one JSON file per recommendation card)
  action-queue/             (one JSON file per queued action)
  sessions/                 (Ask session transcripts — pruned to 50)
  chat-sessions/            (AI chat session records — pruned to 50)
  chat-config.json          (system prompt + model for AI assistant)
  cluster-selection.json    (active source + cluster toggles from Chunk 16)
  overlap-status.json       (durable overlap triage/workflow states)
  settings.json
  graph-rebuild-status.json (background rebuild job state)
```

## Data Contracts

**Decision record:** id, target_type, target_id, classification, rationale, evidence, created_at, created_by, status

**Recommendation record:** id, mode, title, summary, evidence, confidence, risk, effort, proposed_action, optional action_plan, optional overlap metadata/dossier, status, created_at

**Action queue record:** id, source_recommendation_id, action_type, description, dry_run_command, approval_required, approved_at, executed_at, result, rollback_note

**Decision packet:** schema_version, recommendation, evidence nodes/provenance, optional overlap dossier, judgement, recommendation_plan, related decisions, queued action state, operator choices, markdown

**Chat config:** system_prompt, model

**Cluster selection:** sources (array of {id, name, enabled}), clusters (array of {id, name, enabled})

**Overlap status record:** pair_key, status (untriaged / triaged / task-created / dismissed), triage verdict, triage confidence, triage action, timestamps

## Dependencies

| Dependency | Purpose | Required |
|------------|---------|----------|
| Graphify CLI | Graph query/path/explain | Yes |
| Python 3.11+ | Backend runtime | Yes |
| FastAPI + Uvicorn | HTTP server | Yes |
| slowapi | Rate limiting | Yes |
| Node 20+ / npm | Frontend build | Yes |
| React 18 + Vite | Frontend framework | Yes |
| Cytoscape.js | Graph visualization | Yes |
| Ollama | Local model synthesis for Ask, Recommendations, Chat | Optional — degrades gracefully |

## Environment Variables

All hardcoded paths and service URLs are configurable via environment variables. See `backend/.env.example` and `frontend/.env.example`.

| Variable | Where | Default | Purpose |
|----------|-------|---------|---------|
| `GRAPH_PATH` | backend | `workspace/demo/graph.json` | Path to graph.json |
| `STATE_DIR` | backend | `workspace/state` | Persistent state root |
| `CORS_ORIGINS` | backend | `http://localhost:5173` | Allowed frontend origins; include each exact localhost or LAN origin used by browsers |
| `OLLAMA_URL` | backend | `http://localhost:11434` | Ollama server base URL |
| `API_KEY` | backend | (unset) | Bearer token for network-facing deployments |
| `VITE_API_URL` | frontend | `http://localhost:8000` | Backend URL for browser requests |

## Authentication

Set `API_KEY` in the backend environment to require `Authorization: Bearer <key>` or `X-API-Key: <key>` on all non-health endpoints. Without `API_KEY`, the backend is open — safe for `localhost` use, not safe for network exposure. See `docs/deployment-guide.md` for setup.

## Key Decisions

- ADR-001: Standalone repo rather than Graphify subfolder (GitHub-ready scope, cleaner install path)
- ADR-002: FastAPI over Flask (async, typed, auto-generated OpenAPI docs)
- ADR-003: Cytoscape.js over Sigma.js or D3 (interactive graph workflows, good click/expand model)
- ADR-004: JSON files over SQLite for MVP state (minimal setup, inspectable, Git-friendly; Supabase backend added in Chunk Eleven)
- ADR-005: Env-var configuration over config files (Docker-friendly, no private paths in committed files)
- ADR-006 (Chunk 17): AI assistant as floating overlay panel, not a tab — available in every tab without navigation, draggable and resizable by the user
- ADR-007 (Chunks 20–26): Decision-flow polish stays inside the existing surfaces; Command Center is an attention layer, not a replacement for detailed tabs
- ADR-008 (Chunks 27–30): Ground-level decision evidence should aggregate in read-only packets before mutating workflows; approval and execution remain in existing recommendation and Work Queue controls
