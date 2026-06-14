# Durable Development Engineering Policy

Document type: risk-scaled operating policy
Audience: coding team, contractors, AI coding agents, technical reviewers, and project leads
Applies to: internal tools, SaaS products, websites, automations, AI-assisted builds, scripts, prototypes intended to become products, and production systems.

## Purpose

This policy defines how software must be designed, built, reviewed, tested, secured, deployed, and maintained.

The goal is not to slow the team down. The goal is to prevent the expensive mess that comes from fast, careless building: fragile code, hidden security holes, unclear ownership, dead documentation, mystery bugs, impossible rollbacks, and systems nobody wants to touch six months later.

The standard is simple: build the smallest useful thing in the safest durable way.

## How To Apply This Policy

This policy defines the default direction of travel for good engineering work. Apply it through the project's `risk_tier`, `governance_level`, and active build pathway rather than as identical ceremony for every change.

- Low-risk documentation, scripts, experiments, and prototypes may satisfy this policy with lightweight notes, manual validation, and clear limits.
- Medium-risk work should add repeatable checks and documented release or operating expectations where the project surface justifies them.
- High-risk and critical work need stronger review, automated validation, rollback planning, security review, and retained evidence.
- If a control is not practical for a specific project or chunk, record the reason, compensating control, and review point instead of silently ignoring it.

The policy should make clean execution steadier. It should not block small, reversible progress when risk is low and the tradeoff is explicit.

## Core Engineering Rules

### Long-term code health comes first

Every change must improve or preserve the long-term health of the codebase.

A change must not be merged if it makes the system harder to understand, test, secure, operate, or safely change unless the tradeoff is explicit, approved, and documented.

### Working code is not enough

A change is not complete simply because it appears to run.

It must also have risk-appropriate review or self-review, validation, security consideration, observability where useful, documentation where needed, architecture fit, and a known rollback or recovery expectation.

### Prefer clear, boring, proven solutions

The default solution should be simple, mature, and easy to explain.

Do not add custom frameworks, clever abstractions, exotic libraries, or unnecessary infrastructure unless the team can clearly explain why the standard option is not enough, what risk the alternative introduces, how it will be tested, how it will be maintained, and how it can be replaced later.

### Keep changes small

Large pull requests are high-risk.

A pull request should normally do one thing: one feature, one bug fix, one refactor, one dependency update, or one migration. Do not combine unrelated work.

### Delete dead code

Dead code, unused files, abandoned features, stale comments, and misleading documentation must be removed or clearly marked for removal.

Keeping old material "just in case" creates confusion and risk.

## AI-Era Software Fundamentals

AI-assisted development does not make code quality less important. It makes code quality more important.

Bad code is not cheap. Bad code becomes more expensive when AI agents rapidly build on top of weak structure, unclear naming, shallow modules, duplicated business rules, and missing tests.

The framework therefore expects fundamentals-first software:

- shared design concept before meaningful coding
- clear domain language used consistently in code, docs, tests, UI, prompts, and runbooks
- deep modules with simple interfaces
- small vertical slices
- fast feedback loops
- test-first or test-near development for important behavior
- deliberate interface design
- visible errors, logs, and validation
- no fake claims of production readiness
- continuous small investment in system design

The agent should not blindly regenerate code from specs while ignoring the condition of the codebase. When generated code makes the system harder to understand, test, secure, operate, or modify, the agent must flag the design issue and recommend the smallest safe improvement.

The central question is not only "Did the code run?" The central question is: "Is this codebase becoming easier or harder to change?"

### Shared design concept before coding

Before meaningful implementation work, reach a shared design concept.

If a request is broad, ambiguous, risky, or likely to affect architecture, data, permissions, automation, production, or user trust, clarify enough of the following to build safely:

- problem being solved
- user or customer
- desired behavior
- non-goals
- important workflows
- data involved
- system boundaries
- acceptance criteria
- failure modes
- risk
- rollback or recovery expectations

Do not create a plan just to appear productive. Create the plan only after the design concept is clear enough for risk-appropriate implementation.

For unclear, high-risk, or important work, the owner may ask for a focused design interview before planning or coding. The agent should ask only the questions needed to clarify behavior, boundaries, risks, and acceptance criteria, then stop when the shared design concept is clear enough for risk-appropriate implementation.

### Feedback loops are the speed limit

The rate of feedback is the speed limit.

Do not generate large amounts of code before checking types, tests, linting, runtime behavior, or user-visible results.

Work in small deliberate steps:

1. Write or update a test, check, or validation case.
2. Make the smallest useful change.
3. Run the fastest relevant feedback loop.
4. Inspect the result.
5. Refactor if needed.
6. Continue.

Do not outrun the feedback loop. Do not claim success without running the checks that are practical for the change, or clearly stating why validation could not be run.

### Test-first or test-near development

For meaningful business logic, important workflows, permissions, data transformations, AI tool actions, and bug fixes, prefer test-first or test-near development.

A failing test, executable check, or clear validation case should exist before or alongside the implementation.

Do not require full formal TDD for every tiny change. Use risk-based judgment.

Use stronger test-first or test-near behavior for authorization, billing, money movement, data migrations, workflow state transitions, calculations, AI tool permissions, destructive actions, external integrations, recurring bug fixes, public API contracts, and security-sensitive code.

Good tests verify important behavior, not implementation trivia.

### Deep modules over shallow modules

Prefer deep modules with simple interfaces over shallow modules with complex interfaces.

A good module hides meaningful complexity behind a small, clear boundary.

A weak module exposes too much, does too little, or exists only as pass-through glue.

Every module must earn its place. It should own a real responsibility, hide complexity, protect a boundary, or improve testability. If it does none of those things, do not create it.

Challenge shallow modules when you see:

- many tiny files that each do almost nothing
- wrappers that only rename another call
- pass-through functions with no validation, authorization, transformation, or error handling
- modules that expose many functions but hide little complexity
- business rules scattered across UI, API, database, and automation code
- unclear boundaries between domain logic, persistence, presentation, and integration
- generic service, helper, manager, or utility modules that mix unrelated responsibilities

### No flimsy layers

Do not create shallow layers that only pass data through without owning a clear responsibility.

A layer, service, helper, wrapper, adapter, hook, or utility must justify its existence by isolating a real concern such as validation, authorization, persistence, integration, transformation, orchestration, presentation, or error handling.

Avoid premature abstraction before the second or third real use case exists. Avoid future-proof architecture that makes the current feature harder to understand.

### Design the interface, delegate the implementation

The owner, reviewer, and planning agent should pay special attention to module interfaces, public contracts, data shapes, permissions, side effects, and boundaries.

AI may assist with implementation details, but important interfaces must be deliberate and reviewable.

A good interface should make the module easy to test, easy to call, hard to misuse, and safe to change internally.

For important modules, define purpose, inputs, outputs, errors, permissions, side effects, persistence touched, external services used, and tests at the boundary.

### Invest in design every day

Every meaningful change should invest in the design of the system.

Do not only make the requested change. Leave the touched area slightly clearer, better named, better tested, easier to understand, or easier to modify.

This is not permission for broad rewrites. Prefer small, safe design improvements near the work being performed.

## Stack Guidance

This policy is stack-agnostic. Common defaults include Next.js, React, TypeScript, Tailwind CSS, Python, Supabase/Postgres, Vercel, GitHub, GitHub Actions, AI coding tools, automation tools, and Microsoft 365/SharePoint where business workflow requires it.

These tools are acceptable defaults when they fit the project, but they are not mandatory. The team must still choose the best tool for the specific job.

### Next.js, React, and TypeScript

When using Next.js, React, and TypeScript:

- Use TypeScript strictness where practical.
- Use the current Next.js App Router unless there is a reason to use another pattern.
- Keep server-side business logic out of client components.
- Validate data at server boundaries.
- Use server-side authorization for sensitive actions.
- Use route handlers and server actions carefully and test them.
- Avoid oversized React components.
- Separate UI state, server state, and domain rules.
- Use ESLint and formatting checks.
- Use accessibility basics from the beginning.
- Use error, loading, and empty states intentionally.
- Use environment variables for deployment-specific configuration.
- Keep secrets server-side only.

### Supabase and Postgres

When using Supabase or Postgres:

- Treat the database as a core security boundary.
- Enable and test Row Level Security where client-accessible tables are involved.
- Never rely only on frontend filtering for access control.
- Use migrations for schema changes.
- Keep schema changes reviewable.
- Test policies, permissions, and edge cases.
- Use indexes intentionally, especially around RLS policy performance.
- Do not expose service-role keys to browsers.
- Store secrets securely.
- Keep audit fields for important records.
- Avoid storing duplicate facts unless there is a clear reason.

### Hosted Deployment

When using Vercel or a similar hosted deployment platform:

- Use preview deployments for pull requests where available.
- Keep production deployments protected.
- Use environment-specific configuration.
- Avoid manual production changes.
- Add monitoring and error tracking for production apps.
- Know the rollback path.
- Avoid platform lock-in unless the benefit is worth it.

### Python

When using Python:

- Use type hints where practical.
- Use a formatter and linter.
- Use virtual environments.
- Use locked dependencies.
- Add tests for business logic.
- Validate external inputs.
- Keep scripts idempotent when possible.
- Avoid silent failure.
- Log operationally useful events.

### AI-Agent and Tool Workflows

When building AI-assisted systems:

- Treat AI output as untrusted.
- Validate tool arguments before execution.
- Require human approval for destructive actions.
- Scope tools narrowly.
- Log tool calls and outcomes.
- Prevent retrieved documents or prompt text from overriding safety, permissions, or system rules.
- Separate planning from execution for high-risk workflows.
- Add dry-run mode where possible.
- Never let an AI agent silently delete, send, purchase, deploy, modify production data, or change permissions.

## Tool Selection Policy

The team must choose tools intentionally, not because they are popular, new, or convenient for a demo.

Before adopting a major tool, library, framework, platform, database, queue, AI service, hosting layer, or automation system, assess:

| Criterion | Required question |
|---|---|
| Fit | Does it solve the actual problem cleanly? |
| Maturity | Is it stable enough for the project risk level? |
| Maintenance | Is it actively maintained? |
| Community | Is there enough adoption and support? |
| Security | Does it have a reasonable security posture? |
| License | Is the license acceptable? |
| Lock-in | Can we leave later without a rewrite? |
| Cost | What does it cost now and at scale? |
| Complexity | Does it reduce or increase system complexity? |
| Team capability | Can the team operate and debug it? |
| Integration | Does it fit the existing architecture? |
| Observability | Can we monitor and troubleshoot it? |
| Portability | Can it run in the environments we need? |
| Failure mode | What happens when it is down, slow, or wrong? |

Classify each tool:

| Level | Meaning |
|---|---|
| Approved default | Safe default for common use. |
| Approved with review | Good tool, but needs project-specific justification. |
| Experimental | Allowed in prototypes only. |
| Restricted | Requires explicit approval. |
| Prohibited | Not allowed. |

For meaningful tools, create a short tool decision record covering the problem, options compared, selected tool, rationale, risks, cost, lock-in and exit plan, security notes, and operating notes.

## Required Development Flow

Every meaningful change must follow this flow.

### Frame the problem

Before coding, define:

- User or business problem.
- Desired outcome.
- Non-goals.
- Acceptance criteria.
- Data touched.
- Security and privacy impact.
- Failure modes.
- Rollback expectations.

### Design the change

A short design note, ADR, or build-pathway note is required for changes involving authentication, authorization, sensitive data, payment or financial records, public API contracts, database schema, infrastructure, production deployment, AI agents with tool access, background jobs, destructive actions, new major dependencies, or anything difficult to roll back.

### Build in small vertical slices

Prefer a complete thin slice over a large unfinished layer.

A good slice includes the UI or API entry point if applicable, validation, business logic, persistence or integration, tests, error handling, and basic observability.

### Review

Every non-trivial change requires review appropriate to its risk. For low-risk solo work, a documented self-review and validation note may be enough. For high-risk and critical work, use an independent reviewer or explicit approval path.

Reviewers must check correctness, simplicity, architecture fit, security, authorization, input validation, error handling, tests, data impact, observability, and rollback path.

### Test

Testing must match the risk.

Required test types may include unit tests, integration tests, end-to-end tests, contract tests, security tests, migration tests, performance tests, and manual verification.

Manual testing alone is not enough for important behavior.

### Release

Before production release:

- CI checks pass.
- Tests pass.
- Required reviews are complete.
- Security findings are addressed or accepted.
- Rollback path is known.
- Monitoring is in place.
- Release notes are written if users or operators are affected.

## Definition of Ready

A meaningful implementation task is ready when the team has enough clarity for the risk involved:

- Clear problem statement.
- Owner.
- Acceptance criteria.
- Known dependencies.
- Relevant design notes or links.
- Security and privacy notes where needed.
- Test expectations.
- Rollback expectations for risky work.

If "done" cannot be explained before starting, either narrow the task or record the uncertainty as part of the chunk.

## Definition of Done

A change is done only when:

- Acceptance criteria are met.
- Code is reviewed or self-reviewed at a level appropriate to the risk.
- Automated checks pass.
- Tests are appropriate to the risk.
- Security and privacy concerns are addressed.
- Errors are handled.
- Logs and metrics are added where useful.
- Documentation is updated.
- Dead code is removed.
- Rollback path is known.
- The result can be operated and debugged.

"Works locally" is not done.

## Definition of Shipped

Ship readiness is a separate evidence gate from Definition of Done.

Use [Ship-Ready Engineering Standard](../standards/ship-ready-engineering-standard.md) before merging, releasing, handing off, or declaring a meaningful product increment complete. That standard verifies the user outcome, last-mile UX states, security and data safety, tests and verification, operational readiness, clean finish, known risks, and rollback path.

## Pull Request Policy

Pull requests must be small enough to review properly. If a pull request is too large to understand in one review session, split it.

A pull request should cover:

- Summary.
- Why the change is needed.
- Scope.
- Out of scope.
- Testing performed.
- Risk level.
- Rollback path.
- Notes for reviewer.

A pull request must not merge if it breaks the build, fails tests, lacks meaningful test coverage for meaningful behavior, exposes secrets, weakens auth or permissions without explicit review, adds risky dependencies without review, creates unclear ownership, has unclear rollback for risky changes, or makes the codebase materially harder to maintain.

## Repository Standard

Every governed repo should move toward this golden-path structure as the project matures and risk justifies it:

- `README.md`
- `CONTRIBUTING.md`
- `CODEOWNERS`
- `CHANGELOG.md`
- `SECURITY.md`
- `.env.example`
- `docs/architecture.md`
- `docs/decisions/`
- `docs/runbooks/`
- `src/`
- `tests/`
- `.github/workflows/`
- `.github/pull_request_template.md`

Minimum expectations:

- README explains how to run, test, build, deploy, and troubleshoot.
- CONTRIBUTING explains workflow.
- SECURITY explains how vulnerabilities and secrets are handled.
- Architecture docs explain system shape and trust boundaries.
- Runbooks explain common operational failures.
- ADRs document meaningful decisions.

## Coding Standards

Names must reveal intent. Avoid meaningless names like `data`, `thing`, `stuff`, `manager`, `helper`, `misc`, and `utils`. Use domain-specific names.

Functions should do one coherent thing. Avoid functions that mix validation, authorization, business logic, persistence, UI formatting, logging, and external calls.

Modules should have one reason to change. Avoid dumping unrelated behavior into shared utility files.

Comments should explain why, not restate what the code does.

Errors must not be swallowed. The system should fail clearly, log useful context, return safe user-facing messages, preserve internal debugging detail, and avoid leaking secrets or private data.

Configuration must not be hardcoded. Use environment variables or managed config for secrets, URLs, feature flags, service credentials, deployment-specific settings, timeouts, and rate limits.

## Code Quality Review Checklist

For meaningful code changes, check:

1. Is the responsibility of each changed file clear?
2. Does each function do one coherent thing?
3. Are names domain-specific and easy to search?
4. Are inputs validated at the boundary?
5. Is authorization enforced server-side where relevant?
6. Are errors handled without being swallowed?
7. Are important behaviors covered by tests?
8. Is logging useful without leaking secrets?
9. Does this avoid unnecessary dependencies?
10. Is there a rollback or recovery path for risky changes?
11. Would a new developer understand this code in six months?
12. Did this change make the next correct change easier?

## Refactor Triggers

The agent should recommend refactoring when it sees:

- the same business rule in more than one place
- a function that needs comments to explain basic flow
- a component or module that has more than one reason to change
- repeated copy-paste with small edits
- growing conditional branches that should become explicit states
- unclear ownership between UI, API, database, automation, and domain logic
- data shapes passed around as loose dictionaries or untyped objects
- tests that only check mocks instead of behavior
- errors caught and ignored
- code that cannot be safely tested without production access
- modules that expose a large interface while hiding little complexity
- generated code that is hard for humans and AI to navigate

The agent should not automatically refactor everything it sees. It should flag the issue, explain the risk, recommend the smallest safe improvement, and proceed only if the change fits the current task or the owner approves the refactor.

## Security Policy

Security is required from the start.

Every project must address, at a level appropriate to its risk and feature surface:

- Authentication.
- Authorization.
- Input validation.
- Output encoding.
- Secret management.
- Dependency security.
- Secure logging.
- Secure error handling.
- Data protection.
- Backup and recovery.
- Audit trails for important actions.

Authorization must be enforced server-side. Frontend hiding is not security.

Secrets must never be committed, logged, pasted into issues, or exposed to browsers.

All dependencies must be justified, scanned, and kept current.

File upload and download features must validate type, size, access, storage location, and download permissions.

AI systems must never be granted broad destructive power without human approval and hard permission boundaries.

## Supply Chain and CI/CD Policy

Production, high-risk, and critical repos should use:

- Branch protection.
- Required reviews.
- Required status checks.
- Dependency scanning.
- Secret scanning.
- Static analysis where practical.
- Lockfiles.
- Least-privilege CI tokens.
- Protected production deployments.

CI/CD for deployable systems should build from clean environments, install from lockfiles, run tests before deploy, avoid long-lived secrets, separate build and deploy permissions where practical, produce traceable artifacts, and prevent unreviewed production deployment.

## Testing Policy

Test important behavior, not implementation trivia.

Prioritize tests for:

- Business rules.
- Authorization.
- Validation.
- Error paths.
- Data transformations.
- Critical user journeys.
- Workflow state transitions.
- Migrations.
- Security-sensitive code.
- Bug fixes.

Good tests are deterministic, fast enough to run often, readable, behavior-focused, and meaningful when they fail.

## Observability Policy

Production systems must be debuggable.

Minimum expectations:

- Structured logs.
- Error tracking.
- Health checks.
- Key metrics.
- Request or correlation IDs.
- Deployment markers.
- Alerts for user-impacting issues.
- Runbooks for known failures.

Logs must not leak secrets, tokens, payment details, or sensitive personal data.

## Documentation Policy

Documentation must reduce future confusion.

Document how to run, deploy, test, and recover; why major decisions were made; public contracts; security assumptions; and known limitations.

Delete or update documentation that contradicts the code.

## AI Coding Agent Policy

AI coding agents must follow this instruction block unless overridden by a more specific task:

```md
You are working in an existing codebase. Do not rewrite the project unless explicitly instructed.

First:
1. Inspect the repository structure.
2. Identify relevant files.
3. Explain the current flow.
4. Propose the smallest safe change.
5. Identify risks before editing.

While coding:
- Preserve existing architecture unless there is a clear reason to change it.
- Keep changes small and reviewable.
- Do not introduce unnecessary dependencies.
- Do not remove behavior without evidence.
- Add or update tests for behavior changes.
- Validate inputs and outputs.
- Enforce permissions server-side.
- Do not hide failures.
- Do not fabricate APIs, files, test results, or successful commands.
- Run available checks when possible.

Before finishing:
- Summarize files changed.
- Summarize tests run.
- Identify unverified items.
- Identify risks.
- Identify follow-up work.
```

AI-generated code must be reviewed like human-written code.

## Anti-Patterns That Must Be Challenged

Stop and reassess when you see:

- Giant pull requests.
- Unreviewed production hotfixes.
- UI-only authorization.
- Secrets in code.
- Catch-all error swallowing.
- Repeated copy-paste.
- Dead code kept indefinitely.
- Business rules duplicated across layers.
- Untyped blobs passed everywhere.
- Manual production deploys.
- Database changes with no rollback thought.
- AI-generated code merged without review.
- New dependencies for trivial work.
- Documentation that sounds current but is wrong.
- Specs changed repeatedly while generated code quality is ignored.
- Code regenerated over and over without inspecting design degradation.
- Large AI-generated diffs with no clear review path.
- Shallow module sprawl.
- Verbose code that hides weak domain understanding.
- Tests added only after the implementation is already tangled.
- Mocks that test implementation trivia instead of behavior.
- Domain terms used inconsistently across code and docs.
- AI agents making design decisions without recording rationale.
- Implementation proceeding before the design concept is shared.
- Code that is hard for both humans and AI to navigate.
- Generated code merged because it looks plausible.
- Fabricated test results or assumed command success.
- Changes that make the system harder to debug.

## Golden Path for Any Repo

Every repo should move toward:

1. Clear README.
2. One-command local setup.
3. `.env.example`.
4. Formatting.
5. Linting.
6. Type checking where available.
7. Unit tests.
8. Integration tests for key boundaries.
9. CI on every pull request.
10. Branch protection.
11. Dependency scanning.
12. Secret scanning.
13. Code owners.
14. Pull request template.
15. Architecture note.
16. ADR folder.
17. Security policy.
18. Deployment pipeline.
19. Monitoring.
20. Runbook.
21. Changelog and release notes.
22. Regular cleanup.

## Final Policy Rule

When in doubt, choose the option that makes the next correct change easier: smaller, clearer, safer, better tested, easier to review, easier to reverse, and easier to explain.
