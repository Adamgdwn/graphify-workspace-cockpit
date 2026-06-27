# Agent Inventory

Document ID: AGT-INV-001
Status: current
Last Updated: 2026-06-23

| Agent ID | Name | Purpose | Autonomy | Model | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AG-001 | Ask Synthesizer | Answer workspace questions via `graphify query/path/explain` with cluster-filtered context and optional Ollama synthesis; return short answer + evidence nodes + follow-ups | A1 (read-only, no file mutations) | Ollama local (optional) | Adam Goodwin | Implemented (Chunk 3, cluster-aware Chunk 16) |
| AG-002 | Recommendation Generator | Generate ranked recommendation cards from cluster-filtered graph context using local model; output structured records with evidence, confidence, risk, and proposed action | A1 (write to `state/recommendations/` only) | Ollama local | Adam Goodwin | Implemented (Chunk 6, cluster-aware Chunk 16) |
| AG-003 | Steady Work Agent | Run bounded background analysis missions: find archive candidates, identify duplicated build surfaces, rank next-build candidates, find weak docs/tests; write recommendation cards only, no file mutations | A1 (write to `state/recommendations/` only) | Ollama local | Adam Goodwin | Implemented (Chunk 7) |
| AG-004 | Action Executor | Execute approved actions from work queue with dry-run first, explicit approval gate, rollback note, and execution report | A2 (requires explicit human approval before execution) | N/A (shell/git subprocess) | Adam Goodwin | Implemented (Chunk 8) |
| AG-005 | AI Assistant | Stream conversational responses from Ollama using cluster-filtered graph context; read-only; cannot trigger actions, decisions, or mutations; session records saved to `state/chat-sessions/` | A1 (read-only) | Ollama local (required for chat) | Adam Goodwin | Implemented (Chunk 17) |
| AG-006 | Graph Build Router | Decide whether selected workspace graph generation should stay local or use configured elevated Graphify extraction | A1 for local routing; external call only when `GRAPH_ESCALATION_ENABLED=true` and provider credentials are configured | Ollama local router plus configured Graphify extract backend | Adam Goodwin | Implemented (2026-06-23) |

## Autonomy Level Reference

- **A1** — Read-only analysis or bounded writes to app state only. No file mutations outside `workspace/state/`. No external calls.
- **A2** — Executes workspace actions. Requires dry-run preview and explicit human approval before each action. Execution report required. Rollback note required.
- **A3+** — Not used. Would require separate governance decision.

## Notes

- AG-001 through AG-003 and AG-005 are safe by construction: they cannot mutate workspace files or call external services.
- AG-004 is gated: enabled only after dry-run infrastructure and approval UI are validated.
- AG-006 is disabled by default for external calls. When enabled, it may send selected graph extraction context to the configured provider and records the routing decision in rebuild status.
- All agents log to `workspace/state/sessions/` (Ask) or `workspace/state/chat-sessions/` (AI Assistant).
- Model is Ollama-local for Ask, recommendations, steady work, chat, and the graph routing decision. If Ollama is unreachable, AG-006 falls back to size/root heuristics.
