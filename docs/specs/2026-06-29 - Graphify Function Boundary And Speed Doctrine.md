# Graphify Function Boundary And Speed Doctrine

Date: 2026-06-29
Status: active boundary doctrine
Owner: Adam Goodwin
Completion target: Draft complete

## Purpose

This document captures the 2026-06-29 Graphify information-transfer reset.

Graphify is the CNS relationship-transfer function. Its job is to turn isolated
facts into bounded, provenance-backed relationship intelligence fast enough that
Freedom and GAIL OS can use it during normal reasoning and governance without
feeling the cost.

The phrase "quantum speed" is an operating bar, not a literal physics claim:
Graphify context should arrive as a tight relationship packet, not as a graph
dump, model call, broad file read, or heavy extraction run.

## Current Fact Base

Inspection source: GitHub repo `Adamgdwn/graphify-workspace-cockpit` on
2026-06-29.

- `cns_store/` is the indexed SQLite relationship store.
- `cns_api/` exposes the machine-callable CNS API.
- Six hot read endpoints serve GAIL OS and Freedom.
- Five HTTP write lanes exist and are API-key guarded when `CNS_API_KEY` is set:
  EvidencePacket, OKP, CharterProfile, stale-claim execution, and admin ingest.
- The GAIL OS GraphFact importer exists in `cns_store/gail_os_fact_importer.py`.
- Current documented benchmark evidence shows all six query patterns at p95
  under 0.3ms on a 12,687-entity / 19,477-relationship real graph.

Several older docs still use pre-implementation wording such as "all endpoints
are GET," "first write path," or "GraphFact importer is future scope." Treat
those as historical statements unless a 2026-06-29-or-newer plan restates them.

## Boundary Rule

Graphify is not a passive viewer. It is allowed to write Graphify-owned
relationship memory through approved lanes.

Graphify is not an authority layer. It may not approve actions, issue authority
envelopes, mutate external business systems, or execute missions on its own.

Short version:

```text
Graphify owns relationship intelligence.
GAIL OS owns authority and action state.
Freedom owns executive reasoning and operator-facing orchestration.
```

## What Graphify Owns

Graphify owns:

- entity and relationship memory
- dependency maps and neighborhood traversal
- source references, provenance, and freshness markers
- relationship-derived context packets for Freedom and GAIL OS
- graph-internal evidence, OKP, charter, stale-claim, and GraphFact records
- proposal or candidate nodes that are explicitly labelled as candidates
- bounded routing hints that help another layer choose what to inspect next

## What Graphify Does Not Own

Graphify does not own:

- authority decisions
- action approval
- external action execution
- live M365 writes or other business-system writes
- destructive local workspace mutation
- unbounded graph payloads in the hot path
- mandatory full-graph context injection into Freedom
- model-based reasoning inside the hot read plane

## Runtime Planes

### Hot Context Read Plane

Purpose: answer direct relationship questions during Freedom or GAIL OS
reasoning.

Allowed work:

- indexed SQLite reads
- bounded depth traversal
- bounded top-N relationship summaries
- source/provenance/freshness metadata

Forbidden work:

- extraction
- LLM calls
- full graph reads
- unbounded neighbor lists
- write side effects

Target: keep this plane comfortably inside the existing p95 SLA. Future work
should aim for p95 below 25ms local and below 100ms hosted for bounded hot
context packets, while retaining the existing 250ms ceiling for wider
neighborhood checks.

### Warm Relationship Write Plane

Purpose: update Graphify-owned memory after governed events.

Allowed work:

- idempotent upserts
- source-ref preserving relationship writes
- API-key guarded HTTP write lanes already approved by contract
- extraction-pipeline GraphFact ingestion

Rules:

- no placeholder target entities unless a later contract explicitly allows it
- no authority decisions
- no external side effects
- no hot-path blocking extraction

### Cold Extraction Plane

Purpose: ingest or refresh source graphs and large external fact batches.

Allowed work:

- `graphify` extraction or update
- batch imports
- scheduled or operator-triggered refresh
- larger validation and sanitization passes

Rules:

- asynchronous by default
- does not block hot reads
- produces freshness metadata so consumers know whether the graph is current

### Cockpit And Admin Plane

Purpose: human/operator visibility, map review, diagnostics, and controlled
admin actions.

Rules:

- may expose richer views than the hot API
- must not redefine authority boundaries
- must make graph freshness, speed, and degraded state visible

## Speed Doctrine

Graphify gets faster by moving less, earlier, and with stronger shape.

1. Serve packets, not graphs.
2. Pre-rank relationships where the store already has enough signal.
3. Cap depth, neighbor count, and response bytes by default.
4. Keep extraction and LLM work out of hot reads.
5. Make freshness explicit instead of silently over-trusting stale context.
6. Preserve source refs so consumers can inspect the precise evidence only
   when needed.
7. Benchmark representative high-degree and larger-graph cases before widening
   any contract.

## Context Packet Shape

Future hot-path work should converge toward a bounded packet shape:

```text
entity_id
label / kind / repo / path
domain / authority hint
top_relationships[N]
recent_mission_or_evidence_refs[N]
source_refs[N]
freshness
confidence / relationship weight
degraded flags
next_query_hints
```

The packet should be useful on its own and point to deeper reads without
forcing those reads up front.

## Degraded Mode

Graphify unavailability must be explicit.

Freedom may continue with `graphify_degraded: true` when a mission proposal can
be safely framed without relationship context. GAIL OS may continue only when
the governing policy allows the missing graph context. If graph context is part
of an authority check, the safe default is hold, not guess.

## Change Admission Rules

Any future Graphify change that affects CNS planning or execution must answer:

- Which runtime plane does it touch?
- Is it hot, warm, cold, or operator/admin work?
- What is the max payload?
- What is the p95 budget?
- What authority boundary prevents it from executing or approving actions?
- What stale/degraded signal reaches the consumer?
- What source refs prove where the relationship came from?

No new endpoint should merge without those answers.

## Planning Impact

The active implementation plan for this doctrine is:

`docs/2026-06-29 - Graphify Quantum Speed Execution Plan.md`

Older Phase 2/Phase 3 docs remain evidence. They are not restart authority when
they conflict with this doctrine or the 2026-06-29 execution plan.
