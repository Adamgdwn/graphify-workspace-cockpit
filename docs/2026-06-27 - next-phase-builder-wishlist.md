# Next-Phase Builder Wish List
**Date:** 2026-06-27
**For:** Agentic multi-agent agent builder — first probe of this repo post Phase 2
**Status:** Standing brief — read before planning Phase 3 or any cross-repo work

---

## Read This First

This document is a wish list and strategic brief from the architect who completed
Phase 2. Before you plan or execute any Phase 3 work, internalize the framing
here. Getting Graphify's role wrong at the start of Phase 3 planning will
propagate incorrect assumptions into every subsequent chunk.

---

## The Single Most Important Thing to Get Right

**Graphify is not a service. It is the world model.**

Every other system in this architecture — Freedom, GAIL OS, AG Operations — is
only as correct as what Graphify knows. Freedom reasons from Graphify context.
GAIL OS validates authority envelopes using Graphify data. When AG Operations
completes a mission, the evidence must feed back into Graphify. If Graphify's
data is stale, you do not get slow decisions — you get confident decisions made
from wrong premises. That is worse than a failure.

Analogies that are accurate, not decorative:
- **Rail system** — Freedom and GAIL OS are trains. Graphify is the rails.
  Trains can be fast or slow; without rails they go nowhere.
- **River system** — all cognitive flow moves through Graphify. You can add
  tributaries (new entity domains, new repos), but the river is Graphify.
- **Neuronal connectome** — Graphify is the relationship fabric. The brain does
  not have a filing system you can point to as a discrete component. It *is* its
  connections. Graphify is the connections.

When you plan Phase 3, weight Graphify accordingly. It is not one service in a
flat list of services. It is the layer that makes all other services coherent.

---

## The Four-Repo Topology

### 1. Graphify — The Foundational Substrate
**Repo:** `/home/adamgoodwin/code/Tools/graphify/`
**Cockpit (admin/vis UI):** `/home/adamgoodwin/code/agents/graphify-workspace-cockpit/`
**Phase 2 status:** Complete. CNS API live on port 8001. 217 tests passing.

What Phase 2 delivered:
- SQLite store (`cns_store/`) — entities, relationships, metadata, fully indexed
- HTTP API (`cns_api/`) — 6 endpoints covering all GAIL OS and Freedom query patterns
- Containerized, cloud-ready, env-var configured
- Speed SLAs verified: all p95 < 0.3ms on 12,687-node real graph (SLA: <100ms)
  Headroom: ~330–500× within SLA bounds
- BLK-002 resolved: Graphify is now externally callable via HTTP

Current limitation: Graphify knows code repos. It does not yet know M365 entities.
That is Phase 4 and is gated behind AG Operations base readiness (see below).

**Architectural note:** `cns_store/` and `cns_api/` currently live in the cockpit
repo (pragmatic for Phase 2 development). Architecturally they belong in the
Graphify core repo. The cockpit should be a consumer/admin client, not a host.
This migration is the right foundation before Phase 3 integration but is not a
blocker — do not treat it as Phase 3 Chunk 1; treat it as a tracked debt item.

### 2. GAIL OS — Autonomic Governance Layer
**Status:** HTTP API complete (Chunks 20–23). CP-1 gate pending.
**CP-1 gate:** Freedom calls GAIL OS HTTP API and receives a PolicyDecision.
This is the next critical path item. Lives in the Freedom/GAIL OS repos, not
this one.

GAIL OS uses Graphify for:
- Connector scope validation before issuing authority envelopes
- Entity neighborhood traversal (blast radius calculation)
- Authority chain traceability for audit

### 3. Freedom — Executive Cognition Layer
**Status:** CP-1 gate not yet closed.
**CP-1 gate:** Freedom → GAIL OS HTTP call. Required before Phase 3 full
cognitive cycle can run.

Freedom uses Graphify for:
- Entity context enrichment before mission proposal
- Recent mission history (prevents redundant/contradictory proposals)
- Domain mapping (determines which authority envelope to request)

### 4. AG Operations Workspace — The Action Surface
**Status:** 2 chunks from a solid base. Microsoft 365 agentic environment.
**Gate:** Do not plan M365-to-CNS integration specifics until those 2 chunks
complete and the base is stable. Inputs and outputs must be carefully specified
at that point — do not assume or infer them.

When AG Operations is base-ready, it becomes:
- The first real-world action surface (emails, meetings, documents, tasks)
- The first source of non-codebase entities for Graphify to index
- The first consumer of the Phase 3 EvidencePacket feedback loop

---

## The Cognitive Cycle (Full — Not Yet Wired)

```
Observe
  │
  ▼
RELATE ──── Graphify ──── (world model: who/what/how connected)
  │
  ▼
Reason ──── Freedom ──── (propose missions from Graphify context)
  │
  ▼
Govern ──── GAIL OS ──── (validate authority, blast radius, policy)
  │
  ▼
Act ──── AG Operations M365 ──── (execute in the real world)
  │
  ▼
EvidencePackets ──► feed back into Graphify store ──► cycle updates
```

Phase 3 goal: close this loop. Currently: Graphify can answer queries, but
EvidencePackets do not yet feed back in. The "Learn" step is Phase 3's core
addition to Graphify. Without it, the system is smart but not self-correcting.

---

## Priority Sequencing (Wish List)

### P0 — CP-1 Gate (do this first)
Close Freedom → GAIL OS HTTP call. This is the single most urgent item. It
does not require AG Operations to be complete. It does not require Phase 3
Graphify changes. It is the prerequisite for every subsequent integration.

### P1 — AG Operations Base Completion
Complete the 2 remaining AG Operations chunks. Only then plan M365 integration
inputs/outputs. Do not guess the interface before the base is stable.

### P2 — Phase 3 EvidencePacket Feedback Loop
After CP-1 is closed, wire EvidencePackets back into the Graphify store. This
is the "Learn" step. The write path through the API (explicitly excluded in
Phase 2) opens here. Design it carefully — this is the first write path in
the API layer and the first place the store grows from runtime behavior, not
just extraction.

### P3 — M365 Entity Ingestion into Graphify
After AG Operations is base-stable, extend Graphify's extraction to reach M365
entities: contacts, files, conversations, meetings, permission graph. The CNS
store schema is designed to absorb new entity types — this is an extraction
extension, not a schema rewrite. But it requires knowing what M365 produces
(hence P1 gate).

### P4 — CNS Repo Migration (tracked debt, not urgent)
Move `cns_store/` and `cns_api/` from the cockpit repo into Graphify core.
Cockpit becomes a pure consumer. This is architecturally correct but is not
blocking any Phase 3 work — do it when cross-repo coordination cost becomes
higher than migration cost.

---

## What to Avoid

- **Do not flatten Graphify to peer status.** In any architecture diagram or
  planning document, Graphify must be shown as the substrate layer, not as one
  service in a horizontal row.

- **Do not plan M365 integration before AG Operations 2 chunks complete.** The
  interface is not defined yet. Speculation here creates technical debt.

- **Do not open a write path through the CNS API without careful design.** The
  EvidencePacket feedback loop is the first and only correct reason to add it.
  Any other write path through the API is a design smell.

- **Do not skip CP-1 to jump straight to Phase 3 Graphify work.** CP-1 is the
  integration proof that Freedom and GAIL OS can actually communicate. Without
  it, Phase 3 is adding pipes to a system that hasn't proven it can move water.

---

## Technical Facts for Context

| Item | Value |
|------|-------|
| CNS API port | 8001 |
| CNS store engine | SQLite (WAL mode, FK enforcement) |
| Total tests passing | 217 |
| Real graph benchmark | 12,687 nodes / 19,477 relationships |
| p95 latency (all queries) | < 0.3ms (SLA: <100ms single, <250ms neighborhood) |
| BLK-002 | Resolved 2026-06-27 |
| CP-1 gate | Pending (Freedom → GAIL OS HTTP call) |
| AG Operations | 2 chunks from base readiness |
| Graphify Phase 2 | Complete and committed 2026-06-27 |

---

## One-Line Summary for Agent Bootstrap

> Graphify is the world model. Phase 2 is done. Close CP-1 first, then
> complete AG Operations 2 remaining chunks, then plan Phase 3 integration.
> Do not diminish Graphify to a peer service — everything else depends on it.
