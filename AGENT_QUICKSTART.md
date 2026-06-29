# Agent Quickstart

Purpose: restart cheaply after clearing, compaction, or handoff without reading
generated output or old pathway history.

## First Five Reads

1. `git status --short`
2. `AGENTS.md`
3. `START_HERE.md` for material work or active-plan continuation
4. `docs/session-handoff-2026-06-28.md` for the latest shutdown note
5. `docs/2026-06-27 - next-phase-builder-wishlist.md` for Phase 3 priorities
6. Only the files named by the selected chunk

Use `docs/context-map.md` when routing is unclear. Use
`docs/workspace-scope-and-signal-plan.md` only for completed workspace scope
and signal history. Use
`docs/stabilization-plan.md` only for completed stabilization evidence. Use
`docs/current-build-pathway.md` only for archived 0-to-1 build evidence,
regression history, or validation details from the original build.

## Avoid By Default

- `graphify-out/` and `graphify-out/cache/`
- `frontend/node_modules/`, `frontend/dist/`, `frontend/build/`
- `.venv/`, `backend/.venv/`, `__pycache__/`, `.pytest_cache/`
- `workspace/state/`
- logs, generated reports, and environment files

Do not print, summarize, index, or commit secrets. The master environment file
is outside this repo at `/home/adamgoodwin/code/.env.master`; use presence-only
checks.

## Current Shape

- Backend: FastAPI in `backend/main.py`, with shared helpers in
  `backend/graph_schema.py`, `backend/state_store.py`, `backend/services/`, and
  `backend/connectors/`.
- Frontend: React/Vite TypeScript in `frontend/src/`, organized around the
  seven cockpit tabs plus the floating `AICopilot`.
- State: local JSON under `workspace/state/`, ignored and user-specific.
- Demo graph: committed fixture at `workspace/demo/graph.json`.
- Generated repo graph: local-only `graphify-out/`, rebuilt with
  `graphify update . --no-cluster` when needed.
- Phase 2 CNS complete as of 2026-06-28: `cns_store/` + `cns_api/` live on
  port 8001, GAIL OS GraphFact extraction pipeline (20E), 331/331 tests, all
  SLAs satisfied. 5 critical bugs fixed in final sweep (depth=2 traversal,
  store-info endpoint, mission/authority kind mismatches, undocumented 5th write
  lane, hardcoded timestamps). `cns_api/auth.py` is now the shared auth module.
- Next priorities (P1–P4): see `docs/2026-06-27 - next-phase-builder-wishlist.md`.
  P1 (AG Operations base) is blocked on M365 sign-in/auth. P2 (EvidencePacket
  feedback loop) can start independently.
- Relationship-map (Map/UI): Slices 1-5 complete, owner-reviewed, video-ready.
  Automatic graph escalation drafted behind explicit env configuration.

## Validation Defaults

Use the chunk's validation commands first. For docs-only cleanup, `git status
--short` and `git diff --check` are usually enough. After code changes, run
`graphify update . --no-cluster` or record why it was skipped.
