# Start Here

Last Updated: 2026-06-16T20:49:51-06:00
Status: stabilization Chunk 7 task complete; current-build pathway archived
Owner: Adam Goodwin

## Fast Startup

Use this file as the lightweight router. Do not load the historical build log by
default.

1. Run `git status --short`.
2. Read `AGENTS.md`.
3. Read `docs/stabilization-plan.md`.
4. Load only the files named in the selected stabilization chunk.
5. Open `docs/current-build-pathway.md` only when investigating old chunk
   history, validation evidence, or regressions from the original 0-to-1 build.

## State at Pause

The first 30 build chunks are complete. The cockpit is a working local-first
decision surface with seven tabs (`Command`, `Ask`, `Map`, `Decisions`,
`Recommendations`, `Work Queue`, `Settings`) plus a floating AI assistant
overlay. The prior decision-tool polish path is integration complete and now
archived in `docs/current-build-pathway.md`.

The active next path is controlled hosted beta stabilization in
`docs/stabilization-plan.md`. Chunk 1 is task complete: graph schema handling now
normalizes `links` and legacy/internal `edges`, Settings counts both shapes
correctly, connector ingest emits canonical `links`, and backend contract tests
exist for this slice. Chunk 2 is task complete: Settings now calls
`POST /graphs/{name}/activate`, backend activation tests cover demo/uploaded
graphs plus useful failures, and launcher-compatible smoke validation passed.
Chunk 3 is task complete: Ask/Rebuild now route through a Graphify service
wrapper, structured Graphify errors and readiness status are exposed in backend
and Settings, and Docker backend build installs `graphifyy`. Chunk 4 is task
complete: frontend backend calls now use a shared API client, Settings can save,
test, and clear the browser-local API key, protected-mode 401/403 copy is
normalized, and authenticated plus unauthenticated smoke validation passed.
Chunk 5 is task complete: graph upload now rejects unsafe names, oversized
files, invalid JSON, missing nodes, malformed links, and invalid activation
candidates; uploaded graphs are normalized and written atomically before
activation. Chunk 6 is task complete: local JSON state writes now use
parent-safe atomic replacement through `backend/state_store.py`, clean empty
state tests cover the main persisted file surfaces, and launcher-compatible
smoke validation passed. Chunk 7 is task complete: Caddy now routes `/api/*`
before the frontend catch-all, strips `/api` before proxying to the backend, and
hosted smoke instructions cover `GET /api/health` plus `GET /`. The recommended
next implementation chunk is Chunk 8: Minimum Backend Test Suite.

Open owner-review flags before remaining implementation:
- Project is classified as `AI agent with tools` while selected governance is
  low / level 1; do not auto-change governance, but use stronger review for
  hosted beta auth, uploads, deployment, Graphify execution, and Supabase mode.
- Graphify runtime decision is resolved for this pass: Docker/runtime installs
  `graphifyy`, while missing custom runtimes report `GRAPHIFY_MISSING` without
  breaking the rest of the cockpit UI.
- Do not run live Supabase migrations without explicit owner approval.
- API-key browser storage is implemented with localStorage for this beta pass;
  select a stronger hosted auth/session pattern before broader or untrusted
  production exposure.

## Where Things Live

| What | Where |
|------|-------|
| Active stabilization plan | `docs/stabilization-plan.md` |
| Archived build history | `docs/current-build-pathway.md` — superseded for startup |
| Architecture + ADRs | `docs/architecture.md` |
| Roadmap and non-goals | `docs/roadmap.md` |
| Full 0→1 build record | `docs/handover.md` |
| Operator manual | `docs/manual.md` |
| Operational runbook | `docs/runbook.md` |
| Context routing map | `docs/context-map.md` |

## To Resume

1. `git status --short` — preserve unrelated work.
2. Read `docs/stabilization-plan.md`.
3. Pick or confirm the next stabilization chunk.
4. Load only the files named in that chunk.
5. Use `docs/context-map.md` if routing is still unclear.

## Work Patterns

**Ordinary scoped work:**
1. `git status --short`
2. Read repo-local agent instructions (`AGENTS.md`)
3. Use `docs/context-map.md` when context routing is unclear
4. Inspect only the specific files or errors needed
5. Run targeted validation after the change

**Material or risk-triggering changes:**
1. `bash scripts/governance-preflight.sh`
2. `docs/standards/README.md` → `docs/policy/durable-development-engineering-policy.md`
3. `docs/standards/ship-ready-engineering-standard.md` before declaring complete
4. `date -Iseconds` — timestamp the work
5. Work in the smallest complete chunk that can be reviewed safely

Risk-triggering work: production, deployment, auth, payments, secrets, database
migrations, external side effects, infrastructure, destructive actions, autonomous
tool use, governance changes, release readiness.

## Agent Handoff

Update this file only when the top-level plan or pause state changes. Put
detailed stabilization progress in `docs/stabilization-plan.md`. Treat
`docs/current-build-pathway.md` as an archived historical record unless Adam
explicitly asks to reopen it.
