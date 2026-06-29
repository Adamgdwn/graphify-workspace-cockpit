# Session Handoff — 2026-06-28

Objective:

Document sweep (weak chunks, weak docs, flimsy layers) across Phase 2 CNS
substrate and cockpit docs. Fix everything that was genuinely broken or
misleading, ship it clean.

---

## What Happened This Session

**Two conversation threads; one commit.**

Thread 1 — context recovery and M365 status check:
- Adam confirmed AG Operations is still blocked on M365 sign-ins/authorizations.
- No M365 integration work was initiated (correctly gated).

Thread 2 — document sweep:
- Found 5 CRITICAL bugs + 10 WEAK + 5 MINOR issues.
- Fixed all 5 criticals and the highest-impact weaks.
- 331/331 tests passing after all changes.
- Committed as `e4f7258 fix + docs: document sweep — 5 critical bugs + doc alignment`.

---

## What Changed

### Critical bugs fixed

**C1 — `entity_neighborhood(depth=2)` silently ignored depth parameter**
- `cns_store/queries.py`: depth was accepted but the function always returned
  depth=1 results. Docstring even said "depth>1 not yet supported."
- GAIL OS was calling `?depth=2` for blast-radius assessment and getting wrong data.
- Fix: extracted `_add_neighbors_of()` inner function; true 2-hop traversal with
  `seen_ids` deduplication.

**C2 — `GET /api/cns/admin/store-info` was undocumented and unimplemented**
- Endpoint Family Map spec documented it; admin.py never implemented it.
- Fix: added `StoreInfoResponse` model and full endpoint implementation (entity
  count, relationship count, store size bytes, retrieved_at).

**C3 — `_MISSION_REL_KINDS` and `_AUTHORITY_REL_KINDS` never matched anything**
- Both frozensets in `cns_store/queries.py` used lowercase kind names.
- GAIL OS extraction pipeline writes uppercase: `EVIDENCED_BY`, `ACTED_ON`,
  `PRODUCED_EVIDENCE`, `GOVERNS`, `AUTHORIZED_BY`.
- Freedom's `recent_mission_context()` was permanently silently empty.
- GAIL OS authority chain was permanently silently empty.
- Fix: added uppercase variants to both frozensets while preserving historical
  workspace-graph lowercase kinds.

**C4 — `POST /api/cns/admin/ingest` undocumented in 20D contract**
- The 20D contract said "four approved write lanes" and declared any additional
  lane a violation. The admin ingest endpoint was a fifth lane with no contract entry.
- Fix: updated 20D contract table to document it as the explicitly sanctioned
  exception lane.

**C5 — hardcoded timestamp fallback `"2026-06-28T00:00:00Z"`**
- Both `cns_store/gail_os_fact_importer.py` and `cns_store/stale_claim_executor.py`
  used a hardcoded future date as the fallback when no `ingest_timestamp` was provided.
- This corrupted Signal Gravity L2 time-decay scoring for any fact that didn't
  supply an explicit timestamp.
- Fix: `datetime.now(timezone.utc).isoformat()` in both files. Existing tests
  were unaffected (all pass explicit timestamps).

### Code quality fix

**W8 — `_require_api_key` copy-pasted in 5 route files**
- Created `cns_api/auth.py` with canonical `require_api_key()`.
- Removed local definitions from all 5 route files; renamed all call sites.

### Doc fixes

- `AGENTS.md`: replaced stale "Phase 2 work (next)" section with accurate Phase 2
  complete description + live endpoint list. Test count 217 → 331.
- `START_HERE.md`: updated Status, Fast Startup routing, State at Pause (Phase 2
  complete summary + P1–P4 priority queue). Removed stale relationship-map-plan
  references in startup steps 3–4.
- `docs/context-map.md`: added 3 new routing rows for CNS specs (20D, 20E,
  Endpoint Family Map).
- `docs/2026-06-27 - next-phase-builder-wishlist.md`: test count 217 → 331 (2 occurrences).
- `docs/specs/2026-06-28 - Graphify CNS Connectome Contract.md` (20D): updated
  "four approved write lanes" to "five"; added admin ingest row to table;
  corrected layer diagram and footer note.

---

## State at Handoff

**Phase 2 CNS complete. No open criticals. 331/331 passing.**

| Item | Status |
|------|--------|
| CNS API (port 8001) | Live |
| `cns_store/` — SQLite store | Complete |
| GAIL OS GraphFact extraction pipeline (20E) | Complete |
| Speed SLAs all p95 < 0.3ms | Verified |
| CP-5 (OKP proof-chain v1-l2) | Closed |
| 5 critical bugs | Fixed this session |
| `cns_api/auth.py` shared auth module | Created |

---

## Remaining Sweep Items (Not Fixed)

These are real but lower urgency — none are broken, just inconsistent:

- **W3**: Architecture docs (`docs/ARCHITECTURE_MAP.md`,
  `docs/2026-06-24 - architecture.md`) have no CNS layer section.
- **W6**: `list_charter_entities` in `cns_store/queries.py` still filters Python-side
  instead of using SQL WHERE/LIMIT. Works correctly; efficiency only.
- **W7**: API key guard on CNS read endpoints is applied asymmetrically;
  not documented in 20D as a deliberate choice.
- **W9**: 3 endpoints lack `response_model`: charter_execute POST, OKP proof-chain
  GET, OKP neighborhood GET.
- M1–M5: Minor items not addressed.

---

## Pending Work Queue (From Wishlist)

**P1 — AG Operations base stable** (blocked — M365 sign-in/auth unresolved)
2 chunks remaining. Do not plan M365 extraction inputs/outputs until base stable.

**P2 — EvidencePacket feedback loop**
Wire runtime evidence from executed actions back into Graphify. Receiver side
ready (extraction pipeline exists); need emitter side in GAIL OS. Can start
independently of P1.

**P3 — M365 entity ingestion into Graphify**
After P1 stable. Extend extraction to reach M365 contacts, files, conversations,
meetings, permission graph. Requires `m365_adapter` emitter added to
`_ACCEPTED_EMITTERS` in `cns_store/gail_os_fact_importer.py`.

**P4 — CNS repo migration**
Move `cns_store/` and `cns_api/` from cockpit repo into Graphify core. Tracked
debt, not blocking.

---

## 01 Work Tracking (Windows)

The Windows-side `01 Work Tracking\Enhanced Graphify` doc was NOT updated this
session — the direct cable link was not active. Update manually with this
summary when back on Windows:

> 2026-06-28: Document sweep and CNS Phase 2 close-out. Fixed 5 critical bugs
> (depth=2 traversal, store-info endpoint, mission/authority kind mismatch,
> contract undocumented 5th lane, hardcoded timestamps). Shared auth module
> created. 331/331 tests. Phase 2 complete. P1 still blocked on M365 auth.

---

## Validation

```
python -m pytest cns_store/ cns_api/ -q   → 331/331 passing
git log --oneline -3                       → e4f7258 fix + docs: document sweep...
```

---

## To Resume

1. `git status --short`
2. Read `AGENTS.md`
3. Read `docs/2026-06-27 - next-phase-builder-wishlist.md` for P1–P4 priority queue
4. For CNS work: load `docs/specs/2026-06-28 - Graphify CNS Connectome Contract.md` (20D)
5. P2 (EvidencePacket feedback loop) can start independently — see wishlist for scoping

Completion status: **Task complete.** Phase 2 closeout done.
