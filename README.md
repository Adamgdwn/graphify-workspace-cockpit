# Graphify Workspace Cockpit

A local-first decision cockpit for developers and builders who use [Graphify](https://github.com/safishamsi/graphify) to map their workspace.

> Show me what I have, explain what it means, recommend what to do next, and wait for permission before acting.

---

## Built on Graphify

This project is powered by **[Graphify](https://github.com/safishamsi/graphify)** — an open-source tool by [safishamsi](https://github.com/safishamsi) that extracts semantic knowledge graphs from codebases and workspaces.

Graphify does the heavy lifting:
- Indexes your workspace into a traversable `graph.json`
- Exposes `graphify query`, `graphify path`, and `graphify explain` commands
- Finds relationships, communities, and patterns across any codebase or project folder

The cockpit is a UI layer on top of that graph. All credit for the core extraction and query engine belongs to the Graphify project.

Install Graphify first:

```bash
pip install graphifyy
```

Then generate your workspace graph:

```bash
graphify . --output workspace/out/graph.json
```

---

## What This Cockpit Does

Replaces fragmented static dashboards and desktop launchers with a single coherent surface across five tabs:

| Tab | What it does |
|-----|--------------|
| **Ask** | Natural language questions answered from your graph (`graphify query/path/explain`) with optional local Ollama synthesis |
| **Map** | Interactive project-level relationship map — click to inspect, filter by type/theme/decision, drill down on demand |
| **Decisions** | Durable ledger of human decisions about workspace areas: active, finish, merge, archive, extract, productize, or ignore |
| **Recommendations** | Model-backed cards with evidence, confidence, risk, and accept/reject/defer controls |
| **Work Queue** | Approval-gated action queue with dry-run previews, rollback notes, and execution reports |

---

## Safety Model

- Read-only by default. No destructive actions without explicit human approval.
- Recommendations are proposals — they do not trigger actions.
- No autonomous commits, pushes, deletes, or external service calls in MVP.
- User-supplied graphs stay local. Secrets and environment files are never indexed, printed, or committed.

---

## Status

Early development — Chunk Two (app shell) in progress. See [docs/current-build-pathway.md](docs/current-build-pathway.md) for the live build route.

- Owner: Adam Goodwin
- Governance level: 1 (low — intentional)
- Risk tier: low

---

## Quick Start

```bash
# Fill in after Chunk Two (app shell is complete)
```

---

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python FastAPI |
| Frontend | React + Vite (TypeScript) |
| Graph view | Cytoscape.js |
| Local model | Ollama HTTP API (optional) |
| Graph input | Graphify `graph.json` |

---

## Documentation

- [docs/architecture.md](docs/architecture.md) — component map, data flow, state layout
- [docs/current-build-pathway.md](docs/current-build-pathway.md) — live build route and chunk status
- [docs/agent-inventory.md](docs/agent-inventory.md) — agent definitions and autonomy levels
- [docs/tool-permission-matrix.md](docs/tool-permission-matrix.md) — what the cockpit can and cannot do
- [docs/risks/risk-register.md](docs/risks/risk-register.md) — known risks and controls
- [docs/roadmap.md](docs/roadmap.md) — what's next

---

## Credits

Core graph engine: **[Graphify](https://github.com/safishamsi/graphify)** by [safishamsi](https://github.com/safishamsi) — `pip install graphifyy`

Cockpit UI, recommendation layer, decision ledger, and work queue: Adam Goodwin
