# Risk Register

Document ID: RSK-REG-001
Status: current
Last Updated: 2026-06-29

## Current Risk Classification

- Tier: low (intentional owner override — governance_level:1 confirmed 2026-06-14)
- Owner: Adam Goodwin
- Last reviewed: 2026-06-29

## Key Risks

| ID | Risk | Likelihood | Impact | Controls | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | Private graph data exposure | Medium | High | Local-first graph loading; Supabase and cloud connectors are opt-in only; user selects graph path; secrets excluded from indexing | Adam Goodwin | Open |
| R-002 | Prompt injection from indexed graph text | Medium | Medium | Graph text treated as data, not instructions; Ollama results are proposals only; no auto-execution from model output | Adam Goodwin | Open |
| R-003 | Accidental file mutation | Low | High | Mutations limited to `workspace/state/` by default except explicitly queued actions; dry-run required before any approved action; rollback note required | Adam Goodwin | Open |
| R-004 | Noisy or misleading recommendations | High | Low | Recommendations are proposals only; evidence links shown; user must accept before any action; decision ledger tracks outcomes and suppresses already-decided items | Adam Goodwin | Open |
| R-005 | Over-trusting model output | Medium | Medium | Model outputs are cards not commands; approval gate separates recommendation from execution; dry-run required for all actions | Adam Goodwin | Open |
| R-006 | Token overlap causing redundant findings | High | Low | Ranking model weights build direction and decision value over raw token overlap; decision ledger suppresses already-classified items | Adam Goodwin | Open |
| R-007 | Large graph freezing the frontend | Medium | Medium | Map renders at project/cluster level by default; file-level expansion on demand only; Cytoscape.js virtualization if needed | Adam Goodwin | Open |
| R-008 | Secret committed to graph or state file | Low | High | .env and secret files excluded from graph indexing and workspace reads; no secret content in state files; use presence-only credential checks; pre-commit scan remains a recommended follow-up | Adam Goodwin | Open |
| R-009 | Graphify boundary drift: either passive viewer or hidden authority layer | Medium | High | 2026-06-29 boundary doctrine; Graphify may write approved relationship memory but cannot approve, authorize, or execute actions; candidates must stay labelled as candidates | Adam Goodwin | Open |
| R-010 | Graphify hot path becomes runtime ballast | Medium | High | Hot read plane forbids extraction, LLM calls, unbounded payloads, and full graph reads; active speed plan requires bounded context packets, freshness flags, and p95/payload validation | Adam Goodwin | Open |
