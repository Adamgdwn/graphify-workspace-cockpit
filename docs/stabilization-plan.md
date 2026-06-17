# Graphify Workspace Cockpit Stabilization Plan

Last Updated: 2026-06-16T20:49:51-06:00
Status: active plan - Chunk 7 task complete; next recommended chunk is Chunk 8 Minimum Backend Test Suite
Owner: Adam Goodwin

## Startup Routing

This document supersedes `docs/current-build-pathway.md` as the active planning
surface. `docs/current-build-pathway.md` is retained as historical build and
validation evidence only.

For normal continuation:

1. Run `git status --short`.
2. Read `AGENTS.md`.
3. Read this file.
4. Load only the files named in the selected chunk.
5. Do not open the archived current-build pathway unless investigating prior
   chunk history, validation evidence, or a regression from the original build.

## 1. Executive Summary

This plan converts the cockpit from a strong local demo into a controlled hosted
beta candidate. The audit findings are valid enough to treat as release blockers:
graph runtime assumptions, API-key usability, graph schema drift, unsafe upload
paths, clean-state writes, Caddy route ordering, stale Supabase migration shape,
and missing backend contract tests.

The work should be done in small PRs. Do not combine security fixes, deployment
fixes, state-store hardening, and backend module splitting in one pass.

Preserve the current product while hardening it. The seven-tab workflow
(`Command`, `Ask`, `Map`, `Decisions`, `Recommendations`, `Work Queue`,
`Settings`) and the AI assistant overlay should remain usable after each chunk.

## 2. Current Risk Ranking

P0 - blocks hosted beta:

- Backend tests now exist, but coverage is still partial until the remaining P0
  backend contracts are added.

Resolved in Chunk 1:

- Graph schema normalization now accepts `links` and legacy/internal `edges`,
  emits canonical `links`, rejects malformed relationship records, and fixes
  Settings relationship counts for both shapes.

Resolved in Chunk 2:

- Settings now activates listed graphs through `POST /graphs/{name}/activate`,
  refreshes state after success, preserves backend failure details, and backend
  tests cover demo/uploaded activation plus missing or invalid graph names.

Resolved in Chunk 3:

- Graphify runtime access now goes through `backend/services/graphify_service.py`,
  Ask/Rebuild return structured errors such as `GRAPHIFY_MISSING`,
  `GRAPHIFY_TIMEOUT`, and `GRAPHIFY_COMMAND_FAILED`, `/health` and `/settings`
  expose Graphify status, Settings displays the runtime state, and the Docker
  backend image installs `graphifyy` through `backend/requirements.txt`.

Resolved in Chunk 4:

- Frontend backend calls now go through `frontend/src/api/client.ts`, which
  prefixes `VITE_API_URL`, sends a browser-stored `X-API-Key` when present,
  preserves `FormData` multipart handling, and normalizes 401/403 copy to
  "API key required or invalid." Settings now lets beta users save, test, and
  clear the key locally even when protected `/settings` calls are unauthorized.

Resolved in Chunk 5:

- Graph upload now sanitizes filenames, rejects traversal, non-JSON names,
  oversized files, invalid JSON, missing nodes, malformed links, and strict
  upload-only link target errors. Uploaded graphs are normalized to canonical
  `links`, written atomically inside `GRAPHS_DIR`, and only activated after
  validation. Existing graph activation now rejects invalid graph files before
  switching Settings state.

Resolved in Chunk 6:

- Local JSON state writes now go through `backend/state_store.py` atomic
  same-directory replacement with parent creation. Decisions, recommendations,
  actions, settings, sessions, connector sync status, Microsoft auth cache/flow
  JSON, graph uploads, scan dirs, semantic edges, overlap statuses, cluster
  selection, device tracking, and chat config/session metadata use the helper.
  Clean empty-state tests cover the persisted local file surfaces without
  calling network-backed Graphify or Ollama paths.

Resolved in Chunk 7:

- `config/Caddyfile` now handles `/api/*` before the frontend SPA catch-all and
  strips `/api` before proxying to the backend. Deployment docs, README,
  runbook, and demo checklist now document `VITE_API_URL=/api` for same-origin
  Caddy hosting plus hosted smoke checks for `GET /api/health` and `GET /`.

P1 - beta confidence:

- Supabase migration does not include newer recommendation/action fields such as
  `action_plan`, `overlap`, and `overlap_dossier`.
- `backend/main.py` is large enough that behavior changes are hard to review.

Governance flag: `project-control.yaml` classifies this as `AI agent with tools`
while selected `risk_tier` is `low` and `governance_level` is `1`. Per local
standards, this does not automatically change governance, but hosted beta work
should be treated as an owner-review checkpoint for auth, uploads, deployment,
tool execution, and Supabase mode.

## 2.1 Owner Decisions Needed

Record these as accepted decisions, accepted exceptions, or deferred gates before
the relevant implementation chunk proceeds:

- Governance level: keep low / level 1 for this stabilization pass, raise it, or
  explicitly accept stronger review as a compensating control without changing
  `project-control.yaml`.
- Graphify runtime: resolved for this stabilization pass by installing
  `graphifyy` in Docker/runtime and keeping a clear `GRAPHIFY_MISSING`
  readiness/error mode for custom or broken runtimes.
- API-key browser storage: localStorage accepted for this beta pass through
  Chunk 4 implementation; select a stronger hosted auth/session pattern before
  broader or untrusted production exposure.
- Supabase migration policy: allow a new migration file only, or approve live
  migration application separately.
- CI expansion: add backend `pytest` and frontend production build to CI once
  tests exist.

## 3. Context-Window Strategy

- Start each implementation chunk with `git status --short`, `AGENTS.md`, and
  this plan.
- Avoid `graphify-out/`, `graphify-out/cache/`, `frontend/node_modules/`,
  `frontend/dist/`, `.venv/`, `__pycache__/`, and generated graph dumps.
- Search before opening large files. `backend/main.py` is over 3,000 lines; load
  only the target route/helper ranges for the chunk.
- Add tests before broad refactors. Backend module splitting waits until the
  release-blocking contracts have coverage.
- Stop after each chunk once validation passes and this plan is updated.
- Use `docs/current-build-pathway.md` only as an archive for old validation
  evidence or regression context.

## 4. Repo Inspection Strategy

Baseline evidence gathered on 2026-06-16:

- Backend entrypoint: `uvicorn backend.main:app`.
- Frontend build command: `cd frontend && npm run build`.
- Frontend typecheck command: `cd frontend && npm run typecheck`.
- Backend dependencies: `backend/requirements.txt`; pytest was added in Chunk 1.
- Graphify runtime: `backend/requirements.txt` now includes `graphifyy>=0.8.37`;
  the local validation environment installed `graphifyy 0.8.40`, and Docker
  backend build verified the CLI is installed in the image.
- Current demo graph: `workspace/demo/graph.json`, using `links`.
- Connector ingest: `backend/connectors/ingest.py`, now normalizes existing
  graph data and emits canonical `links`.
- Graph activation route: backend has `POST /graphs/{name}/activate`; Settings
  now calls that route and backend validates activation names against demo or
  uploaded graph files.
- Graph upload route: `POST /graph/upload` in `backend/main.py`, now sanitizes
  file names, validates and normalizes graph JSON, writes atomically under
  `GRAPHS_DIR`, and activates only after successful validation.
- Local state writes: `backend/state_store.py` owns atomic JSON replacement for
  the file backend, and `tests/test_clean_state.py` covers fresh empty-state
  writes for the main persisted surfaces.
- Caddy route file: `config/Caddyfile`, now handles `/api/*` before the
  frontend catch-all and strips `/api` before proxying to the backend.
- Supabase migration: `db/migrations/001_initial.sql`, missing newer optional
  JSON fields used in current records.
- Existing tests: `tests/` now covers graph schema normalization, settings
  counts, and connector ingest compatibility.

## 5. Chunked Implementation Plan

### Chunk 0: Orientation and Baseline Validation

Goal: Confirm actual structure, commands, and breakpoints before code changes.

Why this matters: The audit is directionally correct, but every fix should start
from current files, not stale assumptions.

Files to inspect first: `README.md`, `AGENTS.md`, this plan,
`backend/main.py` route index only, `backend/requirements.txt`,
`frontend/package.json`, `Dockerfile`, `docker-compose.yml`,
`config/Caddyfile`, `db/migrations/`.

Files likely to change: `docs/stabilization-plan.md`, `START_HERE.md`,
`docs/context-map.md`, and optionally archived pathway pointers.

Exact implementation steps:

1. Run `git status --short`.
2. Run `bash scripts/governance-preflight.sh`.
3. Record baseline commands, route mismatches, test availability, and runtime assumptions.
4. Do not touch runtime code in this chunk.

Validation commands:

```bash
bash scripts/governance-preflight.sh
python -m compileall -q backend
source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

Acceptance criteria:

- Baseline findings are documented.
- P0 blockers are ordered.
- Next implementation chunk is owner-approved or explicitly selected.
- Owner-decision items are recorded as decisions, exceptions, or deferred gates.

Rollback note: Revert only the planning doc changes from this chunk.

Token/context warning: Keep this to source/config/doc summaries. Do not inspect
generated graph data.

### Chunk 1: Graph Schema Normalization

Status: **task complete** — 2026-06-16T17:47:37-06:00

Completion target: Task complete

Goal: Stop the app from mixing `links` and `edges`.

Why this matters: Settings, graph health, connector ingest, and map behavior
cannot be trusted if relationship counts depend on which key a graph uses.

Files to inspect first: `backend/main.py` graph load/settings/full/summary
ranges, `backend/connectors/ingest.py`, `workspace/demo/graph.json`,
`frontend/src/tabs/Settings.tsx`, `frontend/src/tabs/Map.tsx` type contracts.

Files likely to change: `backend/graph_schema.py`, `backend/main.py`,
`backend/connectors/ingest.py`, `tests/test_graph_schema.py`,
`tests/test_settings_counts.py`, `tests/fixtures/demo_graph_links.json`,
`tests/fixtures/demo_graph_edges.json`.

Exact implementation steps:

1. Add `backend/graph_schema.py` with `normalize_graph`, `validate_graph`, and
   `count_links`.
2. Accept both `links` and legacy/internal `edges`, normalize to `links`.
3. Convert link relation from `relation`, fallback `label`, fallback `"related"`.
4. Reject malformed links missing `source` or `target`.
5. Use the normalizer in graph load and settings counts.
6. Update connector ingest to emit normalized `links` or call the normalizer.
7. Add focused tests for links, edges, malformed links, and settings counts.

Validation commands:

```bash
python -m pytest tests/test_graph_schema.py tests/test_settings_counts.py
python -m compileall -q backend
graphify update . --no-cluster
```

Validation completed:

- Passed: `bash scripts/governance-preflight.sh` with 0 warnings.
- Passed: `backend/.venv/bin/python -m pytest` — 9 tests passed.
- Passed: `backend/.venv/bin/python -m compileall -q backend`.
- Passed: `graphify update . --no-cluster` rebuilt `graphify-out/graph.json`
  with 1050 nodes and 15947 edges.
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`; Vite
  still reports the existing large chunk warning.
- Passed after starting local backend/frontend:
  `source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs` — 8 smoke
  checks passed.

Acceptance criteria:

- [x] Graphs with `links` and graphs with `edges` report correct relationship counts.
- [x] Settings no longer reports false zero-edge state for Graphify graphs.
- [x] Connector-created graph data works with core graph routes.
- [x] Existing Command, Ask, Map, Decisions, Recommendations, Work Queue, Settings,
  and AI assistant surfaces still load after the change.

Rollback note: Revert `backend/graph_schema.py` and callers; keep tests if they
document the bug and are marked expected-failing only by owner decision.

Token/context warning: Do not open full generated Graphify outputs; use fixtures.

### Chunk 2: Graph Activation Fix

Status: **task complete** — 2026-06-16T18:01:05-06:00

Completion target: Task complete

Goal: Make Settings activate listed graphs through the backend's real route.

Why this matters: A user must be able to upload, list, and switch graphs without
guessing API paths.

Files to inspect first: `frontend/src/tabs/Settings.tsx`, `backend/main.py`
graph management routes.

Files likely to change: `frontend/src/tabs/Settings.tsx`,
`tests/test_graph_activation.py`, possibly a small backend test fixture.

Exact implementation steps:

1. Confirm backend route `POST /graphs/{name}/activate`.
2. Change Settings activation call from `POST /graphs/{name}` to
   `POST /graphs/{name}/activate`.
3. Refresh list/settings after success.
4. Keep user-visible failure message from backend `detail`.
5. Add backend activation tests for demo and uploaded graph names.

Validation commands:

```bash
python -m pytest tests/test_graph_activation.py
source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck
source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

Validation completed:

- Passed: `bash scripts/governance-preflight.sh` with 0 warnings.
- Passed: `backend/.venv/bin/python -m pytest tests/test_graph_activation.py`
  — 4 tests passed.
- Passed: `backend/.venv/bin/python -m pytest` — 13 tests passed.
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`.
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`; Vite
  still reports the existing large chunk warning.
- Passed: `bash -n launcher/launch-cockpit.sh`.
- Passed after starting with `bash scripts/start.sh`:
  `source "$HOME/.nvm/nvm.sh" && FRONTEND_URL=http://localhost:5173 node scripts/demo-path-smoke.mjs`
  — 8 smoke checks passed. Note: this URL matches the launcher/start script;
  the smoke script default `127.0.0.1:5173` did not reach this Vite session.

Acceptance criteria:

- [x] User can activate a listed graph from Settings.
- [x] Failed activation gives a useful message.
- [x] Existing upload flow still activates uploaded graphs.
- [x] Seven-tab shell still renders after graph activation changes.

Rollback note: One-line frontend route rollback plus test update.

Token/context warning: Do not bundle API-key client work into this chunk.

### Chunk 3: Graphify Runtime Detection and Service Wrapper

Status: **task complete** — 2026-06-16T18:19:44-06:00

Completion target: Task complete

Goal: Make Graphify dependency explicit, testable, and visible.

Why this matters: Ask/Rebuild currently depend on a CLI that Docker does not
install or verify. Missing Graphify should be a readiness warning, not a vague
runtime failure.

Files to inspect first: `backend/main.py` Ask/Rebuild ranges,
`backend/requirements.txt`, `Dockerfile`, `docker-compose.yml`, `README.md`,
`docs/deployment-guide.md`, `docs/runbook.md`.

Files likely to change: `backend/services/graphify_service.py`, `backend/main.py`,
`Dockerfile`, `backend/requirements.txt` only if packaging is accepted,
`README.md`, `docs/deployment-guide.md`, `tests/test_graphify_service.py`.

Exact implementation steps:

1. Add `is_graphify_available`, `get_graphify_version`, `run_graphify_ask`, and
   `run_graphify_update` behind a small service boundary.
2. Return structured errors such as `GRAPHIFY_MISSING` and `GRAPHIFY_TIMEOUT`.
3. Extend `/health`, `/settings`, or a new readiness endpoint with Graphify status.
4. Decide whether Docker installs `graphifyy` or documents demo-only runtime mode.
5. Route Ask/Rebuild through the wrapper.
6. Add tests that monkeypatch missing CLI and command failure behavior.

Validation commands:

```bash
python -m pytest tests/test_graphify_service.py
python -m compileall -q backend
docker compose build backend
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

Validation completed:

- Passed: `bash scripts/governance-preflight.sh` with 0 warnings.
- Passed: `backend/.venv/bin/pip install -r backend/requirements.txt`; installed
  `graphifyy 0.8.40` under the `graphifyy>=0.8.37` requirement.
- Passed: `backend/.venv/bin/python -m pytest tests/test_graphify_service.py`
  — 8 tests passed.
- Passed: `backend/.venv/bin/python -m pytest` — 21 tests passed.
- Passed: `backend/.venv/bin/python -m compileall -q backend`.
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`.
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`; Vite
  still reports the existing large chunk warning.
- Passed: `docker compose build backend`.
- Passed: `bash -n scripts/start.sh && bash -n launcher/launch-cockpit.sh`.
- Passed after starting with `bash scripts/start.sh`:
  `source "$HOME/.nvm/nvm.sh" && API_URL=http://localhost:8000 FRONTEND_URL=http://localhost:5173 node scripts/demo-path-smoke.mjs`
  — 8 smoke checks passed.
- Passed: `graphify update . --no-cluster` rebuilt `graphify-out/graph.json`
  with 1131 nodes and 29146 edges.
- Verified: `curl http://localhost:8000/health` exposed
  `graph_loaded: true` and `graphify.available: true`.
- Verified: `curl http://localhost:8000/settings` exposed Graphify runtime
  status with version information.
- Passed: `graphify update . --no-cluster` rebuilt `graphify-out/graph.json`
  with 1094 nodes and 20691 edges.

Acceptance criteria:

- [x] Ask/Rebuild never expose raw `FileNotFoundError` behavior.
- [x] UI can tell whether Graphify is available.
- [x] Docker/runtime expectation is documented and testable.
- [x] Missing Graphify does not break the rest of the cockpit UI.

Rollback note: Restore direct subprocess calls only if wrapper regressions block
local demo, keeping docs warning in place.

Token/context warning: Avoid backend route splitting here.

### Chunk 4: Frontend API Client and API Key Support

Status: **task complete** — 2026-06-16T18:46:30-06:00

Completion target: Task complete

Goal: Make hosted secure mode usable from the browser UI.

Why this matters: With `API_KEY` set, the backend is protected but the frontend
currently has no shared way to send credentials.

Files to inspect first: `frontend/src/config.ts`, all `fetch(` call sites under
`frontend/src`, `backend/main.py` API-key middleware, `docs/deployment-guide.md`,
`README.md`.

Files likely to change: `frontend/src/api/client.ts`, `frontend/src/config.ts`,
`frontend/src/App.tsx`, `frontend/src/tabs/*.tsx`,
`frontend/src/components/AICopilot.tsx`, `frontend/src/tabs/Settings.tsx`,
docs for hosted setup.

Exact implementation steps:

1. Add `apiFetch(path, options)` that prefixes `API`, reads localStorage key,
   sets `X-API-Key` when present, and avoids JSON content-type for `FormData`.
2. Replace direct frontend `fetch(`${API}...`)` calls with `apiFetch`.
3. Add Settings controls to save, test, and clear the API key locally.
4. Normalize 401/403 user copy to "API key required or invalid."
5. Preserve unauthenticated localhost behavior when backend `API_KEY` is unset.
6. Add lightweight tests if the repo adopts frontend test tooling later; for now
   rely on typecheck/build and manual auth smoke.

Validation commands:

```bash
source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck
source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build
API_KEY=testkey uvicorn backend.main:app --host 127.0.0.1 --port 8000
source "$HOME/.nvm/nvm.sh" && SMOKE_API_KEY=testkey node scripts/demo-path-smoke.mjs
```

Implementation completed:

- Added `frontend/src/api/client.ts` with `apiFetch`, localStorage API-key
  helpers, and shared 401/403 copy.
- Replaced direct frontend backend `fetch` calls with `apiFetch` across App,
  the AI assistant, and all seven tabs.
- Added Settings API controls to save, test, and clear the API key locally.
- Kept upload calls on `FormData` without forcing a JSON content type.
- Updated `scripts/demo-path-smoke.mjs` to accept `SMOKE_API_KEY` or `API_KEY`
  without printing the secret value.
- Updated hosted setup docs in `README.md` and `docs/deployment-guide.md`.

Validation completed:

- Passed: `bash scripts/governance-preflight.sh` with 0 warnings.
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck`.
- Passed: `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build`; Vite
  still reports the existing large chunk warning.
- Passed protected backend check: no-key `GET /settings` returned 401, keyed
  `GET /settings` returned 200 with `api_key_required: true`.
- Passed authenticated smoke:
  `API_URL=http://127.0.0.1:8000 FRONTEND_URL=http://localhost:5173 SMOKE_API_KEY=testkey node scripts/demo-path-smoke.mjs`
  — 8 checks passed.
- Passed unauthenticated local smoke:
  `API_URL=http://127.0.0.1:8000 FRONTEND_URL=http://localhost:5173 node scripts/demo-path-smoke.mjs`
  — 8 checks passed.
- Passed: `graphify update . --no-cluster` rebuilt `graphify-out/graph.json`
  with 1101 nodes and 24121 edges.

Acceptance criteria:

- [x] Hosted frontend can call authenticated backend.
- [x] Uploads still work because multipart boundaries are not broken.
- [x] Unauthorized responses show clear user-facing copy.
- [x] Existing unauthenticated local dev still works when backend `API_KEY` is unset.
- [x] Seven-tab browser smoke passes with the new API client.

Rollback note: Revert to direct fetch only if local UI is blocked; keep backend
auth unchanged.

Token/context warning: This touches many frontend files. Keep changes mechanical
and avoid visual redesign.

### Chunk 5: Graph Upload Hardening

Status: **task complete** — 2026-06-16T19:21:41-06:00

Completion target: Task complete

Goal: Make graph upload safe and schema-aware.

Why this matters: Upload is a trust boundary. Raw filenames and weak validation
are not acceptable for hosted beta.

Files to inspect first: `backend/main.py` upload/list/activate routes,
`backend/graph_schema.py` after Chunk 1, `frontend/src/tabs/Settings.tsx`.

Files likely to change: `backend/main.py`, `backend/graph_schema.py`,
`tests/test_graph_upload.py`, fixtures under `tests/fixtures/`.

Exact implementation steps:

1. Sanitize filename with `Path(file.filename or "").name`.
2. Reject empty names, path traversal, non-`.json`, oversized files, invalid
   JSON, missing nodes, and malformed links.
3. Normalize graph before writing.
4. Write atomically inside `GRAPHS_DIR`.
5. Do not activate invalid graphs.
6. Return safe filename and normalized counts.

Validation commands:

```bash
python -m pytest tests/test_graph_upload.py
python -m compileall -q backend
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

Implementation completed:

- Added upload filename normalization and rejection for empty names, path
  separators, and non-`.json` names.
- Added a 10 MiB upload limit and safe `400` / `413` / `422` error details.
- Extended graph normalization so upload/activation paths can require node IDs,
  unique node IDs, and links that reference known nodes while preserving legacy
  normalization tolerance for existing generated graphs.
- Normalized uploaded graph JSON before writing and returned safe filename,
  node count, and link count.
- Wrote uploaded graph JSON atomically under `GRAPHS_DIR`.
- Validated existing graph files before activation so invalid uploaded files do
  not replace the active graph path.
- Added `tests/test_graph_upload.py` and schema coverage for strict link-target
  validation.

Validation completed:

- Passed: `bash scripts/governance-preflight.sh` with 0 warnings.
- Passed: `backend/.venv/bin/python -m pytest tests/test_graph_upload.py tests/test_graph_schema.py`
  — 17 tests passed.
- Passed: `backend/.venv/bin/python -m pytest` — 33 tests passed.
- Passed: `backend/.venv/bin/python -m compileall -q backend`.
- Passed after starting with `bash scripts/start.sh`:
  `source "$HOME/.nvm/nvm.sh" && API_URL=http://localhost:8000 FRONTEND_URL=http://localhost:5173 node scripts/demo-path-smoke.mjs`
  — 8 smoke checks passed.
- Verified: `curl http://localhost:8000/health` returned `graph_loaded: true`
  and no graph error after preserving compatibility with the existing generated
  graph's duplicate node ID.

Acceptance criteria:

- [x] Valid graph upload succeeds and activates.
- [x] Invalid JSON, missing nodes, malformed links, traversal names, non-json
  names, and oversized files are rejected.
- [x] Upload/activation failures preserve a usable Settings tab error state.

Rollback note: Revert upload route only; do not remove graph schema tests.

Token/context warning: Do not inspect real private graph files.

### Chunk 6: Atomic State Writes and Clean-State Safety

Status: **task complete** — 2026-06-16T19:37:26-06:00

Completion target: Task complete

Goal: Prevent fresh deployments from failing or corrupting local JSON state.

Why this matters: First-run reliability is core beta readiness, and state writes
are scattered across decisions, recommendations, actions, settings, sessions,
connectors, chat, semantic edges, and overlap statuses.

Files to inspect first: `backend/main.py` write helpers and all `write_text` /
`write_bytes` call sites, `backend/connectors/*.py`.

Files likely to change: `backend/state_store.py`, `backend/main.py`,
`backend/connectors/ingest.py`, `backend/connectors/microsoft_auth.py`,
`tests/test_clean_state.py`.

Exact implementation steps:

1. Add `write_json_atomic(path, payload)` that creates parents, writes a temp
   file, then replaces.
2. Add `write_bytes_atomic` only if needed for upload.
3. Convert local JSON state writes to the helper.
4. Keep best-effort device tracking non-fatal.
5. Test with a temporary empty state directory.

Validation commands:

```bash
python -m pytest tests/test_clean_state.py
python -m compileall -q backend
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

Implementation completed:

- Added `backend/state_store.py` with atomic same-directory JSON replacement and
  parent directory creation.
- Converted local JSON writes in `backend/main.py`,
  `backend/connectors/ingest.py`, and `backend/connectors/microsoft_auth.py` to
  the helper. Non-JSON approved action note creation remains a direct text
  write because it is user content, not JSON state.
- Added `tests/test_clean_state.py` covering a missing state directory for graph
  upload/settings, decisions/device tracking, recommendations, actions, cluster
  selection, scan dirs, overlap status, semantic edges, connector sync status,
  Ask transcript storage, and chat config.
- No `write_bytes_atomic` was added; upload hardening stores normalized graph
  JSON through the shared atomic JSON helper.

Validation completed:

- Passed: `bash scripts/governance-preflight.sh` with 0 warnings.
- Passed: `backend/.venv/bin/python -m pytest tests/test_clean_state.py` — 2 tests passed.
- Passed: `backend/.venv/bin/python -m pytest` — 35 tests passed.
- Passed: `backend/.venv/bin/python -m compileall -q backend`.
- Passed after starting with `bash scripts/start.sh`:
  `source "$HOME/.nvm/nvm.sh" && API_URL=http://localhost:8000 FRONTEND_URL=http://localhost:5173 node scripts/demo-path-smoke.mjs`
  — 8 smoke checks passed.

Acceptance criteria:

- [x] Fresh empty state directory can write settings, decisions, recommendations,
  actions, missions if applicable, overlap status, semantic edges, scan dirs, and chat config.
- [x] JSON writes are atomic for local file backend.
- [x] Existing local demo state can still be read after the helper conversion.

Rollback note: Restore specific caller writes only if helper introduces a
regression; keep parent-directory creation fixes.

Token/context warning: This is broad inside `backend/main.py`; use `rg write_text`
and edit callers in batches with tests.

### Chunk 7: Caddy and Deployment Routing Fix

Status: **task complete** — 2026-06-16T20:49:51-06:00

Completion target: Task complete

Goal: Make hosted `/api/*` routing reliable.

Why this matters: Hosted frontend can appear healthy while backend API requests
are served by the SPA catch-all.

Files to inspect first: `config/Caddyfile`, `docker-compose.yml`,
`Dockerfile.frontend`, `config/nginx.conf`, `docs/deployment-guide.md`,
`README.md`.

Files likely to change: `config/Caddyfile`, `docs/deployment-guide.md`,
`README.md`, `scripts/demo-path-smoke.mjs` only if adding API-prefix smoke.

Exact implementation steps:

1. Move `handle /api/*` before frontend `handle`.
2. Strip `/api` before proxying to backend.
3. Align docs so `VITE_API_URL=/api` or hosted absolute API URL guidance is not contradictory.
4. Add smoke instructions for `GET /api/health` and `GET /`.

Validation commands:

```bash
docker compose --profile https config
docker compose build frontend backend
```

Implementation completed:

- Moved the Caddy `/api/*` handler above the frontend catch-all and kept
  `uri strip_prefix /api` before proxying to `backend:8000`.
- Updated README and deployment guidance to recommend `VITE_API_URL=/api` for
  same-origin Caddy deployments, while keeping absolute backend URLs for
  separated frontend/API deployments.
- Added hosted Caddy route smoke instructions to the deployment guide, runbook,
  and demo path checklist.

Validation completed:

- Passed: `bash scripts/governance-preflight.sh` with 0 warnings.
- Passed: `docker compose --profile https config`.
- Passed: `docker compose build frontend backend`; frontend build still reports
  the existing npm audit advisory count during `npm ci`.
- Passed: isolated Caddy route smoke with the built backend/frontend images and
  `config/Caddyfile`: `GET /api/health` reached backend JSON and `GET /`
  returned frontend HTML.
- Passed: `git diff --check`.
- Passed: `graphify update . --no-cluster` rebuilt `graphify-out/graph.json`
  with 1131 nodes and 30946 edges.

Acceptance criteria:

- [x] `GET /api/health` routes to backend JSON.
- [x] `GET /` routes to frontend.
- [x] Deployment docs match actual Caddy behavior.
- [x] Runbook and demo checklist describe the hosted API-prefix smoke.

Rollback note: Revert Caddyfile and docs if hosted profile is not used, but keep
the issue documented.

Token/context warning: Do not change unrelated nginx or Docker behavior.

### Chunk 8: Minimum Backend Test Suite

Goal: Add enough tests that release-critical paths cannot silently regress.

Why this matters: Focused tests now exist from Chunks 1-6, but the hosted beta
still needs remaining backend contract coverage and CI expansion so regressions
cannot silently pass.

Files to inspect first: `backend/main.py`, `backend/requirements.txt`, any local
test guidance in docs, existing CI workflow.

Files likely to change: `backend/requirements.txt` or a dev requirements file,
`tests/conftest.py`, `tests/fixtures/*.json`, `tests/test_graph_schema.py`,
`tests/test_settings_counts.py`, `tests/test_graph_upload.py`,
`tests/test_graph_activation.py`, `tests/test_api_key_auth.py`,
`tests/test_clean_state.py`, `.github/workflows/ci.yml`.

Exact implementation steps:

1. Add pytest dependency through the least disruptive dependency path.
2. Add fixtures for links graph, edges graph, malformed graph.
3. Use FastAPI `TestClient` with temporary env/state isolation.
4. Cover schema, settings counts, upload, activation, API-key middleware, and
   clean-state writes.
5. Expand CI to run backend `pytest`.
6. Add frontend production build to CI, not only TypeScript typecheck.

Validation commands:

```bash
python -m pytest
python -m compileall -q backend
source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build
```

Acceptance criteria:

- `python -m pytest` passes locally.
- Tests cover all P0 backend contracts named in this plan.
- CI runs backend pytest and frontend production build.

Rollback note: Keep fixtures and tests if possible; remove only CI wiring if it
blocks unrelated work.

Token/context warning: Do not overbuild test harness abstractions.

### Chunk 9: Supabase Schema Alignment

Goal: Prevent Supabase mode from pretending to be ready when migrations are stale.

Why this matters: Current recommendation/action records use fields not present in
the initial migration.

Files to inspect first: `db/migrations/001_initial.sql`, Supabase persistence
ranges in `backend/main.py`, `docs/integration-guide.md`,
`docs/deployment-guide.md`, `docs/runbook.md`.

Files likely to change: `db/migrations/002_recommendation_action_plans.sql`,
`backend/main.py` only for schema-version readiness, docs listed above,
`tests/test_supabase_schema_contract.py` if practical without live Supabase.

Exact implementation steps:

1. Add migration columns:
   `recommendations.action_plan`, `recommendations.overlap`,
   `recommendations.overlap_dossier`, and `actions.action_plan` as JSONB.
2. Document migration order and Supabase mode limitation.
3. Add runtime readiness warning if `STORAGE_BACKEND=supabase` cannot verify required shape.
4. If verification is not practical, clearly mark Supabase mode as not hosted-beta-ready until migration is applied.

Validation commands:

```bash
python -m compileall -q backend
```

Acceptance criteria:

- Supabase docs match actual record shapes.
- Supabase mode either works with the new migration or visibly reports a schema gap.
- Any live migration remains separately owner-approved.

Rollback note: Database migration rollback requires owner review; do not remove
columns once applied unless explicitly approved.

Token/context warning: Do not run live Supabase commands without owner approval.

### Chunk 10: Workspace Readiness Panel

Goal: Make first-use runtime state obvious.

Why this matters: A beta user should know what works, what is missing, and what
to do next without debugging ports, CLIs, or optional services.

Files to inspect first: `frontend/src/tabs/Dashboard.tsx`,
`frontend/src/tabs/Settings.tsx`, `backend/main.py` health/settings/status ranges,
Graphify service after Chunk 3, graph schema after Chunk 1.

Files likely to change: `backend/main.py` or `backend/routes/runtime.py`,
`frontend/src/tabs/Dashboard.tsx`, `frontend/src/styles.css`,
`tests/test_runtime_status.py`.

Exact implementation steps:

1. Add `GET /runtime/status` or extend a current status endpoint.
2. Include backend online, Graphify available, Ollama available, active graph
   validity, node/link counts, auth required, connector status, warnings, and
   next best action.
3. Render compact readiness state at top of Command Center.
4. Link warnings to Settings actions where possible.

Validation commands:

```bash
python -m pytest tests/test_runtime_status.py
source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck
source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

Acceptance criteria:

- New user can immediately tell whether workspace is Ready, Partial, or Not Ready.
- Missing Graphify/Ollama/auth/graph issues are visible and actionable.
- The readiness panel does not displace or obscure existing Command Center
  attention cards.

Rollback note: Remove panel and endpoint if noisy; keep Graphify status in health.

Token/context warning: Avoid broad dashboard redesign.

### Chunk 11: Connector Graph Normalization

Goal: Make connector data compatible with local Graphify graph data.

Why this matters: Cloud connector ingest currently uses an internal `edges`
shape and `label` relation, which can drift from Graphify `links`.

Files to inspect first: `backend/connectors/ingest.py`,
`backend/connectors/base.py`, `backend/connectors/sharepoint.py`,
`backend/connectors/onenote.py`, graph schema helper after Chunk 1.

Files likely to change: connector files above, `tests/test_connector_ingest.py`.

Exact implementation steps:

1. Define connector node and link contracts in one helper or docstring.
2. Emit `links` with `relation`, `source`, `target`, and `weight`.
3. Normalize existing graph before merge.
4. Write merged graph atomically.
5. Test term-overlap merge against small fixtures.

Validation commands:

```bash
python -m pytest tests/test_connector_ingest.py
python -m compileall -q backend
graphify update . --no-cluster
```

Acceptance criteria:

- Connector-created relationships appear in graph counts.
- Connector nodes remain grouped/labeled correctly in UI.

Rollback note: Connector-only rollback should not affect local demo graph routes.

Token/context warning: Do not initiate Microsoft auth or external connector syncs.

### Chunk 12: Token-Saving Repo Cleanup and Agent Docs

Goal: Make the repo easier and cheaper for future AI coding agents to inspect.

Why this matters: Large generated output and missing file summaries increase
context risk and make future changes slower.

Files to inspect first: `.gitignore`, `AGENTS.md`, `docs/context-map.md`,
`docs/architecture.md`, top-level file list.

Files likely to change: `.gitignore`, `AGENT_QUICKSTART.md`,
`docs/ARCHITECTURE_MAP.md`, `docs/FILE_SUMMARIES.md`, `docs/KNOWN_ISSUES.md`,
small fixtures under `tests/fixtures/`, `docs/context-map.md`, `START_HERE.md`.

Exact implementation steps:

1. Confirm generated directories are ignored: `graphify-out/`, caches,
   `node_modules/`, `dist/`, `build/`, `.venv/`, `__pycache__/`, `*.pyc`.
2. Add concise architecture and file-summary docs that point agents to source
   files without reading generated outputs.
3. Add known-issues doc linked to this stabilization plan.
4. Keep docs summary-only and under context-friendly size.

Validation commands:

```bash
git status --short
git diff --check
```

Acceptance criteria:

- A future agent can orient without reading generated graph/cache files.
- Existing context map remains accurate.
- `START_HERE.md` points to this plan and identifies
  `docs/current-build-pathway.md` as an archive.

Rollback note: Documentation-only rollback is safe.

Token/context warning: Do not duplicate long existing docs.

### Chunk 13: Backend Module Split Plan

Goal: Reduce `backend/main.py` complexity after tests exist.

Why this matters: `backend/main.py` is over 3,000 lines, making risk-sensitive
fixes harder to review. But a split before contract tests would be reckless.

Files to inspect first: passing backend tests, `backend/main.py` route index,
new helper modules from earlier chunks.

Files likely to change: `backend/app.py`, `backend/config.py`, `backend/auth.py`,
`backend/graph_schema.py`, `backend/state_store.py`, `backend/services/*`,
`backend/routes/*`, `backend/main.py`.

Exact implementation steps:

1. Freeze behavior with tests.
2. Move config/auth/state/schema/service code first.
3. Move routes by bounded area: health, graph, ask, settings, recommendations,
   actions, missions, connectors, chat.
4. Keep `backend.main:app` import-compatible.
5. Run full tests after each move group.
6. Do not hide feature changes in the module split.

Validation commands:

```bash
python -m pytest
python -m compileall -q backend
curl http://127.0.0.1:8000/health
```

Acceptance criteria:

- Routes behave the same after move.
- Tests pass before and after split.
- `uvicorn backend.main:app` still works.

Rollback note: Move-only refactor must be easy to revert as one PR.

Token/context warning: Large refactor. Do only after chunks 1-10 are stable.

## 6. Validation Matrix

| Area | Command/Test | Expected Result |
|---|---|---|
| Governance | `bash scripts/governance-preflight.sh` | 0 warnings or accepted gaps |
| Python syntax | `python -m compileall -q backend` | No errors |
| Backend tests | `python -m pytest` | All tests pass |
| Frontend typecheck | `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run typecheck` | No TypeScript errors |
| Frontend build | `source "$HOME/.nvm/nvm.sh" && cd frontend && npm run build` | Build succeeds |
| CI | `.github/workflows/ci.yml` | Backend pytest and frontend production build run once tests exist |
| Graph schema | `pytest tests/test_graph_schema.py` | Links/edges normalize correctly |
| Upload safety | `pytest tests/test_graph_upload.py` | Unsafe uploads rejected |
| API auth | `pytest tests/test_api_key_auth.py` | Auth works as expected |
| Clean state | `pytest tests/test_clean_state.py` | Empty state writes succeed |
| Repo graph refresh | `graphify update . --no-cluster` | Local graph rebuild succeeds after code changes, or skipped reason is recorded |
| Demo smoke | `source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs` | Core demo path still responds |
| Manual demo checklist | `docs/demo-path-checklist.md` | Seven-tab workflow remains usable after UI-facing chunks |
| Docker backend | `docker compose build backend` | Build succeeds |
| Hosted routing | `GET /api/health` through Caddy | Backend JSON response |

## 7. Suggested Branch / PR Sequence

1. PR 1: Baseline and test skeleton.
2. PR 2: Graph schema normalization.
3. PR 3: Graph activation fix and upload hardening.
4. PR 4: Graphify runtime service.
5. PR 5: Frontend API client and API-key support.
6. PR 6: Atomic state writes and clean-state safety.
7. PR 7: CI expansion once backend tests exist.
8. PR 8: Caddy and deployment routing fixes.
9. PR 9: Readiness panel.
10. PR 10: Supabase schema alignment.
11. PR 11: Connector normalization.
12. PR 12: Agent docs and repo cleanup.
13. PR 13: Backend module split.

## 8. Definition of Beta-Ready

- Fresh clone has documented, repeatable setup.
- Frontend build succeeds.
- Backend imports and starts.
- Demo graph reports correct node/link counts.
- Ask works or clearly explains Graphify is missing.
- Hosted frontend works with backend API key enabled.
- Upload cannot escape graph directory.
- Invalid graph files are rejected.
- Empty state directory does not 500 on first writes.
- Caddy routes `/api/*` to backend and `/` to frontend.
- Supabase mode either works with current schema or is clearly marked not ready.
- Minimum backend tests pass.
- CI runs backend tests and frontend production build.
- Demo smoke and relevant manual checklist pass after UI-facing chunks.
- README and deployment docs match actual behavior.
- Runbook, changelog, risk register, and context map reflect the stabilization path.
- Generated graph/cache files are not needed for normal inspection.
- Future agents have architecture and file-summary docs.

## 9. Do-Not-Touch List

- Large generated graph files.
- `graphify-out/cache/`.
- `frontend/node_modules/`.
- `frontend/dist/` except by build command.
- Branding and unrelated visual styling.
- Package upgrades unrelated to release blockers.
- Backend module split before tests exist.
- Live Supabase project commands without owner approval.
- Microsoft connector auth/sync during local planning unless a connector chunk
  explicitly calls for it.

## 10. Final Implementation Notes

Start with Chunk 1 unless Adam wants a pure test-skeleton pass first. The highest
leverage sequence is schema normalization, activation/upload fixes, Graphify
runtime status, API-key frontend support, then state/deployment hardening.

Treat hosted beta as a release-readiness path, not a feature sprint. Each chunk
should leave the local demo working, update validation evidence, and stop before
the next risk surface.
