# Demo Path Checklist

Last Updated: 2026-06-16T20:46:08-06:00
Status: active
Owner: Adam Goodwin

## Purpose

Use this checklist before recording or demonstrating the cockpit decision flow.
It pairs one automated smoke check with a short manual walkthrough for the
operator journey that still needs human judgement.

## Preconditions

- Backend is running at `http://127.0.0.1:8000` or `API_URL` points to the active backend. For hosted Caddy, use the API prefix, such as `https://cockpit.example.com/api`.
- Frontend is running at `http://127.0.0.1:5173` or `FRONTEND_URL` points to the active frontend. For hosted Caddy, use the frontend origin, such as `https://cockpit.example.com`.
- `curl http://127.0.0.1:8000/health` returns `{"status":"ok",...}`.
- For hosted Caddy, `curl https://cockpit.example.com/api/health` returns backend JSON and `curl -I https://cockpit.example.com/` returns the frontend route.
- If Ask, Chat, or Recommendations need synthesized language, Ollama is running.

## Automated Smoke Check

Run:

```bash
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

Optional overrides:

```bash
source "$HOME/.nvm/nvm.sh" && API_URL=http://localhost:8000 FRONTEND_URL=http://localhost:5173 node scripts/demo-path-smoke.mjs
```

Hosted Caddy override:

```bash
source "$HOME/.nvm/nvm.sh" && API_URL=https://cockpit.example.com/api FRONTEND_URL=https://cockpit.example.com node scripts/demo-path-smoke.mjs
```

If the hosted backend has `API_KEY` set, provide it as `SMOKE_API_KEY` or
`API_KEY`.

The smoke check verifies:

- Backend health is reachable.
- The graph summary has nodes.
- Ask returns an answer with evidence nodes.
- Decisions, Recommendations, Work Queue actions, and overlap report endpoints are readable.
- The frontend renders the Command Center and the core tab labels.

This is intentionally not a full browser interaction suite. The repo currently
does not carry Playwright, Vitest, or another frontend test runner. Until one is
added, the automated gate protects the live backend/frontend contract and this
manual checklist protects the click path.

## Manual Walkthrough

1. Open the app and confirm the first tab is `Command`.
2. Confirm `Command Center` shows attention cards for:
   - `Pending Recommendations`
   - `Accepted, Not Queued`
   - `Dry-Run Ready Actions`
   - `Untriaged Overlaps`
3. Click `Ask`, submit `What projects are in this workspace?`, and confirm an answer plus `Evidence nodes`.
4. Click one evidence node and confirm the app moves to `Map` with a focus notice for Ask evidence.
5. In `Map`, confirm the mode switch shows `Explore`, `Trace`, `Overlap`, and `Review`.
6. Click `Decisions`, create or edit one low-risk demo decision, and confirm it appears in the active decision list.
7. Return to `Map` and confirm the decision badge is visible on the relevant node when that target is present in the graph.
8. Click `Recommendations` and confirm pending cards show evidence chips, confidence, risk, `Next action`, and `Review Decision Packet`.
9. Open one decision packet and confirm it separates evidence, judgement, recommendation, approval, decision status, and open questions; optionally export Markdown or JSON.
10. Accept one appropriate recommendation, then click `Queue Action`.
11. Click `Work Queue`, run `Dry Run` for the queued action, and confirm a preview appears before `Execute` is available.
12. Do not execute unless the demo explicitly calls for it; execution remains a human approval step.

## Recording Notes

- Prefer the real graph when available; if `demo_mode` is true, call that out.
- Use Command Center as the opening shot for the world-class decision workflow.
- Show the Ask evidence click into Map because it proves the app is not just a chat surface.
- Show one decision packet in Recommendations because it proves the tool is no longer a 50,000-foot recommendation list.
- Treat action execution as optional. The safety point is the dry-run gate and rollback note.

## Known Manual Gate

Full Ask -> Evidence -> Map -> Decision -> Recommendation -> Work Queue
interaction coverage remains manual for now because the frontend has no browser
test framework installed. Add Playwright or component tests in a future chunk if
this becomes a repeated release gate instead of a demo-readiness gate.
