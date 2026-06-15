# Model Registry

Document ID: MDL-REG-001
Status: current
Last Updated: 2026-06-14

| Model ID | Provider | Version | Purpose | Approved For | Owner | Last Reviewed |
| --- | --- | --- | --- | --- | --- | --- |
| M-001 | Ollama | Local (user-configured) | Ask synthesis and recommendation/steady-work generation | Local inference only; no data leaves the machine | Adam Goodwin | 2026-06-14 |
| M-002 | Anthropic Claude | claude-sonnet-4-6 | Development-time agent coding via Claude Code | Not used at runtime in the app | Adam Goodwin | 2026-06-14 |

## Notes

- M-001 (Ollama) is optional. The cockpit degrades gracefully to graph-only answers when Ollama is unavailable.
- No runtime model connects to external services without explicit user configuration.
- Model outputs are proposals only — they do not trigger actions without human approval.
- Update this registry before adding a new model provider or enabling a hosted model option at runtime.
- Hosted model adapters (Claude API, OpenAI, etc.) are post-MVP. Require a separate ADR and governance decision before enabling.
