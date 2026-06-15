# AI Bootstrap Rules

## Purpose
This repository must be workable by Claude, Codex, and local coding agents
using the same operating rules.

## Change rules
- Prefer editing existing files over creating duplicate replacements.
- Keep changes small and reversible.
- Do not rename or move core files unless explicitly instructed.
- Explain new dependencies before adding them.
- Update docs when behavior, interfaces, or architecture change.
- Build the smallest useful thing in the safest durable way.
- Treat "works locally" as incomplete until validation, security/privacy impact, documentation, and rollback expectations are addressed.

## Governance
- For ordinary scoped work, start with `git status --short`, this file, and the specific files or errors relevant to the task.
- Read `START_HERE.md` and follow `docs/current-build-pathway.md` for material implementation work, unclear scope, handoffs, or changes that affect the active plan.
- Use `docs/context-map.md` when deciding which docs, standards, or source areas to load.
- Use `docs/standards/README.md` as the standards map for coding and release work.
- Review `docs/standards/engineering-governance-by-use-case.md`, confirm the work matches `use_case.primary`, and do not override the selected `risk_tier` or `governance_level`.
- Review `docs/policy/durable-development-engineering-policy.md` before meaningful implementation work.
- Review `docs/standards/ship-ready-engineering-standard.md` before declaring meaningful work complete.
- Use `docs/standards/context-hygiene-standard.md` for long sessions, scoped repository reads, compaction, and handoffs.
- Run governance preflight for material or risk-triggering work:
  `bash scripts/governance-preflight.sh`
- Governance triggers include production, deployment, authentication, authorization, payments, secrets, sensitive data, database migrations, customer communications, external side effects, infrastructure or provider settings, destructive actions, autonomous tool use, risk classification, governance policy changes, or release readiness.
- Review `project-control.yaml` for governance level, risk tier, and required controls.
- Do not add temporary lean-out plans or one-off tool notes as permanent mandatory startup reads.
- Record deviations as exceptions rather than ignoring them.
- Capture the work timestamp with `date -Iseconds` and use it in material work notes, decisions, validation, and handoffs.

## Work chunking
- Work in context-window-friendly chunks.
- Each chunk should have one objective, clear input files, clear output files or behavior, and explicit validation.
- Each meaningful chunk should state its target completion state: `Draft complete`, `Task complete`, `Integration complete`, `Release ready`, or `Blocked`.
- Project completion is a human decision. Agents may report only bounded completion states when criteria and verification evidence support them.
- Stop when the chunk's definition of done is met, when its stop condition is reached, or when repeated attempts stop producing new evidence.
- In `docs/current-build-pathway.md`, label active and planned chunks as second-level headings using spelled-out numbers, such as `## Chunk One - Short Objective`, `## Chunk Two - Short Objective`, and `## Chunk Three - Short Objective`.
- Update `docs/current-build-pathway.md` when the active chunk or next handoff changes.

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

Use lean startup: keep always-on checks short, and trigger heavy governance, Graphify, plugin, MCP, and release checks by task risk or scope.

The repository remembers. Agents rent context. Keep work packets, scout summaries, validation, and handoffs durable enough that the next agent does not need the chat thread.

Keep read-only scout outputs summary-only.

## Graphify Policy

Use the canonical Graphify governance file at `/home/adamgoodwin/code/Tools/graphify/docs/agent-governance.md`.

Before broad source exploration, architecture analysis, dependency tracing, unfamiliar large-surface work, or cross-repo planning, use Graphify first and reference `/home/adamgoodwin/code/Tools/graphify/workspace/out/graph.json`. Use the workspace graph for cross-repo routing. For known files, build or test errors, small scoped edits, or routine docs checks, use normal repo inspection first. When a new repo becomes active, set up repo-local Graphify with `graphify-setup-project /path/to/repo`.

For full semantic repo graphs in heavy active repos, run `/graphify /path/to/repo` from Claude Code. Current Graphify skills can use Claude Code subagents when no Gemini key is set, so policy should constrain token burn through per-repo scope, caching, strict ignores, and cheap updates rather than hard-coding a provider or extraction backend.

After code changes, update the relevant graph with `graphify update . --no-cluster`, or update the workspace graph for cross-repo work.

Preserve existing secret-handling rules: do not index, print, summarize, or commit secrets or environment files.

## Commands

- Install backend:  `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Install frontend: `cd frontend && npm install`
- Dev (both):       `bash scripts/start.sh`  (launches uvicorn on :8000 and Vite on :5173)
- Type-check:       `cd frontend && npx tsc --noEmit`
- Build frontend:   `cd frontend && npm run build`
- Validate backend: `cd backend && .venv/bin/python -c "import main; print('OK')"`
- Test:             No formal test suite yet. Smoke-test via `curl http://localhost:8000/health`.

## Document control
- Architecture decisions go in `docs/`
- If code behavior changes, update the nearest controlled document in the same task

## Completion standard
A task is not complete until relevant validation is run or a blocker is clearly stated. Use honest completion labels: `Draft complete`, `Task complete`, `Integration complete`, `Release ready`, or `Blocked`. Do not declare a whole project complete unless an authorized human has made that decision.
