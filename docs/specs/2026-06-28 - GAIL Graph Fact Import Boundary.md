# GAIL OS Graph Fact Import Boundary

**Date:** 2026-06-28
**Chunk:** 20E — GAIL OS + Graphify Safe Graph-Fact Extraction Lane
**Status:** Boundary defined — import lane scoped for Phase 3 implementation
**GAIL OS schema:** `gail-ai-operating-system-rev-2/contracts/json-schema/graph-fact.schema.json`
**GAIL OS contract:** `gail-ai-operating-system-rev-2/docs/contracts/2026-06-28 - Graphify Fact Export Contract.md`

---

## Purpose

This document defines the Graphify side of the GAIL OS → Graphify graph-fact extraction lane. It states what Graphify will accept, how it will ingest the data, and what it will NOT do — specifically, it will not accept write paths through the HTTP API.

---

## The Extraction-Write / API-Read Rule (Must Be Preserved)

```
GAIL OS emits GraphFact records
    │
    │  via extraction pipeline trigger
    ▼
Graphify extraction pipeline
    │  reads GraphFact records from GAIL OS output
    │  validates against graph-fact.schema.json
    │  sanitization check (no secrets, no PII beyond entity record)
    │  maps to entity/relationship updates
    ▼
CNS store (SQLite) — the only write destination
    │
    │  reads only — no write path through HTTP API
    ▼
Graphify HTTP API (port 8001)
    ← Freedom queries entity context, mission history, domain mapping
    ← GAIL OS queries connector validation, neighborhood, authority chain
```

**Hard rule:** No `POST`, `PUT`, `PATCH`, or `DELETE` endpoint is added to `cns_api/routes/` for GraphFact ingestion. The extraction pipeline is the only writer. This is the Graphify design rule and it must not be violated in Phase 3 implementation.

---

## What Graphify Will Accept from GAIL OS

The Graphify extraction pipeline will accept `GraphFact` records conforming to `graph-fact.schema.json` (`$id: https://gail-os.local/contracts/json-schema/graph-fact.schema.json`).

### Accepted Fact Types → Store Mapping

| `fact_type` | Graphify Store Action |
|---|---|
| `entity_observed` | Upsert entity with attributes from `sanitized_payload` |
| `relationship_observed` | Upsert relationship between `subject_entity_id` and `object_entity_id` with `relationship_kind` |
| `mission_completed` | Update entity with mission completion metadata; add `EVIDENCED_BY` relationship to evidence record |
| `action_executed` | Update entity with action execution metadata; add `ACTED_ON` relationship |
| `evidence_recorded` | Add `EvidencePacket` as a graph node; link to mission and action entities |
| `connector_registered` | Upsert connector entity; establish `GOVERNS` relationship chain |
| `authority_granted` | Update connector entity with authority level; add `AUTHORIZED_BY` relationship |

### Accepted `emitted_by` Values

Only facts from these GAIL OS modules are accepted:
- `approval_actions`
- `evidence_recorder`
- `mission_lifecycle`
- `connector_registry`
- `policy_gate`
- `authority_engine`

Facts from any other source are rejected at the extraction boundary.

---

## What Graphify Will NOT Accept

| Rejected Input | Reason |
|---|---|
| GraphFacts with non-null `sanitized_payload` containing secrets or credentials | Sanitization rule — GAIL OS must sanitize before emission |
| GraphFacts with `emitted_by` not in the accepted list | Unregistered source — one-writer rule for fact emission |
| GraphFacts with `status != "emitted"` or `"queued"` | Only unprocessed facts are accepted; `ingested` and `rejected` are terminal states from Graphify's perspective |
| HTTP POST to any CNS API endpoint with GraphFact payload | No write path through HTTP API — extraction pipeline only |
| Real-time streaming of GraphFacts | Batch/scheduled extraction only in Phase 3 |

---

## Ingestion Pipeline (Phase 3 Scope)

The Phase 3 implementation will add a Graphify extraction source for GAIL OS GraphFacts. The pipeline will:

1. Read `GraphFact` records from a GAIL OS output directory or queue (path to be defined in Phase 3)
2. Validate each record against `graph-fact.schema.json`
3. Run sanitization check on `sanitized_payload` (no secrets, no PII beyond entity record)
4. Map the fact to entity/relationship table updates in the CNS store
5. Set `status = "ingested"` or `"rejected"` and write `ingestion_notes`
6. Update entity `importance_tier` and relationship `weight` based on evidence frequency

The extraction pipeline trigger is the same as current (CLI trigger or scheduled run) — not real-time.

---

## Connection to 20C Schemas

Two CP-1 schemas from 20C are relevant to GraphFact ingestion:

| Schema | Role in Import |
|---|---|
| `source-ref.schema.json` | `source_ref_id` in GraphFact traces back to the GAIL OS entity of record; Graphify stores this to maintain provenance |
| `graph-context-ref.schema.json` | `graph_ref_id` in GraphFact links to an existing Graphify entity; used to update rather than create when the entity already exists |

---

## Connection to 20D Endpoint Map

The 6 HTTP endpoints documented in `docs/specs/2026-06-28 - Graphify Endpoint Family Map.md` are all reads. None of them accept GraphFact records. The GraphFact import boundary is strictly an extraction pipeline concern.

After Phase 3 ingestion runs:
- `GET /api/cns/entity/{entity_id}/mission-history` will return mission events ingested from GAIL OS GraphFacts
- `GET /api/cns/entity/{entity_id}/neighborhood` will reflect relationships created by `relationship_observed` and `connector_registered` facts
- `GET /api/cns/connector/{connector_id}/authority-chain` will reflect `authority_granted` facts

---

## Phase 3 Readiness Gate (G3-GPHY)

This document opens the path to G3-GPHY (see `agentic-multi-agent-agent-builder/docs/infrastructure/2026-06-28 - Promotion Gates.md`). The gate condition:

> **G3-GPHY:** GAIL OS `graph-fact.schema.json` defined; Graphify import boundary documented.

**G3-GPHY is now OPEN** — both conditions satisfied by 20E.

Phase 3 implementation still requires:
- GAIL OS HTTP API live (G2-GAIL — Chunk 21) to trigger extraction from GAIL OS
- Phase 3 extraction pipeline code in Graphify (`extraction/gail_os_facts.py` or equivalent)
- Adam authorization for Phase 3 scope

---

## Stop Condition (Confirmed)

This document defines the import boundary only. No implementation code was added to Graphify by this document. No new endpoints added. No new write paths. Extraction-write / API-read rule preserved.

---

*Boundary status: Task complete. G3-GPHY gate opened by this document + GAIL OS graph-fact.schema.json. No live ingestion active. Phase 3 implementation is future scope.*
