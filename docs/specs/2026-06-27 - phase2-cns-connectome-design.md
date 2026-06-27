# Graphify Phase 2 — CNS Connectome Design

**Date:** 2026-06-27
**Status:** Architecture decisions locked — ready for Phase 2 implementation post CP-1
**Context:** Written after Phase 0/1 complete. Decisions resolved 2026-06-27 (store, extraction frequency, graph size, cloud-first scope).

---

## The Identity Shift

Graphify today is an extraction pipeline that produces a static artifact (JSON file) readable by humans and CLI tools. That is Phase 0 Graphify.

Phase 2 Graphify is a **cognitive substrate**: always-alive, machine-callable, sub-100ms queryable. Not a new tool layered on top — the store *is* what Graphify becomes. The JSON output becomes a bootstrap artifact and a human-readable snapshot, not the primary interface.

The analogy the user named is right: the human brain doesn't have a filing system we can point to as a discrete component. It *is* its connections. Graphify stops being a visualizer and becomes the CNS connectome — the relationship fabric that other layers query to reason.

---

## Three-Part Architecture

```
┌─────────────────────┐
│   Extraction Layer  │  (unchanged from current)
│   Walk repos        │  Runs on schedule or on-demand.
│   Extract entities  │  Writes to store. Not real-time — it's the indexer.
│   + relationships   │
└──────────┬──────────┘
           │ writes
           ▼
┌─────────────────────┐
│    Store Layer      │  THIS IS GRAPHIFY'S BRAIN
│   SQLite (struct)   │  Persists. Grows. Is not a cache.
│   + Chroma/Qdrant   │  SQLite = entity/relationship graph traversal
│     (semantic)      │  Chroma/Qdrant = embedding-based similarity queries
└──────────┬──────────┘
           │ reads
           ▼
┌─────────────────────┐
│     API Layer       │  Thin HTTP. Machine-first.
│   GAIL OS queries   │  Low-latency because it's serving from indexed store,
│   Freedom queries   │  not re-reading files. Sub-100ms per query target.
└─────────────────────┘
```

**Design rule:** Extraction writes. API reads. No write path through the API in Phase 2. The only write path in Phase 2 is the extraction pipeline.

**Phase 3 addition (learning loop):** EvidencePackets feed back into the store — this is where the system becomes self-referential. After an action completes and an EvidencePacket is written, Graphify ingests the evidence and updates relationship weights / context. This is the "Learn" step in the CNS cycle.

---

## Speed Contract

- Single relationship query at decision time: **< 100ms**
- Full entity neighborhood traversal: **< 250ms**
- Semantic similarity query (embedding lookup): **< 500ms**

These aren't aspirational — they're the SLA GAIL OS needs to evaluate an action without adding decision latency. Sub-100ms on a local SQLite store with proper indexing is straightforward. The semantic store adds latency only for queries that need it.

**Benchmark results — 2026-06-27 (Chunk 2.8):**
Graph: 12,687 entities, 19,477 relationships (real workspace, 15.9 MB JSON).

| Query | p50 | p95 | p99 | SLA | Result |
|-------|-----|-----|-----|-----|--------|
| entity_context | 0.2ms | 0.2ms | 0.2ms | <100ms | PASS |
| domain_mapping | 0.1ms | 0.2ms | 0.2ms | <100ms | PASS |
| recent_mission_context | 0.1ms | 0.2ms | 0.2ms | <100ms | PASS |
| authority_chain | 0.2ms | 0.3ms | 0.3ms | <100ms | PASS |
| entity_neighborhood | 0.2ms | 0.2ms | 0.2ms | <250ms | PASS |
| validate_connector | 0.2ms | 0.2ms | 0.2ms | <100ms | PASS |

All SLAs satisfied at 30 reps each on the real workspace graph. Headroom: ~330–500× within SLA bounds.

---

## What GAIL OS Needs to Query at Decision Time

This is the question that drives the Phase 2 API shape. At minimum:

**1. Connector scope validation**
> "Is connector `[id]` registered and active for domain `[domain]`?"
→ Structural graph query. Answers before GAIL OS issues an authority envelope.

**2. Entity neighborhood**
> "What entities are adjacent to action target `[entity_id]`?"
→ Traversal query. Tells GAIL OS the blast radius of an action.

**3. Pattern consistency (Phase 3)**
> "Is action type `[type]` consistent with recent patterns for domain `[domain]`?"
→ Semantic similarity query. Feeds the "Learn" step. Phase 3, not Phase 2.

**4. Authority chain traceability**
> "What authority chain produced the R-level for this connector?"
→ Structural query. Supports audit and evidence generation.

---

## What Freedom Needs to Query

Freedom's role in the cognitive cycle is "Observe → Propose." Before proposing a mission, Freedom should ask Graphify:

**1. Entity relevance**
> "What do I know about `[entity]`? What is it connected to?"
→ Context enrichment before mission proposal.

**2. Recent mission context**
> "Has a mission targeting `[entity]` been attempted recently? What was the outcome?"
→ Pulls from the evidence feedback loop. Prevents redundant or contradictory proposals.

**3. Domain mapping**
> "Which domain does `[entity]` belong to? Who governs it?"
→ Determines which authority envelope to request from GAIL OS.

---

## What Phase 2 Does NOT Include

- No live M365 graph queries (that's Phase 4)
- No write path through the API
- No real-time extraction (batch/scheduled is correct for Phase 2)
- No removal of the existing JSON file output — it stays as a human-readable snapshot
- No Graphify UI changes — the navigator stays, but is not Phase 2 scope

---

## Phase 2 Deliverables

1. **Store schema** — entity table, relationship table, metadata table, embedding table. Typed. Migrated from existing JSON graph.
2. **Extraction → store write path** — extraction pipeline writes to SQLite + Chroma instead of (or in addition to) JSON.
3. **HTTP API** — FastAPI (same stack as GAIL OS Chunk 21 for consistency). Endpoints covering the 3 GAIL OS queries and 3 Freedom queries above. Returns structured JSON.
4. **Performance validation** — query benchmarks against a realistic graph size (estimate: 500–2000 entities for current workspace).
5. **BLK-002 resolved** — Graphify becomes externally callable; Freedom can query it.
   *Resolved 2026-06-27:* CNS API service exposes 6 HTTP endpoints on port 8001. Any external
   caller (Freedom, GAIL OS, or remote cloud worker) can query the graph via HTTP without running
   the Graphify CLI locally. All 6 endpoints tested, speed SLAs confirmed.*

---

## Sequencing Constraint

Phase 2 Graphify work is **parallel to, not blocking** Chunks 20–23 (GAIL OS HTTP API + CP-1 gate). The CP-1 gate only requires that Freedom can call GAIL OS. Graphify is not on the CP-1 critical path.

After CP-1, Phase 2 Graphify and Phase 3 (Freedom ↔ OS + Graphify full integration) proceed together. The first full cognitive cycle — Observe → **Relate (Graphify)** → Reason (Freedom) → Govern (GAIL OS) → Act — requires Graphify Phase 2 to be complete.

---

## Decisions — Phase 2 Architecture (2026-06-27)

The four open questions are resolved. These decisions are locked for Phase 2 implementation.

**1. Store choice: SQLite-only, Chroma migration path in schema**
SQLite-only for Phase 2. Chroma migration path is designed into the schema from day one — embedding columns are reserved and the table structure anticipates a vector store, but Chroma is not a Phase 2 dependency. Add Chroma when semantic query patterns are proven in production.

**2. Extraction frequency: On-demand + scheduled, no file-watcher**
Extraction triggers on explicit runs (CLI command or API trigger) and on a scheduled interval. No file-watcher. Resource conservation is the constraint: the store can be minutes to hours stale at decision time. GAIL OS and Freedom need relationship context, not real-time file state.

**3. Graph size: Nimble, evolve with the system**
No ceiling constraint for Phase 2. Current workspace graph (~1,700 nodes, ~3,400 edges) is the performance baseline. As CNS entity domains expand, the store grows — continuous evolution, not a fixed target. The speed SLA is the correct constraint, not node count.

**4. Cloud scope: Cloud-first API design from day one**
Graphify Phase 2 is **cloud-first by design**. The HTTP API layer is not a local-only service — it will be deployed to a shared cloud endpoint soon after the Linux-local launch, and Graphify must reach across all platforms: Linux, Windows, cloud workers, and future enterprise client environments.

*Architecture implications of cloud-first:*
- HTTP API designed for cloud deployment from the start: containerized, env-var configured, no local path assumptions in the API layer
- SQLite store has an explicit migration path to a cloud-accessible store (Turso, PostgreSQL, or equivalent) — Phase 2 SQLite is the starting point, not the ceiling
- Extraction pipeline runs on any extraction node (Linux, Windows, cloud worker) and writes to the store via the same schema; extraction is platform-agnostic by design
- The cockpit is the visualization and admin layer; the Phase 2 API is the shared service Freedom and GAIL OS call
- BLK-004 (Windows Enhanced Graphify extraction) is resolved architecturally: any extraction node uses the same schema and writes to the same store — no separate Windows artifact

*What cloud-first does NOT change in Phase 2:*
- Phase 2 starts with a Linux-local SQLite deployment — cloud deployment follows, it does not precede
- No write path through the API in Phase 2
- No real-time extraction in Phase 2
- Batch/scheduled extraction remains correct

---

*Spec status: Open questions resolved 2026-06-27. Phase 2 implementation ready to begin post CP-1.*
