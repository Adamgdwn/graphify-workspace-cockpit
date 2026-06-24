# ADR-009: Automatic Graph Escalation

Status: accepted
Date: 2026-06-23
Owner: Adam Goodwin

## Context

Large or broad workspace selections can exceed the practical local `graphify update --no-cluster` path. The desired operator behavior is that the cockpit decides quickly whether a selected graph can stay local or should use a stronger Graphify extraction backend, then proceeds without another per-run prompt.

The project remains local-first by default. Runtime calls to hosted model providers are not allowed unless explicitly configured.

## Decision

Add an env-gated graph generation router:

- `GRAPH_ESCALATION_ENABLED=false` by default.
- When enabled and `GRAPH_ESCALATION_BACKEND` is set, the backend asks the local Ollama model for a JSON route decision: `local` or `elevated`.
- If Ollama is unavailable or returns invalid JSON, deterministic file/root thresholds choose the route.
- Local route runs `graphify update --no-cluster`.
- Elevated route runs `graphify extract --backend <configured> --no-cluster` with optional model and timeout settings.
- Both routes continue through the same workspace scope filtering, graph merge, activation, and stale semantic-cache clearing path.
- `/graph/rebuild/status` reports the selected route and decision metadata.

## Consequences

Selected graph extraction content may leave the machine only after explicit env configuration. Disabling the feature is a rollback path: set `GRAPH_ESCALATION_ENABLED=false` or remove `GRAPH_ESCALATION_BACKEND`, then restart the backend.

This ADR does not enable hosted chat, recommendation, action execution, or arbitrary external HTTP adapters. Those remain separate decisions.
