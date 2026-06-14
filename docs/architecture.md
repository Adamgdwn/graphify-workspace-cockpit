# Architecture Overview

Document ID: ARCH-001
Status: draft
Last Updated: 2026-06-14

## Summary

Graphify Workspace Cockpit is a local web application that turns a Graphify `graph.json` into a decision-making surface. The backend exposes graph query, recommendation, decision, and action endpoints. The frontend renders a five-tab cockpit shell with interactive graph, Q&A, decision ledger, recommendation cards, and work queue.

## Components

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Backend API | Python FastAPI | Expose graph query, recommendation, decision, and action endpoints |
| Graphify Adapter | Graphify CLI subprocess | Run `graphify query/path/explain` against user-selected `graph.json` |
| Ollama Adapter | Ollama HTTP API | Local model synthesis for Ask and Recommendation endpoints (optional) |
| Frontend Shell | React/Vite TypeScript | Five-tab cockpit UI: Ask, Map, Decisions, Recommendations, Work Queue |
| Graph View | Cytoscape.js | Interactive project-level graph, click-to-inspect, on-demand drill-down |
| State Store | JSON files on disk | Decisions, recommendations, action queue, sessions, settings |

## Data Flow

1. User loads cockpit → frontend fetches project-level graph from backend
2. User asks a question → backend selects graphify tool path, runs CLI, optionally synthesizes with Ollama, returns answer + evidence nodes
3. User inspects map → frontend renders Cytoscape.js at project/cluster level; click expands to file level on demand
4. Model generates recommendation → backend runs Ollama prompt against graph context, writes structured card to `workspace/state/recommendations/`
5. User accepts recommendation → backend writes action record to `workspace/state/action-queue/`; no execution without explicit approval
6. User approves action → backend runs dry-run preview first, then executes on approval, writes result + rollback note to action record

No sensitive data flows through the backend. Graph files remain on local disk. No external calls in MVP.

## Boundaries and Non-Goals (MVP)

- No cloud sync or multi-user support
- No autonomous commits, pushes, or deletes
- No editing source files from the UI
- No whole-workspace semantic re-extraction from the UI
- File mutations limited to `workspace/state/` except for explicitly approved and dry-run-verified actions

## State File Layout

```
workspace/state/
  decisions.json
  recommendations/       (one JSON file per recommendation card)
  action-queue/          (one JSON file per queued action)
  sessions/              (Ask session transcripts)
  settings.json
```

## Data Contracts

See `docs/specs/` for full schemas. Summary:

**Decision record:** id, target_type, target_id, classification, rationale, evidence, created_at, created_by, status

**Recommendation record:** id, question, recommendation, recommended_action, target_ids, evidence, risk, confidence, requires_approval, status, created_at

**Action queue record:** id, source_recommendation_id, action_type, description, dry_run_command, approval_required, approved_at, executed_at, result, rollback_note

## Dependencies

| Dependency | Purpose | Required |
|------------|---------|----------|
| Graphify CLI | Graph query/path/explain | Yes |
| Python 3.11+ | Backend runtime | Yes |
| FastAPI + Uvicorn | HTTP server | Yes |
| Node 20+ / npm | Frontend build | Yes |
| React 18 + Vite | Frontend framework | Yes |
| Cytoscape.js | Graph visualization | Yes |
| Ollama | Local model synthesis | Optional (degrades gracefully) |

## Key Decisions

- ADR-001: Standalone repo rather than Graphify subfolder (GitHub-ready scope, cleaner install path)
- ADR-002: FastAPI over Flask (async, typed, auto-generated OpenAPI docs)
- ADR-003: Cytoscape.js over Sigma.js or D3 (interactive graph workflows, good click/expand model)
- ADR-004: JSON files over SQLite for MVP state (minimal setup, inspectable, Git-friendly; revisit at scale)
