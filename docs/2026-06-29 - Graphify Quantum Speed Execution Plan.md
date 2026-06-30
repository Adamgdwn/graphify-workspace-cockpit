# Graphify Quantum Speed Execution Plan

Date: 2026-06-29
Status: active plan for Graphify function acceleration
Owner: Adam Goodwin
Completion target: Draft complete

## Purpose

This is the context-window-friendly execution plan for making Graphify the
fastest possible relationship-transfer layer in the CNS.

Start here for Graphify CNS work that touches the API, store, learning loop,
Speed SLA, Freedom/GAIL OS integration, GraphFact ingestion, or authority
boundary. Use `docs/relationship-map-plan.md` only for Map/UI product work.

## Read Order

1. `AGENTS.md`
2. `START_HERE.md`
3. `docs/specs/2026-06-29 - Graphify Function Boundary And Speed Doctrine.md`
4. This file
5. The chunk-specific files named below

Avoid historical plans unless a chunk explicitly calls for them.

## Discovery Summary

GitHub inspection on 2026-06-29 found:

- `main` has four merged PRs and no open issues.
- The current execution surface is `cns_store/`, `cns_api/`, and the benchmark
  script `scripts/cns_benchmark.py`.
- Hot reads are concentrated in `cns_store/queries.py` and
  `cns_api/routes/{freedom,gail_os}.py`.
- Store-internal writes are split across evidence, OKP, charter, stale-claim,
  admin ingest, and GraphFact importer modules.
- The current docs contain stale pre-implementation wording about all endpoints
  being read-only, EvidencePacket feedback being the first write path, and the
  GraphFact importer being future scope.
- Governance preflight currently fails because required canonical docs are
  named with date-prefixed filenames while the script expects undated aliases.

## Operating Thesis

Graphify should behave like a relationship bus with memory:

```text
facts in -> relationship memory -> bounded context packets out
```

The hot path must not carry the whole graph, extraction work, or authority
decisions. It should carry the smallest useful relationship packet with enough
provenance for Freedom or GAIL OS to decide what to inspect next.

## Chunk GQ-0 - Planning Reset

Status: task complete on 2026-06-29
Target state: Task complete

Goal: land the boundary doctrine and active execution plan, then route future
Graphify CNS work away from stale Phase 2/Phase 3 assumptions.

Files:

- `docs/specs/2026-06-29 - Graphify Function Boundary And Speed Doctrine.md`
- `docs/2026-06-29 - Graphify Quantum Speed Execution Plan.md`
- `AGENTS.md`
- `START_HERE.md`
- `AGENT_QUICKSTART.md`
- `docs/context-map.md`
- stale spec supersession notes
- `docs/CHANGELOG.md`
- `docs/risks/risk-register.md`

Done when:

- new doctrine and execution plan exist
- startup routes point here for Graphify CNS/API/store work
- stale docs are marked as historical or superseded where they conflict
- validation and governance caveats are recorded

Validation:

- `bash scripts/governance-preflight.sh`
- `git diff --check`
- targeted `rg` for stale active-plan wording

Stop condition:

- stop before code implementation beyond planning/routing docs

## Chunk GQ-1 - Contract Alignment Cleanup

Status: queued
Target state: Task complete
Budget: small

Goal: make the implemented API/store surface and docs agree.

Context to load:

- `docs/specs/2026-06-29 - Graphify Function Boundary And Speed Doctrine.md`
- `docs/specs/2026-06-28 - Graphify CNS Connectome Contract.md`
- `docs/specs/2026-06-28 - Graphify Endpoint Family Map.md`
- `docs/specs/2026-06-28 - GAIL Graph Fact Import Boundary.md`
- `cns_api/app.py`
- `cns_api/routes/`
- `cns_store/gail_os_fact_importer.py`

Likely changes:

- replace stale "all endpoints are GET" language with read-plane/write-lane
  language
- make the approved lane table match code
- state that the GraphFact importer exists but remains extraction-only
- add a small docs-contract check if practical

Done when:

- no active doc says Graphify has zero write lanes
- no active doc says EvidencePacket feedback is still the first write path
- endpoint docs distinguish hot reads from guarded store-internal writes

Validation:

- `rg -n "all endpoints|first write path|future scope|No POST|read-only" docs AGENTS.md START_HERE.md`
- focused tests if code comments or contract checks change

Stop condition:

- stop before adding or changing endpoint behavior

## Chunk GQ-2 - Hot Context Packet API

Status: queued
Target state: Draft complete or Task complete
Budget: medium

Goal: add a bounded context-packet read path so Freedom can ask one sharp
question and receive one sharp answer.

Context to load:

- doctrine doc
- `cns_store/queries.py`
- `cns_store/models.py`
- `cns_api/routes/freedom.py`
- `tests/test_cns_store_queries.py`
- `tests/test_cns_api_freedom.py`

Proposed shape:

```text
GET /api/cns/entity/{entity_id}/brief?profile=freedom&max_neighbors=12
```

Packet fields:

- entity identity
- domain / authority hint
- top relationships by weight and kind
- recent mission/evidence refs
- source refs where present
- freshness/degraded flags
- next query hints

Rules:

- no LLM call
- no extraction
- max neighbor cap required
- p95 target below 25ms local on the current benchmark graph
- response byte budget documented before merge

Validation:

- unit tests for cap, ordering, missing entity, malformed metadata, and source
  refs
- API tests for response shape and query bounds
- benchmark check added or updated for the brief path

Stop condition:

- if the brief needs semantic embeddings to be useful, split semantic ranking
  into a later chunk and keep GQ-2 structural only

## Chunk GQ-3 - Speed Envelope Guardrails

Status: queued
Target state: Task complete
Budget: medium

Goal: make speed regression hard to hide.

Context to load:

- `scripts/cns_benchmark.py`
- `cns_store/schema.py`
- `cns_store/queries.py`
- query/API tests

Likely changes:

- synthetic high-degree fixture
- larger generated benchmark graph option
- p95 and payload-size reporting
- per-query result count reporting
- index coverage notes or SQLite `EXPLAIN QUERY PLAN` spot checks where useful

Done when:

- benchmark output can show latency plus payload shape
- high-degree entity tests prove caps hold
- CI or local checks can catch obvious hot-path slowdowns

Stop condition:

- stop before optimizing prematurely if current measured p95 remains far under
  target and no high-degree failure appears

## Chunk GQ-4 - Freshness And Degraded-State Signals

Status: queued
Target state: Task complete
Budget: medium

Goal: make stale context visible to Freedom, GAIL OS, and the cockpit.

Context to load:

- `cns_store/db.py`
- `cns_store/schema.py`
- importers and writer modules
- health/admin routes

Likely changes:

- store metadata for graph version, import time, source graph path/hash, and
  last write lane
- health/store-info fields for stale/degraded state
- response metadata in context packets

Done when:

- consumers can tell fresh, stale, empty, and unavailable states apart
- no consumer has to infer staleness from missing neighbors alone

Stop condition:

- stop before adding external monitoring infrastructure

## Chunk GQ-5 - Learning Write-Lane Unification

Status: queued
Target state: Draft complete
Budget: medium

Goal: reconcile evidence, OKP, charter, stale-claim, and GraphFact writes under
one relationship-memory model.

Context to load:

- `cns_store/evidence_writer.py`
- `cns_store/operating_knowledge_writer.py`
- `cns_store/charter_writer.py`
- `cns_store/stale_claim_executor.py`
- `cns_store/gail_os_fact_importer.py`
- associated tests

Questions to answer:

- Which writer owns each fact?
- Which records are source of truth versus derived relationship memory?
- How are duplicate events de-duplicated?
- Which source refs are mandatory?
- Which writes can happen by HTTP and which must remain extraction-only?

Done when:

- a concrete contract or implementation slice exists for idempotency and
  provenance across all write lanes
- no lane can accidentally imply authority or external execution

Stop condition:

- stop before adding a new write lane

## Chunk GQ-6 - Proposal And Candidate Plane

Status: queued
Target state: Draft complete
Budget: medium

Goal: let Graphify surface high-value candidate work without letting candidates
become approvals.

Context to load:

- stale-claim executor
- OKP and charter writers
- Freedom/GAIL OS integration contracts

Expected behavior:

- Graphify can create candidate nodes, relationship alerts, stale-claim review
  candidates, and routing hints.
- Every candidate is labelled as a candidate.
- Freedom may reason over candidates.
- GAIL OS must approve before any external or destructive action.

Done when:

- proposal/candidate semantics are documented and testable
- no endpoint name or response field implies approval

Stop condition:

- stop before wiring candidate generation to live action execution

## Chunk GQ-7 - Hosted Scale And Store Decision Gate

Status: queued-secondary
Target state: Draft complete
Budget: strategic

Goal: decide when SQLite on mounted storage is still right and when the CNS
store should migrate or replicate.

Context to load:

- deployment docs
- `cns_store/db.py`
- Azure/container notes from the control repo when this becomes active

Gate signals:

- hosted p95 consistently breaches target
- write contention blocks hot reads
- Azure Files SQLite behavior becomes unreliable
- store size or concurrency makes operational recovery fragile
- consumers need multi-region or multi-writer behavior

Potential outcomes:

- keep SQLite with stricter WAL/backup operations
- move job registry into SQLite first
- replicate read models
- migrate to Postgres/Turso or a graph/vector store once query patterns justify
  it

Stop condition:

- stop before migration work without explicit owner approval

## Chunk GQ-8 - Cockpit Speed And Freshness Views

Status: queued-secondary
Target state: Task complete
Budget: medium

Goal: expose the new speed and freshness truth to the operator.

Context to load:

- cockpit Dashboard/Settings/Map surfaces
- admin/store-info route
- freshness output from GQ-4

Done when:

- operator can see graph size, freshness, degraded state, and hot-path latency
- cockpit can preview a context packet without drawing the whole graph

Stop condition:

- stop before a broad Map redesign

## Non-Goals

- Do not make Graphify an authority engine.
- Do not add live external writes.
- Do not require full graph payloads in Freedom's hot path.
- Do not make LLM calls required for hot reads.
- Do not migrate storage until measured evidence justifies it.
- Do not reopen old Map/UI work unless Adam explicitly asks.

## Validation Notes

2026-06-29:

- `bash scripts/governance-preflight.sh` currently fails because the validator
  expects undated canonical docs while this repo uses dated filenames for those
  docs. Treat this as a pre-existing control-doc alignment gap.
- `git diff --check` passed.
- `python3 -m py_compile cns_store/ingest.py` passed for the docstring-only code
  comment update.
- Targeted stale-language scan only returns intentional supersession warnings
  in the 2026-06-29 plan/doctrine and historical wishlist.
- This planning reset does not change executable behavior.
