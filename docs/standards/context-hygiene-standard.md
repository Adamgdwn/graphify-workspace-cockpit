# Context Hygiene Standard

Document type: supporting engineering standard
Status: active
Owner: Project owner or human technical lead
Audience: coding agents, human coders, reviewers, and project owners
Applies to: coding sessions, agent workflows, long-running implementation threads, reviews, handoffs, and governed build upgrades.

## Purpose

This standard defines practical context and token hygiene for agent-assisted software work.

Context is a limited working-memory budget. Agents should prefer small, relevant, refreshable context over large, persistent, low-signal transcript history. Good context hygiene improves reliability, reduces drift, lowers token cost, and helps future agents resume work without rereading the entire repository.

Context hygiene must not be used as an excuse to skip required governance, security, architecture, testing, or task-critical reading. The goal is to keep the active working set sharp, not to work blind.

## Relationship To Other Standards

Use this standard alongside:

- `docs/current-build-pathway.md`
- `docs/policy/durable-development-engineering-policy.md`
- `docs/standards/engineering-governance-by-use-case.md`
- `docs/standards/ship-ready-engineering-standard.md`
- `docs/standards/document-control-standard.md` when durable docs or handoffs are being updated

The required engineering standards define what good and ship-ready work means. This standard defines how agents should manage context while doing that work.

## Core Principle

The repository remembers. Agents rent context.

Keep active context minimal, relevant, current, and recoverable.

Prefer:

- scoped file reads over whole-repository scans
- phase summaries over endless transcripts
- exact next objectives over broad intentions
- durable handoff notes over chat memory
- targeted diffs over repeated rereads
- refreshable standards files over copied policy blobs
- stable, cache-friendly instruction prefixes over rewritten prompt dumps
- summary-only investigation outputs over transcripts

## Context Tiers And Budgets

Classify project knowledge by how often it should be loaded:

| Tier | Load Pattern | Examples | Rule |
|---:|---|---|---|
| 0 | Always loaded | Root agent instructions, safety rules, core commands | Keep tiny and current |
| 1 | Task loaded | Current work packet, bug report, acceptance criteria | Load only for the task |
| 2 | On demand | Architecture, standards, API contracts, domain rules | Route by path |
| 3 | Search first | Long logs, audits, transcripts, research docs | Search or summarize before opening |
| 4 | Archive | Superseded plans and historical notes | Load only with a specific reason |

Every governed repo should maintain `docs/context-map.md` as the short routing
map for these tiers. Keep the context map practical: what to load first, what to
load by task type, and what to avoid unless needed.

Assign a budget class before substantial agent work:

| Budget | Use For | Default Behavior |
|---|---|---|
| Tiny | Copy change, simple docs fix, known-file typo | One pass, no broad search |
| Small | One component, endpoint, command, or focused bug | Limited reads and one validation loop |
| Medium | Feature slice or meaningful governance update | Plan, build, verify, handoff |
| Large | Cross-cutting change or unfamiliar subsystem | Scout first, then scoped implementation |
| Strategic | Architecture, security, migration, release readiness | ADR or pathway note, staged work packets, stronger review |

The budget class is a planning aid, not an excuse to under-read security,
architecture, or task-critical material.

## Cache-Friendly Prompting

Stable instructions should live in durable files and remain stable between
turns. Put task-specific details at the end of the prompt or work packet.

Avoid repeatedly pasting or slightly rewriting long global instructions. That
hurts prompt-cache reuse and makes important constraints easier to bury.

For meaningful tasks, prefer a scoped work packet with:

- goal
- context to load first
- files or folders to avoid unless needed
- constraints
- done-when checks
- handoff expectation

## Agent Routing

Use one main editing agent by default. Add subagents only when they reduce
context pollution or provide independent review.

Use read-only scouts for high-volume discovery, log review, dependency survey,
test-gap review, migration impact review, or security review. Scout outputs
must be summaries, not transcripts, and should include scope searched, relevant
findings, file references, smallest useful next action, confidence, and what not
to carry forward.

Do not run overlapping editing agents on the same files unless a human
explicitly coordinates the merge.

## Required Agent Behaviors

### Keep Ambient Context Lean

Root instructions should stay compact. Place detailed guidance near the relevant directory, workflow, standard, or task scope.

Disable or avoid unused tools, connectors, MCP servers, and background integrations when they are not helping the current task. Tool metadata and unused integration context can crowd out useful working memory.

### Lean Startup And Preflight

Start every repo session with the smallest safe orientation:

- check `git status --short`
- read the short repo-local agent instructions
- protect secrets and preserve unrelated work
- identify whether the task triggers deeper governance, architecture, tool, or release checks

For low-risk targeted work, do not run full governance preflight or read every governance document by default. Read the relevant instruction sections and files, make the scoped change, then run task-relevant validation.

Run governance preflight and deeper standards review when the task involves production, deployment, authentication, authorization, payments, secrets, sensitive data, database migrations, customer communications, external side effects, infrastructure or provider settings, destructive actions, autonomous tool use, risk classification, governance policy changes, or release readiness.

Use Graphify for broad architecture, cross-repo routing, dependency or path analysis, unfamiliar large surfaces, and explicit `/graphify` requests. For known files, build or test errors, small scoped edits, and routine docs checks, use normal repo inspection first.

Use specialized plugins, MCP servers, hooks, and provider tools when they are relevant to the current task. Do not make one-off tool use permanent startup load unless repeated need, startup cost, narrow scope, and rollback path are documented.

Temporary lean-out guides may be used during cleanup, but they should not become permanent mandatory startup reads.

Integration note: `/home/adamgoodwin/Downloads/cost_effective_agentic_coding_context_standard.md` was integrated into this standard on 2026-06-13. Do not add that downloaded standard as a new mandatory startup read.

### Work In Phases

Divide substantial work into clear phases such as discovery, planning, implementation, testing, cleanup, and handoff.

At phase boundaries, write or update a short durable summary instead of relying on transcript history. For governed builds, `docs/current-build-pathway.md` is the preferred live handoff location.

For meaningful tasks, separate discovery from implementation from review when
the cost or risk justifies it. Tiny tasks may combine phases, but the agent
should still avoid reading unrelated files.

### Compact Or Reset Before Drift

Do not wait until the context window is nearly exhausted. Summarize or reset when signal quality starts dropping.

Use compaction or a fresh handoff when:

- a major phase completes
- the active objective changes
- the thread starts repeating mistakes
- the agent ignores earlier constraints
- broad exploration is complete and implementation is about to begin
- validation is complete and only handoff remains
- the next step can be stated more clearly than the transcript can preserve it

After compaction, restate critical constraints: architecture decisions, safety limits, acceptance criteria, project risk, validation expectations, and exact next objective.

### Control Repository Scope

Start with the smallest useful file set.

Broad repository exploration is a deliberate cost decision. Use it when ownership, architecture, or impact is unclear, then narrow quickly to the files and symbols needed for the current chunk.

Prefer diffs, targeted excerpts, and focused tests over repeated full-file or full-tree reads.

### Budget Iteration Loops

Every read, reason, edit, and verify loop has a cost.

For routine changes, keep loops short and use fast feedback. For difficult, ambiguous, risky, or security-sensitive work, spend more reasoning budget deliberately and record why.

If a loop stops producing new information, summarize the state, narrow the task, or reset context with a sharper objective.

Stop and reset sooner when an agent rereads the same files without a new reason,
solves adjacent problems, asks to read everything, patches randomly after test
failures, or lets generated files, dependency folders, logs, or transcripts
dominate context.

### Stop Low-Yield Loops

Stopping is part of disciplined agent behavior. A governed agent should stop,
summarize, and hand back control when continued work would mostly consume
context without improving the project state.

Stop or escalate when:

- two or three similar attempts fail without meaningful new insight
- tests keep failing for the same unclear reason
- acceptance criteria conflict or are missing
- architectural uncertainty could create rework
- security, privacy, data integrity, money, deployment, or autonomy risk appears
- the next decision is product judgment rather than coding judgment
- the current chunk's documented stop condition has been reached

When stopping for a blocker, report what failed, what was attempted, likely root
causes, available options, and the recommended next bounded decision.

### Do Not Expand Scope By Momentum

Agents should work from the current build chunk, work packet, or explicit user
request, not from general product ambition.

- Work on one approved task or tightly related sub-task set at a time.
- Record newly discovered useful work as follow-up, not automatic current-scope
  work.
- Do not continue into adjacent backlog items merely because the current task
  went well.
- Do not keep polishing, refactoring, or optimizing after the current definition
  of done is met unless explicitly re-scoped.
- Progress requires changed project state, verification evidence, or a clarified
  blocker; activity alone is not progress.

## Handoff Summary Template

Use this template at phase boundaries, before compaction, or when handing work to another agent:

```md
## Handoff - YYYY-MM-DDTHH:MM:SS-06:00

Objective:

Current state:

Files touched:

Decisions made:

Active constraints:

Validation run:

Known risks or unverified items:

Completion status:

Exact next step:
```

Keep handoffs short enough to be read at the start of the next session.

## Token-Friendly Done

A task is token-friendly done when:

- the agent did not read unrelated areas of the repo
- the prompt or work packet had a clear goal, constraints, context, and done-when
- the work stayed inside the agreed scope
- model, tool, plugin, and subagent use matched task difficulty
- subagent outputs were summaries, not transcripts
- tests or checks were run, or the reason they were not run is documented
- decisions were captured in a pathway note, handoff, ADR, or controlled doc
- the next agent can continue without reading the chat thread
- stale context was compacted, cleared, or summarized before it polluted the next phase

## Reusable Agent Prompt Block

The following block can be adapted into `AGENTS.md`, `AI_BOOTSTRAP.md`, `CLAUDE.md`, or other agent instruction files:

> Operate with strict context hygiene. Keep active context minimal, relevant, current, and recoverable. Work in clear phases. Summarize at phase boundaries. Compact or reset before quality degrades. Re-state critical constraints after compaction. Narrow file scope before reading. Prefer targeted diffs and specific files over whole-repo exploration. Treat tokens as a budget, but do not skip required governance, security, architecture, or task-critical reading. Stop low-yield loops early and reset with a sharper objective.

> Use lean startup: check git state, read short repo-local instructions, and trigger heavy governance, Graphify, plugin, MCP, and release checks by task risk or scope instead of by default.

> Use `docs/context-map.md` to route task-specific context. The repo remembers; agents rent context. Keep always-loaded files compact, give agents scoped work packets for meaningful tasks, and return summaries rather than transcripts from read-only scouts.

> Work from the current approved task, not from general ambition. Do not expand
> scope by momentum. Stop when the task-level definition of done is met, when the
> documented stop condition is reached, or when repeated attempts stop producing
> new evidence. Report `Draft complete`, `Task complete`, `Integration complete`,
> `Release ready`, or `Blocked` only when evidence supports that state. Project
> completion is a human decision.

## User-Facing Guidance

When working with an agent:

- Keep instructions short and specific to the current task.
- Point the agent at the smallest useful files or directories when you know them.
- Break large work into phases.
- Ask for a summary before switching phases or starting a fresh thread.
- Compact or reset before the agent begins drifting.
- Use deep reasoning for hard, ambiguous, risky, or architectural questions.
- Stop low-yield loops and restart with a sharper prompt.

## Review Checklist

Before declaring substantial agent work complete, check:

- required governance files were read for the task
- working scope was narrowed after discovery
- broad scans were justified or avoided
- active plan and next step are durable
- validation evidence is recorded
- open risks and unverified items are stated
- the completion status is honest and evidence-backed
- low-yield loops stopped with a clear blocker or next decision
- handoff notes are short enough for another agent to use
