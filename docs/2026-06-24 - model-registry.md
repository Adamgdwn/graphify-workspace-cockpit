# Model Registry

Document ID: MDL-REG-001
Status: current
Last Updated: 2026-06-23

| Model ID | Provider | Version | Purpose | Approved For | Owner | Last Reviewed |
| --- | --- | --- | --- | --- | --- | --- |
| M-001 | Ollama | Local (user-configured) | Ask synthesis and recommendation/steady-work generation | Local inference only; no data leaves the machine | Adam Goodwin | 2026-06-14 |
| M-002 | Anthropic Claude | claude-sonnet-4-6 | Development-time agent coding via Claude Code | Not used at runtime in the app | Adam Goodwin | 2026-06-14 |
| M-003 | Graphify elevated extraction backend | User-configured via `GRAPH_ESCALATION_BACKEND` | Optional elevated graph extraction after local Ollama route decision | Runtime graph generation only when `GRAPH_ESCALATION_ENABLED=true` and provider credentials are explicitly configured | Adam Goodwin | 2026-06-23 |

## Notes

- M-001 (Ollama) is optional. The cockpit degrades gracefully to graph-only answers when Ollama is unavailable.
- No runtime model connects to external services without explicit user configuration.
- M-003 is disabled by default. When enabled, selected graph content may be sent to the configured Graphify extraction backend.
- Model outputs are proposals only — they do not trigger actions without human approval.
- Update this registry before adding a new model provider or enabling a hosted model option at runtime.
- Hosted model adapters for chat, recommendations, or autonomous actions remain post-MVP. Graph generation escalation is limited to the Graphify CLI extraction path and is documented in ADR-009.
