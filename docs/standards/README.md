# Engineering Standards Index

Document type: standards index
Status: active
Owner: Project owner or human technical lead
Audience: coding agents, human coders, reviewers, project owners, and release reviewers

## Purpose

This is the first standards file a coding session should read when it needs the engineering rules for a governed build.

It points to the standards that define what good code means, how controls scale by use case and risk, and what evidence is required before work can be called ship-ready.

## Required Coding Session Reading

For meaningful implementation work, read these in order:

1. [Durable Development Engineering Policy](../policy/durable-development-engineering-policy.md)
2. [Engineering Governance By Use Case](engineering-governance-by-use-case.md)
3. [Ship-Ready Engineering Standard](ship-ready-engineering-standard.md)

Together, these answer:

- What makes code durable and maintainable?
- What controls fit this type of project?
- What evidence proves the work is ready for a real user?
- What completion state can be honestly claimed without rushing the broader project?

## Supporting Engineering Standards

Use these when the work touches the matching area. Some governed projects may start with only the required baseline standards and then receive supporting standards through later governance upgrades.

| Standard | Use When |
|---|---|
| AI Agent Governance Standard | Building or changing agents, tools, autonomy, prompt registries, model registries, or agent permissions. |
| Context Hygiene Standard | Managing long agent sessions, context windows, token budgets, compaction, scoped repo reads, or handoffs. |
| Deployment And Release Standard | Changing deployment, release, rollback, environments, external providers, or production promotion. |
| Document Control Standard | Creating or maintaining durable docs, handoffs, records, standards, pathway logs, ADRs, audits, or runbooks. |
| Documentation Standard | Writing user, operator, architecture, setup, process, or support documentation. |
| Monorepo Standard | Structuring or changing a monorepo, package boundaries, shared libraries, or workspace layout. |
| Repository And Naming Standard | Naming repositories, files, modules, directories, and common project structure. |
| Risk Classification Standard | Classifying risk tier, governance level, sensitive surfaces, or escalation needs. |
| Security And Secrets Standard | Handling secrets, auth, permissions, private data, external credentials, or trust boundaries. |
| Testing Standard | Choosing test levels, writing validation evidence, or judging test adequacy. |

## Context Routing

Use `docs/context-map.md` before broad repository reading when the right files or
standards are unclear. It routes task types to the smallest useful context set.

## Coding Agent Rule

Do not rely on memory from a previous chat to know the engineering standards. Read this index, then open the standards relevant to the current task.

If this project only contains a subset of the standards, use the local files first. When the New Build Governance Agent source repository is available, use its `docs/standards/README.md` as the source of truth for missing or older project-local copies.
