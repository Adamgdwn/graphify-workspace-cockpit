# Agent Instructions

## CNS Role (Guided AI Labs Agentic OS — 2026-06-25)

**Layer:** Graphify — Connectome / Relationship Intelligence
**Function:** Graph nodes/edges, dependency maps, research ingestion, context routing, relationship intelligence for all CNS layers
**In the CNS loop:** `OS evidence → Graphify updates → Freedom learns (via graph context queries)`

Graphify is the CNS connectome. It is not a developer tool and not a product spoke. Without Graphify, Freedom reasons over isolated facts. The architecture requires relationship intelligence at the core.

**Current state:** FastAPI + React, "second video ready" as of 2026-06-21. Primary API and visualization surface on Linux. This is the canonical Graphify instance.

**Cross-machine role:** Linux cockpit = primary (query API, visualization, decision surface). Windows Enhanced Graphify = extraction node for Windows repos (GAIL OS Rev 2, M365 Foundation) that Linux cannot run natively. Single `graph.json` as source of truth, synced via GitHub. (DEC-005)

**Phase 2 work (next):**
- Extend graph schema for CNS entity domains (Mission, Action, AuthorityEnvelope, EvidencePacket as GraphNode types)
- Add ResearchClaim and EvidencePacket node types
- Expose HTTP graph query API for external callers (Freedom, GAIL OS)
- Ensure Windows Enhanced Graphify extraction output validates against this repo's schema as canonical

**Integration contracts:**
- Provides: `POST /api/graph/query` — graph context queries from Freedom and GAIL OS
- Consumes: EvidencePacket summaries from GAIL OS (as new GraphNodes after Phase 2+)
- Consumes: ResearchClaim ingestion from build agent research mandate

**Authority boundary:** Graphify provides read-only context. Graphify recommendations are mission candidates, not execution approval. Graphify may not approve or execute actions — that is GAIL OS jurisdiction.

For cross-repo coordination state, see `agentic-multi-agent-agent-builder/docs/build-control/`.

---


## Normal Startup

For ordinary scoped work:

1. run `git status --short`
2. read this file
3. use `docs/context-map.md` when context routing is unclear
4. inspect the specific files, errors, or docs needed for the task
5. run targeted validation after the change

For a one-page restart path after clearing, compaction, or agent handoff, use
`AGENT_QUICKSTART.md`. It routes to the active plan and summarizes which
generated directories to avoid.

Do not turn `START_HERE.md`, pathway docs, governance standards, Graphify, plugins, MCP servers, or provider tools into an automatic startup chain for every small edit.

## Governance Triggers

Before making material or risk-triggering code or configuration changes in this repository:

1. read `START_HERE.md`
2. review the active plan named in `START_HERE.md` (currently `docs/relationship-map-plan.md`; `docs/workspace-scope-and-signal-plan.md`, `docs/stabilization-plan.md`, and `docs/current-build-pathway.md` are archived)
3. review `docs/standards/README.md`
4. review `docs/standards/engineering-governance-by-use-case.md`
5. review `docs/policy/durable-development-engineering-policy.md`
6. review `docs/standards/ship-ready-engineering-standard.md`
7. run the governance preflight check
8. review `project-control.yaml`
9. note any open exceptions relevant to the work
10. capture a timestamp with `date -Iseconds`
11. proceed only after the project passes preflight or any gaps are explicitly accepted

Risk-triggering work includes production, deployment, authentication, authorization, payments, secrets, sensitive data, database migrations, customer communications, external side effects, infrastructure or provider settings, destructive actions, autonomous tool use, risk classification, governance policy changes, or release readiness.

## Preflight

```bash
bash scripts/governance-preflight.sh
```

## Working Rules

- Follow the repository standards by default.
- Use `docs/standards/README.md` as the standards map for coding and release work.
- Confirm the requested work matches the project's `use_case.primary` classification.
- Apply the durable development standard: build the smallest useful thing in the safest durable way.
- Treat Definition of Shipped as a separate evidence gate before declaring meaningful work complete.
- Use `docs/standards/context-hygiene-standard.md` for long sessions, scoped repository reads, compaction, and handoffs.
- Apply lean startup: keep always-on checks short, and trigger heavy governance, Graphify, plugin, MCP, and release checks by task risk or scope.
- Use `docs/context-map.md` to route task-specific context before loading broad docs or source trees.
- Do not silently skip required documentation or controls.
- Record justified deviations as exceptions.
- Reassess governance when risk, autonomy, data sensitivity, or money movement changes.
- Keep work in context-window-friendly chunks with one objective, clear files, validation, and handoff notes.
- Define the target completion state for each meaningful chunk: `Draft complete`, `Task complete`, `Integration complete`, `Release ready`, or `Blocked`.
- Project completion is a human decision. Agents may report only bounded completion states when the documented criteria and verification evidence support that label.
- Stop when the chunk's definition of done is met, when its stop condition is reached, or when repeated attempts stop producing new evidence.
- In the active plan document, keep chunk headings clear and consistent with that plan's existing format; do not reformat archived chunks just to match an older convention.
- Timestamp material work, decisions, validation, and handoffs.
- Update the active plan document when the active plan, status, or next chunk changes.

## Fundamentals-First AI Coding

Build fundamentals-first software. AI speed does not make bad code cheap.

Before meaningful coding, reach shared understanding. Use consistent domain language. Prefer deep modules with simple interfaces over shallow pass-through layers.

Let feedback loops set the pace: types, tests, linting, runtime checks, and user-visible validation.

Design interfaces deliberately, then implement in small vertical slices.

Avoid flimsy pass-through layers, generic helpers, premature abstractions, swallowed errors, untyped blobs, duplicated business rules, hidden production assumptions, and fake validation claims.

When you see weak design, flag it and propose the smallest safe improvement instead of rewriting the project.

Every change should make the next correct change easier.

## Context Hygiene

Operate with strict context hygiene. Keep active context minimal, relevant, current, and recoverable.

Work in clear phases. Summarize at phase boundaries. Compact or reset before quality degrades. Re-state critical constraints after compaction.

Narrow file scope before reading. Prefer targeted diffs and specific files over whole-repo exploration.

Treat tokens as a budget, but do not skip required governance, security, architecture, or task-critical reading.

The repository remembers. Agents rent context. Keep work packets, scout summaries, validation, and handoffs durable enough that the next agent does not need the chat thread.

Keep read-only scout outputs summary-only.

## Graphify Policy

Use the canonical Graphify governance file:

`/home/adamgoodwin/code/Tools/graphify/docs/agent-governance.md`

Before broad source exploration, architecture analysis, dependency tracing, unfamiliar large-surface work, or cross-repo planning, use Graphify first and reference the workspace graph at:

`/home/adamgoodwin/code/Tools/graphify/workspace/out/graph.json`

Use the workspace graph for cross-repo routing. When a new repo becomes active, set up repo-local Graphify with:

```bash
graphify-setup-project /path/to/repo
```

For full semantic repo graphs in heavy active repos, run `/graphify /path/to/repo` from Claude Code. Current Graphify skills can use Claude Code subagents when no Gemini key is set, so policy should constrain token burn through per-repo scope, caching, strict ignores, and cheap updates rather than hard-coding a provider or extraction backend.

Use Graphify to orient, then inspect only the files needed for the actual change. Do not require Graphify for known files, build or test errors, small scoped edits, or routine docs checks. After code changes, update the relevant graph with `graphify update . --no-cluster`, or update the workspace graph for cross-repo work. Preserve existing secret-handling rules: do not index, print, summarize, or commit secrets or environment files.
