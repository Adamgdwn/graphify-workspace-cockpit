# Architecture Map

Document type: concise source routing map
Status: current
Owner: Adam Goodwin

Use this file when you need the system shape without loading generated graphs or
large source files. For the fuller narrative, read `docs/architecture.md`.

## Runtime Components

| Area | Start Here | Notes |
|---|---|---|
| Backend API | `backend/main.py` | FastAPI app and current route surface. Search route names before opening broad ranges. |
| Graph schema | `backend/graph_schema.py` | Normalizes canonical `links` plus legacy/internal `edges`. |
| Atomic state writes | `backend/state_store.py` | Parent-safe JSON replacement helper used by persisted local state. |
| Graphify runtime | `backend/services/graphify_service.py` | CLI wrapper, readiness checks, structured Graphify errors. |
| Cloud connectors | `backend/connectors/` | SharePoint/OneNote auth, adapter node contracts, and graph merge helpers. |
| Frontend shell | `frontend/src/App.tsx` | Seven-tab shell and cross-tab state orchestration. |
| API client | `frontend/src/api/client.ts` | Shared backend requests, `VITE_API_URL`, API-key header, error normalization. |
| Command Center | `frontend/src/tabs/Dashboard.tsx` | Runtime readiness panel and attention cards. |
| Map | `frontend/src/tabs/Map.tsx` | Cytoscape graph view and drill-down behavior. |
| Settings | `frontend/src/tabs/Settings.tsx` | Graph activation/upload, API key, Graphify/Ollama/readiness controls. |
| Assistant | `frontend/src/components/AICopilot.tsx` | Floating SSE chat overlay. |

## Data And State

| Data | Location | Commit Policy |
|---|---|---|
| Demo graph | `workspace/demo/graph.json` | Committed fixture. |
| Local user state | `workspace/state/` | Ignored; do not commit runtime state. |
| Generated repo graph | `graphify-out/` | Ignored; rebuild locally when useful. |
| Backend env example | `backend/.env.example` | Committed template only. |
| Frontend env example | `frontend/.env.example` | Committed template only. |
| Real env files | `.env`, `backend/.env`, `frontend/.env` | Ignored; do not inspect or commit. |

## Primary Flows

| Flow | Files To Inspect |
|---|---|
| Ask/Graphify query | `backend/main.py`, `backend/services/graphify_service.py`, `frontend/src/tabs/Ask.tsx` |
| Graph upload and activation | `backend/main.py`, `backend/graph_schema.py`, `frontend/src/tabs/Settings.tsx`, `tests/test_graph_upload.py`, `tests/test_graph_activation.py` |
| Runtime readiness | `backend/main.py`, `frontend/src/tabs/Dashboard.tsx`, `tests/test_runtime_status.py` |
| Recommendation to action | `backend/main.py`, `frontend/src/tabs/Recommendations.tsx`, `frontend/src/tabs/WorkQueue.tsx` |
| Connector ingest | `backend/connectors/`, `tests/test_connector_ingest.py` |
| Supabase readiness | `backend/main.py`, `db/migrations/`, `tests/test_supabase_schema_contract.py` |

## Reading Rules

- Search `backend/main.py` before loading large ranges.
- Prefer tests as executable contracts before editing routes.
- Keep `graphify-out/`, dependency folders, and local state out of active
  context unless a task explicitly concerns generated output.
