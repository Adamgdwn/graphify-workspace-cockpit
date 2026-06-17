# Known Issues

Document type: current limitations and review gates
Status: current
Owner: Adam Goodwin

This file summarizes the live issues agents should notice before widening scope.
The active continuation plan lives in `docs/relationship-map-plan.md`.
Completed workspace scope and signal evidence lives in
`docs/workspace-scope-and-signal-plan.md`.
Completed stabilization evidence lives in `docs/stabilization-plan.md`.

## Active Technical Debt

- `backend/main.py` is still a large compatibility facade, but Chunk 13 moved
  config, app construction, auth, storage readiness, and several route groups
  into dedicated modules. Split remaining graph/settings/recommendation/action/
  mission/rebuild/overlap areas only when future work touches them.
- `docs/standards/README.md` references supporting standards that are not all
  present in this repo. Use the local files first, then the governance source
  repo only if a missing standard is task-critical.
- Graphify output is generated local state. `graphify-out/` should not be read
  or committed; rebuild it locally when needed.

## Owner-Review Gates

- Project classification is `AI agent with tools`, while `project-control.yaml`
  keeps selected `risk_tier: low` and `governance_level: 1`. Treat this as the
  accepted stabilization review prompt; do not change governance without owner
  approval.
- Do not run live Supabase migrations without explicit owner approval. Chunk 9
  added the source-controlled migration file only.
- API-key storage in browser localStorage is accepted for this beta pass. Choose
  stronger hosted auth/session handling before broad or untrusted production
  exposure.
- Cloud connector sync can touch Microsoft services. Do not initiate auth or
  external connector syncs unless the active task explicitly requires it.

## Current Next Work

- Continue from `START_HERE.md` and
  `docs/relationship-map-plan.md`.
- Future follow-up scope should be owner-selected, bounded, and recorded in
  the active plan or a new plan.
