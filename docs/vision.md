# Vision: Cockpit As Knowledge Backbone

Created: 2026-06-14
Owner: Adam Goodwin
Status: active strategic direction

## What This Cockpit Is Becoming

The Graphify Workspace Cockpit started as a personal tool for exploring one
workspace graph on one Linux machine. That framing is already too small.

The cockpit is the knowledge and decision layer of Adam's AI-native operating
system. It is the place where:

- workspace knowledge is made readable (Ask, Map)
- human decisions about that knowledge are made durable (Decisions)
- model-backed recommendations are reviewed and accepted (Recommendations)
- approved changes are previewed, confirmed, and recorded (Work Queue)

Every one of those outputs — a decision, an accepted recommendation, an executed
action — is a governed artifact that other agents and devices should be able to
read without re-deriving it.

## Role in the Guided AI Labs CNS

Within the Guided AI Labs Agentic OS — the governed "central nervous system" (CNS)
that co-builds for the organization — this cockpit **is** the Graphify layer: the
**connectome / relationship-intelligence** core. It is one of three CNS core layers:

- **Freedom** — executive cognition: reasons, prioritizes, plans, orchestrates.
- **Guided AI Labs Operating System** — authority envelopes, evidence ledger, and the
  action state machine.
- **Graphify (this cockpit + the Graphify engine)** — relationship intelligence: maps
  repos, clients, workflows, agents, evidence, research claims, and the dependencies
  between them, and answers context queries for the other two layers.

Graphify is core cognitive infrastructure, not a product spoke or a "graph viewer":
without it, Freedom reasons over isolated facts. Phase 2 exposes the graph as a
queryable HTTP API (`POST /api/graph/query`) so Freedom and the OS can read
relationship context directly — see `AGENTS.md` for the integration contracts.

> **Naming note (2026-06-26):** The sections below describe the mission-execution
> layer as **UAOS (User AI Operating System)**. UAOS was **superseded by the Guided AI
> Labs Operating System (GAIL OS Rev 2) on 2026-06-21** and is now reference-only. Read
> "UAOS" below as the Guided AI Labs Operating System / GAIL OS: the handoff contract,
> read-only boundary, and approval-gate roles are unchanged — only the canonical repo
> and name moved. A full rename across this and related docs is tracked separately.

## The Three-Layer Architecture

```
Layer 1 — Knowledge Extraction
  Graphify CLI + graph.json
  Reads repos, docs, and workspace structure
  Produces a semantic workspace graph

Layer 2 — Decision Intelligence (this cockpit)
  Graphify Workspace Cockpit
  Reads the graph
  Answers questions, shows relationships, proposes recommendations
  Records human decisions, accepted recommendations, approved actions
  Exports durable governed artifacts

Layer 3 — Mission Execution
  Guided AI Labs Operating System / GAIL OS (formerly UAOS)
  Reads cockpit artifacts through the handoff contract
  Proposes missions from accepted recommendations
  Executes through policy-gated tool adapters
  Records evidence, validation, and learning
```

This data-flow layering (extraction → decision → execution) is the cockpit's internal
pipeline view. It is the same system as the CNS core triad above, seen along a different
axis: Graphify spans Layers 1–2 (extraction + decision intelligence), and the GAIL OS is
the Layer 3 execution and authority spine.

The cockpit sits between knowledge extraction and mission execution. It is a
human review and decision surface, not an autonomous executor.

## The Multi-Device Picture

Guided AI Labs operates across:

- Adam's Linux workstation (primary build machine)
- A Windows laptop (Microsoft 365 business environment)
- An Android tablet (mobile operator cockpit)
- Future additional machines and team members

Each device has a role:

| Device | Role in the cockpit architecture |
|---|---|
| Linux workstation | Trusted worker — runs graphify extraction, hosts cockpit backend, executes approved local actions |
| Windows laptop | Operator cockpit + business workspace — reviews decisions, approves recommendations, accesses Microsoft 365 surfaces |
| Android tablet | Operator cockpit — inspects map, reads recommendations, approves or rejects, checks mission status |
| Future team members | Role-based reviewers and approvers via shared state backend |

After Chunk Ten, any of these devices can reach the cockpit backend over HTTPS.
After Chunk Eleven, the same decision state is visible and consistent on all of
them without manual sync.

## Why The Cockpit Is The Right Backbone

An AI operating system needs memory. Not model memory — governed, auditable,
durable record-keeping of what decisions have been made, what was recommended,
what was approved, and what was executed.

The cockpit provides exactly that:

- **Decision ledger** — what has been classified, and why, with timestamps
- **Recommendation queue** — what the model proposed, what was accepted or deferred
- **Action log** — what was approved, dry-run, executed, and how to undo it

These records do not live in a chat thread. They do not disappear when a
context window closes. They are JSON files today, a shared database in Chunk
Eleven, but the schema and the governance rules are already in place.

When the OS needs to know "what has Adam decided about the agents/ workspace
area?" it reads the cockpit's decision ledger. When it needs a mission
candidate, it reads the handoff endpoint. When it needs to know what actions
have already been taken, it reads the action log. The cockpit answers all of
these without being asked to invent new facts.

## The Handoff Contract

The connection between the cockpit and the OS (GAIL OS, formerly UAOS) is explicit
and read-only.

The cockpit exports executed actions in OS mission envelope format via:

```
GET /actions?status=executed&format=uaos
```

Each record in the payload includes:

- `source_recommendation_id` — the recommendation that led to this action
- `evidence` — the graph nodes that supported the recommendation
- `decision_classification` — the human classification of the target area
- `confidence`, `risk` — from the recommendation card
- `proposed_mission_title` — derived from the action description
- `stop_triggers` — inherited from the recommendation; what the OS must not do
  without further approval
- `action_log` — what was actually executed, with rollback note

The OS reads this endpoint, validates against its own policy gate, and proposes
a mission. It does not execute automatically. The handoff is read-only. The
approval boundary remains in the OS.

## What Is Not The Cockpit's Job

The cockpit does not:

- execute autonomous commits, pushes, or destructive actions
- make decisions on Adam's behalf
- consume unconfigured external services or write to external systems directly
- serve as the execution engine for OS missions
- replace Codex or Claude as a coding assistant
- grant other users access without a separate governance decision

Those responsibilities belong to the GAIL OS and its governed tool adapters.

## Build Sequence

```
Chunks 1–8  — feature complete local tool
Chunk 9     — portable: installable anywhere, env-var configured, Dockerized
Chunk 10    — network-ready: any device can reach it, auth-gated, HTTPS
Chunk 11    — shared truth: decisions sync across devices, OS handoff live
Chunks 12–19 — real graph, UX polish, cloud connectors, assistant, overlap triage
Chunks 20–26 — Command-first decision workflow, evidence navigation, demo readiness
```

The cockpit became company-wide-capable infrastructure at Chunk Eleven. Later
chunks turned it into a more coherent decision workflow and added demo evidence,
while keeping release and project-completion decisions with Adam.

## Related Documents

- `docs/relationship-map-plan.md` — the active relationship-map plan
- `docs/workspace-scope-and-signal-plan.md` — completed workspace scope and signal history
- `docs/stabilization-plan.md` — completed hosted-beta stabilization evidence
- `docs/current-build-pathway.md` — archived 0-to-1 build history
- `docs/roadmap.md` — the full feature progression
- `docs/architecture.md` — component and data flow detail
- `docs/integration-guide.md` — Graphify → OS handoff contract (created in Chunk Eleven)
- `agentic-multi-agent-agent-builder/docs/build-control/` — CNS cross-repo coordination state
