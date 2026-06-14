# Agent Inventory

Document ID: AGT-INV-001
Status: draft
Last Updated: 2026-06-14

| Agent ID | Name | Purpose | Autonomy | Model | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AG-001 | Ask Synthesizer | Answer workspace questions via graphify query/path/explain with optional Ollama synthesis; return short answer + evidence nodes + map slice + follow-ups | A1 (read-only, no file mutations) | Ollama local (optional) | Adam Goodwin | Planned |
| AG-002 | Recommendation Generator | Generate ranked recommendation cards from graph context using local model; output structured records with evidence, confidence, risk, and proposed action | A1 (write to state/recommendations/ only) | Ollama local | Adam Goodwin | Planned |
| AG-003 | Steady Work Agent | Run bounded background analysis missions: find archive candidates, identify duplicated build surfaces, rank next-build candidates, find weak docs/tests; write recommendation cards only, no file mutations | A1 (write to state/recommendations/ only) | Ollama local | Adam Goodwin | Planned |
| AG-004 | Action Executor | Execute approved actions from work queue with dry-run first, explicit approval gate, rollback note, and execution report | A2 (requires explicit human approval before execution) | N/A (shell/git subprocess) | Adam Goodwin | Planned |

## Autonomy Level Reference

- **A1** — Read-only analysis or bounded writes to app state only. No file mutations outside `workspace/state/`. No external calls.
- **A2** — Executes workspace actions. Requires dry-run preview and explicit human approval before each action. Execution report required. Rollback note required.
- **A3+** — Not used in MVP. Would require separate governance decision.

## Notes

- AG-001 through AG-003 are safe by construction: they cannot mutate workspace files or call external services.
- AG-004 is gated and disabled for MVP. Enable only after dry-run infrastructure and approval UI are validated.
- All agents log to `workspace/state/sessions/`.
