"""Runtime and health route group."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter


@dataclass(frozen=True)
class RuntimeDeps:
    graph_path: Callable[[], str]
    demo_graph_path: Callable[[], str]
    load_graph: Callable[[], dict]
    graphify_status: Callable[..., dict]
    ollama_status: Callable[[], dict]
    storage_status: Callable[..., dict]
    connector_readiness: Callable[[], dict]
    api_key_required: Callable[[], bool]
    app_version: Callable[[], str]
    count_links: Callable[[dict], int]
    graph_validation_error: type[Exception]
    safe_error_message: Callable[[Exception], str]


def runtime_action(label: str, destination: str | None = "settings") -> dict:
    action: dict[str, str] = {"label": label}
    if destination:
        action["destination"] = destination
    return action


def runtime_warning(
    code: str,
    message: str,
    *,
    severity: Literal["warning", "error"] = "warning",
    action_label: str = "Open Settings",
    destination: str | None = "settings",
) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "action": runtime_action(action_label, destination),
    }


def active_graph_readiness(deps: RuntimeDeps) -> dict:
    graph_path = deps.graph_path()
    if not graph_path:
        return {
            "name": None,
            "path": "",
            "configured": False,
            "exists": False,
            "valid": False,
            "node_count": 0,
            "link_count": 0,
            "error": "No workspace graph has been generated or uploaded yet.",
        }
    graph_file = Path(graph_path)
    base = {
        "name": graph_file.name,
        "path": graph_path,
        "configured": True,
        "exists": graph_file.exists(),
        "valid": False,
        "node_count": 0,
        "link_count": 0,
        "error": None,
    }
    try:
        data = deps.load_graph()
    except FileNotFoundError as exc:
        base["error"] = f"Graph not found: {exc}"
    except deps.graph_validation_error as exc:
        base["error"] = f"Invalid graph: {exc}"
    except json.JSONDecodeError as exc:
        base["error"] = f"Invalid JSON: {exc}"
    except Exception as exc:
        base["error"] = deps.safe_error_message(exc)
    else:
        base.update({
            "exists": True,
            "valid": True,
            "node_count": len(data.get("nodes", [])),
            "link_count": deps.count_links(data),
        })
    return base


def build_health(deps: RuntimeDeps) -> dict:
    graph = deps.graph_path()
    graph_configured = bool(graph)
    demo_mode = (
        Path(graph).resolve() == Path(deps.demo_graph_path()).resolve()
        if graph_configured
        else False
    )
    graph_loaded = False
    graph_error = None
    if graph_configured:
        try:
            deps.load_graph()
            graph_loaded = True
        except Exception as exc:
            graph_error = str(exc)
    else:
        graph_error = "No workspace graph has been generated or uploaded yet."
    return {
        "status": "ok",
        "version": deps.app_version(),
        "demo_mode": demo_mode,
        "graph_configured": graph_configured,
        "graph_loaded": graph_loaded,
        "graph_error": graph_error,
        "graphify": deps.graphify_status(include_version=False),
        "storage": deps.storage_status(),
    }


def build_runtime_status(deps: RuntimeDeps) -> dict:
    graph = active_graph_readiness(deps)
    graphify = deps.graphify_status(include_version=False)
    ollama = deps.ollama_status()
    storage = deps.storage_status()
    connectors = deps.connector_readiness()

    warnings: list[dict] = []
    if not graph.get("configured"):
        warnings.append(runtime_warning(
            "NO_GRAPH",
            "This instance does not have a workspace graph yet.",
            severity="warning",
            action_label="Open Workspace Scope",
            destination="scope",
        ))
    elif not graph["valid"]:
        warnings.append(runtime_warning(
            "GRAPH_INVALID",
            graph["error"] or "Active graph is missing or invalid.",
            severity="error",
            action_label="Open graph settings",
        ))
    if not graphify.get("available"):
        warnings.append(runtime_warning(
            graphify.get("code") or "GRAPHIFY_UNAVAILABLE",
            graphify.get("message") or "Graphify CLI is not available.",
            action_label="Review Graphify setup",
        ))
    if not ollama.get("connected"):
        warnings.append(runtime_warning(
            "OLLAMA_UNAVAILABLE",
            f"Ollama is not reachable at {ollama.get('url')}.",
            action_label="Review Ollama settings",
        ))
    elif not ollama.get("chat_model_available", True):
        warnings.append(runtime_warning(
            "OLLAMA_MODEL_UNAVAILABLE",
            f"Configured Ollama model {ollama.get('chat_model')} is not installed at {ollama.get('url')}.",
            action_label="Review Ollama settings",
        ))
    if not storage.get("ready", True):
        warnings.append(runtime_warning(
            "STORAGE_NOT_READY",
            storage.get("warning") or "Storage backend is not ready.",
            action_label="Review storage setup",
        ))
    if connectors.get("error"):
        warnings.append(runtime_warning(
            "CONNECTORS_UNAVAILABLE",
            f"Connector status could not be checked: {connectors['error']}",
            action_label="Review connectors",
        ))
    else:
        unauthenticated = [
            item["display_name"] or item["id"]
            for item in connectors["items"]
            if item["configured"] and not item["authenticated"]
        ]
        if unauthenticated:
            warnings.append(runtime_warning(
                "CONNECTOR_AUTH_REQUIRED",
                f"Connector authentication needed for {', '.join(unauthenticated)}.",
                action_label="Connect Microsoft",
            ))
        if connectors["error_count"]:
            warnings.append(runtime_warning(
                "CONNECTOR_SYNC_ERROR",
                "One or more connector sync jobs reported an error.",
                action_label="Review connector sync",
            ))

    if not graph.get("configured"):
        readiness = "not_ready"
        summary = "This instance does not have a workspace graph yet."
    elif not graph["valid"]:
        readiness = "not_ready"
        summary = "Active graph needs attention before the workspace is usable."
    elif warnings:
        readiness = "partial"
        summary = "Core workspace is available with runtime warnings."
    else:
        readiness = "ready"
        summary = "Workspace runtime is ready."

    next_best_action = (
        warnings[0]["action"]
        if warnings
        else runtime_action("Open graph map", "map")
    )

    return {
        "state": readiness,
        "summary": summary,
        "checked_at": datetime.now(tz=timezone.utc).isoformat(),
        "backend": {"online": True, "version": deps.app_version()},
        "graph": graph,
        "graphify": graphify,
        "ollama": ollama,
        "auth": {"api_key_required": deps.api_key_required()},
        "storage": storage,
        "connectors": connectors,
        "warnings": warnings,
        "next_best_action": next_best_action,
    }


def connector_readiness(
    *,
    list_connectors: Callable[[], list[dict]],
    safe_error_message: Callable[[Exception], str],
) -> dict:
    try:
        connectors = list_connectors()
    except Exception as exc:
        return {
            "items": [],
            "configured_count": 0,
            "authenticated_count": 0,
            "syncing_count": 0,
            "error_count": 1,
            "error": safe_error_message(exc),
        }

    items: list[dict] = []
    for connector in connectors:
        sync = connector.get("sync") or {}
        items.append({
            "id": connector.get("id"),
            "display_name": connector.get("display_name"),
            "configured": bool(connector.get("configured")),
            "authenticated": bool(connector.get("authenticated")),
            "sync_status": sync.get("status") or "never_synced",
            "sync_error": sync.get("error"),
        })

    return {
        "items": items,
        "configured_count": sum(1 for item in items if item["configured"]),
        "authenticated_count": sum(1 for item in items if item["authenticated"]),
        "syncing_count": sum(1 for item in items if item["sync_status"] == "syncing"),
        "error_count": sum(
            1
            for item in items
            if item["sync_status"] == "error" or bool(item["sync_error"])
        ),
        "error": None,
    }


def create_runtime_router(
    *,
    health_endpoint: Callable[[], dict],
    runtime_status_endpoint: Callable[[], dict],
    limiter,
) -> APIRouter:
    router = APIRouter()
    router.add_api_route(
        "/health",
        limiter.exempt(health_endpoint),
        methods=["GET"],
        name="health",
    )
    router.add_api_route(
        "/runtime/status",
        runtime_status_endpoint,
        methods=["GET"],
        name="get_runtime_status",
    )
    return router
