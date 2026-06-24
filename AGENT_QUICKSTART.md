# Agent Quickstart

Purpose: restart cheaply after clearing, compaction, or handoff without reading
generated output or old pathway history.

## First Five Reads

1. `git status --short`
2. `AGENTS.md`
3. `START_HERE.md` for material work or active-plan continuation
4. `docs/session-handoff-2026-06-23.md` for the latest shutdown note
5. `docs/relationship-map-plan.md` for the current slice
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
- Current relationship-map state: Slices 1-5 are complete; the latest active
  work is owner review and targeted UX tuning after the June 20 video shoot,
  semantic actionability tightening, map-specific recommendations, scoped count
  fixes, two-repo label/source metadata polish, and Map-local Semantic Analysis
  run/rerun UX. Same-session polish fixed Workspace Scope Profile estimates so
  default-ignored bulk no longer consumes the bounded file-count budget, raised
  the Evidence cap to 15,000 visible nodes, and fixed excluded-parent scope
  selections cancelling explicitly included child folders. Automatic graph
  escalation is now drafted behind explicit env configuration: local Ollama
  chooses `local` or `elevated`, then rebuild runs either `graphify update
  --no-cluster` or configured `graphify extract --backend ... --no-cluster`.
  Next useful step is owner verification against a broad real workspace scope.

## Validation Defaults

Use the chunk's validation commands first. For docs-only cleanup, `git status
--short` and `git diff --check` are usually enough. After code changes, run
`graphify update . --no-cluster` or record why it was skipped.
