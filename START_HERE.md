# Start Here

Last Updated: 2026-06-14
Status: paused — build complete
Owner: Adam Goodwin

## State at Pause

All 17 chunks complete. The cockpit is a working local-first decision surface:
six tabs (Ask, Map, Decisions, Recommendations, Work Queue, Settings) plus a
floating AI assistant overlay. Desktop launcher is at
`~/Desktop/graphify-cockpit.desktop`.

Last commit: `15e2a83` — Chunks 15–17 + full documentation handover pass.

## Where Things Live

| What | Where |
|------|-------|
| Build history and chunk status | `docs/current-build-pathway.md` |
| Architecture + ADRs | `docs/architecture.md` |
| Roadmap and non-goals | `docs/roadmap.md` |
| Full 0→1 build record | `docs/handover.md` |
| Operator manual | `docs/manual.md` |
| Operational runbook | `docs/runbook.md` |
| Context routing map | `docs/context-map.md` |

## To Resume

1. `git status --short` — confirm clean tree.
2. Read `docs/handover.md` for the full build record and resume context.
3. Define any new work as a new chunk in `docs/current-build-pathway.md`.
4. Use `docs/context-map.md` to select what to load for the task.

## Work Patterns

**Ordinary scoped work:**
1. `git status --short`
2. Read repo-local agent instructions (`CLAUDE.md`, `AI_BOOTSTRAP.md`)
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
detailed chunk progress in `docs/current-build-pathway.md`.
