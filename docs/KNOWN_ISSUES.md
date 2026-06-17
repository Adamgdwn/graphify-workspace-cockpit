# Known Issues

Document type: current limitations and review gates
Status: current
Owner: Adam Goodwin

This file summarizes the live issues agents should notice before widening scope.
The detailed implementation history lives in `docs/stabilization-plan.md`.

## Active Technical Debt

- `backend/main.py` is still large. Chunk 13 is the planned module-split pass,
  after the contract tests added in earlier stabilization chunks.
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

- Continue with `docs/stabilization-plan.md`, currently moving from Chunk 12 to
  Chunk 13.
- Keep future chunks bounded and update `START_HERE.md` plus the active plan
  when status changes.
