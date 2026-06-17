# Agent Quickstart

Purpose: restart cheaply after clearing, compaction, or handoff without reading
generated output or old pathway history.

## First Five Reads

1. `git status --short`
2. `AGENTS.md`
3. `START_HERE.md` for material work or active-plan continuation
4. `docs/relationship-map-plan.md` for the current slice
5. Only the files named by the selected chunk

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

## Validation Defaults

Use the chunk's validation commands first. For docs-only cleanup, `git status
--short` and `git diff --check` are usually enough. After code changes, run
`graphify update . --no-cluster` or record why it was skipped.
