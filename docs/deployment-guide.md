# Deployment Guide

Last Updated: 2026-06-19

This guide covers running the Graphify Workspace Cockpit beyond the default
local dev setup — on a Windows machine via Docker Desktop, on a Linux server,
and optionally with HTTPS via Caddy.

---

## Local Dev (any OS)

See the main [README](../README.md) Quick Start. The fastest path is the
one-command launcher — `launcher/launch-cockpit.sh` on Linux/macOS,
`launcher\launch-cockpit.bat` on Windows — which bootstraps and starts both
services; `scripts/start.sh` is the manual equivalent. No Docker required.

---

## Windows — Docker Desktop

> **Non-Docker option:** there's now a best-effort native launcher — double-click
> `launcher\launch-cockpit.bat` (needs Python 3.10+ and Node 18+ on PATH). It
> isn't yet tested across native Windows setups, so the Docker path below remains
> the verified option. A true double-click app with a native installer is planned
> once usability on more machines is confirmed.

### Prerequisites

| Requirement | Install |
|-------------|---------|
| Windows 10 21H2+ or Windows 11 | — |
| Docker Desktop >= 4.x | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| Git for Windows | [git-scm.com](https://git-scm.com/) |

> **Note:** Docker Desktop on Windows uses WSL 2 by default. Enable WSL 2
> in Docker Desktop settings if not already active.

### Steps

**1. Clone the repo** (Git Bash or PowerShell):

```bash
git clone https://github.com/Adamgdwn/graphify-workspace-cockpit.git
cd graphify-workspace-cockpit
```

**2. Configure** (optional — demo graph is used by default):

```bash
copy backend\.env.example .env
```

Edit `.env` in Notepad to set `GRAPH_PATH` if you have a local graph, or leave
it as-is to use the bundled demo.

**3. Start:**

```bash
docker-compose up --build
```

Docker Desktop pulls images, builds the frontend, and starts both services.
The backend image installs `graphifyy` through `backend/requirements.txt`, so
the Graphify CLI is available for Ask and graph rebuild inside the container.

**4. Open the cockpit:**

Open `http://localhost:5173` in any browser. Backend API is at `http://localhost:8000`.

### Notes for Windows

- **Volume mounts**: `workspace/state/` is mounted into the backend container.
  On Windows, Docker mounts from the WSL 2 filesystem. State persists between
  container restarts as long as the checkout directory is not deleted.
- **Ollama on Windows**: If Ollama is running natively on Windows (not in a
  container), set `OLLAMA_URL=http://host.docker.internal:11434` in your `.env`.
  `host.docker.internal` is Docker Desktop's built-in alias for the host machine.
- **Firewall**: Docker Desktop manages port exposure. No Windows Firewall rules
  are needed for localhost access.

---

## Linux Server

Same as Windows Docker above, but with native Docker (no Desktop required):

```bash
sudo apt install docker.io docker-compose-plugin   # Debian/Ubuntu
git clone https://github.com/Adamgdwn/graphify-workspace-cockpit.git
cd graphify-workspace-cockpit
cp backend/.env.example .env
docker compose up --build -d
```

Access from the same machine: `http://localhost:5173`

Access from another machine on the local network: `http://<server-ip>:5173`

If you configure graph scan directories for Docker, mount those host paths into
the backend container and use the in-container paths in Settings. The demo graph
works without any additional mounts.

---

## API Key (network-facing deployments)

When the cockpit is reachable from devices other than localhost, set `API_KEY`
to require a bearer token on all non-health endpoints.

**Generate a key:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Set in `.env`:**

```
API_KEY=your-generated-key-here
```

**Use in requests** (curl example):

```bash
curl -H "Authorization: Bearer your-generated-key-here" http://localhost:8000/decisions
# OR
curl -H "X-API-Key: your-generated-key-here" http://localhost:8000/decisions
```

The `/health` endpoint is always open without auth.

The browser UI can use the same key. Open Settings → API, paste the key, and use
Test to confirm it. The key is stored in that browser's localStorage and sent as
`X-API-Key` on backend requests, including graph uploads.

For LAN use where all devices are trusted, the simplest approach is SSH port
forwarding to access a remote server. Leave `API_KEY` unset for fully-trusted
private networks.

---

## HTTPS via Caddy (optional)

Caddy terminates HTTPS and proxies both the frontend and backend. This is
optional — the cockpit works without it.

### When you need Caddy

- Accessing the cockpit from outside your LAN (public domain)
- Devices that require HTTPS

### When you do NOT need Caddy

- LAN use where you control the network
- Localhost-only use on a single machine
- SSH port-forwarding to access a remote server

### Setup

**1. Set `DOMAIN` in your environment:**

```bash
export DOMAIN=cockpit.example.com
```

**2. Point DNS** for `cockpit.example.com` at your server's public IP.

**3. Configure `VITE_API_URL`** so the browser routes API calls through Caddy:

In `.env`:
```
VITE_API_URL=/api
CORS_ORIGINS=https://cockpit.example.com
```

Use `/api` for the Caddy profile because the browser talks to the same origin
as the frontend. `config/Caddyfile` matches `/api/*` before the frontend
catch-all, strips `/api`, and forwards the request to the backend. Use an
absolute backend URL only when the frontend is not being served through this
same-origin Caddy proxy.

**4. Start with the `https` profile:**

```bash
docker-compose --profile https up --build
```

Caddy obtains a Let's Encrypt certificate on first startup. The cockpit is
available at `https://cockpit.example.com`.

### Localhost self-signed

Run Caddy without setting `DOMAIN` and it falls back to `localhost` with a
self-signed certificate. The browser will show a warning — click through to
access the cockpit over HTTPS locally.

### Caddyfile location

`config/Caddyfile` — edit to customise routing, add rate limiting, or add
extra security headers before public internet exposure.

---

## Multi-Device LAN Access (no domain)

To reach the cockpit from an Android tablet or another laptop on the same
Wi-Fi network without a domain name:

1. Find the server's LAN IP: `ip addr | grep "inet "` (Linux) or `ipconfig` (Windows)
2. Set `CORS_ORIGINS=http://<server-ip>:5173` in `.env`
3. Set `API_KEY` to protect the network-facing API
4. `docker-compose up --build`
5. Open `http://<server-ip>:5173` on any device on the same Wi-Fi

No Caddy or DNS required for LAN access.

---

## Optional Supabase Storage

The default hosted beta path uses file-backed state in `workspace/state/`.
Supabase is opt-in through `STORAGE_BACKEND=supabase`.

Before starting a Supabase-backed backend, apply migrations in order:

```bash
psql "$DATABASE_URL" < db/migrations/001_initial.sql
psql "$DATABASE_URL" < db/migrations/002_recommendation_action_plans.sql
```

Do not run live Supabase migrations without owner approval. After startup, check
`/health` or `/settings/org`; `storage.ready` must be `true` before treating
Supabase mode as hosted-beta-ready. If it is `false`, the response names the
required migration.

---

## Rollback

For file-backed deployments, rollback is:

1. `docker-compose down`
2. `git checkout <previous-tag>`
3. `docker-compose up --build`

State in `workspace/state/` is JSON files. Back them up before upgrading if
decisions or recommendations are important to preserve.

Supabase deployments include additive database migrations. Once
`db/migrations/002_recommendation_action_plans.sql` has been applied, do not
drop those columns as part of a routine app rollback. Database rollback requires
separate owner review and a data-preservation plan.

---

## Validation (post-deploy smoke checks)

```bash
curl http://localhost:8000/health           # -> {"status":"ok","version":"..."}
curl http://localhost:8000/settings         # -> active graph name + node count
curl http://localhost:8000/status/ollama    # -> {"connected":true/false,...}
```

For the Caddy HTTPS profile, verify both route families through the public
origin:

```bash
curl https://cockpit.example.com/api/health # -> backend JSON
curl -I https://cockpit.example.com/        # -> frontend HTML route
```

For local self-signed Caddy checks, use `https://localhost` and add `-k` to the
`curl` commands.

The `/health` and `/settings` responses include `graphify.available`. If it is
false, `graphify.code` is `GRAPHIFY_MISSING`.

For Supabase-backed deployments, `/health`, `/settings`, and `/settings/org`
also include `storage.ready`. Treat `storage.ready: false` as a hold on hosted
beta use until the named migration has been applied.

If Node is available through nvm, run the live demo smoke gate:

```bash
source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs
```

For hosted Caddy, point the smoke gate at the API prefix and frontend origin. If
`API_KEY` is set, provide it as `SMOKE_API_KEY` or `API_KEY`:

```bash
source "$HOME/.nvm/nvm.sh" && API_URL=https://cockpit.example.com/api FRONTEND_URL=https://cockpit.example.com node scripts/demo-path-smoke.mjs
```

Open `http://localhost:5173` → confirm all seven tabs render (`Command`, `Ask`, `Map`, `Decisions`, `Recommendations`, `Work Queue`, `Settings`) → confirm the AI assistant button appears in the bottom-right corner → confirm Settings tab shows active graph and Ollama status → confirm Map shows Explore / Trace / Overlap / Review modes and the Overlap Analysis panel when semantic edges are available.

---

## Troubleshooting

**Port already in use:** `docker-compose down` then `docker-compose up --build`.

**Backend won't start:** Check `docker-compose logs backend`. Common cause:
`GRAPH_PATH` pointing to a file that doesn't exist inside the container.

**Graphify missing:** `/health` and `/settings` include `graphify.available`.
If false, rebuild the backend image after installing dependencies or confirm the
runtime `PATH` contains `graphify`. Ask and graph rebuild return
`GRAPHIFY_MISSING` while the rest of the cockpit remains usable.

**Ollama not connecting:** Verify Ollama is running on the host with
`curl http://localhost:11434/api/tags`. In Docker, use
`OLLAMA_URL=http://host.docker.internal:11434`.

**CORS errors in browser console:** Ensure `CORS_ORIGINS` includes the exact
origin (scheme + host + port) the browser is using to access the frontend.

**API key 401:** Check that the request includes `Authorization: Bearer <key>`
or `X-API-Key: <key>`. The `/health` endpoint is always open without auth.

**Graph upload fails:** Ensure the file is valid JSON with a `nodes` array at
the top level. Graphify's `graph.json` always satisfies this.
