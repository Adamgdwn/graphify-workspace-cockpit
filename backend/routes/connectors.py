"""Cloud connector route group."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

try:
    from backend.connectors import microsoft_auth
    from backend.connectors.ingest import merge_nodes_into_graph
    from backend.connectors.onenote import OneNoteConnector
    from backend.connectors.sharepoint import SharePointConnector
except ModuleNotFoundError:
    from connectors import microsoft_auth
    from connectors.ingest import merge_nodes_into_graph
    from connectors.onenote import OneNoteConnector
    from connectors.sharepoint import SharePointConnector


SYNC_STATUS: dict[str, dict] = {}
SYNC_LOCK = threading.Lock()
CONNECTOR_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "connectors.json"
SUPPORTED_CONNECTORS = ("sharepoint", "onenote")


@dataclass(frozen=True)
class ConnectorDeps:
    workspace_state: Callable[[], Path]
    connectors_dir: Callable[[], Path]
    graphs_dir: Callable[[], Path]
    settings_file: Callable[[], Path]
    graph_path: Callable[[], str]
    write_json_atomic: Callable[[Path, dict], None]
    clear_graph_caches: Callable[[], None]


def is_microsoft_authenticated(workspace_state: Path) -> bool:
    return microsoft_auth.is_authenticated(workspace_state)


def load_connector_config() -> dict:
    if CONNECTOR_CONFIG_PATH.exists():
        try:
            return json.loads(CONNECTOR_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {"sharepoint": {"site_urls": []}, "sync_interval_hours": 0}


def connector_status_path(deps: ConnectorDeps) -> Path:
    return deps.connectors_dir() / "sync-status.json"


def load_sync_status(deps: ConnectorDeps) -> dict:
    path = connector_status_path(deps)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def save_sync_status(status: dict, deps: ConnectorDeps) -> None:
    deps.write_json_atomic(connector_status_path(deps), status)


def run_connector_sync(connector_id: str, deps: ConnectorDeps) -> None:
    """Background sync job; mirrors the mission runner pattern."""
    now = datetime.now(tz=timezone.utc).isoformat()
    with SYNC_LOCK:
        SYNC_STATUS[connector_id] = {
            "status": "syncing",
            "started_at": now,
            "finished_at": None,
            "item_count": 0,
            "error": None,
        }

    try:
        cfg = load_connector_config()
        graph_path = Path(deps.graph_path())
        item_count = 0

        if connector_id == "sharepoint":
            site_urls = cfg.get("sharepoint", {}).get("site_urls", [])
            connector = SharePointConnector(deps.workspace_state(), site_urls)
            items = connector.list_items()
            nodes = connector.to_graph_nodes(items)
            item_count = len(nodes)
        elif connector_id == "onenote":
            connector = OneNoteConnector(deps.workspace_state())
            items = connector.list_items()
            nodes = connector.to_graph_nodes(items)
            item_count = len(nodes)
        else:
            raise ValueError(f"Unknown connector: {connector_id}")

        if nodes:
            new_graph = merge_nodes_into_graph(nodes, graph_path, deps.graphs_dir())
            settings: dict = {}
            settings_file = deps.settings_file()
            if settings_file.exists():
                try:
                    settings = json.loads(settings_file.read_text())
                except Exception:
                    pass
            settings["graph_path"] = str(new_graph)
            deps.write_json_atomic(settings_file, settings)
            deps.clear_graph_caches()

        finished = datetime.now(tz=timezone.utc).isoformat()
        result = {
            "status": "complete",
            "started_at": now,
            "finished_at": finished,
            "item_count": item_count,
            "error": None,
        }
    except Exception as exc:
        finished = datetime.now(tz=timezone.utc).isoformat()
        result = {
            "status": "error",
            "started_at": now,
            "finished_at": finished,
            "item_count": 0,
            "error": str(exc),
        }

    with SYNC_LOCK:
        SYNC_STATUS[connector_id] = result
    save_sync_status({**load_sync_status(deps), connector_id: result}, deps)


def list_connectors(deps: ConnectorDeps) -> list[dict]:
    cfg = load_connector_config()
    persisted = load_sync_status(deps)

    def _status(connector_id: str) -> dict:
        with SYNC_LOCK:
            mem = SYNC_STATUS.get(connector_id)
        return mem or persisted.get(connector_id) or {}

    workspace_state = deps.workspace_state()
    ms_authed = microsoft_auth.is_authenticated(workspace_state)
    ms_configured = microsoft_auth.is_configured()

    return [
        {
            "id": "sharepoint",
            "display_name": "SharePoint",
            "source": "microsoft",
            "configured": ms_configured,
            "authenticated": ms_authed,
            "site_urls": cfg.get("sharepoint", {}).get("site_urls", []),
            "sync": _status("sharepoint"),
        },
        {
            "id": "onenote",
            "display_name": "OneNote",
            "source": "microsoft",
            "configured": ms_configured,
            "authenticated": ms_authed,
            "sync": _status("onenote"),
        },
    ]


def start_microsoft_auth(deps: ConnectorDeps) -> dict:
    try:
        return microsoft_auth.start_device_flow(deps.workspace_state())
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def poll_microsoft_auth(deps: ConnectorDeps) -> dict:
    return microsoft_auth.poll_device_flow(deps.workspace_state())


def sync_connector(connector_id: str, deps: ConnectorDeps) -> dict:
    if connector_id not in SUPPORTED_CONNECTORS:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    if not microsoft_auth.is_authenticated(deps.workspace_state()):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Microsoft. Complete device code auth first.",
        )
    with SYNC_LOCK:
        current = SYNC_STATUS.get(connector_id, {})
    if current.get("status") == "syncing":
        raise HTTPException(status_code=409, detail="Sync already in progress.")

    thread = threading.Thread(
        target=run_connector_sync,
        args=(connector_id, deps),
        daemon=True,
    )
    thread.start()
    return {"connector_id": connector_id, "status": "syncing"}


def connector_sync_status(connector_id: str, deps: ConnectorDeps) -> dict:
    if connector_id not in SUPPORTED_CONNECTORS:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    with SYNC_LOCK:
        mem = SYNC_STATUS.get(connector_id)
    if mem:
        return mem
    persisted = load_sync_status(deps)
    return persisted.get(connector_id) or {"status": "never_synced"}


def revoke_connector_auth(connector_id: str, deps: ConnectorDeps) -> dict:
    if connector_id not in (*SUPPORTED_CONNECTORS, "microsoft"):
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    microsoft_auth.revoke_token(deps.workspace_state())
    return {"revoked": True, "connector_id": connector_id}


def create_connectors_router(deps_factory: Callable[[], ConnectorDeps]) -> APIRouter:
    router = APIRouter()

    @router.get("/connectors")
    def list_connectors_endpoint() -> list[dict]:
        return list_connectors(deps_factory())

    @router.post("/connectors/microsoft/auth")
    def start_microsoft_auth_endpoint() -> dict:
        return start_microsoft_auth(deps_factory())

    @router.post("/connectors/microsoft/auth/poll")
    def poll_microsoft_auth_endpoint() -> dict:
        return poll_microsoft_auth(deps_factory())

    @router.post("/connectors/{connector_id}/sync", status_code=202)
    def sync_connector_endpoint(connector_id: str) -> dict:
        return sync_connector(connector_id, deps_factory())

    @router.get("/connectors/{connector_id}/status")
    def connector_sync_status_endpoint(connector_id: str) -> dict:
        return connector_sync_status(connector_id, deps_factory())

    @router.delete("/connectors/{connector_id}/auth", status_code=200)
    def revoke_connector_auth_endpoint(connector_id: str) -> dict:
        return revoke_connector_auth(connector_id, deps_factory())

    return router
