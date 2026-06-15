# Context Map

Document type: project context routing map
Status: current
Owner: Adam Goodwin
Audience: coding agents, human coders, reviewers, and project owners

## Purpose

This file keeps agent context loads small, deliberate, and recoverable.

The repository remembers. Agents rent context. Use this map to decide what to
load first, what to load by task type, and what to avoid unless the task needs
it.

## Always Load

- `AGENTS.md` or the active agent instruction file
- `START_HERE.md` for material work, unclear scope, or changes to the active plan
- `project-control.yaml` when risk, governance level, controls, or required docs matter

Keep these files compact. They should route to durable docs, not duplicate them.

## Load By Task

| Task | Load First |
|---|---|
| Current plan, chunking, validation, or handoff | `docs/current-build-pathway.md` |
| Engineering standards map | `docs/standards/README.md` |
| Context windows, token budgets, compaction, scoped reads, or handoffs | `docs/standards/context-hygiene-standard.md` |
| Durable implementation, design quality, testing discipline, or AI coding fundamentals | `docs/policy/durable-development-engineering-policy.md` |
| Use-case controls, risk tier, governance level, or owner decisions | `docs/standards/engineering-governance-by-use-case.md` |
| Completion labels, Definition of Shipped, release evidence, or finish reports | `docs/standards/ship-ready-engineering-standard.md` |
| Architecture decisions or system shape | `docs/architecture.md` and relevant ADRs |
| Domain terms or naming | `docs/domain-language.md` |
| Deployment, release, rollback, or environment changes | `docs/deployment-guide.md`, `docs/runbook.md`, and release standards |
| Agent autonomy, tools, prompts, models, or permissions | `docs/agent-inventory.md`, `docs/model-registry.md`, `docs/prompt-register.md`, and `docs/tool-permission-matrix.md` |

## Search Before Loading

- long audit reports
- old pathway history below the current active chunk
- logs, generated reports, and command output
- exported manifests
- archived plans or superseded briefs

Use `rg` or targeted file excerpts before opening long files.

## Avoid Unless Needed

- `.git/`
- `.venv/`, `venv/`, `node_modules/`, and dependency caches
- build output, coverage, and generated artifacts
- ignored Graphify output
- secrets and environment files
- large transcripts or pasted chat histories

Do not print, summarize, index, or commit secrets.

## Work Packet Reminder

For meaningful work, define:

- goal
- budget class: Tiny, Small, Medium, Large, or Strategic
- context to load first
- files or folders to avoid unless needed
- constraints and non-goals
- done-when checks
- handoff location

Tiny edits may use an inline version of this packet. Large or strategic work
should record the packet in `docs/current-build-pathway.md`, an ADR, or a short
handoff note.

## Maintenance

Update this file when the repo's routing paths change or when agents repeatedly
load the wrong material. Keep it short enough to read at startup when context
routing is unclear.
