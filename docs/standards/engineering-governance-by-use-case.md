# Engineering Governance By Use Case

Document type: use-case governance standard
Audience: project owners, coding teams, contractors, AI coding agents, and reviewers
Purpose: define engineering and governance expectations for the main kinds of systems built under this framework.

## Why This Exists

Not all code carries the same risk.

A public marketing website, SaaS application, backend API, AI agent with tool access, and workflow automation all need good engineering, but they do not need identical controls.

The right approach is risk-based engineering:

- lightweight controls for low-risk work
- stronger controls for systems that touch users, money, permissions, private data, or production operations
- very strong controls for AI agents and automation that can take action on behalf of a person or organization

## Core Rule

Every project must be classified by use case before development begins.

The user-selected `risk_tier` and `governance_level` in `project-control.yaml` remain the source of truth for the project. Use-case classification informs recommended controls. It does not override the selected `risk_tier` or `governance_level`. Any change to governance level requires an explicit owner decision.

When the use-case standard suggests stronger controls than the current risk tier, treat that as a review prompt:

- clearly flag the governance mismatch warning
- explain why stronger controls are recommended
- identify the specific controls that should be considered
- ask the owner to confirm whether to keep or revise the governance level
- document the outcome as an accepted recommendation, accepted exception, deferred decision, or explicit governance-level change
- document any accepted gap or compensating control
- update `project-control.yaml` only through an explicit owner decision

Do not silently raise or lower `risk_tier`, `governance_level`, required controls, project classification, or release gates. Do not block normal development solely because a use-case standard suggests stronger controls unless the selected governance level already makes that blocker mandatory.

Preferred warning language:

> This project appears to fit a higher-risk use case than the currently selected governance level. I recommend reviewing the following stronger controls before proceeding. The selected governance level remains unchanged unless the owner explicitly approves a change.

Use these terms consistently:

- recommended control
- strong recommendation
- review prompt
- governance mismatch warning
- owner confirmation required before changing governance level
- accepted exception
- compensating control

Avoid these terms unless enforcement truly exists:

- must upgrade
- automatically raise
- force
- block all work
- required regardless of selected governance level
- override selected governance

## Governance Recommendation Model

Governance reports and agent handoffs should distinguish between:

- `selected_governance_level`: the level recorded in `project-control.yaml`
- `selected_risk_tier`: the risk tier recorded in `project-control.yaml`
- `detected_use_case_risk`: risk suggested by project type, use case, data, tools, or deployment surface
- `recommended_controls`: controls suggested by this use-case standard or software quality signals
- `required_controls`: controls actually required by the selected governance level and project policy
- `owner_decision`: keep current level, raise level, lower level, defer, or accept exception

Separate compliance findings into:

| Category | Meaning |
|---|---|
| Required gaps | Missing controls required by the selected governance level. |
| Recommended improvements | Suggested controls based on use case, software fundamentals, or risk signals. |
| Design quality warnings | Weak layers, shallow modules, vague names, missing tests, hidden complexity, or missing feedback loops. |
| Owner decisions needed | Places where risk, design, scope, or governance should be confirmed by the owner. |
| Accepted exceptions | Known gaps accepted with rationale, compensating control, and review point. |

The classification informs:

- design depth
- review level
- security controls
- testing expectations
- documentation requirements
- deployment gates
- monitoring needs
- rollback expectations
- human approval requirements

If a project fits more than one category, consider the stricter controls and document whether the selected `risk_tier` and `governance_level` still fit.

## Fundamentals-First Use-Case Guidance

Use-case controls should be applied with software fundamentals in mind. Stronger use cases need stronger checks, but every project benefits from clear language, small slices, visible errors, and fast feedback.

For low-risk prototypes, allow lightweight notes, manual validation, simple file structure, and fewer formal docs. Still require clear limits, no fake production claims, no committed secrets, basic setup notes, and a cleanup or promotion path.

For medium-risk tools, require or strongly recommend repeatable setup, meaningful tests around business logic, linting or formatting, clear error handling, a documented owner, and basic rollback thinking.

For high-risk or production systems, require or strongly recommend automated tests for critical paths, authorization checks, migration and rollback planning, structured logs, operational visibility, security review, release notes where users or operators are affected, branch protection, and CI.

For AI agents, automations, private data, money, deployment, or destructive actions, require strong controls: explicit permission boundaries, tool inventory, least-privilege scopes, dry-run where practical, action logging, human approval for irreversible or external actions, recovery notes for partial failure, prompt-injection awareness, and separation of planning and execution.

When use-case guidance suggests stronger controls than selected governance requires, present those controls as recommendations or owner-decision prompts unless the selected governance level makes them mandatory.

## Use-Case Categories

The risk and governance columns are typical signals, not automatic overrides.

| Category | Examples | Typical Risk Signal | Typical Control Strength |
|---|---|---:|---:|
| Static / marketing website | Public website, landing page, portfolio, campaign page | Low to Medium | Light to Moderate |
| Interactive website | Forms, lead capture, calculators, gated content | Medium | Moderate |
| Web application / SaaS | User accounts, dashboards, workflows, subscriptions | Medium to High | Strong |
| Backend API / integration service | Internal API, webhook receiver, sync service | High | Strong |
| AI assistant / chat interface | Chatbot, retrieval assistant, summarizer | Medium to High | Strong |
| AI agent with tools | Email/calendar/file/system/deployment/tool-using agent | High to Critical | Very Strong |
| Workflow automation | n8n, Zapier-style flows, scheduled jobs | Medium to High | Moderate to Strong |
| Data / analytics tool | Reports, forecasting, dashboards, ETL scripts | Medium to High | Moderate to Strong |
| Infrastructure / deployment code | CI/CD, IaC, environment config, secrets | High to Critical | Very Strong |
| Internal utility / script | One-off helper, local cleanup tool, admin script | Low to High | Risk-based |
| Prototype / experiment | Demo, proof of concept, spike | Low if isolated | Light, with strict promotion gates |

## Universal Controls

Every project, regardless of size, needs:

- clear purpose
- owner
- README or equivalent usage notes
- source control
- secrets kept out of code
- basic error handling
- basic input validation where inputs exist
- clear setup instructions
- clear known limitations
- no fake claims of production readiness
- review before production use
- removal plan for abandoned experiments

Even prototypes need boundaries.

## Static / Marketing Websites

Primary risks:

- inaccurate or stale content
- poor accessibility
- poor performance
- broken links
- weak SEO structure
- privacy issues from analytics or forms
- misleading claims
- unmaintained dependencies

Required expectations:

- clear page structure
- responsive design
- accessibility basics
- semantic HTML and heading hierarchy
- optimized images
- metadata and Open Graph tags
- broken-link checks
- no exposed secrets
- privacy-conscious analytics
- contact forms protected from abuse
- clear deployment and rollback process

Usually unnecessary:

- heavy integration tests
- database migration process
- formal API contracts
- deep observability unless business-critical

## Interactive Websites

Examples include lead capture forms, calculators, gated downloads, surveys, and intake workflows.

Required expectations:

- server-side validation
- client-side validation for usability
- spam protection
- clear consent and privacy language
- safe storage of form data
- error and success states
- duplicate submission handling
- email or notification failure handling
- tests for scoring or business rules
- access plan when submitted data matters

## Web Applications / SaaS

Primary risks include unauthorized access, tenant data leakage, broken workflows, lost data, payment errors, fragile releases, and weak production debugging.

Required expectations:

- authentication
- server-side authorization
- role or permission model
- tenant isolation where applicable
- input validation
- database migrations
- automated tests
- critical path end-to-end tests
- error tracking and structured logs
- audit trail for important actions
- backup and recovery plan
- rollback plan
- environment separation
- secure secret management
- dependency scanning
- branch protection

For Supabase/Postgres:

- Row Level Security must be intentionally configured for client-accessible tables.
- Policies must be tested.
- Service-role keys must never be exposed to browsers.
- Auth context must be understood.
- Database migrations must be source-controlled.
- Storage buckets need access controls.
- Edge functions must validate inputs and permissions.

## Backend APIs / Integration Services

Examples include REST APIs, GraphQL APIs, webhook receivers, sync services, and payment callback handlers.

Required expectations:

- authentication where applicable
- object-level authorization
- input validation
- consistent error envelope
- rate limiting where exposed
- idempotency for retry-sensitive operations
- request or correlation IDs
- structured logs
- API contract documentation
- integration tests
- webhook signature verification
- safe timeout and retry policy
- least-privilege credentials
- backward-compatible versioning where consumers exist

## AI Assistants / Chat Interfaces

Examples include retrieval assistants, customer support chatbots, summarizers, drafting assistants, and policy Q&A tools.

Required expectations:

- clear scope and limitations
- source attribution where answers rely on documents
- retrieval boundaries
- prompt injection handling
- user data protection
- logging policy
- human review for high-stakes output
- model output treated as untrusted
- evaluation set for important use cases
- refusal and uncertainty behavior
- feedback mechanism
- clear separation between generated content and verified facts

## AI Agents With Tools

AI agents are different from normal applications because they can act.

Required expectations:

- explicit tool inventory
- least-privilege tool scopes
- human approval for destructive or external actions
- dry-run mode
- tool argument validation
- policy engine or hard-coded permission gate
- action logging
- user-visible action summaries
- separation of planning and execution
- confirmation before sending, deleting, purchasing, deploying, or modifying production
- rate limits
- kill switch
- sandboxed execution where applicable
- prompt injection tests
- recovery plan for failed or partial action
- clear responsibility boundary between model, tool, and human

Agent action risk tiers:

| Tier | Action Type | Examples | Required Control |
|---|---|---|---|
| Tier 0 | Read-only, low sensitivity | Read public docs, summarize local non-sensitive note | Logging |
| Tier 1 | Read private data | Search email, read calendar, inspect private files | Auth, permission, audit |
| Tier 2 | Draft action | Draft email, prepare file edit, propose command | User review before execution |
| Tier 3 | External reversible action | Send email, create calendar event, label records | Confirmation, audit, rollback where possible |
| Tier 4 | Destructive or production action | Delete files, deploy code, modify DB, change permissions | Explicit approval, dry-run, backups, rollback, strong audit |
| Tier 5 | Irreversible/high-stakes action | Payments, legal/HR action, public posting, safety-critical control | Human decision required; agent may assist only |

## Workflow Automations

Examples include n8n workflows, scheduled syncs, notifications, CRM updates, report generation, SharePoint/Forms automation, and invoice routing.

Required expectations:

- named owner
- purpose documented
- trigger documented
- inputs and outputs documented
- credentials secured
- failure handling
- alerting on failure
- idempotency where possible
- version or export stored where practical
- test mode or sandbox
- data access minimized
- run history reviewed for critical flows

## Data / Analytics Tools

Examples include financial models, BI dashboards, ETL scripts, operational reports, scenario models, and AI-generated analysis.

Required expectations:

- data sources documented
- assumptions documented
- refresh process documented
- data validation checks
- version control where practical
- clear calculation logic
- access controls
- error checks
- review of high-impact outputs
- clear distinction between actuals, assumptions, forecasts, and scenarios

## Infrastructure / Deployment Code

Examples include CI/CD pipelines, GitHub Actions, infrastructure as code, environment configuration, domain/DNS setup, deployment scripts, monitoring, and secret management.

Required expectations:

- least-privilege credentials
- protected production deployments
- secret scanning
- dependency scanning
- branch protection
- required checks
- environment separation
- rollback plan
- audit trail
- documented deployment process
- no production secrets in local files or repo
- CI/CD permissions reviewed
- manual production changes avoided

## Internal Utilities / Scripts

Risk depends on what the script touches.

Required for all scripts:

- clear purpose
- usage instructions
- safe defaults
- input validation
- error handling
- no hardcoded secrets

Required for high-risk scripts:

- dry-run mode
- confirmation prompt
- backup or rollback path
- logs
- access controls
- peer review
- test against sample data
- explicit production warning

## Prototypes / Experiments

The biggest prototype risk is accidental promotion to production.

Required expectations:

- label clearly as prototype
- define what is being tested
- define what is not production-ready
- avoid real sensitive data unless required and approved
- avoid production credentials
- keep isolated from production
- set review date
- decide whether to delete, harden, or archive

A prototype cannot become production until it has security review, data review, architecture review, tests, documentation, deployment process, monitoring, rollback plan, owner, and known limitations.

## Use-Case Governance Matrix

| Control | Website | Interactive Site | SaaS/App | API | AI Assistant | AI Agent | Automation | Data Tool | Infrastructure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| README | Required | Required | Required | Required | Required | Required | Required | Required | Required |
| Design note | Optional | If logic/data | Required for risky features | Required | Required | Required | If critical | If high-impact | Required |
| Auth | Usually no | If admin/data | Required | Required if private | If private | Required | If private | If private | Required |
| Server-side authorization | N/A | If data | Required | Required | Required for retrieval | Required | Required where applicable | Required where applicable | Required |
| Input validation | Basic | Required | Required | Required | Required | Required | Required | Required | Required |
| Automated tests | Basic optional | Required for logic | Required | Required | Required evals/tests | Required incl. tool tests | Required for critical flows | Required validations | Required |
| Accessibility | Required | Required | Required | N/A | UI dependent | UI dependent | N/A | UI dependent | N/A |
| Security review | Light | Moderate | Required | Required | Required | Strong required | If critical | If sensitive | Strong required |
| Monitoring | Basic | Basic/moderate | Required | Required | Required | Required | Required for critical | Required for scheduled | Required |
| Audit trail | Usually no | For submissions | Required for sensitive actions | Required | For high-impact use | Required | Required for critical | Required for high-impact | Required |
| Rollback plan | Required | Required | Required | Required | Required | Required | Required | Required | Required |
| Human approval gate | Usually no | Sometimes | For risky ops | For risky ops | For high-stakes output | Required for risky actions | For destructive flows | For high-impact outputs | Required for production |

## Minimum Review Level By Risk

| Risk Level | Examples | Required Review |
|---|---|---|
| Low | Static content update, styling fix, typo | Self-check or light peer review |
| Medium | Form, dashboard, non-sensitive data workflow | Peer review, tests for logic |
| High | Auth, permissions, customer data, API, database migration | Senior review, security review, tests, rollback |
| Critical | Production infrastructure, destructive automation, AI agent with tools, payment/legal/safety actions | Formal approval, threat model, strong tests, monitoring, rollback, human gate |

## Best-Practice Decision Tree

Use this when deciding how much process a change needs.

```text
Does it touch production?
  Yes -> require review, tests, rollback, monitoring.
  No -> continue.

Does it touch private/sensitive data?
  Yes -> require security/privacy review and access controls.
  No -> continue.

Can it change, send, delete, deploy, charge, or publish something?
  Yes -> require approval gate and audit trail.
  No -> continue.

Does it involve AI output influencing action?
  Yes -> validate output, scope tools, require human review for high risk.
  No -> continue.

Does it create or change a public contract/API/database schema?
  Yes -> require design note, tests, version/migration plan.
  No -> continue.

Is it only content/styling with no data/security impact?
  Yes -> light review is enough.
```

## Practical Use-Case Labels

Every repo should declare its use-case classification in the README or project intake record.

Example:

```md
## Project Classification

Primary use case: Web application / SaaS
Secondary use cases: AI assistant, workflow automation
Selected risk_tier: high
Selected governance_level: 3
Sensitive data: Yes
Production action capability: No
Human approval required: For admin bulk actions
```

This keeps the team honest about what standard applies.
