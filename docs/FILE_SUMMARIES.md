# File Summaries

Document type: context-saving file guide
Status: current
Owner: Adam Goodwin

This is a short routing guide, not a replacement for source inspection. Open the
target file only when the current task needs its details.

## Root

| Path | Summary |
|---|---|
| `AGENTS.md` | Repo-local agent rules, governance triggers, Graphify policy, and working constraints. |
| `AGENT_QUICKSTART.md` | One-page restart path for agents after clearing or compaction. |
| `START_HERE.md` | Lightweight active-plan router and current pause state. |
| `README.md` | Product overview, local/Docker setup, safety model, and configuration reference. |
| `project-control.yaml` | Selected use case, risk tier, governance level, required docs, and agent controls. |
| `.gitignore` | Keeps generated graphs, runtime state, dependency folders, caches, logs, and env files out of commits. |

## Backend

| Path | Summary |
|---|---|
| `backend/main.py` | Import-compatible FastAPI facade plus remaining graph/settings/recommendation/action/mission/rebuild/overlap behavior. Large file: search first. |
| `backend/app.py` | FastAPI construction, rate limiting, CORS, and API-key middleware registration. |
| `backend/auth.py` | API-key middleware with dynamic config callbacks for tests/runtime patching. |
| `backend/config.py` | Backend path, env, graph, API-key, CORS, and secret-marker defaults. |
| `backend/graph_schema.py` | Shared graph validation and normalization helpers for `nodes`, canonical `links`, and legacy/internal `edges`. |
| `backend/state_store.py` | Atomic JSON write helpers for local persisted state. |
| `backend/storage_status.py` | File/Supabase storage readiness and required-schema-column warnings. |
| `backend/services/graphify_service.py` | Graphify CLI availability, command execution, timeouts, and structured errors. |
| `backend/routes/ask.py` | Ask endpoint, Graphify output parsing, evidence filtering, and session transcript writes. |
| `backend/routes/chat.py` | In-cockpit assistant config and SSE chat streaming route. |
| `backend/routes/cluster_selection.py` | Source/cluster selection route and available-cluster/source calculation. |
| `backend/routes/connectors.py` | Microsoft connector auth, sync status, and background SharePoint/OneNote sync routes. |
| `backend/routes/decisions.py` | Decision ledger storage helpers and routes. |
| `backend/routes/runtime.py` | Health and runtime readiness response builders and routes. |
| `backend/connectors/base.py` | Connector item models plus shared graph node/link contract helpers. |
| `backend/connectors/ingest.py` | Merges connector data into active graph files with canonical links. |
| `backend/connectors/sharepoint.py` | SharePoint adapter and graph node conversion. |
| `backend/connectors/onenote.py` | OneNote adapter and graph node conversion. |
| `backend/connectors/microsoft_auth.py` | Microsoft OAuth flow/cache helpers for connector sync. |

## Frontend

| Path | Summary |
|---|---|
| `frontend/src/App.tsx` | Main cockpit shell, tab navigation, shared state, and layout composition. |
| `frontend/src/api/client.ts` | Shared API client for base URL, API key, multipart handling, and auth error copy. |
| `frontend/src/tabs/Dashboard.tsx` | Command Center, workspace readiness, graph health, and attention cards. |
| `frontend/src/tabs/Ask.tsx` | Ask flow, Graphify-backed answers, and evidence display. |
| `frontend/src/tabs/Map.tsx` | Cytoscape graph map, filtering, and node detail inspection. |
| `frontend/src/tabs/Decisions.tsx` | Decision ledger UI. |
| `frontend/src/tabs/Recommendations.tsx` | Recommendation cards, decision packets, accept/reject/defer flows. |
| `frontend/src/tabs/WorkQueue.tsx` | Approval-gated action queue and dry-run/execution status. |
| `frontend/src/tabs/Settings.tsx` | Graph source controls, API key, runtime status, uploads, and connector settings. |
| `frontend/src/components/AICopilot.tsx` | Floating assistant panel with SSE streaming chat. |
| `frontend/src/styles.css` | Global cockpit layout and visual system. |

## Tests And Fixtures

| Path | Summary |
|---|---|
| `tests/fixtures/` | Small graph fixtures for canonical links, legacy edges, and malformed graph validation. |
| `tests/test_graph_schema.py` | Graph normalization and validation contracts. |
| `tests/test_settings_counts.py` | Settings counts across graph relationship shapes. |
| `tests/test_graph_upload.py` | Upload name, size, JSON, node/link, and activation validation. |
| `tests/test_graph_activation.py` | Graph activation contract and failure handling. |
| `tests/test_graphify_service.py` | Graphify service readiness and error contracts. |
| `tests/test_connector_ingest.py` | Connector graph node/link contracts and merge behavior. |
| `tests/test_runtime_status.py` | Workspace readiness endpoint behavior. |
| `tests/test_api_key_auth.py` | API-key middleware behavior. |
| `tests/test_clean_state.py` | Empty-state local persistence behavior. |
| `tests/test_supabase_schema_contract.py` | Supabase schema readiness contract. |

## Docs

| Path | Summary |
|---|---|
| `docs/context-map.md` | Context routing by task type. |
| `docs/stabilization-plan.md` | Active hosted-beta stabilization plan and chunk evidence. |
| `docs/current-build-pathway.md` | Archived 0-to-1 build history; load only for old evidence or regressions. |
| `docs/architecture.md` | Full architecture overview and data flow narrative. |
| `docs/ARCHITECTURE_MAP.md` | Concise source routing map for implementation work. |
| `docs/FILE_SUMMARIES.md` | This context-saving guide to important files and generated/local-only paths. |
| `docs/KNOWN_ISSUES.md` | Current known limitations, owner-review gates, and post-stabilization notes. |
| `docs/deployment-guide.md` | Hosted deployment and environment guidance. |
| `docs/runbook.md` | Operator procedures and smoke checks. |
| `docs/manual.md` | User/operator manual. |
| `docs/standards/` | Local engineering, governance, context-hygiene, and ship-ready standards. |

## Generated Or Local-Only

| Path | Summary |
|---|---|
| `graphify-out/` | Generated local repo graph and caches. Ignored; rebuild with `graphify update . --no-cluster`. |
| `workspace/state/` | Local runtime state. Ignored and user-specific. |
| `frontend/node_modules/`, `frontend/dist/`, `frontend/build/` | Dependency and build output. Ignored. |
| `.venv/`, `backend/.venv/`, `__pycache__/`, `.pytest_cache/` | Python environments and caches. Ignored. |
