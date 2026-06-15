# Start Here

Last Updated: 2026-06-14T08:18:40-06:00
Status: current
Owner: Adam Goodwin

## Current Plan

This is the first file an agent should read when starting work in this project. Keep it short, current, and pointed at the active build path.

Current status:

All 17 chunks of the build pathway are complete as of 2026-06-14. The cockpit
is a working local-first decision surface. See `docs/current-build-pathway.md`
for the full chunk status table and `docs/roadmap.md` for what was built and
what comes next.

Priorities for any new work:

- confirm scope against `docs/current-build-pathway.md` (all 17 chunks done — new work needs explicit direction)
- apply `docs/policy/durable-development-engineering-policy.md` during implementation
- apply `docs/standards/ship-ready-engineering-standard.md` before declaring meaningful work complete
- use `docs/context-map.md` as the short routing map for task-specific context loads
- keep startup lean: use short repo orientation first, then trigger governance, Graphify, plugins, MCP tools, and release checks by task risk or scope
- use Graphify before broad source exploration or architecture analysis, using workspace routing plus repo-local semantic graphs for heavy active repos
- keep work in context-window-friendly chunks
- timestamp material work, decisions, validation, and handoffs

## Current Build Pathway

Use [docs/current-build-pathway.md](docs/current-build-pathway.md) as the live build route.

For ordinary scoped work:

1. Run `git status --short`.
2. Read the repo-local agent instructions.
3. Use `docs/context-map.md` when context routing is unclear.
4. Inspect the specific files, errors, or docs needed for the task.
5. Run targeted validation after the change.

For material or risk-triggering changes:

1. Run `bash scripts/governance-preflight.sh`.
2. Review `docs/standards/README.md`.
3. Review `docs/standards/engineering-governance-by-use-case.md`.
4. Review `docs/policy/durable-development-engineering-policy.md`.
5. Review `docs/standards/ship-ready-engineering-standard.md`.
6. Review `project-control.yaml`.
7. Check `exceptions` in `project-control.yaml` and any exception records.
8. For broad source exploration, architecture analysis, dependency tracing, or cross-repo planning, use the Graphify policy at `/home/adamgoodwin/code/Tools/graphify/docs/agent-governance.md` before reading raw source broadly. Reference `/home/adamgoodwin/code/Tools/graphify/workspace/out/graph.json` for cross-repo routing, set up repo-local Graphify when a new repo becomes active, run `/graphify /path/to/repo` from Claude Code for full semantic repo graphs on heavy active repos, and update the relevant graph after code changes.
9. Capture the work timestamp with `date -Iseconds`.
10. Work in the smallest complete chunk that can be reviewed safely.

Risk-triggering work includes production, deployment, authentication, authorization, payments, secrets, sensitive data, database migrations, customer communications, external side effects, infrastructure or provider settings, destructive actions, autonomous tool use, risk classification, governance policy changes, or release readiness.

## Agent Handoff

Update this file only when the top-level plan or handoff point changes. Put detailed step-by-step progress in `docs/current-build-pathway.md`.
