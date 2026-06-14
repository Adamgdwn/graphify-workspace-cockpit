# Initial Scope — Graphiphy Workspace Cockpit

Generated: 2026-06-14T08:18:40-06:00

## Classification

| Field          | Value |
|----------------|-------|
| Project name   | Graphiphy Workspace Cockpit |
| Slug / dir     | graphify-workspace-cockpit |
| Type           | agent |
| Governance     | 1 |
| Risk tier      | low |
| Stack          | AI agent |
| Primary model  | hybrid |
| Location       | /home/adamgoodwin/code/agents/graphify-workspace-cockpit |

## Build approach

Primary builder: **hybrid**

## Scope brief

**Problem:** Makes knowledge of the build searchable and connected

**User / consumer:** Owner

**MVP:** cockpit with Ask, Map, Decisions, Recommendations, and Work Queue; read/recommend first, no destructive/external actions without explicit approval.

## First session checklist

- [ ] Read `START_HERE.md`
- [ ] Review `docs/current-build-pathway.md`
- [ ] Review `docs/standards/README.md`
- [ ] Review `docs/standards/engineering-governance-by-use-case.md`
- [ ] Review `docs/policy/durable-development-engineering-policy.md`
- [ ] Review `docs/standards/ship-ready-engineering-standard.md`
- [ ] Fill in commands in `AI_BOOTSTRAP.md`
- [ ] Confirm governance level and risk tier in `project-control.yaml`
- [ ] Add first ADR if architecture decisions were made at intake
- [ ] Run governance preflight: `bash scripts/governance-preflight.sh`
