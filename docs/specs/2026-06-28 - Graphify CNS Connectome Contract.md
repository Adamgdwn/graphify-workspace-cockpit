# Graphify CNS Connectome Contract

**Date:** 2026-06-28
**Chunk:** 20D — Graphify CNS Connectome Contract Normalization
**Status:** Contract complete — Phase 2 implementation active
**Port:** 8001 (configurable via `CNS_API_PORT`)
**Related schemas:** `graph-context-ref.schema.json`, `source-ref.schema.json` (GAIL OS `contracts/json-schema/`)

---

## Graphify's Role in the CNS

Graphify is the CNS **connectome** — the relationship fabric that other layers query to reason. Just as the human brain is defined by its connections rather than its components, Graphify is defined by the relationships it holds and serves.

The analogy is a **rail system** or **electrical grid**: Freedom and GAIL OS are the trains and devices; Graphify is the network they run on. Without Graphify, Freedom and GAIL OS reason over isolated facts. With Graphify, they inherit context, blast-radius awareness, authority traceability, and relationship intelligence from the full workspace graph.

---

## Layer Identity

```
┌───────────────────────────────────────────────────────┐
│              Freedom (Executive Cognition)             │
│     Observe → Propose → (Graphify enrichment) →       │
│                    Submit to GAIL OS                   │
└──────────────────────┬───────────────────────────────-┘
                       │ queries (read-only)
                       ▼
┌───────────────────────────────────────────────────────┐
│           Graphify — Connectome / Relationship Field   │
│   6 read-only HTTP endpoints on port 8001             │
│   SQLite store (12,687 entities, 19,477 relationships) │
│   p50 per query: 0.1–0.2ms (all SLAs satisfied)       │
└──────────────────────┬───────────────────────────────-┘
                       │ queries (read-only)
                       ▼
┌───────────────────────────────────────────────────────┐
│              GAIL OS (Authority + Governance)          │
│     Validates connectors, blast radius, auth chain     │
│     before issuing AuthorityEnvelopes                  │
└───────────────────────────────────────────────────────┘
```

---

## Authority Boundary (Hard Rule)

**Graphify provides read-only context. Graphify has no approval authority. Graphify has no execution authority.**

| What Graphify CAN do | What Graphify CANNOT do |
|---|---|
| Answer structural relationship queries | Approve or reject actions |
| Return entity context, neighborhood, domain info | Issue AuthorityEnvelopes |
| Return authority chain traceability data | Execute actions |
| Surface mission history (read from store) | Write to mission records |
| Inform mission proposals (read-only input to Freedom) | Propose missions itself |
| Ingest EvidencePackets submitted by GAIL OS / AG Operations (live — POST /api/cns/evidence) | Author or generate evidence records (Graphify is not the source; GAIL OS and AG Operations are) |

The canonical statement from AGENTS.md:
> "Graphify recommendations are mission candidates, not execution approval. Graphify may not approve or execute actions — that is GAIL OS jurisdiction."

---

## Extraction-Write / API-Read Boundary

This is the fundamental Graphify design rule. It must be preserved as Phase 2 evolves into Phase 3.

```
Extraction pipeline  →  WRITES  →  CNS Store (SQLite)
HTTP API             ←  READS   ←  CNS Store (SQLite)
```

**One narrow HTTP write path exists: `POST /api/cns/evidence` (EvidencePacket ingest — live as of feat/phase4/4.6).**

The actors that write to the store:
1. The extraction pipeline (CLI trigger or scheduled run)
2. `POST /api/cns/evidence` — accepts EvidencePackets submitted by GAIL OS / AG Operations. API-key protected. Upsert semantics. Never creates placeholder entities. Relationship edges only to existing entities.

The GraphFact ingestion lane (GAIL OS telemetry → Graphify graph structure) remains extraction-pipeline only — no HTTP write path for GraphFact payloads.

Any PR or change that adds a write endpoint beyond the EvidencePacket lane to `cns_api/routes/` is a **violation of this contract** and must be reviewed before merge.

---

## Connection to CP-1 Schemas (20C)

Two CP-1 JSON Schema contracts (GAIL OS `contracts/json-schema/`) describe Graphify reference anchors:

### `graph-context-ref.schema.json`

Used when GAIL OS or Freedom embeds a Graphify entity reference into a mission, action, or evidence packet.

| Field | Type | Description |
|---|---|---|
| `graph_ref_id` | string (`gref-` prefix) | Unique identifier for this reference |
| `entity_id` | string | The Graphify entity being referenced |
| `entity_type` | string | Type of entity (e.g. `connector`, `repo`, `function`) |
| `relationship_type` | string | Relationship being cited (e.g. `GOVERNS`, `DEPENDS_ON`) |
| `target_entity_id` | string (optional) | Second entity in the relationship |
| `query_context` | string | Reason this graph reference was pulled |
| `confidence` | number 0.0–1.0 | Confidence of the relationship from the store |
| `graph_timestamp` | ISO 8601 string | When this reference was extracted |
| `source_ref_id` | string (optional) | Links to a `source-ref` record |

A `graph-context-ref` is the evidence that Freedom or GAIL OS consulted Graphify before making a decision. It anchors the mission/action record to specific graph facts.

### `source-ref.schema.json`

Used to trace any entity back to its source of truth in a specific repo and commit.

| Field | Type | Description |
|---|---|---|
| `source_id` | string (`src-` prefix) | Unique source reference identifier |
| `source_system` | enum | `gail-os`, `freedom`, `graphify`, `m365`, `github`, `local` |
| `entity_id` | string | The entity this refers to |
| `ref_type` | string | Type of reference (e.g. `action`, `connector`, `schema`) |
| `repo_path` | string | Path within the source repo |
| `ref_value` | string | Git SHA, file hash, or record ID |
| `created_at` | ISO 8601 string | When this reference was created |

A Graphify entity's canonical source-of-truth reference uses `source_system: "graphify"`.

---

## Speed SLA (Phase 2, Verified 2026-06-27)

Graph: 12,687 entities, 19,477 relationships (15.9 MB JSON, real workspace).

| Endpoint | p50 | p95 | p99 | SLA | Status |
|---|---|---|---|---|---|
| `entity_context` | 0.2ms | 0.2ms | 0.2ms | <100ms | PASS |
| `domain_mapping` | 0.1ms | 0.2ms | 0.2ms | <100ms | PASS |
| `recent_mission_context` | 0.1ms | 0.2ms | 0.2ms | <100ms | PASS |
| `authority_chain` | 0.2ms | 0.3ms | 0.3ms | <100ms | PASS |
| `entity_neighborhood` | 0.2ms | 0.2ms | 0.2ms | <250ms | PASS |
| `validate_connector` | 0.2ms | 0.2ms | 0.2ms | <100ms | PASS |

All SLAs satisfied. Headroom: ~330–500× within SLA bounds.

---

## What This Contract Does NOT Cover

Per 20D stop condition:

- No new endpoints added (6 endpoints are the Phase 2 surface)
- No write path through the API
- No live M365 graph queries (Phase 4)
- No real-time extraction (batch/scheduled is Phase 2 design)
- No Graphify approval authority added
- EvidencePacket HTTP write lane is now live (`POST /api/cns/evidence` — feat/phase4/4.6). The GraphFact extraction pipeline (GAIL OS telemetry → graph structure) remains Phase 3 scope.

---

## Deployment Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `CNS_STORE_PATH` | Yes | — | Path to SQLite store |
| `CNS_API_PORT` | No | 8001 | Listening port |
| `CNS_API_HOST` | No | 0.0.0.0 | Bind address |
| `CNS_API_KEY` | No | "" | Auth key; empty = auth disabled |

Build: `docker build -f Dockerfile.cns-api -t graphify-cns-api .`

---

*Contract status: Updated 2026-06-28 post feat/phase4/4.6. EvidencePacket HTTP write lane live (POST /api/cns/evidence). GraphFact extraction boundary unchanged (extraction pipeline only). Authority boundary enforced.*
