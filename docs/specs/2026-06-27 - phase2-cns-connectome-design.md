# Graphify Phase 2 — CNS Connectome Design

**Date:** 2026-06-27
**Status:** Design intent — pre-implementation spec
**Context:** Written after Phase 0/1 complete, before Adam's independent Graphify work begins.
**Resumes at:** Deep dive into all 3 core repos + plan revision after Graphify work done.

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

---

## Sequencing Constraint

Phase 2 Graphify work is **parallel to, not blocking** Chunks 20–23 (GAIL OS HTTP API + CP-1 gate). The CP-1 gate only requires that Freedom can call GAIL OS. Graphify is not on the CP-1 critical path.

After CP-1, Phase 2 Graphify and Phase 3 (Freedom ↔ OS + Graphify full integration) proceed together. The first full cognitive cycle — Observe → **Relate (Graphify)** → Reason (Freedom) → Govern (GAIL OS) → Act — requires Graphify Phase 2 to be complete.

---

## Open Questions for Adam's Graphify Work

Before writing Phase 2 code, the following should be answered:

1. **Store choice:** SQLite only, or SQLite + Chroma from the start? If the semantic query need is clear now, add Chroma in Phase 2. If uncertain, SQLite-only is a safe start with a migration path.
2. **Extraction frequency:** On-demand (triggered by extraction run), scheduled (cron), or file-watcher? The answer affects how stale the store can be at decision time.
3. **Graph size estimate:** How many entities does the current workspace graph contain? This sets the performance baseline.
4. **Windows extraction:** BLK-004 (Windows Enhanced Graphify hasn't run) — does the Phase 2 store need to include Windows repo entities from the start, or is Linux-only acceptable for CP-1?

These four answers should be in hand before Phase 2 spec is finalized.
