"""Microsoft Graph API authentication via MSAL device code flow.

Token cache: workspace/state/connector-tokens/microsoft.json
Flow state:  workspace/state/connector-tokens/microsoft_flow.json

Required env vars (when using Microsoft connectors):
  MICROSOFT_CLIENT_ID  — Azure AD app registration client ID
  MICROSOFT_TENANT_ID  — tenant ID or "common" for multi-tenant
"""
from __future__ import annotations

import json
import os
from pathlib import Path

MICROSOFT_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID", "")
MICROSOFT_TENANT_ID = os.environ.get("MICROSOFT_TENANT_ID", "common")

SCOPES = [
    "https://graph.microsoft.com/Files.Read.All",
    "https://graph.microsoft.com/Notes.Read.All",
    "offline_access",
]


def _tokens_dir(state_dir: Path) -> Path:
    p = state_dir / "connector-tokens"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_app(state_dir: Path):
    """Return (msal.PublicClientApplication, SerializableTokenCache). Raises on import error."""
    try:
        import msal  # type: ignore
    except ImportError:
        raise RuntimeError(
            "msal package not installed. Run: pip install msal>=1.28.0"
        )

    cache = msal.SerializableTokenCache()
    cache_path = _tokens_dir(state_dir) / "microsoft.json"
    if cache_path.exists():
        cache.deserialize(cache_path.read_text())

    app = msal.PublicClientApplication(
        client_id=MICROSOFT_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}",
        token_cache=cache,
    )
    return app, cache, cache_path


def _persist(cache, cache_path: Path) -> None:
    if cache.has_state_changed:
        cache_path.write_text(cache.serialize())


def is_configured() -> bool:
    return bool(MICROSOFT_CLIENT_ID)


def is_authenticated(state_dir: Path) -> bool:
    if not is_configured():
        return False
    cache_path = _tokens_dir(state_dir) / "microsoft.json"
    if not cache_path.exists():
        return False
    try:
        app, cache, cache_path = _get_app(state_dir)
        accounts = app.get_accounts()
        if not accounts:
            return False
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _persist(cache, cache_path)
            return True
    except Exception:
        pass
    return False


def start_device_flow(state_dir: Path) -> dict:
    """Start device code flow. Returns {user_code, verification_uri, message}."""
    if not is_configured():
        raise RuntimeError("MICROSOFT_CLIENT_ID env var not set")
    app, cache, cache_path = _get_app(state_dir)
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "error" in flow:
        raise RuntimeError(
            f"Device flow error: {flow.get('error_description', flow['error'])}"
        )
    flow_path = _tokens_dir(state_dir) / "microsoft_flow.json"
    flow_path.write_text(json.dumps(flow))
    return {
        "user_code": flow["user_code"],
        "verification_uri": flow["verification_uri"],
        "message": flow.get("message", ""),
    }


def poll_device_flow(state_dir: Path) -> dict:
    """Poll once for token. Returns {status: pending|complete|error, detail?}."""
    flow_path = _tokens_dir(state_dir) / "microsoft_flow.json"
    if not flow_path.exists():
        return {"status": "error", "detail": "No pending device flow — start auth first"}
    try:
        app, cache, cache_path = _get_app(state_dir)
        flow = json.loads(flow_path.read_text())
        # timeout=5 → try for 5 s then return; MSAL returns error: authorization_pending if not done
        result = app.acquire_token_by_device_flow(flow, timeout=5)
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}

    if "error" in result:
        if result["error"] in ("authorization_pending", "slow_down"):
            return {"status": "pending"}
        return {"status": "error", "detail": result.get("error_description", result["error"])}

    _persist(cache, cache_path)
    flow_path.unlink(missing_ok=True)
    return {"status": "complete"}


def get_token(state_dir: Path) -> str | None:
    """Return a valid access token from cache, or None."""
    if not is_configured():
        return None
    cache_path = _tokens_dir(state_dir) / "microsoft.json"
    if not cache_path.exists():
        return None
    try:
        app, cache, cache_path = _get_app(state_dir)
        accounts = app.get_accounts()
        if not accounts:
            return None
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _persist(cache, cache_path)
            return result["access_token"]
    except Exception:
        pass
    return None


def revoke_token(state_dir: Path) -> None:
    """Clear cached token and any pending flow."""
    tokens_dir = _tokens_dir(state_dir)
    for name in ("microsoft.json", "microsoft_flow.json"):
        p = tokens_dir / name
        if p.exists():
            p.unlink()
