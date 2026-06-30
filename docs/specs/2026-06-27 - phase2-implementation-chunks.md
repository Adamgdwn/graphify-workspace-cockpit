# Graphify Phase 2 — Implementation Chunk Plan

**Date:** 2026-06-27
**Status:** Historical Phase 2 implementation plan — completed/superseded for active planning
**Parent spec:** `docs/specs/2026-06-27 - phase2-cns-connectome-design.md`
**Loop discipline:** read → execute → update docs → hardness test → commit → compact → 10s pause → next chunk

> 2026-06-29 supersession note: this file is retained as Phase 2 execution
> history. Active Graphify CNS/API/store/speed planning lives in
> `docs/2026-06-29 - Graphify Quantum Speed Execution Plan.md`.

---

## Chunk P0 — Commit Pending Documentation Changes

**Goal:** Close out the previous session's work: spec augmentation + 17 doc renames + cross-reference updates.

**Files:**
- All staged renames in `docs/` (17 files, `R` status)
- Modified: `README.md`, `START_HERE.md`, `docs/context-map.md`, `docs/ARCHITECTURE_MAP.md`, `docs/CHANGELOG.md`, and ~10 more cross-reference files
- Modified: `docs/specs/2026-06-27 - phase2-cns-connectome-design.md`

**Hardness test:**
- `git status` shows clean after commit
- `grep -r 'docs/roadmap.md\|docs/vision.md\|docs/architecture.md' --include='*.md' .` returns nothing

**Definition of done:** One commit with all pending doc changes, clean working tree.

---

## Chunk 2.1 — SQLite Store: Schema + Connection Layer

**Goal:** Create the CNS store foundation. Define the entity, relationship, metadata, and
embedding-reserved tables. Wire up connection management and schema initialization.

**Architecture note:** This lives in a new `cns_store/` top-level module (sibling of `backend/`).
It is a shared library consumed by both the cockpit backend and the Phase 2 CNS API service.
No API surface in this chunk — pure data layer.

**Files to create:**
- `cns_store/__init__.py`
- `cns_store/schema.py` — table definitions as typed dataclasses + SQL DDL strings
- `cns_store/db.py` — `get_connection()`, `init_db()`, path from env var `CNS_STORE_PATH`
- `tests/test_cns_store.py` — schema creation, table existence, roundtrip insert/query

**Schema shape (locked by spec decision 1):**
```
entities(id TEXT PK, label TEXT, kind TEXT, repo TEXT, path TEXT, cluster TEXT,
         importance_tier TEXT, metadata_json TEXT, created_at TEXT, updated_at TEXT)

relationships(id TEXT PK, source_id TEXT FK, target_id TEXT FK, kind TEXT,
              weight REAL, metadata_json TEXT, created_at TEXT)

store_metadata(key TEXT PK, value TEXT, updated_at TEXT)

entity_embeddings(entity_id TEXT PK FK, embedding_blob BLOB, model TEXT,
                  created_at TEXT)   -- reserved; not populated in Phase 2
```

**Indexes (for speed SLA):**
- `entities(kind)`, `entities(repo)`, `entities(label)`
- `relationships(source_id)`, `relationships(target_id)`, `relationships(kind)`

**Hardness test:**
- `pytest tests/test_cns_store.py -v` — all pass
- `python -m compileall cns_store` — clean
- Manually verify: `python -c "from cns_store.db import init_db; init_db('/tmp/test.db')"` succeeds

**Definition of done:** `cns_store` module importable, schema initializes clean SQLite DB,
tests pass.

---

## Chunk 2.2 — JSON Graph Importer

**Goal:** Import an existing Graphify `graph.json` into the SQLite store. This is the
bootstrap path — new deployments and CI tests use this to seed from the current JSON graph.
JSON output is NOT removed; it stays as a human-readable snapshot.

**Files to create:**
- `cns_store/importer.py` — `import_graph(graph_json_path, db_path)` function
- `tests/fixtures/mini_graph.json` — small test fixture (10 entities, 15 relationships)
- `tests/test_cns_store_importer.py` — import fixture, verify entity/relationship counts,
  verify a known entity is queryable

**Import logic:**
- Read `nodes` array → `entities` table (map Graphify fields to schema columns)
- Read `links` array → `relationships` table
- Write `store_metadata` key `imported_from`, `imported_at`, `node_count`, `link_count`
- Idempotent: re-import clears and replaces (not append)
- Logs import summary to stdout

**Hardness test:**
- `pytest tests/test_cns_store_importer.py -v` — all pass
- `python -m compileall cns_store` — clean
- Smoke: import the real workspace graph and verify entity count matches node count in JSON

**Definition of done:** `import_graph()` successfully loads any valid Graphify JSON graph
into SQLite, idempotent, tests pass.

---

## Chunk 2.3 — Query Layer (6 CNS Query Patterns)

**Goal:** Implement the six query patterns that GAIL OS and Freedom need at decision time.
Each query must hit the correct SQLite indexes and stay within the speed SLA.

**Files to create:**
- `cns_store/queries.py` — one function per query pattern
- `tests/test_cns_store_queries.py` — one test class per query, fixture uses mini_graph

**The six query patterns:**

*GAIL OS queries:*
1. `validate_connector(connector_id, domain, db_path) → ConnectorValidation`
   > "Is connector [id] registered and active for domain [domain]?"
2. `entity_neighborhood(entity_id, db_path, depth=1) → NeighborhoodResult`
   > "What entities are adjacent to action target [entity_id]?"
3. `authority_chain(connector_id, db_path) → AuthorityChain`
   > "What authority chain produced the R-level for this connector?"

*Freedom queries:*
4. `entity_context(entity_id, db_path) → EntityContext`
   > "What do I know about [entity]? What is it connected to?"
5. `recent_mission_context(entity_id, db_path, limit=10) → MissionHistory`
   > "Has a mission targeting [entity] been attempted recently?"
6. `domain_mapping(entity_id, db_path) → DomainInfo`
   > "Which domain does [entity] belong to? Who governs it?"

**Return types:** typed dataclasses in `cns_store/models.py` (create this file too).

**Hardness test:**
- `pytest tests/test_cns_store_queries.py -v` — all pass
- Timing check: run query 1 and 4 against the real workspace graph 100× and assert p95 < 100ms
- `python -m compileall cns_store` — clean

**Definition of done:** All 6 query functions implemented, typed, tested. Speed SLA
verified against real graph size.

---

## Chunk 2.4 — CNS API Service: FastAPI Skeleton + Health

**Goal:** Create the standalone CNS query API service — a separate FastAPI app from the
cockpit backend. Cloud-first: env-var configured, no local path assumptions in the API layer.

**Architecture:** `cns_api/` is a sibling to `backend/`. It imports from `cns_store/`.
Runs on port 8001 (cockpit backend stays on 8000).

**Files to create:**
- `cns_api/__init__.py`
- `cns_api/config.py` — reads from env: `CNS_STORE_PATH`, `CNS_API_PORT`, `CNS_API_KEY` (optional)
- `cns_api/app.py` — FastAPI app factory
- `cns_api/main.py` — uvicorn entry point
- `cns_api/routes/__init__.py`
- `cns_api/routes/health.py` — `GET /health` → `{"status": "ok", "store": "connected|missing", "node_count": N}`
- `Dockerfile.cns-api` — containerized, `CNS_STORE_PATH` via env, no local paths baked in
- `tests/test_cns_api_health.py` — health endpoint returns 200, store status reflects init state

**Requirements:** FastAPI, uvicorn — add to new `cns_api/requirements.txt`

**Hardness test:**
- `CNS_STORE_PATH=/tmp/test.db uvicorn cns_api.main:app --port 8001` starts clean
- `curl http://localhost:8001/health` returns `{"status": "ok"}`
- `pytest tests/test_cns_api_health.py -v` — all pass
- `docker build -f Dockerfile.cns-api .` succeeds

**Definition of done:** CNS API service starts, health endpoint works, containerized.

---

## Chunk 2.5 — GAIL OS Query Endpoints (3 endpoints)

**Goal:** Wire the three GAIL OS query functions from Chunk 2.3 into HTTP endpoints on the
CNS API service.

**Files to create/modify:**
- `cns_api/routes/gail_os.py` — 3 endpoint handlers
- `cns_api/app.py` — register GAIL OS router
- `tests/test_cns_api_gail_os.py` — contract tests for all 3 endpoints

**Endpoints:**
```
GET /api/cns/connector/{connector_id}/validate?domain={domain}
→ 200 ConnectorValidation | 404 not found

GET /api/cns/entity/{entity_id}/neighborhood?depth={1}
→ 200 NeighborhoodResult | 404 not found

GET /api/cns/connector/{connector_id}/authority-chain
→ 200 AuthorityChain | 404 not found
```

**Contract requirements:**
- All responses are JSON with typed fields (Pydantic models)
- 404 when entity/connector not found in store
- No write path — all GET, read-only
- Response time target: < 100ms (verified by hardness test)

**Hardness test:**
- `pytest tests/test_cns_api_gail_os.py -v` — all pass
- Timing: all 3 endpoints respond < 100ms against real workspace graph
- `curl` smoke against running service for each endpoint

**Definition of done:** 3 GAIL OS endpoints live, tested, typed, < 100ms.

---

## Chunk 2.6 — Freedom Query Endpoints (3 endpoints)

**Goal:** Wire the three Freedom query functions from Chunk 2.3 into HTTP endpoints.

**Files to create/modify:**
- `cns_api/routes/freedom.py` — 3 endpoint handlers
- `cns_api/app.py` — register Freedom router
- `tests/test_cns_api_freedom.py` — contract tests for all 3 endpoints

**Endpoints:**
```
GET /api/cns/entity/{entity_id}/context
→ 200 EntityContext | 404 not found

GET /api/cns/entity/{entity_id}/mission-history?limit={10}
→ 200 MissionHistory (may be empty list, never 404)

GET /api/cns/entity/{entity_id}/domain
→ 200 DomainInfo | 404 not found
```

**Contract requirements:** Same as Chunk 2.5. All JSON, Pydantic-typed, read-only.

**Hardness test:**
- `pytest tests/test_cns_api_freedom.py -v` — all pass
- `curl` smoke for each endpoint
- Mission-history endpoint handles empty history gracefully (200 + empty list)

**Definition of done:** 3 Freedom endpoints live, tested, typed. All 6 CNS endpoints now
accessible on the running service.

---

## Chunk 2.7 — Extraction Write Path + On-Demand Trigger

**Goal:** Close the write loop. The CNS API can now trigger an extraction run that updates
the SQLite store. On-demand only (no file-watcher per spec decision 2).

**Files to create/modify:**
- `cns_store/ingest.py` — `run_extraction(source_path, db_path)`: runs `graphify update`,
  reads resulting JSON, calls `import_graph()`
- `cns_api/routes/admin.py` — `POST /api/cns/admin/ingest` → triggers extraction async,
  returns job ID; `GET /api/cns/admin/ingest/{job_id}` → status
- `cns_api/app.py` — register admin router
- `tests/test_cns_store_ingest.py` — unit tests for ingest with mock graphify subprocess
- `tests/test_cns_api_admin.py` — contract tests for trigger + status endpoints

**Security note:** `/api/cns/admin/*` requires `CNS_API_KEY` header if key is configured.
This is the only write-path-adjacent surface in Phase 2.

**Hardness test:**
- `pytest tests/test_cns_store_ingest.py tests/test_cns_api_admin.py -v` — all pass
- Smoke: `POST /api/cns/admin/ingest` with real workspace path → SQLite updated
- Verify store `node_count` increases after extraction on a real repo
- Verify no file-watcher process is started (resource conservation)

**Definition of done:** On-demand extraction trigger works end-to-end. Store is updatable
without restarting the service.

---

## Chunk 2.8 — Performance Validation + BLK-002 Close

**Goal:** Verify all speed SLAs against the real workspace graph. Document results. Close
BLK-002 (Graphify not externally callable) with evidence.

**Files to create:**
- `scripts/cns_benchmark.py` — benchmark script: imports real graph, runs all 6 query types
  100× each, reports p50/p95/p99
- `docs/specs/2026-06-27 - phase2-cns-connectome-design.md` — update: add benchmark results
  section under the speed contract

**SLAs to verify (from spec):**
- Single relationship query: p95 < 100ms
- Neighborhood traversal: p95 < 250ms
- (Semantic query is Phase 3 — stub only)

**BLK-002 evidence:**
- Run `curl http://localhost:8001/api/cns/entity/{id}/context` from a separate machine or
  process to confirm the service is externally callable
- Record the response in benchmark output

**Hardness test:**
- All benchmark assertions pass
- BLK-002 marked resolved in `docs/2026-06-15 - roadmap.md` and `docs/context-map.md`
- `pytest tests/ -v` — full test suite still green after benchmark additions

**Definition of done:** All speed SLAs verified. BLK-002 closed with evidence. Spec updated
with real numbers.

---

## Chunk 2.9 — Cloud-Readiness Hardening

**Goal:** Make the CNS API service deployable to cloud from the start. No hardcoded local
paths in the API layer. Docker Compose entry. SQLite migration path documented.

**Files to create/modify:**
- `docker-compose.yml` — add `cns-api` service: `Dockerfile.cns-api`, port 8001,
  `CNS_STORE_PATH` from env file
- `cns_api/config.py` — verify: all paths, ports, and keys come from env vars, no defaults
  that assume Linux local paths
- `docs/specs/2026-06-27 - phase2-cns-connectome-design.md` — add cloud deployment section:
  env-var reference table, SQLite → Turso migration path, container build instructions
- `README.md` — add CNS API section: how to start, how to configure, what endpoints exist

**Hardness test:**
- `docker compose build cns-api` succeeds
- `docker compose up cns-api` with `CNS_STORE_PATH=/data/cns.db` (volume-mounted) →
  health endpoint responds
- `grep -r '/home/adamgoodwin\|localhost\|127.0.0.1' cns_api/` returns nothing
  (no hardcoded local paths in the API layer)
- `pytest tests/ -v` — full suite green

**Definition of done:** Service is containerized, fully env-var configured, no local path
assumptions, documented. Phase 2 is integration complete.

---

## Sequence Summary

| Chunk | Goal | Key Output | Gate |
|-------|------|-----------|------|
| P0 | Commit docs | Clean working tree | git status |
| 2.1 | SQLite schema | `cns_store/` module | pytest, compileall |
| 2.2 | JSON importer | `cns_store/importer.py` | pytest, real graph smoke |
| 2.3 | Query layer | `cns_store/queries.py` | pytest, timing check |
| 2.4 | API skeleton | `cns_api/` service | health endpoint, docker build |
| 2.5 | GAIL OS endpoints | 3 GET endpoints | pytest, < 100ms |
| 2.6 | Freedom endpoints | 3 GET endpoints | pytest, curl smoke |
| 2.7 | Write path | ingest trigger | pytest, real smoke |
| 2.8 | Perf validation | Benchmark results | SLAs pass, BLK-002 closed |
| 2.9 | Cloud hardening | Docker compose | build passes, no local paths |

---

*Plan status: Written 2026-06-27. Loop execution begins at Chunk P0.*
