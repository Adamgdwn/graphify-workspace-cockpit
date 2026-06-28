# Graphify Endpoint Family Map

**Date:** 2026-06-28
**Chunk:** 20D — Graphify CNS Connectome Contract Normalization
**Status:** Map complete — Phase 2 surface locked
**Base URL:** `http://localhost:8001` (or `$CNS_API_HOST:$CNS_API_PORT`)
**All endpoints:** GET (read-only). No POST, PUT, PATCH, DELETE in Phase 2.

---

## Overview

The 6 CNS API endpoints on port 8001 map into three families:

| Family | Endpoints | Consumer | Purpose |
|---|---|---|---|
| **GAIL OS Decision Family** | 3 | GAIL OS | Pre-action validation and audit traceability |
| **Freedom Context Family** | 3 | Freedom | Pre-proposal context enrichment |
| **Shared Infrastructure** | Health + Admin | Both | Service health and store info |

All 6 endpoints are read-only. The CNS store is written only by the extraction pipeline.

---

## Family 1 — GAIL OS Decision Family

GAIL OS calls these endpoints **at action decision time**, before issuing an AuthorityEnvelope. They provide structural relationship intelligence the policy gate needs to evaluate risk and blast radius.

### Endpoint 1 — Connector Scope Validation

```
GET /api/cns/connector/{connector_id}/validate?domain={domain}
```

**Consumer:** GAIL OS  
**Purpose:** Verify that a connector is registered and active for the target domain before GAIL OS grants authority over it.  
**Question answered:** "Is connector `[connector_id]` registered and active for domain `[domain]`?"

**Query parameters:**
| Parameter | Required | Description |
|---|---|---|
| `connector_id` | Yes (path) | Connector entity ID from the CNS store |
| `domain` | Yes (query) | Domain to validate against (e.g. `governance`, `m365`, `graphify`) |

**Response (200 OK):**
```json
{
  "connector_id": "graphify-local",
  "found": true,
  "is_active": true,
  "domain": "graphify",
  "kind": "Connector",
  "repo": "graphify-workspace-cockpit",
  "path": "cns_api/app.py"
}
```

**Error:** `404 Not Found` — connector not in CNS store.

**GAIL OS use:** Before issuing an `AuthorityEnvelope` that grants permission over a connector, GAIL OS confirms the connector is registered and active in the relationship graph. An unregistered connector must not receive authority.

---

### Endpoint 2 — Entity Neighborhood Traversal

```
GET /api/cns/entity/{entity_id}/neighborhood?depth={1|2}
```

**Consumer:** GAIL OS  
**Purpose:** Determine blast radius of an action before approval. What entities are adjacent to the action target?  
**Question answered:** "What entities are adjacent to action target `[entity_id]`?"

**Query parameters:**
| Parameter | Required | Default | Description |
|---|---|---|---|
| `entity_id` | Yes (path) | — | Target entity ID |
| `depth` | No | 1 | Traversal depth: 1 (immediate) or 2 (extended blast radius) |

**Response (200 OK):**
```json
{
  "entity_id": "gail-ai-operating-system-rev-2",
  "found": true,
  "label": "GAIL OS Rev 2",
  "kind": "Repository",
  "neighbor_count": 8,
  "neighbors": [
    {
      "id": "uaos-core-package",
      "label": "uaos-core",
      "kind": "Package",
      "repo": "gail-ai-operating-system-rev-2",
      "path": "packages/uaos-core",
      "relation_kind": "CONTAINS",
      "direction": "outbound",
      "weight": 1.0
    }
  ]
}
```

**Error:** `404 Not Found` — entity not in CNS store.

**GAIL OS use:** Before approving a risky action, GAIL OS can assess what neighboring entities could be affected. `depth=2` gives a wider blast radius view for high-risk-tier actions.

---

### Endpoint 3 — Authority Chain Traceability

```
GET /api/cns/connector/{connector_id}/authority-chain
```

**Consumer:** GAIL OS  
**Purpose:** Audit trail — trace what authority relationships produced the R-level for a connector.  
**Question answered:** "What authority chain produced the R-level for connector `[connector_id]`?"

**Query parameters:**
| Parameter | Required | Description |
|---|---|---|
| `connector_id` | Yes (path) | Connector entity ID |

**Response (200 OK):**
```json
{
  "connector_id": "graphify-local",
  "found": true,
  "chain_length": 3,
  "chain": [
    {
      "entity_id": "graphify-local",
      "label": "Graphify Local CNS API",
      "kind": "Connector",
      "relation_kind": "GOVERNED_BY"
    },
    {
      "entity_id": "gail-os-connector-registry",
      "label": "GAIL OS Connector Registry",
      "kind": "Registry",
      "relation_kind": "REGISTERED_IN"
    },
    {
      "entity_id": "adam-goodwin-operator",
      "label": "Adam Goodwin",
      "kind": "Operator",
      "relation_kind": "AUTHORIZED_BY"
    }
  ]
}
```

**Error:** `404 Not Found` — connector not in CNS store.

**GAIL OS use:** EvidencePacket generation and audit. The authority chain from the graph corroborates the `authority_basis` field in the ApprovalDecision record. This is the link between graph-fact and evidence.

---

## Family 2 — Freedom Context Family

Freedom calls these endpoints **before proposing a mission**, during the Observe phase. They provide relationship context that shapes what missions Freedom considers worth proposing and what authority envelope to request.

### Endpoint 4 — Entity Context Enrichment

```
GET /api/cns/entity/{entity_id}/context
```

**Consumer:** Freedom  
**Purpose:** Enrich Freedom's understanding of an entity before proposing a mission that targets it.  
**Question answered:** "What do I know about `[entity]`? What is it connected to?"

**Query parameters:**
| Parameter | Required | Description |
|---|---|---|
| `entity_id` | Yes (path) | Target entity ID |

**Response (200 OK):**
```json
{
  "entity_id": "approval-actions-module",
  "found": true,
  "label": "approval_actions",
  "kind": "Module",
  "repo": "gail-ai-operating-system-rev-2",
  "path": "packages/uaos-core/src/gail_ai_operating_system/approval_actions.py",
  "cluster": "gail-os-core",
  "importance_tier": "high",
  "connected_count": 5,
  "connected_ids": [
    "action-dataclass",
    "authority-envelope-dataclass",
    "approval-decision-dataclass",
    "uaos-core-package",
    "test-approval-actions"
  ],
  "metadata": {}
}
```

**Error:** `404 Not Found` — entity not in CNS store.

**Freedom use:** Before proposing a mission to modify or interact with an entity, Freedom learns its importance tier, cluster, and connected entities. High-importance entities with many connections warrant more cautious mission proposals.

---

### Endpoint 5 — Recent Mission Context

```
GET /api/cns/entity/{entity_id}/mission-history?limit={n}
```

**Consumer:** Freedom  
**Purpose:** Check if a mission targeting this entity has been attempted recently, and what the outcome was.  
**Question answered:** "Has a mission targeting `[entity]` been attempted recently? What was the outcome?"

**Query parameters:**
| Parameter | Required | Default | Description |
|---|---|---|---|
| `entity_id` | Yes (path) | — | Target entity ID |
| `limit` | No | 10 | Max events to return (1–100) |

**Response (200 OK — always 200, empty list when no history):**
```json
{
  "entity_id": "approval-actions-module",
  "event_count": 2,
  "events": [
    {
      "entity_id": "mission-abc123",
      "label": "Add approval actions module",
      "kind": "Mission",
      "relation_kind": "TARGETS"
    },
    {
      "entity_id": "evidence-abc456",
      "label": "Approval actions implemented (Chunk 20B)",
      "kind": "EvidencePacket",
      "relation_kind": "EVIDENCES"
    }
  ]
}
```

**Note:** Always returns 200 — empty list when no mission relationships exist. An empty list is not an error; it means Freedom has no prior context and the mission is novel.

**Freedom use:** Prevents redundant or contradictory proposals. If a mission was recently completed successfully, Freedom should not re-propose it. If a mission was stopped, Freedom should investigate why before proposing again.

---

### Endpoint 6 — Domain Mapping

```
GET /api/cns/entity/{entity_id}/domain
```

**Consumer:** Freedom  
**Purpose:** Determine which governance domain an entity belongs to, so Freedom knows which authority envelope to request from GAIL OS.  
**Question answered:** "Which domain does `[entity]` belong to? Who governs it?"

**Query parameters:**
| Parameter | Required | Description |
|---|---|---|
| `entity_id` | Yes (path) | Target entity ID |

**Response (200 OK):**
```json
{
  "entity_id": "approval-actions-module",
  "found": true,
  "label": "approval_actions",
  "domain_id": "gail-os-governance-domain",
  "domain_label": "GAIL OS Governance",
  "repo": "gail-ai-operating-system-rev-2",
  "cluster": "gail-os-core"
}
```

**Note:** `domain_id` and `domain_label` are `null` when no governance relationship exists in the store. This is valid — it means the entity has not yet been assigned to a domain.

**Error:** `404 Not Found` — entity not in CNS store.

**Freedom use:** The domain determines which authority envelope to request. An entity in the `gail-os-governance-domain` requires GAIL OS authority. An entity in `m365-domain` requires M365 bridge authority (Phase 4).

---

## Shared Infrastructure

### Health Endpoint

```
GET /health
```

Returns `{"status": "ok"}` when the service is running. Used by Docker Compose healthchecks and external monitors. Available to both GAIL OS and Freedom.

### Admin Endpoint (CNS API key required)

```
GET /api/cns/admin/store-info
```

Returns store statistics: entity count, relationship count, last extraction timestamp. Requires `CNS_API_KEY` header when auth is enabled. Not called in normal decision flow — used for monitoring and debugging.

---

## Consumer Summary

| Consumer | Endpoints Used | When Called | Purpose |
|---|---|---|---|
| GAIL OS | 1, 2, 3 | At action decision time | Connector validation, blast radius, audit chain |
| Freedom | 4, 5, 6 | Before mission proposal | Entity context, mission history, domain governance |
| Both | Health | Service monitoring | Liveness check |
| Operators | Admin | Debugging / ops | Store statistics |

---

## Write Boundary Enforcement

No endpoint in this map creates or modifies store records. The one-writer rule applies:

| Write surface | Writer |
|---|---|
| CNS store (entities + relationships) | Extraction pipeline only |
| EvidencePacket ingestion (Phase 3) | GAIL OS → extraction pipeline (not API) |

Any code change that adds a write path through the HTTP API violates the Graphify extraction-write / API-read contract and must be reviewed as an architectural exception.

---

*Map status: Task complete. 6 endpoints in 2 consumer families + shared infrastructure. No new write paths. Extraction-write / API-read rule preserved.*
