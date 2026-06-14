# Ship-Ready Engineering Standard

Document type: engineering standard
Status: active
Owner: Project owner or human technical lead
Audience: project owners, coding teams, contractors, AI coding agents, technical reviewers, product reviewers, and release reviewers
Applies to: internal tools, SaaS products, websites, automations, AI-assisted builds, prototypes intended to become products, and production systems.

## Purpose

Good code is not the finish line.

Good code means the implementation is technically respectable. Ship-ready code means the product increment can survive a real user, a real deployment, a bad input, a confused operator, a slow network, a security review, and the next change.

The standard is:

> Build the smallest useful thing in the safest durable way, then prove it is ready to ship with evidence.

This standard adds the last-mile gate that sits after normal implementation quality:

```text
Definition of Ready -> Definition of Done -> Definition of Shipped
```

- Definition of Ready answers: Should this work start?
- Definition of Done answers: Is the engineering change complete?
- Definition of Shipped answers: Would we let a real user touch this without apologizing?

A pull request or agent session may meet Definition of Done and still fail Definition of Shipped.

This standard also defines honest completion language for agent-assisted work.
The purpose is to prevent both premature closure and endless iteration. Agents
should be able to say exactly what level of completion has been reached without
pretending the whole project is finished.

## Relationship To Other Standards

This standard does not replace:

- `docs/policy/durable-development-engineering-policy.md`
- `docs/standards/engineering-governance-by-use-case.md`
- `docs/domain-language.md`
- `project-control.yaml`

Use the durable development policy for long-term code health, engineering practice, test discipline, review, security, and maintainability. Use the use-case standard to scale controls by project type and risk signal. Use this standard as the practical ship-readiness gate before merging, releasing, handing off, or declaring a product increment complete.

The human-selected `risk_tier` and `governance_level` in `project-control.yaml` remain the source of truth. This standard can recommend stronger evidence, review, or release checks, but it does not silently change governance level.

## Clean Distinction

| Category | Good code | Ship-ready code |
|---|---|---|
| Primary test | Does the code work? | Does the user outcome work under real conditions? |
| Scope | Function, component, endpoint, page, or script | User journey, data flow, release path, and support path |
| Proof | Tests, types, lint, and build pass | Acceptance criteria are mapped to evidence |
| Security | No obvious insecure code | Server-side authorization, object-level access, runtime validation, safe logs, and no secrets |
| UX | UI renders and basic actions work | Loading, empty, success, error, disabled, unauthorized, duplicate-submit, mobile, accessibility, and clear copy are handled |
| Operations | It deploys | It can be monitored, debugged, rolled back, and supported |
| Documentation | Notes exist | Setup, environment variables, deployment, architecture, limitations, and release notes are current where relevant |
| Agent output | Agent says it is complete | Evidence shows what was verified and what remains unverified |

Good code is an engineering artifact. Ship-ready code is a product increment.

## Completion States

Not all useful progress has the same completion meaning. Use these labels in
work packets, pathway updates, handoffs, pull requests, and finish reports.

| State | Meaning | Who May Declare It |
|---|---|---|
| `Draft complete` | Initial implementation exists, but known tests, hardening, edge cases, UX refinement, documentation, or integration work remains. | Builder or agent, with known gaps stated. |
| `Task complete` | The scoped task acceptance criteria are met, required checks passed or are explicitly marked not run, and documentation or handoff notes are updated. | Builder or agent, when evidence supports it. |
| `Integration complete` | The task works in the surrounding system and does not obviously break dependent flows, contracts, data paths, or operator workflows. | Reviewer, owner, or agent with integration evidence. |
| `Release ready` | Human review is complete, quality gates are satisfied, residual risks are understood, and release or hold decisions are documented. | Owner, reviewer, or delegated release authority. |
| `Project complete` | The broader product or project has met its owner-approved scope, quality, release, and handoff expectations. | Human owner or explicitly delegated human authority only. |
| `Blocked` | The current task cannot proceed safely because information, access, decisions, dependencies, or repeated failures prevent meaningful progress. | Builder or agent, with failure analysis and next decision needed. |

Project completion is a human decision. Agents must not declare a whole project
complete on their own. Agents may declare bounded states such as `Draft
complete`, `Task complete`, `Integration complete`, `Release ready`, or
`Blocked` only when the documented criteria and verification evidence support
that label.

### Completion State Rules

- Do not collapse all progress into "done."
- Do not use `Task complete` when only draft implementation exists.
- Do not use `Release ready` when human review, risk acceptance, deployment
  readiness, or rollback evidence is still missing.
- Do not use `Project complete` unless an authorized human explicitly declares
  it.
- Prefer `Draft complete with known gaps` over a vague success claim.
- Prefer `Blocked with options` over repeated low-yield attempts.
- If completion criteria are ambiguous, stop and clarify the task boundary
  before claiming completion.

### Recommended Finish Report Shape

Use this compact status block at the end of meaningful work:

```text
Status: Draft complete / Task complete / Integration complete / Release ready / Blocked
Completion target: <the state this work was trying to reach>
Checks run: <tests, scripts, reviews, manual checks>
Result: <pass/fail/partial>
Known gaps: <unverified items, risks, deferred work>
Next action: <the next bounded decision or task>
```

The status must match the evidence. A passing local test run may support `Task
complete`; it does not by itself prove `Release ready` or `Project complete`.

## Non-Negotiable Rules

These rules apply to human and AI coding work:

1. The repo is the source of truth. Durable files, issue or PR records, CI logs, ADRs, handoffs, and governance files outrank memory or guesses.
2. The human-selected governance level must not be overridden automatically.
3. Working locally is not done.
4. Scope does not expand silently.
5. One bounded task should not mix unrelated feature work, refactoring, dependency updates, migrations, and visual redesign.
6. Verification must not be fabricated.
7. New dependencies, tools, services, or platforms need meaningful justification.
8. Security-sensitive changes require escalation and human review where risk warrants it.
9. Server-side authority wins over UI hiding, client-only route guards, or obscured IDs.
10. Runtime validation is required at trust boundaries.
11. Every meaningful change needs rollback or recovery thinking.
12. Finish reports must include evidence, known risks, unverified items, and rollback path.
13. AI-generated code must be reviewed like human-written code.
14. User-facing work is incomplete without relevant states, copy, accessibility basics, and recovery paths.

## Required Development Lifecycle

Every meaningful change should move through this lifecycle at a depth appropriate to risk:

1. Frame the problem.
2. Classify risk.
3. Create or confirm the work packet.
4. Design the smallest safe slice.
5. Build.
6. Test.
7. Review.
8. Finish product polish.
9. Run the ship-readiness gate.
10. Release or hold.
11. Operate and learn.
12. Capture handoff.

## Definition Of Ready

A task is ready only when it has enough clarity for the risk involved:

- clear problem statement
- owner
- priority or urgency
- acceptance criteria
- known dependencies
- non-goals
- relevant designs, diagrams, links, or repo context
- data touched
- security and privacy notes where applicable
- test expectations
- rollback expectations for risky work
- product-specific finish expectations
- target completion state for the current chunk
- stop condition or escalation trigger

If the coder cannot explain what "done" means before starting, narrow the task or record the uncertainty in the active chunk.

## Definition Of Done

A change is done only when:

- acceptance criteria are met
- code is reviewed or self-reviewed at a level appropriate to risk
- automated checks pass
- tests match the risk
- security and privacy concerns are addressed
- errors are handled
- logs or metrics are added where useful
- documentation is updated where needed
- dead code and temporary scaffolding are removed or tracked
- rollback path is known
- the result can be operated and debugged
- the finish report states what was not verified
- the finish report uses an honest completion state

"Works locally" is not done.

## Definition Of Shipped

A change is ship-ready only when the following are true at a depth appropriate to the project risk.

### User Outcome Proven

- The stated user, operator, or business outcome works end to end.
- Acceptance criteria are mapped one by one to evidence.
- The smallest useful version is complete.
- The product intent has not been lost in implementation.

### UX States Complete

For every changed user-facing flow, check relevant states:

- loading
- empty
- success
- error
- unauthorized or permission denied
- disabled or pending
- duplicate-submit prevention
- slow network or retry-sensitive behavior
- mobile and responsive layout
- keyboard and focus behavior
- accessible labels
- clear user-facing copy
- no internal implementation jargon

### Security And Data Safe

- Server-side authorization is enforced.
- Object-level access is checked where records are user, tenant, role, or organization scoped.
- Inputs are validated at runtime.
- Secrets are not exposed.
- Logs do not leak sensitive data.
- Error messages are safe and useful.
- File, payment, auth, AI-tool, and automation flows receive extra review where applicable.
- Database row-level security or equivalent controls are tested where applicable.

### Tests And Verification Complete

- Unit tests cover important logic.
- Integration tests cover important boundaries.
- End-to-end or manual verification covers critical journeys.
- Security-sensitive behavior is tested.
- Regression tests are added for bug fixes where practical.
- Test output is included in the finish report.
- Any tests not run are listed honestly.

### Operationally Ready

- Errors are useful and safe.
- Logs, metrics, request IDs, or operation IDs exist where useful.
- Environment variables are documented.
- Deployment path is known.
- Rollback path is known.
- Feature flag, kill switch, or hold path exists for risky changes where practical.
- Runbook or operator notes exist where needed.

### Clean Finish

- No unrelated refactors.
- No unexplained TODOs.
- No dead code left behind.
- No placeholder copy unless explicitly approved.
- Documentation is current.
- Known limitations are stated honestly.

### Evidence Package Attached

The PR, handoff, or finish report includes:

- files changed
- what changed
- commands run
- test results
- screenshots, preview links, or API examples where useful
- what was not verified
- risks
- rollback path
- follow-up work

## Last-Mile Product Finish Checklist

This is the section coders and AI agents most often miss.

### UI And Interaction States

Every changed screen or interaction should answer:

| State | Required question |
|---|---|
| First load | What does the user see while data is loading? |
| Empty | What does the user see when there is no data yet? |
| Success | Does the user know the action worked? |
| Error | Does the user know what failed and what to do next? |
| Unauthorized | Does the user get a safe, clear permission message? |
| Pending | Are buttons disabled or guarded while work is in progress? |
| Duplicate click | Can the user accidentally submit twice? |
| Slow network | Does the UI remain understandable during delay? |
| Offline or degraded | Does the product fail gracefully where relevant? |
| Partial data | Is stale or incomplete data labelled honestly? |

### Copy And Language

User-facing copy must be plain, specific, calm, actionable, consistent with product vocabulary, free of developer jargon, and honest about limitations.

Avoid copy like:

```text
Mutation failed.
```

Prefer copy like:

```text
We could not save the group. Check your connection and try again.
```

### Visual Polish

Visual polish means clarity, not decoration. Check spacing, hierarchy, primary actions, secondary actions, destructive action treatment, responsive layout, readable surfaces, useful motion, and whether charts or cards genuinely improve understanding.

### Accessibility Basics

Changed user-facing flows should check semantic HTML, labels, keyboard navigation, visible focus states, useful alt text, contrast, touch target size, modal focus behavior, and field-associated error messages where applicable.

### Mobile And Responsive

For user-facing web work, check at least narrow mobile, tablet-ish, and desktop widths when practical. Primary actions should be reachable, long content should remain usable, tables should not break layout, sticky elements should not hide content, and dialogs should work on small screens.

### Product-Specific Intent

Generic standards are not enough. Each product must define its own finish criteria. The coder must preserve product intent, not merely produce working components.

## Security And Data Checklist

Use this checklist before security-sensitive work is considered ship-ready.

Authorization:

- sensitive actions are authorized server-side
- object-level access is checked
- role checks do not rely only on frontend state
- IDs, slugs, and URLs cannot be guessed to access another user's data
- admin paths are protected beyond hidden navigation
- database policies match UI promises

Input validation:

- user input
- query params
- route params
- request bodies
- file uploads
- webhooks
- third-party API responses
- AI-generated outputs
- browser storage
- environment variables

Secrets:

- no secrets in repo
- no secrets in logs
- no secrets in screenshots
- no service-role keys in browser bundles
- `.env.example` uses safe placeholders
- CI tokens use least privilege
- production secrets are stored in approved secret management

AI tool and agent actions:

- tool arguments are validated before execution
- destructive actions require approval
- retrieved documents cannot override system rules
- agents cannot silently escalate privilege
- prompt injection is considered
- tool calls and outcomes are logged
- dry-run mode exists for risky actions where practical
- planning and execution are separated for high-risk tasks

## Testing Standard

Always test meaningful business rules, authorization, validation, error paths, data transformations, critical user journeys, workflow state transitions, payment or billing logic, migrations, security-sensitive code, and bug fixes.

Good tests are deterministic, readable, behavior-focused, fast enough to run often, meaningful when they fail, based on realistic examples, and not overly dependent on implementation details.

Finish reports should use this shape:

```md
## Tests Run

| Command | Result | Notes |
|---|---|---|
| npm run lint | Pass/Fail/Not run | |
| npm run typecheck | Pass/Fail/Not run | |
| npm test | Pass/Fail/Not run | |
| npm run build | Pass/Fail/Not run | |
| E2E/manual journey | Pass/Fail/Not run | |
| Security checks | Pass/Fail/Not run | |

## Tests Not Run

List each test not run and why.
```

## Release And Rollback

Before production release:

- CI checks pass.
- Required reviews are complete.
- Security findings are fixed or explicitly accepted.
- Rollback path is known.
- Monitoring is ready where relevant.
- Release notes are written if users or operators are affected.
- Database migrations are reversible or explicitly documented as irreversible.
- Feature flags are used where risk warrants.
- Environment variables are documented.

Rollback can mean reverting code, disabling a feature flag, rolling back deployment, running a corrective migration, restoring data, disabling an integration, hiding a route or entry point, or switching provider or adapter.

If rollback is impossible or risky, state that before release.

## Agentic Delivery Model

Coding agents are specialized workers, not final product owners.

The preferred model is:

```text
Human owner confirms scope, risk, and governance level
    -> Work packet created
    -> Builder implements one bounded change
    -> Automated checks run
    -> Reviewer verifies acceptance, tests, security, UX, docs, and release concerns
    -> Finisher fixes only verified gaps
    -> Ship-readiness gate
    -> Human approval where required
    -> Merge, release, or hold
    -> Handoff written
```

Do not ask one agent to build and be the only judge of whether the work is finished for important or risky changes.

## Work Packet Template

```md
# Work Packet: <Task Name>

## Goal
What must be built or changed?

## Why This Matters
What user, operator, business, security, or product problem does this solve?

## Current Context
What is already true in the repo or product?

## Non-Goals
What must not be changed or built?

## Relevant Files / Areas
What areas are expected to change?

## Acceptance Criteria
- [ ] Criterion one
- [ ] Criterion two

## Risk Classification
Low / Medium / High / Critical, with reason.

## Test Expectations
What validation must be added or run?

## UX / Product Finish Expectations
Which states, copy, accessibility, and responsive behavior matter?

## Security / Privacy Notes
What data, permissions, secrets, or trust boundaries are involved?

## Rollback / Recovery
How can this be reversed or safely held?
```

## Ship-Readiness Review Prompt

Use this prompt before declaring meaningful work complete:

```md
Review this change for ship readiness.

Check:
- acceptance criteria and user outcome
- missing UX states, copy, accessibility, and mobile behavior
- authorization, object-level access, runtime validation, secrets, logs, and error safety
- test adequacy and tests not run
- deployment, rollback, monitoring, and docs
- unapproved scope expansion
- evidence quality in the finish report

Return:
- blockers
- non-blocking improvements
- evidence reviewed
- what remains unverified
- ship / hold recommendation
```
