"""Graphify Workspace Cockpit — backend API."""

from __future__ import annotations

import json
import os
import re
import uuid
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Optional

import hashlib

from fastapi import File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded

try:
    from backend import config as _config
    from backend.app import create_app
    from backend.auth import APIKeyMiddleware
    from backend.graph_schema import GraphValidationError, count_links, normalize_graph
    from backend.map_decision_overlay import (
        build_decision_overlay_context,
        decision_overlay_for_terms,
        overlay_add_term,
        overlay_terms_for_node,
    )
    from backend.routes import ask as _ask_routes
    from backend.routes import chat as _chat_routes
    from backend.routes import cluster_selection as _cluster_selection_routes
    from backend.routes import connectors as _connector_routes
    from backend.routes import decisions as _decision_routes
    from backend.routes import runtime as _runtime_routes
    from backend.routes import workspace_scope as _workspace_scope_routes
    from backend.services.graphify_service import (
        GRAPHIFY_MISSING,
        GraphifyServiceError,
        get_graphify_status,
        run_graphify_ask,
        run_graphify_update,
    )
    from backend.state_store import write_json_atomic
    from backend.storage_status import StorageStatusProvider, safe_error_message
    from backend.workspace_scope import (
        WorkspaceScopeError,
        apply_signal_tiers_to_graph,
        filter_workspace_scope_graph,
        importance_counts,
        is_visible_knowledge_node,
        is_visible_signal_node,
        load_workspace_scope_profile,
        signal_counts,
        workspace_scope_scan_roots,
    )
except ModuleNotFoundError:
    import config as _config
    from app import create_app
    from auth import APIKeyMiddleware
    from graph_schema import GraphValidationError, count_links, normalize_graph
    from map_decision_overlay import (
        build_decision_overlay_context,
        decision_overlay_for_terms,
        overlay_add_term,
        overlay_terms_for_node,
    )
    from routes import ask as _ask_routes
    from routes import chat as _chat_routes
    from routes import cluster_selection as _cluster_selection_routes
    from routes import connectors as _connector_routes
    from routes import decisions as _decision_routes
    from routes import runtime as _runtime_routes
    from routes import workspace_scope as _workspace_scope_routes
    from services.graphify_service import (
        GRAPHIFY_MISSING,
        GraphifyServiceError,
        get_graphify_status,
        run_graphify_ask,
        run_graphify_update,
    )
    from state_store import write_json_atomic
    from storage_status import StorageStatusProvider, safe_error_message
    from workspace_scope import (
        WorkspaceScopeError,
        apply_signal_tiers_to_graph,
        filter_workspace_scope_graph,
        importance_counts,
        is_visible_knowledge_node,
        is_visible_signal_node,
        load_workspace_scope_profile,
        signal_counts,
        workspace_scope_scan_roots,
    )

AskDeps = _ask_routes.AskDeps
AskRequest = _ask_routes.AskRequest
AskResponse = _ask_routes.AskResponse
EvidenceNode = _ask_routes.EvidenceNode
Mode = _ask_routes.Mode
create_ask_router = _ask_routes.create_ask_router
parse_explain_output = _ask_routes.parse_explain_output
parse_path_output = _ask_routes.parse_path_output
parse_query_output = _ask_routes.parse_query_output
suggestions = _ask_routes.suggestions

ChatConfigBody = _chat_routes.ChatConfigBody
ChatDeps = _chat_routes.ChatDeps
_ChatMsgModel = _chat_routes.ChatMsgModel
ChatRequest = _chat_routes.ChatRequest
create_chat_router = _chat_routes.create_chat_router

ClusterSelectionBody = _cluster_selection_routes.ClusterSelectionBody
ClusterSelectionDeps = _cluster_selection_routes.ClusterSelectionDeps
create_cluster_selection_router = _cluster_selection_routes.create_cluster_selection_router

CONNECTOR_CONFIG_PATH = _connector_routes.CONNECTOR_CONFIG_PATH
SYNC_LOCK = _connector_routes.SYNC_LOCK
SYNC_STATUS = _connector_routes.SYNC_STATUS
ConnectorDeps = _connector_routes.ConnectorDeps
_route_connector_status_path = _connector_routes.connector_status_path
_route_connector_sync_status = _connector_routes.connector_sync_status
create_connectors_router = _connector_routes.create_connectors_router
is_microsoft_authenticated = _connector_routes.is_microsoft_authenticated
_route_list_connectors = _connector_routes.list_connectors
_route_load_connector_config = _connector_routes.load_connector_config
_route_load_sync_status = _connector_routes.load_sync_status
_route_poll_microsoft_auth = _connector_routes.poll_microsoft_auth
_route_revoke_connector_auth = _connector_routes.revoke_connector_auth
_route_run_connector_sync = _connector_routes.run_connector_sync
_route_save_sync_status = _connector_routes.save_sync_status
_route_start_microsoft_auth = _connector_routes.start_microsoft_auth
_route_sync_connector = _connector_routes.sync_connector

CreateDecisionRequest = _decision_routes.CreateDecisionRequest
DecisionClassification = _decision_routes.DecisionClassification
DecisionDeps = _decision_routes.DecisionDeps
PatchDecisionRequest = _decision_routes.PatchDecisionRequest
create_decision_record = _decision_routes.create_decision_record
create_decisions_router = _decision_routes.create_decisions_router
list_decisions_response = _decision_routes.list_decisions_response
_route_load_decisions = _decision_routes.load_decisions
patch_decision_record = _decision_routes.patch_decision_record
_route_save_decisions = _decision_routes.save_decisions
_route_upsert_decision = _decision_routes.upsert_decision

RuntimeDeps = _runtime_routes.RuntimeDeps
_route_active_graph_readiness = _runtime_routes.active_graph_readiness
build_health = _runtime_routes.build_health
build_runtime_status = _runtime_routes.build_runtime_status
_route_connector_readiness = _runtime_routes.connector_readiness
create_runtime_router = _runtime_routes.create_runtime_router
runtime_action = _runtime_routes.runtime_action
runtime_warning = _runtime_routes.runtime_warning

WorkspaceScopeDeps = _workspace_scope_routes.WorkspaceScopeDeps
create_workspace_scope_router = _workspace_scope_routes.create_workspace_scope_router
inspect_workspace_scope = _workspace_scope_routes.inspect_workspace_scope

_STATE_DIR_ENV = _config.STATE_DIR_ENV
WORKSPACE_STATE = _config.WORKSPACE_STATE
SESSIONS_DIR = _config.SESSIONS_DIR
SETTINGS_FILE = _config.SETTINGS_FILE
DECISIONS_FILE = _config.DECISIONS_FILE
GRAPHS_DIR = _config.GRAPHS_DIR
DEVICES_FILE = _config.DEVICES_FILE
CONNECTORS_DIR = _config.CONNECTORS_DIR
CLUSTER_SELECTION_FILE = _config.CLUSTER_SELECTION_FILE
CHAT_CONFIG_FILE = _config.CHAT_CONFIG_FILE
CHAT_SESSIONS_DIR = _config.CHAT_SESSIONS_DIR
SCAN_DIRS_FILE = _config.SCAN_DIRS_FILE
WORKSPACE_SCOPE_FILE = _config.WORKSPACE_SCOPE_FILE
SEMANTIC_EDGES_FILE = _config.SEMANTIC_EDGES_FILE
OVERLAP_STATUS_FILE = _config.OVERLAP_STATUS_FILE
_CHAT_DEFAULT_SYSTEM_PROMPT = _config.CHAT_DEFAULT_SYSTEM_PROMPT
_USERS_FILE = _config.USERS_FILE

_DEMO_GRAPH = _config.DEMO_GRAPH
DEFAULT_GRAPH = _config.DEFAULT_GRAPH
API_KEY = _config.API_KEY
GRAPH_UPLOAD_MAX_BYTES = _config.GRAPH_UPLOAD_MAX_BYTES

STORAGE_BACKEND = _config.STORAGE_BACKEND  # "file" | "supabase"

# Supabase client — initialised only when STORAGE_BACKEND=supabase
_supabase_client = None
if STORAGE_BACKEND == "supabase":
    _supabase_url = os.environ.get("SUPABASE_URL", "")
    _supabase_key = os.environ.get("SUPABASE_KEY", "")
    if not _supabase_url or not _supabase_key:
        raise RuntimeError("STORAGE_BACKEND=supabase requires SUPABASE_URL and SUPABASE_KEY env vars.")
    try:
        from supabase import create_client as _create_supabase_client
        _supabase_client = _create_supabase_client(_supabase_url, _supabase_key)
    except ImportError as _e:
        raise RuntimeError(f"STORAGE_BACKEND=supabase requires the 'supabase' package: {_e}")

SUPABASE_SCHEMA_MIGRATION = "db/migrations/002_recommendation_action_plans.sql"
SUPABASE_SCHEMA_REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "recommendations": ("action_plan", "overlap", "overlap_dossier", "context"),
    "actions": ("action_plan",),
}
_supabase_schema_status_cache: dict | None = None
_storage_status_provider = StorageStatusProvider(
    backend_getter=lambda: STORAGE_BACKEND,
    client_getter=lambda: _supabase_client,
    required_migration=SUPABASE_SCHEMA_MIGRATION,
    required_columns=SUPABASE_SCHEMA_REQUIRED_COLUMNS,
)


def _safe_error_message(exc: Exception) -> str:
    return safe_error_message(exc)


def _check_supabase_schema() -> dict:
    """Verify the optional Supabase columns required by current app records."""
    return _storage_status_provider.check_schema()


def _storage_status(force_check: bool = False) -> dict:
    global _supabase_schema_status_cache
    if STORAGE_BACKEND != "supabase":
        return _check_supabase_schema()
    if force_check or _supabase_schema_status_cache is None:
        _supabase_schema_status_cache = _check_supabase_schema()
    return _supabase_schema_status_cache

# In-memory cache — loaded once per server lifetime
_graph_cache: dict | None = None
_summary_cache: dict[str, dict] = {}

_REPO_ROOT = _config.REPO_ROOT
_SECRET_PATH_MARKERS = _config.SECRET_PATH_MARKERS


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        {"error": "rate_limit_exceeded", "detail": str(exc.detail)},
        status_code=429,
        headers={"Retry-After": "60"},
    )


def _prune_sessions(max_count: int = 50) -> None:
    if not SESSIONS_DIR.exists():
        return
    files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[max_count:]:
        try:
            f.unlink()
        except Exception:
            pass


def _prune_chat_sessions(max_count: int = 50) -> None:
    if not CHAT_SESSIONS_DIR.exists():
        return
    files = sorted(CHAT_SESSIONS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[max_count:]:
        try:
            f.unlink()
        except Exception:
            pass


def _load_chat_config() -> dict:
    if CHAT_CONFIG_FILE.exists():
        try:
            return json.loads(CHAT_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {"system_prompt": _CHAT_DEFAULT_SYSTEM_PROMPT, "model": RECOMMEND_MODEL_DEFAULT}


# Rebuild graph state
_REBUILD_STATUS: dict = {"status": "idle", "last_run": None}

# Semantic similarity pass state
_SEMANTIC_STATUS: dict = {
    "status": "idle",   # idle | running | complete | error
    "progress": 0,
    "total": 0,
    "last_run": None,
    "error": None,
    "edge_count": 0,
    "model": None,
}


def _resolve_user(api_key: str) -> str:
    """Map an API key to a human-readable user name via config/users.json.
    Falls back to 'adam' (single-user default) when no mapping exists."""
    if not api_key:
        return "local"
    if _USERS_FILE.exists():
        try:
            users = json.loads(_USERS_FILE.read_text())
            if api_key in users:
                return users[api_key]
        except Exception:
            pass
    return "adam"


def _etag(data: list | dict) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return '"' + hashlib.md5(payload.encode()).hexdigest() + '"'


def _track_device(user_id: str) -> None:
    """Record this user's last-seen timestamp in devices.json (best-effort)."""
    try:
        devices: dict = {}
        if DEVICES_FILE.exists():
            try:
                devices = json.loads(DEVICES_FILE.read_text())
            except Exception:
                pass
        devices[user_id] = datetime.now(tz=timezone.utc).isoformat()
        write_json_atomic(DEVICES_FILE, devices)
    except Exception:
        pass


@asynccontextmanager
async def _lifespan(_app):
    _prune_sessions()
    _prune_chat_sessions()
    yield


app, _limiter = create_app(
    title="Graphify Workspace Cockpit",
    version="0.1.0",
    cors_origins=_config.CORS_ORIGINS,
    api_key_middleware_cls=APIKeyMiddleware,
    api_key_getter=lambda: API_KEY,
    resolve_user=_resolve_user,
    rate_limit_handler=_rate_limit_handler,
    lifespan=_lifespan,
)


def _load_graph() -> dict:
    global _graph_cache
    if _graph_cache is None:
        path = _graph_path()
        if not Path(path).exists():
            raise FileNotFoundError(path)
        with open(path) as f:
            _graph_cache = normalize_graph(json.load(f))
    return _graph_cache


def _graph_path() -> str:
    if SETTINGS_FILE.exists():
        try:
            s = json.loads(SETTINGS_FILE.read_text())
            return s.get("graph_path", DEFAULT_GRAPH)
        except Exception:
            pass
    return DEFAULT_GRAPH


def _load_settings_dict() -> dict:
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text())
            if isinstance(settings, dict):
                return settings
        except Exception:
            pass
    return {}


def _graph_fingerprint(graph: dict) -> str:
    h = hashlib.sha256()
    nodes = sorted(graph.get("nodes", []), key=lambda n: str(n.get("id", "")))
    for node in nodes:
        h.update(str(node.get("id", "")).encode())
        h.update(b"\0")
        h.update(str(node.get("label", "")).encode())
        h.update(b"\0")
        h.update(str(node.get("source_file", "")).encode())
        h.update(b"\0")
        h.update(str(node.get("source_root_name", "")).encode())
        h.update(b"\n")
    h.update(b"links\n")
    links = sorted(
        graph.get("links", []),
        key=lambda link: (
            str(link.get("source", "")),
            str(link.get("target", "")),
            str(link.get("relation", "")),
        ),
    )
    for link in links:
        h.update(str(link.get("source", "")).encode())
        h.update(b"\0")
        h.update(str(link.get("target", "")).encode())
        h.update(b"\0")
        h.update(str(link.get("relation", "")).encode())
        h.update(b"\n")
    return h.hexdigest()


def _semantic_edges_match_graph(graph: dict) -> bool:
    if not SEMANTIC_EDGES_FILE.exists():
        return True
    try:
        data = json.loads(SEMANTIC_EDGES_FILE.read_text())
    except Exception:
        return False
    stored_fingerprint = str(data.get("graph_fingerprint") or "")
    return bool(stored_fingerprint and stored_fingerprint == _graph_fingerprint(graph))


def _clear_semantic_edges_if_graph_changed(path: Path, previous_graph_path: str) -> None:
    if not SEMANTIC_EDGES_FILE.exists():
        return
    clear_cache = previous_graph_path != str(path)
    if not clear_cache:
        try:
            graph = normalize_graph(json.loads(path.read_text()), require_link_targets=True)
            clear_cache = not _semantic_edges_match_graph(graph)
        except Exception:
            clear_cache = True
    if clear_cache:
        try:
            SEMANTIC_EDGES_FILE.unlink()
        except OSError:
            pass


def _activate_rebuild_graph(path: Path) -> None:
    previous_graph_path = _graph_path()
    settings = _load_settings_dict()
    settings["graph_path"] = str(path)
    write_json_atomic(SETTINGS_FILE, settings)
    _clear_semantic_edges_if_graph_changed(path, previous_graph_path)


def _load_saved_workspace_scope() -> dict | None:
    try:
        return load_workspace_scope_profile(WORKSPACE_SCOPE_FILE)
    except WorkspaceScopeError:
        return None


def _configured_source_roots() -> list[Path]:
    roots = [_REPO_ROOT]
    profile = _load_saved_workspace_scope()
    if profile is not None:
        scoped_roots = workspace_scope_scan_roots(profile) or [Path(profile["root"])]
        for root in scoped_roots:
            if root not in roots:
                roots.append(root)
        return roots

    for raw in _load_scan_dirs():
        try:
            root = Path(raw).expanduser().resolve()
        except Exception:
            continue
        if root not in roots:
            roots.append(root)
    return roots


def _workspace_scope_removed_node_count(graph: dict) -> int:
    meta = graph.get("_meta")
    if not isinstance(meta, dict):
        return 0
    scope = meta.get("workspace_scope")
    if not isinstance(scope, dict):
        return 0
    try:
        return max(0, int(scope.get("removed_node_count", 0)))
    except (TypeError, ValueError):
        return 0


def _workspace_scope_summary_metadata(graph: dict) -> dict | None:
    meta = graph.get("_meta")
    if not isinstance(meta, dict):
        return None
    scope = meta.get("workspace_scope")
    if not isinstance(scope, dict):
        return None
    return {
        "profile_name": scope.get("profile_name") or "Workspace Scope",
        "root": scope.get("root") or "",
        "included_paths": list(scope.get("included_paths") or []),
        "excluded_paths": list(scope.get("excluded_paths") or []),
        "scanned_root_count": scope.get("scanned_root_count") or 0,
        "removed_node_count": scope.get("removed_node_count") or 0,
        "generated_at": scope.get("generated_at"),
    }


def _safe_graph_upload_name(filename: str | None) -> str:
    raw_name = (filename or "").strip()
    name = Path(raw_name).name
    if not raw_name or name in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="Graph filename is required.")
    if name != raw_name or "\\" in raw_name:
        raise HTTPException(
            status_code=400,
            detail="Graph filename must not include path separators.",
        )
    if Path(name).suffix.lower() != ".json":
        raise HTTPException(status_code=400, detail="Graph upload must be a .json file.")
    return name


_parse_query_output = parse_query_output
_parse_explain_output = parse_explain_output
_parse_path_output = parse_path_output
_suggestions = suggestions


# ---------------------------------------------------------------------------
# Cluster selection helpers (Chunk Sixteen)
# ---------------------------------------------------------------------------

def _load_cluster_selection() -> dict:
    if CLUSTER_SELECTION_FILE.exists():
        try:
            return json.loads(CLUSTER_SELECTION_FILE.read_text())
        except Exception:
            pass
    return {"sources": ["local", "sharepoint", "onenote"], "clusters": None}


def _save_cluster_selection(sel: dict) -> None:
    write_json_atomic(CLUSTER_SELECTION_FILE, sel)


def _node_source_parts(node: dict) -> list[str]:
    source_file = str(
        node.get("source_file") or node.get("file_path") or node.get("path") or ""
    ).replace("\\", "/")
    return [part for part in source_file.split("/") if part]


def _node_relative_source_parts(node: dict) -> list[str]:
    source_file = str(
        node.get("source_file") or node.get("file_path") or node.get("path") or ""
    ).replace("\\", "/")
    source_root = str(node.get("source_root") or "").strip().replace("\\", "/")
    if source_file and source_root and source_file.startswith(source_root.rstrip("/") + "/"):
        source_file = source_file[len(source_root.rstrip("/")) + 1:]
    return [part for part in source_file.split("/") if part]


def _node_workspace_key(node: dict) -> str:
    source_root = str(node.get("source_root") or "").strip()
    if source_root:
        return source_root
    repo_name = str(
        node.get("repo_project_name") or node.get("source_root_name") or ""
    ).strip()
    if repo_name:
        return repo_name
    parts = _node_source_parts(node)
    return parts[0] if parts else "(root)"


def _node_workspace_label(node: dict, key: str | None = None) -> str:
    label = str(
        node.get("repo_project_name") or node.get("source_root_name") or ""
    ).strip()
    if label:
        return label
    workspace_key = key or _node_workspace_key(node)
    if workspace_key == "(root)":
        return workspace_key
    return Path(workspace_key).name or workspace_key


def _node_cluster_id(node: dict) -> str:
    return _node_workspace_label(node)


def _node_overlap_cluster_id(node: dict) -> str:
    workspace_key = _node_workspace_key(node)
    _, module_label = _node_module_group(node, workspace_key)
    if module_label != "(root)":
        return f"{_node_workspace_label(node, workspace_key)}::{module_label}"
    return _node_workspace_label(node, workspace_key)


def _node_project_relative_parts(node: dict, workspace_key: str) -> list[str]:
    parts = _node_relative_source_parts(node)
    if not parts:
        return []

    has_scope_metadata = any(
        str(node.get(key) or "").strip()
        for key in ("source_root", "repo_project_name", "source_root_name")
    )
    if not has_scope_metadata and parts[0] == workspace_key:
        return parts[1:]
    return parts


def _node_module_group(node: dict, workspace_key: str) -> tuple[str, str]:
    parts = _node_project_relative_parts(node, workspace_key)
    if len(parts) <= 1:
        module = "(root)"
    else:
        module = parts[0]
    return f"{workspace_key}::{module}", module


def _node_path_area(node: dict) -> tuple[str, str] | None:
    parts = _node_relative_source_parts(node)
    if not parts:
        return None
    area = parts[0]
    if len(parts) == 1 and Path(area).suffix:
        return "__workspace_docs__", "Workspace Docs"
    return area, area


def _should_group_summary_by_path(nodes: list[dict]) -> bool:
    """Use path-derived groups when broad scope metadata would collapse the map."""
    if len({_node_workspace_key(node) for node in nodes}) > 1:
        return False
    path_groups = {
        area_label[0]
        for node in nodes
        for area_label in [_node_path_area(node)]
        if area_label is not None
    }
    return len(path_groups) > 1


def _node_path_module_group(node: dict, area: str) -> tuple[str, str] | None:
    parts = _node_relative_source_parts(node)
    if not parts or parts[0] != area:
        return None
    module = parts[1] if len(parts) > 1 else "(root)"
    return f"{area}::{module}", module


def _summary_cluster_getter(
    nodes: list[dict],
    project: str | None = None,
) -> tuple[Callable[[dict], str | None], dict[str, str], dict[str, str]]:
    cluster_labels: dict[str, str] = {}
    cluster_group_types: dict[str, str] = {}
    group_by_path = _should_group_summary_by_path(nodes)
    project_is_path_area = bool(
        project is not None
        and any((area := _node_path_area(n)) is not None and area[0] == project for n in nodes)
    )

    def get_cluster(n: dict) -> str | None:
        if project is None and group_by_path:
            area = _node_path_area(n)
            if area is None:
                return None
            cluster_id, label = area
            cluster_labels.setdefault(cluster_id, label)
            cluster_group_types.setdefault(cluster_id, "repo")
            return cluster_id
        if project_is_path_area and project is not None:
            module = _node_path_module_group(n, project)
            if module is None:
                return None
            module_key, module_label = module
            cluster_labels.setdefault(module_key, module_label)
            cluster_group_types.setdefault(module_key, "module")
            return module_key
        workspace_key = _node_workspace_key(n)
        if project is None:
            cluster_labels.setdefault(workspace_key, _node_workspace_label(n, workspace_key))
            cluster_group_types.setdefault(workspace_key, "repo")
            return workspace_key
        if workspace_key != project:
            return None
        module_key, module_label = _node_module_group(n, workspace_key)
        cluster_labels.setdefault(module_key, module_label)
        cluster_group_types.setdefault(module_key, "module")
        return module_key

    return get_cluster, cluster_labels, cluster_group_types


def _gap_triage(
    *,
    node: dict,
    hidden_counts: Counter[str],
    hidden_link_counts: Counter[str],
    hidden_link_relations: dict[str, set[str]],
    total_link_counts: Counter[str],
) -> dict:
    cluster_id = str(node["id"])
    code_count = int(node.get("code_count") or 0)
    doc_count = int(node.get("doc_count") or 0)
    node_count = int(node.get("node_count") or 0)
    hidden_count = hidden_counts[cluster_id]
    hidden_links = hidden_link_counts[cluster_id]
    relation_list = sorted(hidden_link_relations.get(cluster_id, set()))[:3]

    if cluster_id == "__workspace_docs__" or (
        str(node.get("label") or "").lower() in {"workspace docs", "(root)"}
        and doc_count >= code_count
    ):
        return {
            "gap_type": "root_level_docs_only",
            "gap_detail": "This looks like root-level workspace documentation rather than an isolated project.",
            "gap_evidence": [
                f"{doc_count} document node{'s' if doc_count != 1 else ''} in the group.",
                "No visible cross-group physical links were found.",
            ],
            "gap_actions": ["drill_in", "ask", "monitor", "archive"],
        }

    if hidden_links > 0:
        relation_text = f" ({', '.join(relation_list)})" if relation_list else ""
        return {
            "gap_type": "hidden_by_low_signal_filters",
            "gap_detail": "Low-signal evidence links would connect this group, but default map filters hide those nodes.",
            "gap_evidence": [
                f"{hidden_links} hidden cross-group link{'s' if hidden_links != 1 else ''}{relation_text}.",
                f"{hidden_count} low-signal node{'s' if hidden_count != 1 else ''} in this group.",
            ],
            "gap_actions": ["drill_in", "show_low_signal", "ask", "monitor"],
        }

    if code_count > 0 or node_count > 1:
        return {
            "gap_type": "missing_semantic_extraction",
            "gap_detail": "This group has visible build material, but the stored graph has no cross-group relationships for it.",
            "gap_evidence": [
                f"{code_count} code node{'s' if code_count != 1 else ''} and {doc_count} document node{'s' if doc_count != 1 else ''}.",
                f"{total_link_counts[cluster_id]} total stored link{'s' if total_link_counts[cluster_id] != 1 else ''} touch this group.",
            ],
            "gap_actions": ["drill_in", "ask", "monitor"],
        }

    return {
        "gap_type": "truly_isolated",
        "gap_detail": "No visible or hidden graph relationships connect this group to the current map.",
        "gap_evidence": [
            f"{node_count} visible node{'s' if node_count != 1 else ''} in this group.",
            "No cross-group physical links were found in the stored graph.",
        ],
        "gap_actions": ["drill_in", "ask", "monitor", "archive"],
    }


def _is_node_selected(n: dict, sel_sources: list[str], sel_clusters: list[str] | None) -> bool:
    """Return True if node passes the active source/cluster filter."""
    node_source = n.get("source", "local")
    if node_source not in sel_sources:
        return False
    if sel_clusters is not None:
        cluster = _node_cluster_id(n)
        if cluster and cluster not in sel_clusters:
            return False
    return True


def _source_matches_evidence(node_source: str, evidence_source: str) -> bool:
    node_source = node_source.replace("\\", "/").strip()
    evidence_source = evidence_source.replace("\\", "/").strip()
    if not node_source or not evidence_source:
        return False
    return (
        node_source == evidence_source
        or node_source.endswith(f"/{evidence_source}")
        or evidence_source.endswith(f"/{node_source}")
    )


def _scope_ask_evidence(evidence: list[dict]) -> list[dict]:
    """Attach scope metadata to Ask evidence and hide excluded/low-signal hits."""
    if not evidence:
        return []
    try:
        graph = apply_signal_tiers_to_graph(_load_graph())
    except Exception:
        return evidence

    selection = _load_cluster_selection()
    sel_sources = selection.get("sources", ["local", "sharepoint", "onenote"])
    sel_clusters = selection.get("clusters")
    nodes = [
        n for n in graph.get("nodes", [])
        if isinstance(n, dict)
        and _is_node_selected(n, sel_sources, sel_clusters)
        and is_visible_signal_node(n)
    ]
    by_id = {str(n.get("id", "")): n for n in nodes}
    by_label = {str(n.get("label", "")): n for n in nodes}

    scoped: list[dict] = []
    for item in evidence:
        ev = dict(item)
        label = str(ev.get("label") or "")
        source = str(ev.get("src") or "")
        match = by_id.get(label) or by_label.get(label)
        if match is None and source:
            for node in nodes:
                if _source_matches_evidence(str(node.get("source_file") or ""), source):
                    match = node
                    break
        if match is None:
            if source:
                continue
            scoped.append(ev)
            continue
        ev.setdefault("src", match.get("source_file", ""))
        ev["community"] = _node_workspace_label(match)
        ev["repo"] = _node_workspace_label(match)
        ev["source_root"] = match.get("source_root", "")
        ev["signal_tier"] = match.get("signal_tier", "important")
        ev["signal_reason"] = match.get("signal_reason", "")
        scoped.append(ev)
    return scoped


def _map_decision_overlay_context() -> dict:
    try:
        decisions = _load_decisions()
    except Exception:
        decisions = []
    try:
        recommendations = _load_recommendations()
    except Exception:
        recommendations = []
    try:
        actions = _load_all_actions()
    except Exception:
        actions = []
    recommendations = _current_map_recommendations(recommendations)
    current_rec_ids = {str(rec.get("id") or "") for rec in recommendations}
    actions = [
        action for action in actions
        if not action.get("source_recommendation_id")
        or str(action.get("source_recommendation_id") or "") in current_rec_ids
    ]
    return build_decision_overlay_context(
        decisions=decisions,
        recommendations=recommendations,
        actions=actions,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _runtime_deps() -> RuntimeDeps:
    return RuntimeDeps(
        graph_path=_graph_path,
        demo_graph_path=lambda: _DEMO_GRAPH,
        load_graph=_load_graph,
        graphify_status=lambda **kwargs: get_graphify_status(**kwargs),
        ollama_status=ollama_status,
        storage_status=lambda **kwargs: _storage_status(**kwargs),
        connector_readiness=lambda: _connector_readiness(),
        api_key_required=lambda: bool(API_KEY),
        app_version=lambda: app.version,
        count_links=count_links,
        graph_validation_error=GraphValidationError,
        safe_error_message=_safe_error_message,
    )


def health() -> dict:
    return build_health(_runtime_deps())


_runtime_action = runtime_action
_runtime_warning = runtime_warning


def _active_graph_readiness() -> dict:
    return _route_active_graph_readiness(_runtime_deps())


def _connector_readiness() -> dict:
    return _route_connector_readiness(
        list_connectors=list_connectors,
        safe_error_message=_safe_error_message,
    )


def runtime_status() -> dict:
    return build_runtime_status(_runtime_deps())


def get_runtime_status() -> dict:
    return runtime_status()


app.include_router(create_runtime_router(
    health_endpoint=health,
    runtime_status_endpoint=get_runtime_status,
    limiter=_limiter,
))


def _workspace_scope_deps() -> WorkspaceScopeDeps:
    return WorkspaceScopeDeps(
        inspect_scope=inspect_workspace_scope,
        scope_file=lambda: WORKSPACE_SCOPE_FILE,
        write_json_atomic=write_json_atomic,
    )


app.include_router(create_workspace_scope_router(_workspace_scope_deps))


def _ask_deps() -> AskDeps:
    return AskDeps(
        graph_path=_graph_path,
        run_graphify_ask=lambda **kwargs: run_graphify_ask(**kwargs),
        load_cluster_selection=_load_cluster_selection,
        scope_evidence=_scope_ask_evidence,
        sessions_dir=lambda: SESSIONS_DIR,
        write_json_atomic=write_json_atomic,
        prune_sessions=_prune_sessions,
        graphify_error=GraphifyServiceError,
    )


_ask_router, ask = create_ask_router(_ask_deps)
app.include_router(_ask_router)


@app.get("/graph/summary")
def graph_summary(project: str | None = None, min_weight: int = 2) -> dict:
    """Return a project-level or sub-project-level graph summary.

    At top level (no project param): groups nodes by first path component.
    At project level (?project=agents): groups by second path component within that project.
    Results are cached in memory after first computation.
    """
    global _summary_cache
    selection = _load_cluster_selection()
    sel_sources = selection.get("sources", ["local", "sharepoint", "onenote"])
    sel_clusters = selection.get("clusters")
    sel_hash = hashlib.md5(json.dumps(selection, sort_keys=True).encode()).hexdigest()[:8]
    overlay_context = _map_decision_overlay_context()
    cache_key = f"{project}:{min_weight}:{sel_hash}:{overlay_context['hash']}"
    if cache_key in _summary_cache:
        return _summary_cache[cache_key]

    try:
        graph = _load_graph()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Graph not found: {exc}. Run graphify update first.",
        ) from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid graph: {exc}") from exc

    signal_graph = apply_signal_tiers_to_graph(graph)
    excluded_node_count = _workspace_scope_removed_node_count(signal_graph)
    selected_nodes = [
        n for n in signal_graph["nodes"]
        if _is_node_selected(n, sel_sources, sel_clusters)
    ]
    counts_by_signal = signal_counts(selected_nodes)
    counts_by_importance = importance_counts(selected_nodes)
    nodes_raw: list[dict] = [
        n for n in selected_nodes
        if is_visible_signal_node(n)
    ]
    links_raw: list[dict] = signal_graph["links"]
    node_map: dict[str, dict] = {n["id"]: n for n in nodes_raw}

    get_cluster, cluster_labels, cluster_group_types = _summary_cluster_getter(
        nodes_raw,
        project,
    )

    # Aggregate node counts per cluster
    cluster_stats: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "code": 0, "document": 0, "rationale": 0}
    )
    for n in nodes_raw:
        key = get_cluster(n)
        if key is None:
            continue
        ftype = n.get("file_type", "code")
        cluster_stats[key]["total"] += 1
        cluster_stats[key][ftype] = cluster_stats[key].get(ftype, 0) + 1

    # Build summary node list — filter tiny clusters and the synthetic (root) group
    EXCLUDED_CLUSTERS: set[str] = set()
    min_nodes = 1
    summary_nodes: list[dict] = []
    valid_ids: set[str] = set()
    for cluster_id, stats in sorted(
        cluster_stats.items(), key=lambda x: -x[1]["total"]
    ):
        if stats["total"] < min_nodes or cluster_id in EXCLUDED_CLUSTERS:
            continue
        label = cluster_labels.get(cluster_id) or (cluster_id.split("/")[-1] if "/" in cluster_id else cluster_id)
        code = stats.get("code", 0)
        doc = stats.get("document", 0)
        dominant = "code" if code >= doc else "document"
        summary_nodes.append(
            {
                "id": cluster_id,
                "label": label,
                "group_type": cluster_group_types.get(cluster_id, "group"),
                "node_count": stats["total"],
                "code_count": code,
                "doc_count": doc,
                "rationale_count": stats.get("rationale", 0),
                "dominant_type": dominant,
                "is_drillable": project is None,
            }
        )
        valid_ids.add(cluster_id)

    selected_node_map: dict[str, dict] = {
        str(n.get("id")): n
        for n in selected_nodes
        if n.get("id")
        and str(n.get("signal_tier") or "evidence") != "excluded"
    }
    hidden_counts: Counter[str] = Counter()
    cluster_overlay_terms: dict[str, set[str]] = defaultdict(set)
    for n in selected_node_map.values():
        cluster = get_cluster(n)
        if cluster in valid_ids:
            cluster_overlay_terms[cluster].update(
                overlay_terms_for_node(
                    n,
                    workspace_label=_node_workspace_label(n),
                    cluster_id=_node_cluster_id(n),
                )
            )
        if is_visible_signal_node(n):
            continue
        if cluster in valid_ids:
            hidden_counts[cluster] += 1

    # Aggregate inter-cluster edge weights. Summary relationships are undirected:
    # a broad map should show that two visible areas touch, not split the same
    # relationship by source/target direction.
    edge_weights: Counter[tuple[str, str]] = Counter()
    edge_relations: dict[tuple[str, str], set[str]] = defaultdict(set)
    hidden_link_counts: Counter[str] = Counter()
    hidden_link_relations: dict[str, set[str]] = defaultdict(set)
    total_link_counts: Counter[str] = Counter()
    for link in links_raw:
        src_node = node_map.get(link["source"])
        tgt_node = node_map.get(link["target"])
        selected_src = selected_node_map.get(str(link.get("source")))
        selected_tgt = selected_node_map.get(str(link.get("target")))
        if selected_src and selected_tgt:
            src_cluster_all = get_cluster(selected_src)
            tgt_cluster_all = get_cluster(selected_tgt)
            if (
                src_cluster_all
                and tgt_cluster_all
                and src_cluster_all != tgt_cluster_all
                and src_cluster_all in valid_ids
                and tgt_cluster_all in valid_ids
            ):
                total_link_counts[src_cluster_all] += 1
                total_link_counts[tgt_cluster_all] += 1
                if not (is_visible_signal_node(selected_src) and is_visible_signal_node(selected_tgt)):
                    rel = str(link.get("relation") or "")
                    for cluster in (src_cluster_all, tgt_cluster_all):
                        hidden_link_counts[cluster] += 1
                        if rel:
                            hidden_link_relations[cluster].add(rel)
        if not src_node or not tgt_node:
            continue
        src_cluster = get_cluster(src_node)
        tgt_cluster = get_cluster(tgt_node)
        if (
            src_cluster
            and tgt_cluster
            and src_cluster != tgt_cluster
            and src_cluster in valid_ids
            and tgt_cluster in valid_ids
        ):
            pair = tuple(sorted((src_cluster, tgt_cluster)))
            edge_weights[pair] += 1
            rel = link.get("relation", "")
            if rel:
                edge_relations[pair].add(rel)

    summary_edges: list[dict] = [
        {
            "source": src,
            "target": tgt,
            "weight": w,
            "relations": sorted(edge_relations[(src, tgt)])[:4],
        }
        for (src, tgt), w in edge_weights.most_common()
        if w >= min_weight
    ]
    connection_counts: Counter[str] = Counter()
    connection_weights: Counter[str] = Counter()
    connection_details: dict[str, list[dict]] = defaultdict(list)
    summary_labels = {str(node["id"]): str(node["label"]) for node in summary_nodes}
    for edge in summary_edges:
        source = str(edge["source"])
        target = str(edge["target"])
        weight = int(edge.get("weight") or 0)
        relations = list(edge.get("relations") or [])
        connection_counts[source] += 1
        connection_counts[target] += 1
        connection_weights[source] += weight
        connection_weights[target] += weight
        connection_details[source].append(
            {
                "id": target,
                "label": summary_labels.get(target, target),
                "weight": weight,
                "relations": relations,
            }
        )
        connection_details[target].append(
            {
                "id": source,
                "label": summary_labels.get(source, source),
                "weight": weight,
                "relations": relations,
            }
        )
    for node in summary_nodes:
        node_id = str(node["id"])
        overlay_terms = set(cluster_overlay_terms.get(node_id, set()))
        overlay_add_term(overlay_terms, node_id)
        overlay_add_term(overlay_terms, node.get("label"))
        overlay = decision_overlay_for_terms(overlay_terms, overlay_context)
        node["decision_overlay"] = overlay
        node["decision_classification"] = overlay.get("decision_classification", "")
        node["decision_count"] = overlay.get("decision_count", 0)
        node["recommendation_count"] = overlay.get("recommendation_count", 0)
        node["queued_action_count"] = overlay.get("queued_action_count", 0)
        node["connection_count"] = connection_counts[node_id]
        node["connection_weight"] = connection_weights[node_id]
        node["is_gap"] = len(summary_nodes) > 1 and connection_counts[node_id] == 0
        if node["is_gap"]:
            triage = _gap_triage(
                node=node,
                hidden_counts=hidden_counts,
                hidden_link_counts=hidden_link_counts,
                hidden_link_relations=hidden_link_relations,
                total_link_counts=total_link_counts,
            )
            node.update(triage)
            node["gap_reason"] = triage["gap_detail"]
        else:
            node["gap_reason"] = ""
            node["gap_type"] = ""
            node["gap_detail"] = ""
            node["gap_evidence"] = []
            node["gap_actions"] = []
        node["connections"] = sorted(
            connection_details[node_id],
            key=lambda item: (-int(item.get("weight") or 0), str(item.get("label") or "")),
        )[:6]

    result = {
        "level": "top" if project is None else "project",
        "project": project,
        "total_nodes": sum(s["total"] for s in cluster_stats.values()),
        "signal_counts": counts_by_signal,
        "importance_counts": counts_by_importance,
        "hidden_node_count": counts_by_signal.get("evidence", 0) + counts_by_signal.get("hidden", 0),
        "excluded_node_count": excluded_node_count,
        "workspace_scope": _workspace_scope_summary_metadata(signal_graph),
        "nodes": summary_nodes,
        "edges": summary_edges,
    }
    _summary_cache[cache_key] = result
    return result


@app.get("/graph/full")
def graph_full(
    include_low_signal: bool = False,
    knowledge_only: bool = False,
    max_nodes: int = 10000,
    force: bool = False,
) -> dict:
    """Return all raw nodes and links for full-graph rendering in the Map."""
    try:
        g = apply_signal_tiers_to_graph(_load_graph())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Graph not loaded: {exc}")
    except GraphValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid graph: {exc}") from exc

    def _container(node: dict) -> str:
        workspace_key = _node_workspace_key(node)
        _, module_label = _node_module_group(node, workspace_key)
        return module_label if module_label != "(root)" else "root"

    def _safe_relative_path(path: Path, root: Path) -> str:
        try:
            return str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            return ""

    def _source_roots() -> list[Path]:
        return _configured_source_roots()

    def _path_is_secret_like(source_file: str) -> bool:
        path = source_file.replace("\\", "/").lower()
        parts = [p for p in path.split("/") if p]
        return any(marker in parts or marker in path for marker in _SECRET_PATH_MARKERS)

    source_cache: dict[tuple[str, str], tuple[Path | None, Path | None, str]] = {}
    excerpt_cache: dict[tuple[str, str, str], dict] = {}

    def _resolve_source(source_file: str, source_root: str = "") -> tuple[Path | None, Path | None, str]:
        source_root_key = str(source_root or "").strip()
        cache_key = (source_root_key, source_file)
        if cache_key in source_cache:
            return source_cache[cache_key]
        if not source_file:
            result = (None, None, "")
            source_cache[cache_key] = result
            return result

        raw_path = Path(source_file).expanduser()
        roots: list[Path] = []
        if source_root_key:
            try:
                roots.append(Path(source_root_key).expanduser().resolve())
            except Exception:
                pass
        for root in _source_roots():
            if root not in roots:
                roots.append(root)
        for root in roots:
            try:
                root_resolved = root.resolve()
                candidate = raw_path.resolve() if raw_path.is_absolute() else (root_resolved / raw_path).resolve()
            except Exception:
                continue

            relative = _safe_relative_path(candidate, root_resolved)
            if not relative and candidate != root_resolved:
                continue
            if candidate.exists() and candidate.is_file():
                result = (candidate, root_resolved, relative)
                source_cache[cache_key] = result
                return result

        result = (None, None, "")
        source_cache[cache_key] = result
        return result

    def _line_from_location(source_location: str) -> int | None:
        match = re.search(r"L(\d+)", source_location or "")
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _read_node_excerpt(source_file: str, source_location: str, source_root: str = "", radius: int = 4) -> dict:
        cache_key = (str(source_root or "").strip(), source_file, source_location)
        if cache_key in excerpt_cache:
            return excerpt_cache[cache_key]

        result: dict
        if not source_file:
            result = {"start_line": None, "lines": [], "unavailable_reason": "No source file recorded."}
        elif _path_is_secret_like(source_file):
            result = {"start_line": None, "lines": [], "unavailable_reason": "Source excerpt hidden for secret-like path."}
        else:
            source_path, _, _ = _resolve_source(source_file, source_root)
            if source_path is None:
                result = {"start_line": None, "lines": [], "unavailable_reason": "Source file is outside the active roots or unavailable."}
            else:
                try:
                    lines = source_path.read_text(errors="replace").splitlines()
                except Exception:
                    result = {"start_line": None, "lines": [], "unavailable_reason": "Source file could not be read."}
                else:
                    if not lines:
                        result = {"start_line": None, "lines": [], "unavailable_reason": "Source file is empty."}
                    else:
                        line_number = _line_from_location(source_location) or 1
                        index = max(0, min(len(lines) - 1, line_number - 1))
                        start = max(0, index - radius)
                        end = min(len(lines), index + radius + 1)
                        excerpt_lines = [line[:220] for line in lines[start:end]]
                        result = {
                            "start_line": start + 1,
                            "lines": excerpt_lines,
                            "unavailable_reason": "",
                        }
        excerpt_cache[cache_key] = result
        return result

    def _first_meaningful_excerpt_line(excerpt: dict) -> str:
        for raw in excerpt.get("lines", []):
            line = str(raw).strip()
            if not line or line in {"{", "}", ")", "];"}:
                continue
            return line[:160]
        return ""

    def _node_purpose(node: dict, excerpt: dict) -> str:
        label = node.get("label") or node.get("id", "This node")
        node_type = node.get("file_type", "code")
        source_file = node.get("source_file", "")
        metadata = node.get("metadata") or {}
        kind = str(metadata.get("kind", "")).replace("_", " ").strip()
        language = str(metadata.get("language", "")).strip()
        clue = _first_meaningful_excerpt_line(excerpt)

        if node_type == "document":
            base = f"{label} is a document node"
            if source_file:
                base += f" from {source_file}"
            if clue:
                base += f"; the nearby text starts with: {clue}"
            return base + "."

        if node_type == "rationale":
            base = f"{label} is a rationale or decision-context node"
            if source_file:
                base += f" from {source_file}"
            if clue:
                base += f"; the nearby evidence starts with: {clue}"
            return base + "."

        descriptor = kind or "code symbol"
        if language:
            descriptor = f"{language} {descriptor}"
        base = f"{label} appears to be a {descriptor}"
        if source_file:
            base += f" in {source_file}"
        if clue:
            base += f"; the source nearby starts with: {clue}"
        return base + "."

    all_nodes = [n for n in g.get("nodes", []) if isinstance(n, dict)]
    counts_by_signal = signal_counts(all_nodes)
    counts_by_importance = importance_counts(all_nodes)
    excluded_node_count = _workspace_scope_removed_node_count(g)
    effective_knowledge_only = bool(knowledge_only) and not include_low_signal
    baseline_visible_node_ids = {
        n["id"]
        for n in all_nodes
        if is_visible_signal_node(n, include_low_signal=include_low_signal)
    }
    visible_node_ids = {
        n["id"]
        for n in all_nodes
        if is_visible_signal_node(n, include_low_signal=include_low_signal)
        and (not effective_knowledge_only or is_visible_knowledge_node(n))
    }
    knowledge_hidden_node_count = len(baseline_visible_node_ids - visible_node_ids)
    effective_max_nodes = max(100, min(50000, int(max_nodes)))
    if len(visible_node_ids) > effective_max_nodes and not force:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "GRAPH_FULL_TOO_LARGE",
                "message": (
                    "Full evidence graph is too large for default browser rendering. "
                    "Use the overview/drilldown map or narrow the workspace scope."
                ),
                "visible_node_count": len(visible_node_ids),
                "max_nodes": effective_max_nodes,
                "total_node_count": len(all_nodes),
                "hidden_node_count": counts_by_signal.get("evidence", 0) + counts_by_signal.get("hidden", 0),
                "knowledge_hidden_node_count": knowledge_hidden_node_count,
            },
        )

    overlay_context = _map_decision_overlay_context()
    nodes = []
    for n in all_nodes:
        if n.get("id") not in visible_node_ids:
            continue
        source_file = n.get("source_file", "")
        source_location = n.get("source_location", "")
        node_source_root = str(n.get("source_root") or "").strip()
        _, source_root, relative_path = _resolve_source(source_file, node_source_root)
        excerpt = _read_node_excerpt(source_file, source_location, node_source_root)
        source_root_text = str(source_root) if source_root else node_source_root
        source_root_name = str(n.get("source_root_name") or "").strip()
        if not source_root_name and source_root_text:
            source_root_name = Path(source_root_text).name
        relative_source_path = relative_path or "/".join(_node_relative_source_parts(n)) or source_file
        node_payload = {
            "id": n["id"],
            "label": n.get("label", n["id"]),
            "type": n.get("file_type", "code"),
            "cluster": _node_cluster_id(n),
            "source_file": source_file,
            "source_location": source_location,
            "source_root": source_root_text,
            "source_root_name": source_root_name,
            "repo": _node_workspace_label(n),
            "container": _container(n),
            "relative_path": relative_source_path,
            "origin": n.get("_origin", ""),
            "metadata": n.get("metadata") or {},
            "symbol": n.get("label", n["id"]),
            "purpose": _node_purpose(n, excerpt),
            "source_excerpt": excerpt,
            "signal_tier": n.get("signal_tier", "evidence"),
            "signal_reason": n.get("signal_reason", "supporting evidence"),
            "importance_tier": n.get("importance_tier", "evidence"),
            "importance_reason": n.get("importance_reason", n.get("signal_reason", "supporting evidence")),
        }
        overlay_terms = overlay_terms_for_node(
            {**n, **node_payload},
            workspace_label=_node_workspace_label(n),
            cluster_id=_node_cluster_id(n),
        )
        node_overlay = decision_overlay_for_terms(overlay_terms, overlay_context)
        node_payload["decision_overlay"] = node_overlay
        node_payload["decision_classification"] = node_overlay.get("decision_classification", "")
        node_payload["decision_count"] = node_overlay.get("decision_count", 0)
        node_payload["recommendation_count"] = node_overlay.get("recommendation_count", 0)
        node_payload["queued_action_count"] = node_overlay.get("queued_action_count", 0)
        nodes.append(node_payload)

    seen: set[str] = set()
    edges = []
    for lnk in g.get("links", []):
        source = str(lnk.get("source", ""))
        target = str(lnk.get("target", ""))
        if source not in visible_node_ids or target not in visible_node_ids:
            continue
        key = f"{source}::{target}"
        if key in seen:
            continue
        seen.add(key)
        edges.append({
            "source": source,
            "target": target,
            "relation": lnk.get("relation", ""),
            "weight": float(lnk.get("weight", 1.0)),
        })

    low_signal_hidden = counts_by_signal.get("evidence", 0) + counts_by_signal.get("hidden", 0)
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "total_node_count": len(all_nodes),
        "visible_node_count": len(nodes),
        "hidden_node_count": 0 if include_low_signal else low_signal_hidden,
        "excluded_node_count": excluded_node_count,
        "signal_counts": counts_by_signal,
        "importance_counts": counts_by_importance,
        "include_low_signal": include_low_signal,
        "knowledge_only": effective_knowledge_only,
        "knowledge_hidden_node_count": knowledge_hidden_node_count,
        "nodes": nodes,
        "edges": edges,
    }


# ---------------------------------------------------------------------------
# Decision ledger
# ---------------------------------------------------------------------------

def _decision_deps() -> DecisionDeps:
    return DecisionDeps(
        supabase_client=lambda: _supabase_client,
        decisions_file=lambda: DECISIONS_FILE,
        write_json_atomic=write_json_atomic,
    )


def _load_decisions() -> list[dict]:
    return _route_load_decisions(_decision_deps())


def _save_decisions(decisions: list[dict]) -> None:
    _route_save_decisions(decisions, _decision_deps())


def _upsert_decision(record: dict) -> None:
    """Persist a single decision record to the active backend."""
    _route_upsert_decision(record, _decision_deps())


def list_decisions(request: Request):
    return list_decisions_response(
        request,
        load_records=_load_decisions,
        etag=_etag,
        track_device=_track_device,
    )

def create_decision(req: CreateDecisionRequest, request: Request) -> dict:
    return create_decision_record(req, request, upsert_record=_upsert_decision)

def patch_decision(decision_id: str, req: PatchDecisionRequest) -> dict:
    return patch_decision_record(
        decision_id,
        req,
        load_records=_load_decisions,
        upsert_record=_upsert_decision,
    )


app.include_router(create_decisions_router(
    load_records=_load_decisions,
    upsert_record=_upsert_decision,
    etag=_etag,
    track_device=_track_device,
))


# ---------------------------------------------------------------------------
# Recommendation queue
# ---------------------------------------------------------------------------

RECOMMENDATIONS_DIR = WORKSPACE_STATE / "recommendations"
ACTION_QUEUE_DIR     = WORKSPACE_STATE / "action-queue"
NOTES_DIR            = WORKSPACE_STATE / "notes"
RECOMMEND_MODEL_DEFAULT = "phi4:latest"

MODE_PROMPT_FILES: dict[str, str] = {
    "next-build": "recommend_ranked.txt",
    "archive-candidates": "recommend_archive.txt",
    "duplicates": "recommend_duplicates.txt",
}

RecommendationStatus = Literal["pending", "accepted", "rejected", "deferred"]


class GenerateRecommendationRequest(BaseModel):
    mode: Literal["next-build", "archive-candidates", "duplicates"]
    model: Optional[str] = None


class PatchRecommendationRequest(BaseModel):
    status: Optional[RecommendationStatus] = None


def _load_recommendations() -> list[dict]:
    if _supabase_client:
        resp = _supabase_client.table("recommendations").select("*").order("created_at", desc=True).execute()
        return resp.data or []
    if not RECOMMENDATIONS_DIR.exists():
        return []
    recs: list[dict] = []
    for f in RECOMMENDATIONS_DIR.glob("*.json"):
        try:
            recs.append(json.loads(f.read_text()))
        except Exception:
            pass
    return sorted(recs, key=lambda r: r.get("created_at", ""), reverse=True)


def _save_recommendation(rec: dict) -> None:
    if _supabase_client:
        _supabase_client.table("recommendations").upsert(rec).execute()
        return
    write_json_atomic(RECOMMENDATIONS_DIR / f"{rec['id']}.json", rec)


def _load_recommendation(rec_id: str) -> dict | None:
    if _supabase_client:
        resp = _supabase_client.table("recommendations").select("*").eq("id", rec_id).execute()
        return resp.data[0] if resp.data else None
    path = RECOMMENDATIONS_DIR / f"{rec_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


def _recommendation_evidence_terms(rec: dict) -> list[str]:
    raw_items: list[object] = []
    raw_items.extend(rec.get("evidence") if isinstance(rec.get("evidence"), list) else [])
    action_plan = rec.get("action_plan") if isinstance(rec.get("action_plan"), dict) else {}
    raw_items.extend(action_plan.get("source_pairs") if isinstance(action_plan.get("source_pairs"), list) else [])
    overlap = rec.get("overlap") if isinstance(rec.get("overlap"), dict) else {}
    overlap_pairs = overlap.get("top_pairs", []) if isinstance(overlap.get("top_pairs"), list) else []
    for pair in overlap_pairs:
        raw_items.extend([pair.get("label_a"), pair.get("label_b"), pair.get("source"), pair.get("target")])

    terms: list[str] = []
    seen: set[str] = set()
    for raw in raw_items:
        text = str(raw or "").strip()
        if not text:
            continue
        for chunk in re.split(r"↔|<->|->|—", text):
            term = re.sub(r"\s*\(\d+%?\)\s*$", "", chunk).strip(" `[]")
            if term and term not in seen:
                terms.append(term)
                seen.add(term)
    return terms[:20]


def _compact_packet_node(node: dict) -> dict:
    return {
        "id": node.get("id", ""),
        "label": node.get("label", ""),
        "type": node.get("type", ""),
        "cluster": node.get("cluster", ""),
        "repo": node.get("repo", ""),
        "container": node.get("container", ""),
        "relative_path": node.get("relative_path", ""),
        "source_file": node.get("source_file", ""),
        "source_location": node.get("source_location", ""),
        "symbol": node.get("symbol", ""),
        "purpose": node.get("purpose", ""),
    }


def _packet_evidence_nodes(rec: dict) -> list[dict]:
    terms = _recommendation_evidence_terms(rec)
    if not terms:
        return []
    try:
        graph = graph_full()
    except Exception:
        return []

    nodes = graph.get("nodes", [])
    by_id = {str(n.get("id", "")): n for n in nodes}
    by_label = {str(n.get("label", "")): n for n in nodes}
    picked: list[dict] = []
    seen: set[str] = set()
    for term in terms:
        node = by_id.get(term) or by_label.get(term)
        if not node:
            continue
        node_id = str(node.get("id", ""))
        if node_id in seen:
            continue
        picked.append(_compact_packet_node(node))
        seen.add(node_id)
        if len(picked) >= 8:
            break
    return picked


def _related_packet_decisions(rec: dict, evidence_nodes: list[dict]) -> list[dict]:
    decisions = [d for d in _load_decisions() if d.get("status") == "active"]
    if not decisions:
        return []
    search_parts = [
        rec.get("title", ""),
        rec.get("summary", ""),
        rec.get("proposed_action", ""),
        rec.get("mode", ""),
    ]
    search_parts.extend(_recommendation_evidence_terms(rec))
    for node in evidence_nodes:
        search_parts.extend([node.get("id", ""), node.get("label", ""), node.get("cluster", ""), node.get("container", "")])
    haystack = " ".join(str(part).lower() for part in search_parts if part)

    related: list[dict] = []
    for decision in decisions:
        target = str(decision.get("target_id", "")).lower()
        label = str(decision.get("label", "")).lower()
        if target and (target in haystack or any(target == str(n.get("cluster", "")).lower() for n in evidence_nodes)):
            related.append(decision)
        elif label and label in haystack:
            related.append(decision)
    return related[:6]


def _packet_markdown(packet: dict) -> str:
    rec = packet["recommendation"]
    lines = [
        f"# Decision Packet: {rec.get('title', 'Recommendation')}",
        "",
        "## Evidence",
        "",
        rec.get("summary", ""),
        "",
    ]
    for node in packet["evidence"].get("nodes", []):
        path = node.get("relative_path") or node.get("source_file") or "unknown path"
        lines.append(f"- {node.get('label') or node.get('id')}: {node.get('repo') or 'unknown repo'} / {path}")
    dossier = packet["evidence"].get("overlap_dossier")
    if isinstance(dossier, dict) and dossier.get("evidence_summary"):
        lines += ["", "## Overlap Dossier", "", str(dossier["evidence_summary"])]
    lines += [
        "",
        "## Judgement",
        "",
        f"- Status: {packet['judgement'].get('recommendation_status')}",
        f"- Confidence: {packet['judgement'].get('confidence')}",
        f"- Risk: {packet['judgement'].get('risk')}",
        f"- Effort: {packet['judgement'].get('effort')}",
        "",
        "## Recommendation",
        "",
        rec.get("proposed_action", ""),
    ]
    plan = packet.get("recommendation_plan")
    if isinstance(plan, dict):
        lines += ["", f"Canonical target: {plan.get('canonical_target', 'not specified')}"]
        for step in plan.get("concrete_steps", []) if isinstance(plan.get("concrete_steps"), list) else []:
            lines.append(f"- {step}")
    lines += ["", "## Approval Gate", ""]
    for choice in packet.get("operator_choices", []):
        lines.append(f"- {choice}")
    return "\n".join(lines).strip() + "\n"


@app.get("/decision-packets/recommendations/{rec_id}")
def get_recommendation_decision_packet(rec_id: str) -> dict:
    rec = _load_recommendation(rec_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")
    rec = _annotate_recommendation_scope(rec)

    actions = [
        action for action in _load_all_actions()
        if action.get("source_recommendation_id") == rec_id
    ]
    evidence_nodes = _packet_evidence_nodes(rec)
    related_decisions = _related_packet_decisions(rec, evidence_nodes)
    rec_status = rec.get("status", "pending")
    queued_status = actions[0].get("status") if actions else None
    next_gate = (
        "Action has executed; review the result and rollback note in Work Queue."
        if queued_status == "executed"
        else "Action failed; review the failure and recovery note in Work Queue."
        if queued_status == "failed"
        else
        "Review dry-run output in Work Queue before approving execution."
        if queued_status == "dry-run-ready"
        else "Run dry-run in Work Queue before approving execution."
        if queued_status == "pending"
        else "Accept this recommendation before queueing an action."
        if rec_status != "accepted"
        else "Queue an action, then use Work Queue dry-run before execution."
    )

    packet = {
        "schema_version": "1.0",
        "packet_type": "recommendation-decision",
        "id": f"packet-{rec_id}",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "recommendation": rec,
        "evidence": {
            "nodes": evidence_nodes,
            "overlap": rec.get("overlap") if isinstance(rec.get("overlap"), dict) else None,
            "overlap_dossier": rec.get("overlap_dossier") if isinstance(rec.get("overlap_dossier"), dict) else None,
        },
        "judgement": {
            "recommendation_status": rec_status,
            "confidence": rec.get("confidence", 0.0),
            "risk": rec.get("risk", "unknown"),
            "effort": rec.get("effort", "unknown"),
            "model": rec.get("model", ""),
        },
        "recommendation_plan": rec.get("action_plan") if isinstance(rec.get("action_plan"), dict) else None,
        "decisions": {
            "related": related_decisions,
            "count": len(related_decisions),
        },
        "approval": {
            "queued_actions": actions,
            "queued_action_count": len(actions),
            "next_gate": next_gate,
            "execution_locked_to_work_queue": True,
        },
        "operator_choices": [
            "Record or update the decision rationale in the Decisions tab.",
            "Accept, defer, or reject the recommendation in this card.",
            "Queue accepted recommendations from this card.",
            "Run dry-run and approve execution only in Work Queue.",
        ],
    }
    packet["markdown"] = _packet_markdown(packet)
    return packet


def _safe_load_workspace_scope_profile() -> dict | None:
    try:
        return load_workspace_scope_profile(WORKSPACE_SCOPE_FILE)
    except Exception:
        return None


def _build_scope_context(summary: dict) -> dict:
    nodes = summary.get("nodes", []) if isinstance(summary.get("nodes"), list) else []
    signal = summary.get("signal_counts", {}) if isinstance(summary.get("signal_counts"), dict) else {}
    profile = _safe_load_workspace_scope_profile()
    included = [
        {
            "id": str(node.get("id", "")),
            "label": str(node.get("label") or node.get("id") or ""),
            "group_type": str(node.get("group_type") or "group"),
            "node_count": int(node.get("node_count") or 0),
        }
        for node in nodes[:12]
    ]
    excluded_paths: list[str] = []
    exclude_patterns: list[str] = []
    if profile:
        root = Path(str(profile.get("root") or ""))
        for raw_path in profile.get("excluded_paths", [])[:8]:
            path = Path(str(raw_path))
            try:
                excluded_paths.append(path.relative_to(root).as_posix())
            except Exception:
                excluded_paths.append(path.name or str(path))
        exclude_patterns = [
            str(pattern)
            for pattern in profile.get("exclude_patterns", [])
            if isinstance(pattern, str)
        ][:12]

    hidden_count = int(summary.get("hidden_node_count") or 0)
    scoped_excluded_count = int(summary.get("excluded_node_count") or 0)
    visible_nodes = int(summary.get("total_nodes") or 0)
    raw_estimate = visible_nodes + hidden_count + scoped_excluded_count
    estimated_hidden_tokens = max(0, (hidden_count + scoped_excluded_count) * 80)

    context = {
        "scope_name": str(profile.get("profile_name")) if profile else "Active Graph",
        "root": str(profile.get("root")) if profile else "",
        "included_context": included,
        "major_exclusions": {
            "excluded_paths": excluded_paths,
            "default_patterns": exclude_patterns,
            "hidden_low_signal_nodes": hidden_count,
            "scoped_excluded_nodes": scoped_excluded_count,
            "signal_counts": signal,
        },
        "token_savings": {
            "visible_nodes": visible_nodes,
            "estimated_raw_nodes": raw_estimate,
            "estimated_hidden_tokens_per_query": estimated_hidden_tokens,
            "basis": "Hidden low-signal and scoped-excluded graph nodes are kept out of default insight prompts.",
        },
    }
    return _attach_map_context(context, summary=summary)


def _active_map_identity(graph: dict | None = None, summary: dict | None = None) -> dict:
    graph = graph or _load_graph()
    graph_path = _graph_path()
    summary_node_count = None
    if isinstance(summary, dict) and summary.get("total_nodes") is not None:
        try:
            summary_node_count = int(summary.get("total_nodes") or 0)
        except Exception:
            summary_node_count = None
    return {
        "kind": "map",
        "graph_fingerprint": _graph_fingerprint(graph),
        "graph_path": graph_path,
        "graph_name": Path(graph_path).name,
        "graph_node_count": len(graph.get("nodes", [])),
        "summary_node_count": summary_node_count,
    }


def _attach_map_context(context: dict, summary: dict | None = None, graph: dict | None = None) -> dict:
    scoped = dict(context)
    try:
        scoped["map"] = _active_map_identity(graph=graph, summary=summary)
    except Exception:
        scoped["map"] = {"kind": "system", "graph_fingerprint": None}
    return scoped


def _recommendation_scope(rec: dict, current_map: dict | None = None) -> dict:
    context = rec.get("context") if isinstance(rec.get("context"), dict) else {}
    map_context = context.get("map") if isinstance(context.get("map"), dict) else {}
    stored_fingerprint = str(map_context.get("graph_fingerprint") or "")
    if not stored_fingerprint:
        return {
            "kind": "system",
            "label": "System recommendation",
            "matches_current_map": False,
            "graph_name": None,
        }

    current_map = current_map or {}
    current_fingerprint = str(current_map.get("graph_fingerprint") or "")
    graph_name = str(map_context.get("graph_name") or "Saved map")
    matches = bool(current_fingerprint and stored_fingerprint == current_fingerprint)
    return {
        "kind": "current_map" if matches else "other_map",
        "label": "Current map" if matches else f"Other map: {graph_name}",
        "matches_current_map": matches,
        "graph_name": graph_name,
        "graph_node_count": map_context.get("graph_node_count"),
    }


def _annotate_recommendation_scope(rec: dict, current_map: dict | None = None) -> dict:
    return {
        **rec,
        "scope": _recommendation_scope(rec, current_map=current_map),
    }


def _current_map_recommendations(recommendations: list[dict]) -> list[dict]:
    try:
        current_map = _active_map_identity()
    except Exception:
        return []
    return [
        rec
        for rec in recommendations
        if _recommendation_scope(rec, current_map=current_map).get("kind") == "current_map"
    ]


def _build_graph_context(summary: dict) -> str:
    nodes = summary.get("nodes", [])
    edges = summary.get("edges", [])
    scope_context = _build_scope_context(summary)
    major_exclusions = scope_context["major_exclusions"]
    token_savings = scope_context["token_savings"]
    lines = [
        f"Workspace scope: {scope_context['scope_name']}",
        f"Included context: {len(nodes)} project/module groups, {summary.get('total_nodes', '?')} visible signal nodes.",
        (
            "Major exclusions: "
            f"{major_exclusions['hidden_low_signal_nodes']} hidden low-signal nodes, "
            f"{major_exclusions['scoped_excluded_nodes']} scoped-out nodes."
        ),
        (
            "Token-saving frame: "
            f"roughly {token_savings['estimated_hidden_tokens_per_query']} tokens of low-signal context "
            "are excluded from default insight prompts."
        ),
        "",
        "Included project areas (largest first):",
    ]
    for n in nodes[:20]:
        lines.append(
            f"  - {n.get('label') or n['id']} ({n['id']}): "
            f"{n.get('node_count', 0)} nodes, "
            f"group={n.get('group_type', 'group')}, type={n.get('dominant_type', 'code')}"
        )
    excluded_paths = major_exclusions.get("excluded_paths", [])
    if excluded_paths:
        lines.append("")
        lines.append("Explicitly excluded paths:")
        for path in excluded_paths[:8]:
            lines.append(f"  - {path}")
    default_patterns = major_exclusions.get("default_patterns", [])
    if default_patterns:
        lines.append("")
        lines.append(f"Default noisy path filters include: {', '.join(default_patterns[:10])}")
    if edges:
        lines.append("")
        lines.append(f"Top connections ({min(len(edges), 10)} of {len(edges)}):")
        for e in edges[:10]:
            lines.append(f"  - {e['source']} <-> {e['target']} ({e.get('weight', 0)} links)")
    return "\n".join(lines)


def _build_decisions_context(decisions: list[dict]) -> str:
    active = [d for d in decisions if d.get("status") == "active"]
    if not active:
        return "No workspace decisions recorded yet."
    lines = ["Current decisions:"]
    for d in active:
        note = f" — {d['rationale']}" if d.get("rationale") else ""
        lines.append(f"  - {d['target_id']}: {d['classification']}{note}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
    return {}


def _call_ollama(prompt: str, model: str, timeout: int = 120) -> str:
    import urllib.request as _req
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }).encode("utf-8")
    _ollama_base = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    request = _req.Request(
        f"{_ollama_base}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _req.urlopen(request, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "")


@app.get("/recommendations")
def list_recommendations(request: Request):
    try:
        current_map = _active_map_identity()
    except Exception:
        current_map = None
    recs = [
        _annotate_recommendation_scope(rec, current_map=current_map)
        for rec in _load_recommendations()
    ]
    tag = _etag(recs)
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304)
    _track_device(getattr(request.state, "user_id", "local"))
    return JSONResponse(content=recs, headers={"ETag": tag})


@app.post("/recommendations/generate", status_code=201)
def generate_recommendation(req: GenerateRecommendationRequest, request: Request) -> dict:
    try:
        summary = graph_summary()
    except HTTPException:
        summary = {"nodes": [], "edges": [], "total_nodes": 0}
    decisions = _load_decisions()

    graph_ctx = _build_graph_context(summary)
    scope_context = _build_scope_context(summary)
    dec_ctx = _build_decisions_context(decisions)

    prompt_file = Path(__file__).parent / "prompts" / MODE_PROMPT_FILES[req.mode]
    if not prompt_file.exists():
        raise HTTPException(status_code=500, detail=f"Prompt template missing: {prompt_file.name}")

    template = prompt_file.read_text()
    prompt = template.replace("{graph_context}", graph_ctx).replace("{decisions_context}", dec_ctx)

    model = (req.model or RECOMMEND_MODEL_DEFAULT).strip()
    model_used = model
    parsed: dict = {}

    try:
        raw = _call_ollama(prompt, model)
        parsed = _extract_json(raw)
    except Exception:
        model_used = "graph-only"

    now = datetime.now(tz=timezone.utc).isoformat()
    rec: dict = {
        "id": str(uuid.uuid4()),
        "mode": req.mode,
        "title": parsed.get("title") or f"Recommendation: {req.mode}",
        "summary": parsed.get("summary") or "Ollama unavailable — graph context loaded but no synthesis available.",
        "evidence": parsed.get("evidence") if isinstance(parsed.get("evidence"), list) else [],
        "confidence": float(parsed.get("confidence") or 0.0),
        "risk": parsed.get("risk") or "unknown",
        "effort": parsed.get("effort") or "unknown",
        "proposed_action": parsed.get("proposed_action") or "",
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "model": model_used,
        "created_by": getattr(request.state, "user_id", "local"),
        "context": scope_context,
    }
    if isinstance(parsed.get("action_plan"), dict):
        rec["action_plan"] = parsed["action_plan"]
    _save_recommendation(rec)
    return _annotate_recommendation_scope(rec)


@app.patch("/recommendations/{rec_id}")
def patch_recommendation(rec_id: str, req: PatchRecommendationRequest) -> dict:
    rec = _load_recommendation(rec_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")
    now = datetime.now(tz=timezone.utc).isoformat()
    if req.status is not None:
        rec["status"] = req.status
    rec["updated_at"] = now
    _save_recommendation(rec)
    return _annotate_recommendation_scope(rec)


# ── Missions (Steady Work Mode — AG-003) ──────────────────────────────────

import threading as _threading  # noqa: E402

MISSIONS: dict[str, dict] = {}
_CANCEL_FLAGS: dict[str, _threading.Event] = {}
_MISSIONS_LOCK = _threading.Lock()

MISSION_PROMPT_MAP: dict[str, str] = {
    "archive-candidates": "recommend_archive.txt",
    "rank-builds":        "steady_rank_builds.txt",
    "weak-coverage":      "steady_weak_coverage.txt",
    "duplicates":         "recommend_duplicates.txt",
}

MISSION_MODE_MAP: dict[str, str] = {
    "archive-candidates": "archive-candidates",
    "rank-builds":        "next-build",
    "weak-coverage":      "next-build",
    "duplicates":         "duplicates",
}


def _mission_log(mission_id: str, msg: str) -> None:
    with _MISSIONS_LOCK:
        MISSIONS[mission_id]["log"].append(msg)


def _run_mission(mission_id: str, mission_type: str) -> None:
    cancel = _CANCEL_FLAGS[mission_id]

    def log(msg: str) -> None:
        _mission_log(mission_id, msg)

    def finish(status: str) -> None:
        with _MISSIONS_LOCK:
            MISSIONS[mission_id]["status"]      = status
            MISSIONS[mission_id]["finished_at"] = datetime.now(tz=timezone.utc).isoformat()

    try:
        log(f"Started mission: {mission_type}")

        if cancel.is_set():
            finish("cancelled")
            log("Cancelled before context load.")
            return

        log("Loading graph context…")
        try:
            summary = graph_summary()
        except HTTPException:
            summary = {"nodes": [], "edges": [], "total_nodes": 0}

        decisions = _load_decisions()
        graph_ctx = _build_graph_context(summary)
        scope_context = _build_scope_context(summary)
        dec_ctx   = _build_decisions_context(decisions)
        log(f"Context loaded: {summary.get('total_nodes', 0)} nodes, {len(decisions)} decisions.")

        if cancel.is_set():
            finish("cancelled")
            log("Cancelled before Ollama call.")
            return

        prompt_file = Path(__file__).parent / "prompts" / MISSION_PROMPT_MAP[mission_type]
        if not prompt_file.exists():
            finish("failed")
            log(f"Prompt template missing: {prompt_file.name}")
            return

        template = prompt_file.read_text()
        prompt   = template.replace("{graph_context}", graph_ctx).replace("{decisions_context}", dec_ctx)

        log(f"Calling Ollama ({RECOMMEND_MODEL_DEFAULT})…")
        model_used = RECOMMEND_MODEL_DEFAULT
        parsed: dict = {}
        try:
            raw    = _call_ollama(prompt, RECOMMEND_MODEL_DEFAULT, timeout=60)
            parsed = _extract_json(raw)
            log("Ollama returned structured output.")
        except Exception as exc:
            model_used = "graph-only"
            log(f"Ollama unavailable ({type(exc).__name__}); using graph-only card.")

        if cancel.is_set():
            finish("cancelled")
            log("Cancelled after Ollama call (card not saved).")
            return

        mode = MISSION_MODE_MAP.get(mission_type, "next-build")
        now  = datetime.now(tz=timezone.utc).isoformat()
        rec: dict = {
            "id":              str(uuid.uuid4()),
            "mode":            mode,
            "title":           parsed.get("title") or f"Mission: {mission_type}",
            "summary":         parsed.get("summary") or "Analysis complete; Ollama synthesis unavailable.",
            "evidence":        parsed.get("evidence") if isinstance(parsed.get("evidence"), list) else [],
            "confidence":      float(parsed.get("confidence") or 0.0),
            "risk":            parsed.get("risk") or "unknown",
            "effort":          parsed.get("effort") or "unknown",
            "proposed_action": parsed.get("proposed_action") or "",
            "status":          "pending",
            "created_at":      now,
            "updated_at":      now,
            "model":           model_used,
            "created_by":      "mission-agent",
            "context":         scope_context,
        }
        _save_recommendation(rec)

        with _MISSIONS_LOCK:
            MISSIONS[mission_id]["cards_generated"] += 1

        log(f"Card saved: {rec['title']}")
        finish("completed")

    except Exception as exc:
        with _MISSIONS_LOCK:
            MISSIONS[mission_id]["log"].append(f"Unexpected error: {exc}")
            MISSIONS[mission_id]["status"]      = "failed"
            MISSIONS[mission_id]["finished_at"] = datetime.now(tz=timezone.utc).isoformat()


MissionType = Literal["archive-candidates", "rank-builds", "weak-coverage", "duplicates"]


class StartMissionRequest(BaseModel):
    type: MissionType


@app.get("/missions")
def list_missions() -> list[dict]:
    with _MISSIONS_LOCK:
        return sorted(
            [{**m} for m in MISSIONS.values()],
            key=lambda m: m["started_at"],
            reverse=True,
        )


@app.post("/missions", status_code=201)
def start_mission(req: StartMissionRequest) -> dict:
    mission_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc).isoformat()
    mission: dict = {
        "id":              mission_id,
        "type":            req.type,
        "status":          "running",
        "log":             [],
        "cards_generated": 0,
        "started_at":      now,
        "finished_at":     None,
    }
    cancel = _threading.Event()
    with _MISSIONS_LOCK:
        MISSIONS[mission_id]      = mission
        _CANCEL_FLAGS[mission_id] = cancel
    thread = _threading.Thread(
        target=_run_mission, args=(mission_id, req.type), daemon=True
    )
    thread.start()
    with _MISSIONS_LOCK:
        return {**MISSIONS[mission_id]}


@app.get("/missions/{mission_id}")
def get_mission(mission_id: str) -> dict:
    with _MISSIONS_LOCK:
        if mission_id not in MISSIONS:
            raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found.")
        return {**MISSIONS[mission_id]}


@app.post("/missions/{mission_id}/cancel")
def cancel_mission(mission_id: str) -> dict:
    with _MISSIONS_LOCK:
        if mission_id not in MISSIONS:
            raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found.")
        cancel = _CANCEL_FLAGS.get(mission_id)
        if cancel is not None:
            cancel.set()
        if MISSIONS[mission_id]["status"] == "running":
            MISSIONS[mission_id]["status"]      = "cancelled"
            MISSIONS[mission_id]["finished_at"] = datetime.now(tz=timezone.utc).isoformat()
            MISSIONS[mission_id]["log"].append("Cancellation requested.")
        return {**MISSIONS[mission_id]}


# ── Action Queue (Approved Actions — AG-004) ──────────────────────────────


def _save_action(action: dict) -> None:
    if _supabase_client:
        _supabase_client.table("actions").upsert(action).execute()
        return
    write_json_atomic(ACTION_QUEUE_DIR / f"{action['id']}.json", action)


def _load_action(action_id: str) -> dict | None:
    if _supabase_client:
        resp = _supabase_client.table("actions").select("*").eq("id", action_id).execute()
        return resp.data[0] if resp.data else None
    path = ACTION_QUEUE_DIR / f"{action_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _load_all_actions(status_filter: str | None = None) -> list[dict]:
    if _supabase_client:
        query = _supabase_client.table("actions").select("*").order("created_at", desc=True)
        if status_filter:
            query = query.eq("status", status_filter)
        resp = query.execute()
        return resp.data or []
    if not ACTION_QUEUE_DIR.exists():
        return []
    actions = []
    for p in sorted(ACTION_QUEUE_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            actions.append(json.loads(p.read_text()))
        except Exception:
            pass
    if status_filter:
        actions = [a for a in actions if a.get("status") == status_filter]
    return actions


def _build_note_content(action: dict) -> str:
    action_plan = action.get("action_plan") if isinstance(action.get("action_plan"), dict) else None
    lines = [
        f"# {action['rec_title']}",
        "",
        f"> Generated by Graphify Workspace Cockpit — {action['created_at'][:10]}",
        "",
        "## Summary",
        "",
        action.get("rec_summary", ""),
        "",
        "## Proposed Action",
        "",
        action.get("proposed_action_text", ""),
        "",
    ]
    if action_plan:
        lines += ["## Action Plan", ""]
        if action_plan.get("canonical_target"):
            lines += ["### Where", "", str(action_plan["canonical_target"]), ""]
        merge_sources = action_plan.get("merge_sources") if isinstance(action_plan.get("merge_sources"), list) else []
        if merge_sources:
            lines += ["### Sources", ""]
            for source in merge_sources:
                lines.append(f"- {source}")
            lines.append("")
        concrete_steps = action_plan.get("concrete_steps") if isinstance(action_plan.get("concrete_steps"), list) else []
        if concrete_steps:
            lines += ["### How", ""]
            for step in concrete_steps:
                lines.append(f"- {step}")
            lines.append("")
        savings = action_plan.get("savings_estimate") if isinstance(action_plan.get("savings_estimate"), dict) else {}
        if savings:
            lines += ["### Savings Estimate", ""]
            for key in ("duplicate_node_count", "affected_files", "semantic_edge_reduction", "rough_context_savings", "caveat"):
                if savings.get(key) is not None:
                    lines.append(f"- {key.replace('_', ' ')}: {savings[key]}")
            lines.append("")
        risks = action_plan.get("risks") if isinstance(action_plan.get("risks"), list) else []
        if risks:
            lines += ["### Risks", ""]
            for risk in risks:
                lines.append(f"- {risk}")
            lines.append("")
        acceptance = action_plan.get("acceptance_criteria") if isinstance(action_plan.get("acceptance_criteria"), list) else []
        if acceptance:
            lines += ["### Done When", ""]
            for item in acceptance:
                lines.append(f"- {item}")
            lines.append("")
        questions = action_plan.get("open_questions") if isinstance(action_plan.get("open_questions"), list) else []
        if questions:
            lines += ["### Open Questions", ""]
            for question in questions:
                lines.append(f"- {question}")
            lines.append("")
        if action_plan.get("rollback_note"):
            lines += ["### Rollback", "", str(action_plan["rollback_note"]), ""]
    if action.get("evidence"):
        lines += ["## Evidence", ""]
        for ev in action["evidence"]:
            lines.append(f"- {ev}")
        lines.append("")
    lines += [
        "---",
        "",
        f"*Action type: `{action['action_type']}`*  ",
        f"*Source recommendation: `{action['source_recommendation_id']}`*",
    ]
    return "\n".join(lines)


def _build_action_from_rec(rec: dict, created_by: str = "local") -> dict:
    mode         = rec.get("mode", "")
    action_type  = "tag_for_archive" if mode == "archive-candidates" else "create_note"
    action_id    = str(uuid.uuid4())
    safe_title   = re.sub(r"[^a-zA-Z0-9_-]", "_", rec.get("title", "note")[:40]).strip("_") or "note"
    filename     = f"{safe_title}_{action_id[:8]}.md"
    target_path  = str(NOTES_DIR / filename)
    target_rel   = f"workspace/state/notes/{filename}"
    now          = datetime.now(tz=timezone.utc).isoformat()
    return {
        "id":                        action_id,
        "source_recommendation_id":  rec["id"],
        "action_type":               action_type,
        "description":               f"{action_type.replace('_', ' ').title()}: {rec.get('title', '')}",
        "target_path":               target_path,
        "dry_run_command":           f"mkdir -p workspace/state/notes && cat > {target_rel}",
        "proposed_action_text":      rec.get("proposed_action", "").strip() or rec.get("title", ""),
        "evidence":                  rec.get("evidence", []),
        "rec_title":                 rec.get("title", ""),
        "rec_summary":               rec.get("summary", ""),
        "action_plan":               rec.get("action_plan") if isinstance(rec.get("action_plan"), dict) else None,
        "confidence":                rec.get("confidence", 0.0),
        "risk":                      rec.get("risk", "unknown"),
        "dry_run_preview":           None,
        "dry_run_at":                None,
        "approval_required":         True,
        "approved_at":               None,
        "executed_at":               None,
        "result":                    None,
        "rollback_note":             f"To undo: delete {target_rel}",
        "status":                    "pending",
        "created_at":                now,
        "updated_at":                now,
        "created_by":                created_by,
    }


@app.post("/recommendations/{rec_id}/queue", status_code=201)
def queue_recommendation(rec_id: str, request: Request) -> dict:
    rec = _load_recommendation(rec_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")
    if rec.get("status") != "accepted":
        raise HTTPException(status_code=422, detail="Only accepted recommendations can be queued.")
    action = _build_action_from_rec(rec, created_by=getattr(request.state, "user_id", "local"))
    _save_action(action)
    return action


def _to_uaos_envelope(actions: list[dict]) -> dict:
    """Transform executed action records into the UAOS mission envelope format."""
    now = datetime.now(tz=timezone.utc).isoformat()
    items = []
    for a in actions:
        evidence = a.get("evidence", [])
        desc = a.get("description", "")
        items.append({
            "id": a["id"],
            "source_recommendation_id": a.get("source_recommendation_id"),
            "action_type": a.get("action_type"),
            "description": desc,
            "rec_title": a.get("rec_title", ""),
            "rec_summary": a.get("rec_summary", ""),
            "evidence": evidence,
            "confidence": a.get("confidence", 0.0),
            "risk": a.get("risk", "unknown"),
            "proposed_action_text": a.get("proposed_action_text", ""),
            "action_plan": a.get("action_plan") if isinstance(a.get("action_plan"), dict) else None,
            "result": a.get("result"),
            "rollback_note": a.get("rollback_note"),
            "approved_at": a.get("approved_at"),
            "executed_at": a.get("executed_at"),
            "created_by": a.get("created_by", "adam"),
            "uaos_mission_hint": {
                "proposed_mission_title": desc,
                "stop_triggers": [
                    "stop before deleting files",
                    "stop before external commits",
                    "stop before mutating source outside workspace/state/",
                ],
                "approval_level": "A2",
                "files_in_scope": [e for e in evidence if "/" in str(e)],
                "non_goals": ["destructive action", "external service calls"],
            },
        })
    return {
        "schema_version": "1.0",
        "exported_at": now,
        "actions": items,
    }


@app.get("/actions")
def list_actions(
    request: Request,
    status: str | None = Query(default=None),
    format: str | None = Query(default=None),
):
    actions = _load_all_actions(status_filter=status)
    if format == "uaos":
        executed = [a for a in actions if a.get("status") == "executed"]
        return _to_uaos_envelope(executed)
    tag = _etag(actions)
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304)
    _track_device(getattr(request.state, "user_id", "local"))
    return JSONResponse(content=actions, headers={"ETag": tag})


@app.get("/actions/{action_id}")
def get_action(action_id: str) -> dict:
    action = _load_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found.")
    return action


@app.post("/actions/{action_id}/dry-run")
def dry_run_action(action_id: str) -> dict:
    action = _load_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found.")
    if action["status"] == "executed":
        raise HTTPException(status_code=422, detail="Action already executed.")

    target       = Path(action["target_path"])
    file_exists  = target.exists()
    content      = _build_note_content(action)

    now = datetime.now(tz=timezone.utc).isoformat()
    action["dry_run_preview"] = {
        "target_path":    str(target),
        "file_exists":    file_exists,
        "would_create":   not file_exists,
        "preview_content": content,
        "summary": (
            f"Would create {target.name} in workspace/state/notes/"
            if not file_exists
            else f"WARNING: {target.name} already exists — would overwrite."
        ),
    }
    action["dry_run_at"] = now
    action["status"]     = "dry-run-ready"
    action["updated_at"] = now
    _save_action(action)
    return action


class ExecuteActionRequest(BaseModel):
    confirmed: bool


@app.post("/actions/{action_id}/execute")
def execute_action(action_id: str, req: ExecuteActionRequest) -> dict:
    action = _load_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found.")
    if action["status"] != "dry-run-ready":
        raise HTTPException(status_code=422, detail="Dry-run must be completed before execution.")
    if not req.confirmed:
        raise HTTPException(status_code=422, detail="confirmed must be true to execute.")

    now = datetime.now(tz=timezone.utc).isoformat()
    action["approved_at"] = now

    target  = Path(action["target_path"])
    preview = action.get("dry_run_preview") or {}
    content = preview.get("preview_content", _build_note_content(action))

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        action["result"] = {
            "success":      True,
            "file_created": str(target),
            "message":      f"Created {target.name}",
        }
        action["status"] = "executed"
    except Exception as exc:
        action["result"] = {
            "success": False,
            "message": str(exc),
        }
        action["status"] = "failed"

    action["executed_at"] = now
    action["updated_at"]  = now
    _save_action(action)
    return action


# ---------------------------------------------------------------------------
# Chunk Ten — Settings, Ollama status, graph upload
# ---------------------------------------------------------------------------

@app.get("/settings")
def get_settings() -> dict:
    graph_path = _graph_path()
    node_count = 0
    edge_count = 0
    try:
        data = _load_graph()
        node_count = len(data.get("nodes", []))
        edge_count = count_links(data)
    except Exception:
        pass
    return {
        "version": app.version,
        "graph_path": graph_path,
        "graph_name": Path(graph_path).name,
        "node_count": node_count,
        "edge_count": edge_count,
        "state_dir": str(WORKSPACE_STATE),
        "api_key_required": bool(API_KEY),
        "graphify": get_graphify_status(),
        "storage": _storage_status(),
    }


@app.get("/status/ollama")
def ollama_status() -> dict:
    import urllib.request as _req2
    _ollama_base = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    try:
        with _req2.urlopen(f"{_ollama_base}/api/tags", timeout=3) as r:
            data = json.load(r)
            models = [m["name"] for m in data.get("models", [])]
            return {"connected": True, "models": models, "url": _ollama_base}
    except Exception:
        return {"connected": False, "models": [], "url": _ollama_base}


@app.post("/graph/upload", status_code=201)
async def upload_graph(file: UploadFile = File(...)) -> dict:
    """Accept a graph.json file, validate it, store it, and activate it without restart."""
    global _graph_cache, _summary_cache
    name = _safe_graph_upload_name(file.filename)

    content = await file.read(GRAPH_UPLOAD_MAX_BYTES + 1)
    if len(content) > GRAPH_UPLOAD_MAX_BYTES:
        limit_mib = GRAPH_UPLOAD_MAX_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Graph upload exceeds the {limit_mib} MiB limit.",
        )

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}") from exc
    try:
        normalized = normalize_graph(data, require_link_targets=True)
    except GraphValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid graph: {exc}") from exc

    graphs_root = GRAPHS_DIR.resolve()
    dest = (GRAPHS_DIR / name).resolve()
    try:
        dest.relative_to(graphs_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Graph filename is not safe.") from exc

    write_json_atomic(dest, normalized)
    _activate_rebuild_graph(dest)
    _graph_cache = None
    _summary_cache = {}
    return {
        "filename": name,
        "node_count": len(normalized["nodes"]),
        "link_count": len(normalized["links"]),
        "path": str(dest),
        "active": True,
    }


# ---------------------------------------------------------------------------
# Chunk Eleven — graph management, org settings
# ---------------------------------------------------------------------------

@app.get("/graphs")
def list_graphs() -> list[dict]:
    """Return all available graphs with their activation status."""
    active = _graph_path()
    graphs: list[dict] = []

    # Demo graph (always listed if it exists)
    demo = Path(_DEMO_GRAPH)
    if demo.exists():
        graphs.append({
            "name": demo.name,
            "path": str(demo),
            "active": str(demo) == active,
            "source": "demo",
            "uploaded_at": None,
        })

    # Uploaded graphs in GRAPHS_DIR
    if GRAPHS_DIR.exists():
        for p in sorted(GRAPHS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            graphs.append({
                "name": p.name,
                "path": str(p),
                "active": str(p) == active,
                "source": "uploaded",
                "uploaded_at": datetime.fromtimestamp(
                    p.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            })

    # Custom GRAPH_PATH env var not covered above
    active_path = Path(active)
    if not any(g["path"] == active for g in graphs) and active_path.exists():
        graphs.insert(0, {
            "name": active_path.name,
            "path": active,
            "active": True,
            "source": "configured",
            "uploaded_at": None,
        })

    return graphs


def _graph_activation_candidate(name: str) -> Path:
    if not name or name in {".", ".."} or Path(name).name != name or "\\" in name:
        raise HTTPException(
            status_code=400,
            detail="Graph name must match a file name from the graph list.",
        )

    candidate = GRAPHS_DIR / name
    if candidate.is_file():
        return candidate

    demo = Path(_DEMO_GRAPH)
    if demo.name == name and demo.is_file():
        return demo

    raise HTTPException(status_code=404, detail=f"Graph '{name}' not found.")


@app.post("/graphs/{name}/activate")
def activate_graph(name: str) -> dict:
    """Switch the active graph by name. Must exist in GRAPHS_DIR or be the demo graph."""
    global _graph_cache, _summary_cache
    candidate = _graph_activation_candidate(name)
    try:
        normalize_graph(json.loads(candidate.read_text()), require_link_targets=True)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}") from exc
    except GraphValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid graph: {exc}") from exc
    _activate_rebuild_graph(candidate)
    _graph_cache = None
    _summary_cache = {}
    return {"activated": name, "path": str(candidate)}


@app.get("/settings/org")
def get_org_settings() -> dict:
    """Organisation-level view: active graph, Ollama, storage backend, last-seen devices."""
    graph_path = _graph_path()
    devices: dict = {}
    if DEVICES_FILE.exists():
        try:
            devices = json.loads(DEVICES_FILE.read_text())
        except Exception:
            pass
    return {
        "active_graph": {
            "name": Path(graph_path).name,
            "path": graph_path,
        },
        "ollama_url": os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        "storage_backend": STORAGE_BACKEND,
        "storage": _storage_status(),
        "last_seen_devices": [
            {"user": user, "last_seen": ts}
            for user, ts in sorted(devices.items(), key=lambda x: x[1], reverse=True)
        ],
        "graph_stats": _graph_stats(),
    }


def _graph_stats() -> dict:
    """Token savings estimate: (raw_node_count × avg_tokens_per_node) - graph_summary_size."""
    try:
        data = _load_graph()
        raw_node_count = len(data.get("nodes", []))
        avg_tokens_per_node = 80
        # Summary compresses the graph to ~20 cluster groups on average
        summary_token_cost = 20 * avg_tokens_per_node
        tokens_saved = max(0, raw_node_count * avg_tokens_per_node - summary_token_cost)
        return {
            "raw_node_count": raw_node_count,
            "avg_tokens_per_node": avg_tokens_per_node,
            "estimated_tokens_saved_per_query": tokens_saved,
        }
    except Exception:
        return {"raw_node_count": 0, "avg_tokens_per_node": 80, "estimated_tokens_saved_per_query": 0}


# ---------------------------------------------------------------------------
# Chunk Fifteen — Rebuild graph trigger
# ---------------------------------------------------------------------------

import threading as _rebuild_threading  # noqa: E402


def _set_rebuild_error(exc: GraphifyServiceError, ts: str | None = None) -> None:
    _REBUILD_STATUS.update({
        "status": "error",
        "last_run": ts or datetime.now(tz=timezone.utc).isoformat(),
        "error": exc.message,
        "code": exc.code,
        "detail": exc.to_detail(),
    })


def _load_workspace_scope_for_rebuild() -> dict | None:
    try:
        return load_workspace_scope_profile(WORKSPACE_SCOPE_FILE)
    except WorkspaceScopeError as exc:
        raise GraphifyServiceError(
            "WORKSPACE_SCOPE_INVALID",
            str(exc),
            status_code=422,
        ) from exc


def _dedupe_raw_graphify_node_ids(graph: dict) -> dict:
    """Repair duplicate semantic ids in raw Graphify output before strict activation."""
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        return graph

    used_ids: set[str] = set()
    seen_counts: Counter[str] = Counter()
    repaired_nodes: list[object] = []
    changed = False

    for raw_node in nodes:
        if not isinstance(raw_node, dict):
            repaired_nodes.append(raw_node)
            continue
        raw_id = raw_node.get("id")
        if not raw_id:
            repaired_nodes.append(raw_node)
            continue

        node_id = str(raw_id)
        seen_counts[node_id] += 1
        next_id = node_id
        if next_id in used_ids:
            changed = True
            index = seen_counts[node_id]
            next_id = f"{node_id}__duplicate_{index}"
            while next_id in used_ids:
                index += 1
                next_id = f"{node_id}__duplicate_{index}"
            node = dict(raw_node)
            node["id"] = next_id
            node.setdefault("original_graphify_id", node_id)
            repaired_nodes.append(node)
        else:
            repaired_nodes.append(raw_node)
        used_ids.add(next_id)

    if not changed:
        return graph
    repaired = dict(graph)
    repaired["nodes"] = repaired_nodes
    return repaired


def _filtered_scoped_graph_path(
    *,
    source_graph_path: Path,
    destination_path: Path,
    profile: dict,
    scan_root: Path,
) -> tuple[Path, dict]:
    raw_graph = _dedupe_raw_graphify_node_ids(json.loads(source_graph_path.read_text()))
    graph = normalize_graph(raw_graph)
    filtered_graph, stats = filter_workspace_scope_graph(graph, profile, scan_root)
    normalized = normalize_graph(filtered_graph, require_link_targets=True)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(destination_path, normalized)
    return destination_path, stats


def _write_scoped_graph_metadata(
    graph_path: Path,
    *,
    profile: dict,
    scanned_root_count: int,
    removed_node_count: int,
) -> None:
    graph = normalize_graph(json.loads(graph_path.read_text()), require_link_targets=True)
    meta = graph.get("_meta")
    if not isinstance(meta, dict):
        meta = {}
    meta["workspace_scope"] = {
        "profile_name": profile.get("profile_name") or "Workspace Scope",
        "root": profile["root"],
        "included_paths": list(profile.get("included_paths") or []),
        "excluded_paths": list(profile.get("excluded_paths") or []),
        "scanned_root_count": scanned_root_count,
        "removed_node_count": removed_node_count,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    graph["_meta"] = meta
    write_json_atomic(graph_path, graph)


def _merge_normalized_graphs(graph_paths: list[str]) -> dict:
    merged_nodes: list[dict] = []
    merged_links: list[dict] = []
    used_ids: set[str] = set()
    seen_counts: Counter[str] = Counter()

    for graph_path in graph_paths:
        graph = normalize_graph(json.loads(Path(graph_path).read_text()), require_link_targets=True)
        id_map: dict[str, str] = {}
        for raw_node in graph["nodes"]:
            node = dict(raw_node)
            node_id = str(node["id"])
            seen_counts[node_id] += 1
            next_id = node_id
            if next_id in used_ids:
                index = seen_counts[node_id]
                next_id = f"{node_id}__duplicate_{index}"
                while next_id in used_ids:
                    index += 1
                    next_id = f"{node_id}__duplicate_{index}"
                node["id"] = next_id
                node.setdefault("original_graphify_id", node_id)
            used_ids.add(next_id)
            id_map[node_id] = next_id
            merged_nodes.append(node)

        for raw_link in graph["links"]:
            link = dict(raw_link)
            source = id_map.get(str(link["source"]), str(link["source"]))
            target = id_map.get(str(link["target"]), str(link["target"]))
            link["source"] = source
            link["target"] = target
            merged_links.append(link)

    return normalize_graph({"nodes": merged_nodes, "links": merged_links}, require_link_targets=True)


def _merge_graph_outputs(graph_paths: list[str], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if len(graph_paths) == 1:
        import shutil
        shutil.copy(graph_paths[0], str(out_path))
        return
    write_json_atomic(out_path, _merge_normalized_graphs(graph_paths))


def _run_scoped_rebuild(profile: dict, repo_root: Path) -> None:
    scan_roots = workspace_scope_scan_roots(profile)
    if not scan_roots:
        raise GraphifyServiceError(
            "WORKSPACE_SCOPE_EMPTY",
            "Saved workspace scope has no included directories to scan.",
            status_code=422,
        )

    scoped_graph_dir = repo_root / "graphify-out" / "scoped"
    graph_paths: list[str] = []
    scan_errors: list[str] = []
    removed_node_count = 0
    for index, scan_root in enumerate(scan_roots, start=1):
        try:
            run_graphify_update(str(scan_root), cwd=scan_root, timeout=300)
            source_graph_path = scan_root / "graphify-out" / "graph.json"
            if not source_graph_path.exists():
                scan_errors.append(f"{scan_root.name}: no graph.json produced")
                continue
            filtered_path, stats = _filtered_scoped_graph_path(
                source_graph_path=source_graph_path,
                destination_path=scoped_graph_dir / f"{index:03d}-{scan_root.name}.json",
                profile=profile,
                scan_root=scan_root,
            )
            removed_node_count += int(stats["removed_node_count"])
            graph_paths.append(str(filtered_path))
        except GraphifyServiceError as exc:
            scan_errors.append(f"{scan_root.name}: {exc.code}: {exc.message}")
        except Exception as exc:
            scan_errors.append(f"{scan_root.name}: {exc}")

    if not graph_paths:
        reason = scan_errors[0] if scan_errors else "No graphs produced by saved workspace scope"
        raise GraphifyServiceError("WORKSPACE_SCOPE_REBUILD_EMPTY", reason, status_code=503)

    out_path = repo_root / "graphify-out" / "merged-graph.json"
    _merge_graph_outputs(graph_paths, out_path)
    _write_scoped_graph_metadata(
        out_path,
        profile=profile,
        scanned_root_count=len(graph_paths),
        removed_node_count=removed_node_count,
    )
    _activate_rebuild_graph(out_path)


def _run_rebuild() -> None:
    global _graph_cache, _summary_cache
    _REBUILD_STATUS.update({"status": "running", "error": None, "code": None, "detail": None})
    try:
        repo_root = _REPO_ROOT
        workspace_scope_profile = _load_workspace_scope_for_rebuild()
        scan_dirs = _load_scan_dirs()

        if workspace_scope_profile is not None:
            _run_scoped_rebuild(workspace_scope_profile, repo_root)
        elif not scan_dirs:
            # Default: scan just this repo
            result = run_graphify_update(".", cwd=repo_root, timeout=300)
            ts = datetime.now(tz=timezone.utc).isoformat()
            if result.returncode != 0:
                _REBUILD_STATUS.update({
                    "status": "error",
                    "last_run": ts,
                    "error": result.stderr[:500],
                    "code": None,
                    "detail": None,
                })
                return
        else:
            # Scan each configured directory, then merge all graphs
            graph_paths: list[str] = []
            scan_errors: list[str] = []
            for d in scan_dirs:
                try:
                    run_graphify_update(d, cwd=d, timeout=300)
                    candidate = Path(d) / "graphify-out" / "graph.json"
                    if candidate.exists():
                        graph_paths.append(str(candidate))
                except GraphifyServiceError as exc:
                    scan_errors.append(f"{Path(d).name}: {exc.code}: {exc.message}")
            ts = datetime.now(tz=timezone.utc).isoformat()
            if not graph_paths:
                reason = scan_errors[0] if scan_errors else "No graphs produced by configured scan directories"
                _REBUILD_STATUS.update({
                    "status": "error",
                    "last_run": ts,
                    "error": reason,
                    "code": None,
                    "detail": None,
                })
                return
            out_path = repo_root / "graphify-out" / "merged-graph.json"
            try:
                _merge_graph_outputs(graph_paths, out_path)
            except GraphifyServiceError as exc:
                _REBUILD_STATUS.update({
                    "status": "error",
                    "last_run": ts,
                    "error": exc.message,
                    "code": exc.code,
                    "detail": exc.to_detail(),
                })
                return
            # Activate the merged graph
            _activate_rebuild_graph(out_path)

        _graph_cache = None
        _summary_cache = {}
        _REBUILD_STATUS.update({
            "status": "complete",
            "last_run": datetime.now(tz=timezone.utc).isoformat(),
            "error": None,
            "code": None,
            "detail": None,
        })
    except GraphifyServiceError as exc:
        _set_rebuild_error(exc)
    except Exception as exc:
        ts = datetime.now(tz=timezone.utc).isoformat()
        _REBUILD_STATUS.update({
            "status": "error",
            "last_run": ts,
            "error": str(exc),
            "code": None,
            "detail": None,
        })


@app.post("/graph/rebuild", status_code=202)
def trigger_rebuild() -> dict:
    """Trigger a background graphify update rebuild. Returns 202 immediately."""
    if _REBUILD_STATUS.get("status") == "running":
        raise HTTPException(status_code=409, detail="Rebuild already in progress.")
    graphify_status = get_graphify_status(include_version=False)
    if not graphify_status["available"]:
        raise HTTPException(
            status_code=503,
            detail={
                "code": graphify_status.get("code") or GRAPHIFY_MISSING,
                "message": graphify_status.get("message") or "Graphify CLI is not available.",
            },
        )
    t = _rebuild_threading.Thread(target=_run_rebuild, daemon=True)
    t.start()
    return {"status": "running"}


@app.get("/graph/rebuild/status")
def rebuild_status() -> dict:
    """Return current rebuild status and last run timestamp."""
    return {
        "status": _REBUILD_STATUS.get("status", "idle"),
        "last_run": _REBUILD_STATUS.get("last_run"),
        "error": _REBUILD_STATUS.get("error"),
        "code": _REBUILD_STATUS.get("code"),
        "detail": _REBUILD_STATUS.get("detail"),
    }


def _load_scan_dirs() -> list[str]:
    if SCAN_DIRS_FILE.exists():
        try:
            return json.loads(SCAN_DIRS_FILE.read_text())
        except Exception:
            pass
    return []


def _save_scan_dirs(dirs: list[str]) -> None:
    write_json_atomic(SCAN_DIRS_FILE, dirs)


@app.get("/graph/scan-dirs")
def get_scan_dirs() -> dict:
    """Return the list of directories currently configured for graphify scanning."""
    return {"dirs": _load_scan_dirs()}


class ScanDirBody(BaseModel):
    path: str


@app.post("/graph/scan-dirs", status_code=201)
def add_scan_dir(body: ScanDirBody) -> dict:
    """Add a directory to the scan list. Path must exist on disk."""
    p = Path(body.path).expanduser().resolve()
    if not p.is_dir():
        raise HTTPException(status_code=422, detail=f"Not a directory: {p}")
    dirs = _load_scan_dirs()
    sp = str(p)
    if sp not in dirs:
        dirs.append(sp)
        _save_scan_dirs(dirs)
    return {"dirs": dirs}


@app.delete("/graph/scan-dirs")
def remove_scan_dir(body: ScanDirBody) -> dict:
    """Remove a directory from the scan list."""
    p = str(Path(body.path).expanduser().resolve())
    dirs = [d for d in _load_scan_dirs() if str(Path(d).resolve()) != p]
    _save_scan_dirs(dirs)
    return {"dirs": dirs}


# ---------------------------------------------------------------------------
# Semantic similarity pass
# ---------------------------------------------------------------------------

def _read_source_window(source_file: str, n_lines: int = 35) -> str:
    """Read up to n_lines from a node's source file, checking all known repo roots."""
    if not source_file:
        return ""
    roots = _configured_source_roots()
    for root in roots:
        p = root / source_file
        if p.exists():
            try:
                return "\n".join(p.read_text(errors="replace").splitlines()[:n_lines])
            except Exception:
                pass
    return ""


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag = (sum(x * x for x in a) ** 0.5) * (sum(x * x for x in b) ** 0.5)
    return dot / mag if mag else 0.0


def _save_semantic_edges(
    semantic_edges: list[dict],
    model: str,
    threshold: float,
    created_at: str,
    graph: dict | None = None,
) -> None:
    graph = graph or _load_graph()
    write_json_atomic(SEMANTIC_EDGES_FILE, {
        "edges": semantic_edges,
        "model": model,
        "threshold": threshold,
        "created_at": created_at,
        "graph_fingerprint": _graph_fingerprint(graph),
        "graph_node_count": len(graph.get("nodes", [])),
    })


def _semantic_edges_response(data: dict | None = None) -> dict:
    payload = dict(data or {
        "edges": [],
        "model": None,
        "threshold": None,
        "created_at": None,
        "graph_fingerprint": None,
        "graph_node_count": 0,
    })
    edges = payload.get("edges")
    if not isinstance(edges, list):
        edges = []
        payload["edges"] = edges

    current_fingerprint: str | None = None
    current_node_count = 0
    current_edge_match_count = 0
    try:
        graph = _load_graph()
        current_fingerprint = _graph_fingerprint(graph)
        current_nodes = {str(node.get("id") or "") for node in graph.get("nodes", [])}
        current_node_count = len(current_nodes)
        current_edge_match_count = sum(
            1
            for edge in edges
            if str(edge.get("source") or "") in current_nodes
            and str(edge.get("target") or "") in current_nodes
        )
    except Exception:
        pass

    stored_fingerprint = payload.get("graph_fingerprint")
    edge_count = len(edges)
    graph_matches = bool(
        (edge_count == 0 and not stored_fingerprint)
        or (stored_fingerprint and current_fingerprint and stored_fingerprint == current_fingerprint)
    )
    payload["edge_count"] = edge_count
    payload["current_graph_fingerprint"] = current_fingerprint
    payload["current_graph_node_count"] = current_node_count
    payload["current_graph_edge_match_count"] = current_edge_match_count
    payload["graph_matches"] = graph_matches
    payload["graph_stale"] = bool(edge_count > 0 and not graph_matches)
    return payload


def _run_semantic_pass(model: str, threshold: float) -> None:
    import urllib.request as _ureq
    global _SEMANTIC_STATUS
    _SEMANTIC_STATUS.update({
        "status": "running", "progress": 0, "total": 0,
        "error": None, "edge_count": 0, "model": model,
    })
    try:
        g = _load_graph()
        nodes = g.get("nodes", [])
        _SEMANTIC_STATUS["total"] = len(nodes)

        _ollama_base = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        embed_url = f"{_ollama_base}/api/embeddings"

        embeddings: list[tuple[str, list[float]]] = []

        for i, node in enumerate(nodes):
            nid = node["id"]
            label = node.get("label", nid)
            ftype = node.get("file_type", "code")
            window = _read_source_window(node.get("source_file", ""))
            text = f"{ftype}: {label}\n{window}".strip()[:2000]

            try:
                payload = json.dumps({"model": model, "prompt": text}).encode()
                req = _ureq.Request(embed_url, data=payload,
                                    headers={"Content-Type": "application/json"}, method="POST")
                with _ureq.urlopen(req, timeout=90) as resp:
                    vec = json.loads(resp.read()).get("embedding", [])
                if vec:
                    embeddings.append((nid, vec))
            except Exception:
                pass
            _SEMANTIC_STATUS["progress"] = i + 1

        semantic_edges: list[dict] = []
        m = len(embeddings)

        try:
            import numpy as np  # type: ignore
            mat = np.array([v for _, v in embeddings], dtype=np.float32)
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            mat /= np.maximum(norms, 1e-9)
            sim_mat = mat @ mat.T
            rows, cols = np.where(np.triu(sim_mat > threshold, k=1))
            for r, c in zip(rows.tolist(), cols.tolist()):
                semantic_edges.append({
                    "source": embeddings[r][0],
                    "target": embeddings[c][0],
                    "similarity": round(float(sim_mat[r, c]), 4),
                    "relation": "semantic_similar",
                })
        except ImportError:
            for ai in range(m):
                for bi in range(ai + 1, m):
                    s = _cosine_sim(embeddings[ai][1], embeddings[bi][1])
                    if s > threshold:
                        semantic_edges.append({
                            "source": embeddings[ai][0],
                            "target": embeddings[bi][0],
                            "similarity": round(s, 4),
                            "relation": "semantic_similar",
                        })

        ts = datetime.now(tz=timezone.utc).isoformat()
        _save_semantic_edges(semantic_edges, model, threshold, ts, g)

        _SEMANTIC_STATUS.update({
            "status": "complete",
            "last_run": ts,
            "edge_count": len(semantic_edges),
            "error": None,
        })

    except Exception as exc:
        ts = datetime.now(tz=timezone.utc).isoformat()
        _SEMANTIC_STATUS.update({"status": "error", "last_run": ts, "error": str(exc)})


class SemanticPassBody(BaseModel):
    model: str = "nomic-embed-text"
    threshold: float = 0.78


@app.post("/graph/semantic-pass", status_code=202)
def trigger_semantic_pass(body: SemanticPassBody) -> dict:
    """Start a background semantic similarity pass using Ollama embeddings."""
    if _SEMANTIC_STATUS.get("status") == "running":
        raise HTTPException(status_code=409, detail="Semantic pass already in progress.")
    import threading as _sem_t
    _sem_t.Thread(target=_run_semantic_pass, args=(body.model, body.threshold), daemon=True).start()
    return {"status": "running", "model": body.model, "threshold": body.threshold}


@app.get("/graph/semantic-pass/status")
def semantic_pass_status() -> dict:
    return dict(_SEMANTIC_STATUS)


@app.get("/graph/semantic-edges")
def get_semantic_edges() -> dict:
    """Return stored semantic similarity edges."""
    if not SEMANTIC_EDGES_FILE.exists():
        return _semantic_edges_response()
    try:
        return _semantic_edges_response(json.loads(SEMANTIC_EDGES_FILE.read_text()))
    except Exception:
        return _semantic_edges_response()


@app.get("/graph/overlap-summary")
def get_overlap_summary(project: str | None = None) -> dict:
    """Compute semantic overlap groups aligned to the visible summary map."""
    if not SEMANTIC_EDGES_FILE.exists():
        return {
            "groups": [],
            "total_cross_edges": 0,
            "created_at": None,
            "level": "top" if project is None else "project",
            "project": project,
        }
    try:
        sem_data = json.loads(SEMANTIC_EDGES_FILE.read_text())
    except Exception:
        return {
            "groups": [],
            "total_cross_edges": 0,
            "created_at": None,
            "level": "top" if project is None else "project",
            "project": project,
        }

    edges = sem_data.get("edges", [])
    if not edges:
        return {
            "groups": [],
            "total_cross_edges": 0,
            "created_at": sem_data.get("created_at"),
            "level": "top" if project is None else "project",
            "project": project,
        }

    try:
        graph = apply_signal_tiers_to_graph(_load_graph())
    except Exception:
        return {
            "groups": [],
            "total_cross_edges": 0,
            "created_at": sem_data.get("created_at"),
            "level": "top" if project is None else "project",
            "project": project,
        }

    selection = _load_cluster_selection()
    sel_sources = selection.get("sources", ["local", "sharepoint", "onenote"])
    sel_clusters = selection.get("clusters")
    nodes_raw = [
        n for n in graph.get("nodes", [])
        if isinstance(n, dict)
        and _is_node_selected(n, sel_sources, sel_clusters)
        and is_visible_signal_node(n)
    ]
    node_map: dict[str, dict] = {str(n.get("id")): n for n in nodes_raw}
    get_cluster, cluster_labels, _cluster_group_types = _summary_cluster_getter(
        nodes_raw,
        project,
    )
    node_clusters: dict[str, str] = {}
    for node in nodes_raw:
        node_id = str(node.get("id"))
        cluster = get_cluster(node)
        if cluster:
            node_clusters[node_id] = cluster

    def basename(source_file: str) -> str:
        return source_file.replace("\\", "/").split("/")[-1]

    groups: dict[str, dict] = {}
    total_cross = 0
    for edge in edges:
        source_id = str(edge.get("source") or "")
        target_id = str(edge.get("target") or "")
        src_node = node_map.get(source_id)
        tgt_node = node_map.get(target_id)
        if not src_node or not tgt_node:
            continue
        src_cluster = node_clusters.get(source_id)
        tgt_cluster = node_clusters.get(target_id)
        if not src_cluster or not tgt_cluster or src_cluster == tgt_cluster:
            continue
        try:
            similarity = float(edge.get("similarity") or 0)
        except (TypeError, ValueError):
            similarity = 0.0
        total_cross += 1
        cluster_a, cluster_b = sorted((src_cluster, tgt_cluster))
        key = f"{cluster_a}___{cluster_b}"
        if key not in groups:
            groups[key] = {
                "cluster_a": cluster_a,
                "cluster_b": cluster_b,
                "label_a": cluster_labels.get(cluster_a, cluster_a),
                "label_b": cluster_labels.get(cluster_b, cluster_b),
                "edge_count": 0,
                "total_similarity": 0.0,
                "max_similarity": 0.0,
                "same_name_count": 0,
                "pairs": [],
            }

        file_a = str(src_node.get("source_file") or "")
        file_b = str(tgt_node.get("source_file") or "")
        same_name = bool(file_a and file_b and basename(file_a) == basename(file_b))
        groups[key]["edge_count"] += 1
        groups[key]["total_similarity"] += similarity
        groups[key]["max_similarity"] = max(groups[key]["max_similarity"], similarity)
        if same_name:
            groups[key]["same_name_count"] += 1
        groups[key]["pairs"].append(
            {
                "source": source_id,
                "target": target_id,
                "label_a": src_node.get("label", source_id),
                "label_b": tgt_node.get("label", target_id),
                "file_a": file_a,
                "file_b": file_b,
                "similarity": round(similarity, 4),
                "same_name": same_name,
            }
        )

    result: list[dict] = []
    for group in sorted(
        groups.values(),
        key=lambda item: (
            -int(item["same_name_count"] > 0),
            -int(item["edge_count"]),
            -float(item["max_similarity"]),
        ),
    ):
        pairs = sorted(
            group["pairs"],
            key=lambda pair: (
                -int(bool(pair.get("same_name"))),
                -float(pair.get("similarity") or 0),
            ),
        )[:6]
        avg_similarity = (
            group["total_similarity"] / group["edge_count"]
            if group["edge_count"]
            else 0.0
        )
        result.append(
            {
                "cluster_a": group["cluster_a"],
                "cluster_b": group["cluster_b"],
                "label_a": group["label_a"],
                "label_b": group["label_b"],
                "edge_count": group["edge_count"],
                "avg_similarity": round(avg_similarity, 4),
                "max_similarity": round(group["max_similarity"], 4),
                "same_name_count": group["same_name_count"],
                "top_pairs": pairs,
            }
        )

    return {
        "groups": result,
        "total_cross_edges": total_cross,
        "created_at": sem_data.get("created_at"),
        "level": "top" if project is None else "project",
        "project": project,
    }


@app.get("/graph/overlap-report")
def get_overlap_report() -> dict:
    """Compute cross-cluster semantic overlap groups from stored semantic edges + graph."""
    if not SEMANTIC_EDGES_FILE.exists():
        return {"groups": [], "total_cross_edges": 0, "created_at": None}
    try:
        sem_data = json.loads(SEMANTIC_EDGES_FILE.read_text())
    except Exception:
        return {"groups": [], "total_cross_edges": 0, "created_at": None}

    edges = sem_data.get("edges", [])
    if not edges:
        return {"groups": [], "total_cross_edges": 0, "created_at": sem_data.get("created_at")}

    try:
        g = apply_signal_tiers_to_graph(_load_graph())
    except Exception:
        return {"groups": [], "total_cross_edges": 0, "created_at": sem_data.get("created_at")}

    node_meta: dict[str, dict] = {
        n["id"]: {
            "label": n.get("label", n["id"]),
            "cluster": _node_overlap_cluster_id(n),
            "source_file": n.get("source_file", ""),
        }
        for n in g.get("nodes", [])
        if isinstance(n, dict) and is_visible_signal_node(n)
    }

    groups: dict[str, dict] = {}
    total_cross = 0

    for edge in edges:
        sm = node_meta.get(edge["source"])
        tm = node_meta.get(edge["target"])
        if not sm or not tm:
            continue
        sc, tc = sm["cluster"], tm["cluster"]
        if sc == tc:
            continue
        total_cross += 1
        ca, cb = (sc, tc) if sc <= tc else (tc, sc)
        key = f"{ca}___{cb}"
        if key not in groups:
            groups[key] = {"cluster_a": ca, "cluster_b": cb, "edge_count": 0, "total_sim": 0.0, "pairs": []}
        groups[key]["edge_count"] += 1
        groups[key]["total_sim"] += edge["similarity"]
        groups[key]["pairs"].append({
            "source": edge["source"], "target": edge["target"],
            "label_a": sm["label"], "label_b": tm["label"],
            "file_a": sm["source_file"], "file_b": tm["source_file"],
            "similarity": round(edge["similarity"], 4),
        })

    result: list[dict] = []
    for gd in sorted(groups.values(), key=lambda x: -x["edge_count"]):
        top = sorted(gd["pairs"], key=lambda p: -p["similarity"])[:5]
        avg_sim = gd["total_sim"] / gd["edge_count"] if gd["edge_count"] else 0.0
        result.append({
            "cluster_a": gd["cluster_a"],
            "cluster_b": gd["cluster_b"],
            "edge_count": gd["edge_count"],
            "avg_similarity": round(avg_sim, 4),
            "top_pairs": top,
        })

    return {"groups": result, "total_cross_edges": total_cross, "created_at": sem_data.get("created_at")}


class CreateOverlapRecommendationRequest(BaseModel):
    cluster_a: str
    cluster_b: str
    edge_count: int
    avg_similarity: float
    top_pairs: list[dict]
    triage_verdict: Optional[str] = None   # "duplicate" | "reference" | "related"
    triage_action: Optional[str] = None
    triage_confidence: Optional[float] = None
    triage_result: Optional[dict] = None


class TriageOverlapRequest(BaseModel):
    cluster_a: str
    cluster_b: str
    edge_count: int
    avg_similarity: float
    top_pairs: list[dict]
    model: Optional[str] = None


def _truncate_text(value: object, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _bounded_text_list(value: object, *, max_items: int = 5, max_len: int = 180) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for raw in value:
        text = _truncate_text(raw, max_len)
        if text:
            items.append(text)
        if len(items) >= max_items:
            break
    return items


def _overlap_pair_name(pair: dict) -> str:
    left = pair.get("label_a") or pair.get("source") or "left side"
    right = pair.get("label_b") or pair.get("target") or "right side"
    return f"{left} ↔ {right}"


SEMANTIC_INSIGHT_KINDS = {
    "waste_duplicate",
    "gap_missing_bridge",
    "cross_app_similarity",
    "shared_pattern",
    "drift_risk",
    "intentional_reference",
    "low_value",
    "unknown",
}


def _bounded_score(value: object, fallback: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = fallback
    return round(min(1.0, max(0.0, score)), 2)


def _heuristic_overlap_insight(req: TriageOverlapRequest, verdict: str = "related") -> dict:
    pairs = req.top_pairs[:6]
    same_name_count = sum(1 for pair in pairs if pair.get("same_name"))
    max_similarity = max((float(pair.get("similarity") or 0) for pair in pairs), default=req.avg_similarity)
    avg = max(0.0, min(1.0, float(req.avg_similarity or 0)))
    density_bonus = min(0.18, req.edge_count / 250)
    score = 0.35 + (avg * 0.32) + density_bonus
    if same_name_count:
        score += 0.16
    if max_similarity >= 0.94:
        score += 0.08
    if verdict == "duplicate":
        score += 0.12
    elif verdict == "reference":
        score -= 0.06

    if verdict == "duplicate" or same_name_count >= 2 or (same_name_count and max_similarity >= 0.88):
        insight_kind = "waste_duplicate"
        decision_impact = "Likely waste: choose a canonical owner or merge repeated content before the overlap spreads."
    elif verdict == "reference":
        insight_kind = "intentional_reference"
        decision_impact = "Likely intentional relationship: make the source-of-truth and reference direction explicit."
    elif req.edge_count >= 18 and avg >= 0.86:
        insight_kind = "cross_app_similarity"
        decision_impact = "Highly similar areas across applications: compare for shared interfaces, standards, or reusable knowledge."
    elif req.edge_count >= 8 and same_name_count == 0 and avg >= 0.80:
        insight_kind = "gap_missing_bridge"
        decision_impact = "Possible gap: related areas are close semantically but need an explicit bridge, owner, or integration decision."
    elif max_similarity >= 0.92:
        insight_kind = "drift_risk"
        decision_impact = "Drift risk: similar knowledge may diverge unless one side owns the canonical wording or behavior."
    elif req.edge_count >= 4:
        insight_kind = "shared_pattern"
        decision_impact = "Shared pattern: likely reusable vocabulary or design that should be named if it matters across apps."
    else:
        insight_kind = "low_value"
        decision_impact = "Low immediate value: similarity appears too thin for a consolidation decision without more evidence."

    return {
        "insight_kind": insight_kind,
        "actionability_score": _bounded_score(score, 0.5),
        "decision_impact": decision_impact,
        "waste_signal": (
            f"{same_name_count} top pair(s) share filenames and max similarity is {round(max_similarity * 100)}%."
            if same_name_count
            else "No same-filename duplicate signal in the top pairs."
        ),
        "gap_signal": (
            "No same-name canonicality signal; inspect whether these related areas need a cross-reference or owner decision."
            if same_name_count == 0 and avg >= 0.80
            else "Gap signal is secondary to stronger duplicate/reference evidence."
        ),
        "cross_app_similarity": (
            f"{req.edge_count} cross-container semantic links at {round(avg * 100)}% average similarity."
        ),
    }


def _path_container(path: object) -> str:
    parts = [part for part in str(path or "").replace("\\", "/").split("/") if part]
    if not parts:
        return "unknown"
    return "/".join(parts[:2]) if len(parts) > 1 else parts[0]


def _side_examples(top_pairs: list[dict], side: str) -> str:
    label_key = "label_a" if side == "a" else "label_b"
    file_key = "file_a" if side == "a" else "file_b"
    examples: list[str] = []
    for pair in top_pairs[:4]:
        label = str(pair.get(label_key) or "").strip()
        path = str(pair.get(file_key) or "").strip()
        if label and path:
            examples.append(f"{label} ({path})")
        elif label:
            examples.append(label)
        elif path:
            examples.append(path)
    return "; ".join(examples) if examples else "No concrete node examples were supplied."


def _fallback_overlap_dossier(req: TriageOverlapRequest, verdict: str = "related") -> dict:
    pairs = req.top_pairs[:6]
    insight = _heuristic_overlap_insight(req, verdict)
    same_name_count = sum(1 for pair in pairs if pair.get("same_name"))
    max_pair = max(pairs, key=lambda pair: float(pair.get("similarity") or 0), default={})
    max_pct = round(float(max_pair.get("similarity") or req.avg_similarity or 0) * 100)
    avg_pct = round(req.avg_similarity * 100)

    similarities = [
        f"{_overlap_pair_name(pair)} shares {round(float(pair.get('similarity') or 0) * 100)}% semantic similarity"
        + (" and the same filename" if pair.get("same_name") else "")
        + "."
        for pair in pairs[:3]
    ]
    if not similarities:
        similarities = [f"{req.cluster_a} and {req.cluster_b} have overlapping graph terms, but no top pair details were supplied."]

    differences: list[str] = []
    for pair in pairs[:3]:
        left_container = _path_container(pair.get("file_a"))
        right_container = _path_container(pair.get("file_b"))
        if left_container != right_container:
            differences.append(f"Different containers: {left_container} versus {right_container}.")
        left_label = str(pair.get("label_a") or "").strip()
        right_label = str(pair.get("label_b") or "").strip()
        if left_label and right_label and left_label != right_label:
            differences.append(f"Different node names: {left_label} versus {right_label}.")
        if len(differences) >= 4:
            break
    if not differences:
        differences.append("No meaningful difference is visible from the overlap metadata alone.")

    canonicality_signals: list[str] = []
    if same_name_count:
        canonicality_signals.append(f"{same_name_count} top pair(s) share a filename, which is a strong duplicate/canonical-owner signal.")
    if req.avg_similarity >= 0.9:
        canonicality_signals.append(f"Average similarity is {avg_pct}%, so one side may be a redundant copy.")
    if max_pair:
        canonicality_signals.append(f"Highest-similarity pair is {_overlap_pair_name(max_pair)} at {max_pct}%.")
    if not canonicality_signals:
        canonicality_signals.append("Canonical ownership is not clear from graph data; compare recency, call sites, and owner intent before merging.")

    return {
        "verdict": verdict if verdict in ("duplicate", "reference", "related", "unknown") else "related",
        "confidence": round(min(0.85, max(0.35, req.avg_similarity)), 2),
        **insight,
        "reason": (
            f"{req.cluster_a} and {req.cluster_b} overlap across {req.edge_count} semantic connections, "
            f"but the graph alone does not prove whether one side should replace the other."
        ),
        "action": "Inspect the named pairs, choose a canonical owner when duplication is confirmed, and preserve explicit references when both sides serve different jobs.",
        "evidence_summary": (
            f"This matters because {req.edge_count} cross-container semantic connections link {req.cluster_a} and {req.cluster_b} "
            f"(average {avg_pct}%). The top evidence points to {_overlap_pair_name(max_pair) if max_pair else 'the listed pairs'}."
        ),
        "per_side_purpose": {
            "cluster_a": f"{req.cluster_a} appears to cover: {_side_examples(pairs, 'a')}",
            "cluster_b": f"{req.cluster_b} appears to cover: {_side_examples(pairs, 'b')}",
        },
        "similarities": similarities,
        "differences": differences[:5],
        "canonicality_signals": canonicality_signals[:5],
        "open_questions": [
            f"Which side is the intended long-term owner for this knowledge: {req.cluster_a} or {req.cluster_b}?",
            "Are these files duplicates, or is one an intentional summary/reference of the other?",
            "Would merging remove needed context for a specific workflow, repo, or operator?",
        ],
    }


def _normalize_overlap_triage(data: dict, req: TriageOverlapRequest, model: str) -> dict:
    fallback = _fallback_overlap_dossier(req, str(data.get("verdict", "related")))
    verdict = str(data.get("verdict", fallback["verdict"]))
    if verdict not in ("duplicate", "reference", "related"):
        verdict = "related"

    insight_kind = str(data.get("insight_kind", fallback["insight_kind"]))
    if insight_kind not in SEMANTIC_INSIGHT_KINDS:
        insight_kind = fallback["insight_kind"]

    raw_per_side = data.get("per_side_purpose")
    per_side = fallback["per_side_purpose"]
    if isinstance(raw_per_side, dict):
        per_side = {
            "cluster_a": _truncate_text(raw_per_side.get("cluster_a") or raw_per_side.get(req.cluster_a) or per_side["cluster_a"], 320),
            "cluster_b": _truncate_text(raw_per_side.get("cluster_b") or raw_per_side.get(req.cluster_b) or per_side["cluster_b"], 320),
        }

    try:
        confidence = float(data.get("confidence", fallback["confidence"]))
    except (TypeError, ValueError):
        confidence = float(fallback["confidence"])

    return {
        "verdict": verdict,
        "confidence": round(min(1.0, max(0.0, confidence)), 2),
        "insight_kind": insight_kind,
        "actionability_score": _bounded_score(data.get("actionability_score"), fallback["actionability_score"]),
        "decision_impact": _truncate_text(data.get("decision_impact") or fallback["decision_impact"], 520),
        "waste_signal": _truncate_text(data.get("waste_signal") or fallback["waste_signal"], 360),
        "gap_signal": _truncate_text(data.get("gap_signal") or fallback["gap_signal"], 360),
        "cross_app_similarity": _truncate_text(data.get("cross_app_similarity") or fallback["cross_app_similarity"], 360),
        "reason": _truncate_text(data.get("reason") or fallback["reason"], 420),
        "action": _truncate_text(data.get("action") or fallback["action"], 520),
        "evidence_summary": _truncate_text(data.get("evidence_summary") or fallback["evidence_summary"], 520),
        "per_side_purpose": per_side,
        "similarities": _bounded_text_list(data.get("similarities"), max_items=5) or fallback["similarities"],
        "differences": _bounded_text_list(data.get("differences"), max_items=5) or fallback["differences"],
        "canonicality_signals": _bounded_text_list(data.get("canonicality_signals"), max_items=5) or fallback["canonicality_signals"],
        "open_questions": _bounded_text_list(data.get("open_questions"), max_items=5) or fallback["open_questions"],
        "model": model,
    }


def _unique_texts(values: list[object], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _overlap_action_plan(req: CreateOverlapRecommendationRequest, verdict: str, proposed_action: str) -> dict:
    pairs = req.top_pairs[:6]
    triage = req.triage_result if isinstance(req.triage_result, dict) else {}
    insight_kind = str(triage.get("insight_kind") or "unknown")
    decision_impact = _truncate_text(triage.get("decision_impact") or "", 260)
    side_purpose = triage.get("per_side_purpose") if isinstance(triage.get("per_side_purpose"), dict) else {}
    open_questions = _bounded_text_list(triage.get("open_questions"), max_items=5)
    risks = _bounded_text_list(triage.get("risks"), max_items=5)

    files = _unique_texts(
        [p.get("file_a") for p in pairs] + [p.get("file_b") for p in pairs],
        limit=10,
    )
    pair_names = [_overlap_pair_name(p) for p in pairs[:5]]
    same_name_count = sum(1 for p in pairs if p.get("same_name"))

    if verdict == "duplicate":
        canonical_target = (
            f"Choose one canonical owner between {req.cluster_a} and {req.cluster_b}; "
            f"start with the side that is newer, more actively maintained, or closer to operator-facing docs."
        )
        concrete_steps = [
            f"Open the top {len(pair_names)} overlap pair(s) and compare source excerpts before editing.",
            "Select the canonical file or container and list the exact source files that will be merged into it.",
            "Move only non-duplicate detail into the canonical target; preserve useful links or history notes.",
            "Update references that still point to the merged-away wording or stale source.",
            "Re-run graph and overlap checks to confirm the duplicate signal dropped.",
        ]
        default_risks = [
            "A merge could remove context that is intentionally repo-specific.",
            "Choosing the wrong canonical owner could make future maintenance less obvious.",
            "Cross-references may become stale if only text is merged.",
        ]
    elif verdict == "reference":
        canonical_target = (
            f"Keep both {req.cluster_a} and {req.cluster_b}; make the canonical source of truth explicit in the cross-reference."
        )
        concrete_steps = [
            "Identify which side is source-of-truth and which side is reference, summary, or implementation context.",
            "Add or update cross-links so the relationship is obvious from both sides.",
            "Remove only duplicated wording that creates maintenance drift.",
            "Add a short note explaining why both locations remain.",
            "Re-run overlap review and mark the pair documented if the relationship is intentional.",
        ]
        default_risks = [
            "The pair may be intentional but undocumented, so merging could damage useful context.",
            "Cross-references could create circular or noisy documentation if overdone.",
        ]
    else:
        canonical_target = (
            f"Do not merge yet; document the relationship between {req.cluster_a} and {req.cluster_b} and gather owner evidence."
        )
        concrete_steps = [
            "Review the top overlap pairs and decide whether they are same-problem, reference, or shared vocabulary.",
            "Name the different job each side performs.",
            "Add a lightweight relationship note where future operators will see it.",
            "Defer consolidation until a canonical owner is clear.",
        ]
        default_risks = [
            "Similar vocabulary could be mistaken for duplicate implementation.",
            "Deferring the decision could leave future operators with the same ambiguity.",
        ]

    if not risks:
        risks = default_risks

    acceptance_criteria = [
        "The canonical owner or intentional dual-owner relationship is written down.",
        "Every top overlap pair has been reviewed against its source path, not only its label.",
        "Any merged or retained content still preserves repo-specific context needed by an operator.",
        "A follow-up overlap check shows fewer duplicate signals or a documented reason to keep them.",
    ]

    if side_purpose:
        purpose_a = _truncate_text(side_purpose.get("cluster_a") or "", 180)
        purpose_b = _truncate_text(side_purpose.get("cluster_b") or "", 180)
        if purpose_a or purpose_b:
            concrete_steps.insert(
                1,
                f"Use the triage purpose notes as a starting hypothesis: {req.cluster_a}: {purpose_a or 'unknown'}; {req.cluster_b}: {purpose_b or 'unknown'}.",
            )
    if insight_kind != "unknown" and decision_impact:
        concrete_steps.insert(0, f"Use the semantic insight category `{insight_kind}` as the review frame: {decision_impact}")

    return {
        "canonical_target": canonical_target,
        "merge_sources": files or pair_names,
        "concrete_steps": concrete_steps,
        "savings_estimate": {
            "duplicate_node_count": len(pair_names),
            "affected_files": len(files),
            "semantic_edge_reduction": min(req.edge_count, max(0, len(pair_names) * 2)),
            "rough_context_savings": (
                f"Conservative: reviewing or consolidating the top {len(pair_names)} pair(s) could remove "
                f"roughly {min(req.edge_count, max(1, len(pair_names) * 2))} repeated semantic references from future graph context."
            ),
            "caveat": "Estimate is directional only; verify by rerunning Graphify/semantic overlap after the actual edit.",
        },
        "risks": risks,
        "acceptance_criteria": acceptance_criteria,
        "rollback_note": "Keep the original files until review is accepted; rollback is to restore the pre-merge files and remove added cross-reference notes.",
        "open_questions": open_questions or [
            f"Which side should be treated as canonical: {req.cluster_a} or {req.cluster_b}?",
            "Is the overlap duplicate content, an intentional reference, or shared vocabulary?",
            "Who owns the follow-up edit after this recommendation is accepted?",
        ],
        "source_pairs": pair_names,
        "same_name_count": same_name_count,
        "insight_kind": insight_kind,
        "proposed_action": proposed_action,
    }


OverlapWorkflowStatus = Literal["untriaged", "triaged", "task-created", "dismissed"]


class PatchOverlapStatusRequest(BaseModel):
    status: OverlapWorkflowStatus
    cluster_a: Optional[str] = None
    cluster_b: Optional[str] = None
    triage_result: Optional[dict] = None
    recommendation_id: Optional[str] = None


def _load_overlap_statuses() -> dict[str, dict]:
    if not OVERLAP_STATUS_FILE.exists():
        return {}
    try:
        data = json.loads(OVERLAP_STATUS_FILE.read_text())
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items() if isinstance(v, dict)}
    except Exception:
        pass
    return {}


def _save_overlap_statuses(statuses: dict[str, dict]) -> None:
    write_json_atomic(OVERLAP_STATUS_FILE, statuses)


@app.get("/overlap/status")
def list_overlap_statuses() -> dict:
    return {"pairs": _load_overlap_statuses()}


@app.patch("/overlap/status/{pair_key}")
def patch_overlap_status(pair_key: str, req: PatchOverlapStatusRequest) -> dict:
    statuses = _load_overlap_statuses()
    now = datetime.now(tz=timezone.utc).isoformat()
    current = statuses.get(pair_key, {})
    record = {
        **current,
        "pair_key": pair_key,
        "status": req.status,
        "updated_at": now,
    }
    if "created_at" not in record:
        record["created_at"] = now
    if req.cluster_a is not None:
        record["cluster_a"] = req.cluster_a
    if req.cluster_b is not None:
        record["cluster_b"] = req.cluster_b
    if req.triage_result is not None:
        record["triage_result"] = req.triage_result
    if req.recommendation_id is not None:
        record["recommendation_id"] = req.recommendation_id
    statuses[pair_key] = record
    _save_overlap_statuses(statuses)
    return record


@app.post("/overlap/triage")
def triage_overlap(req: TriageOverlapRequest) -> dict:
    """Ask the local LLM to classify overlap as duplicate/reference/related."""
    model = (req.model or RECOMMEND_MODEL_DEFAULT).strip()
    same_name_pairs = [p for p in req.top_pairs if p.get("same_name")]
    pairs_text = "\n".join(
        f"- '{p.get('label_a', '?')}' ↔ '{p.get('label_b', '?')}'  "
        f"[{round(p.get('similarity', 0) * 100)}% similar"
        f"{', same filename' if p.get('same_name') else ''}] "
        f"A path: {p.get('file_a') or 'unknown'}; B path: {p.get('file_b') or 'unknown'}"
        for p in req.top_pairs[:6]
    )
    same_name_note = (
        f"\nNote: {len(same_name_pairs)} pairs share the same filename — strong duplicate signal."
        if same_name_pairs else ""
    )
    prompt = (
        f"You are analysing code-repository overlap. Two repository clusters have "
        f"{req.edge_count} semantically similar content connections "
        f"(avg {round(req.avg_similarity * 100)}% cosine similarity).{same_name_note}\n\n"
        f"Cluster A: {req.cluster_a}\n"
        f"Cluster B: {req.cluster_b}\n\n"
        f"Top overlapping content pairs:\n{pairs_text}\n\n"
        f"Classify this overlap as exactly ONE of:\n"
        f'- "duplicate": content is nearly identical — should be merged into one canonical location\n'
        f'- "reference": one document intentionally references or extends the other — keep both\n'
        f'- "related": similar topic but different enough in purpose to keep separate\n\n'
        f"Do not merely restate that semantic similarity is high. Explain what each side appears to do, "
        f"why the overlap matters to a decision-maker, what looks the same, what differs, whether either "
        f"side looks canonical, and what questions remain before merge/review/document action.\n\n"
        f"Also classify the decision-useful insight as exactly ONE of:\n"
        f'- "waste_duplicate": duplicated work, wording, behavior, or knowledge that can likely be consolidated\n'
        f'- "gap_missing_bridge": related areas lack an explicit owner, reference, integration, or explanatory bridge\n'
        f'- "cross_app_similarity": highly similar parts of multiple applications should be compared for shared interfaces, standards, or reusable knowledge\n'
        f'- "shared_pattern": similar vocabulary/design appears intentional and should be named as a reusable pattern\n'
        f'- "drift_risk": similar material should stay separate but may diverge unless one side is canonical\n'
        f'- "intentional_reference": one side intentionally references, extends, or summarizes the other\n'
        f'- "low_value": similarity is generic vocabulary and is unlikely to drive a useful action\n\n'
        f"Score actionability from 0.0 to 1.0. Give a high score only when the overlap can help cut waste, close a gap, "
        f"or reveal highly similar application areas. Penalize generic vocabulary, framework boilerplate, and weak evidence.\n\n"
        f"Return ONLY valid JSON with no extra text:\n"
        f'{{"verdict":"duplicate"|"reference"|"related","confidence":0.0-1.0,'
        f'"insight_kind":"waste_duplicate"|"gap_missing_bridge"|"cross_app_similarity"|"shared_pattern"|"drift_risk"|"intentional_reference"|"low_value",'
        f'"actionability_score":0.0-1.0,'
        f'"decision_impact":"why this matters for waste, gaps, or multi-application similarity",'
        f'"waste_signal":"specific evidence for or against waste",'
        f'"gap_signal":"specific evidence for or against a missing bridge/owner/reference",'
        f'"cross_app_similarity":"specific evidence about similar parts across applications",'
        f'"reason":"one sentence decision rationale",'
        f'"action":"one sentence recommended action",'
        f'"evidence_summary":"why this matters beyond high similarity",'
        f'"per_side_purpose":{{"cluster_a":"what {req.cluster_a} appears to do","cluster_b":"what {req.cluster_b} appears to do"}},'
        f'"similarities":["concrete similarity"],'
        f'"differences":["concrete difference"],'
        f'"canonicality_signals":["signal or unclear canonicality"],'
        f'"open_questions":["question to answer before acting"]}}'
    )
    try:
        raw = _call_ollama(prompt, model, timeout=90)
        data = json.loads(raw)
        return _normalize_overlap_triage(data, req, model)
    except Exception as exc:
        fallback = _fallback_overlap_dossier(req, "unknown")
        return {
            **fallback,
            "verdict": "unknown",
            "confidence": 0.0,
            "reason": f"Triage failed: {exc}",
            "model": model,
        }


@app.post("/recommendations/from-overlap", status_code=201)
def create_overlap_recommendation(req: CreateOverlapRecommendationRequest, request: Request) -> dict:
    """Create a recommendation from overlap analysis, enriched with triage verdict when available."""
    pairs_text = "\n".join(
        f"- {p.get('label_a', '?')} ↔ {p.get('label_b', '?')} [{round(p.get('similarity', 0) * 100)}% similar]"
        for p in req.top_pairs[:5]
    )
    now = datetime.now(tz=timezone.utc).isoformat()
    effort = "medium" if req.edge_count > 50 else "low"

    verdict = req.triage_verdict or "duplicate"
    triage_result = req.triage_result if isinstance(req.triage_result, dict) else {}
    insight_kind = str(triage_result.get("insight_kind") or "")
    actionability_score = _bounded_score(triage_result.get("actionability_score"), req.triage_confidence or req.avg_similarity)
    decision_impact = _truncate_text(triage_result.get("decision_impact") or "", 420)
    title_prefix = {
        "duplicate": "Merge",
        "reference": "Review Cross-Reference",
        "related": "Document Relationship",
    }.get(verdict, "Consolidate")
    insight_title_prefix = {
        "waste_duplicate": "Cut Waste",
        "gap_missing_bridge": "Close Gap",
        "cross_app_similarity": "Compare Apps",
        "shared_pattern": "Name Pattern",
        "drift_risk": "Prevent Drift",
        "intentional_reference": "Clarify Reference",
        "low_value": "Defer Low-Signal",
    }.get(insight_kind)
    if insight_title_prefix:
        title_prefix = insight_title_prefix
    title = f"{title_prefix}: {req.cluster_a} ↔ {req.cluster_b} ({req.edge_count} overlapping nodes)"

    triage_note = ""
    if req.triage_verdict:
        conf_pct = round((req.triage_confidence or 0) * 100)
        actionability_pct = round(actionability_score * 100)
        insight_note = f"; insight: {insight_kind.replace('_', ' ')}" if insight_kind else ""
        triage_note = f"\n\nLLM triage verdict: {req.triage_verdict.upper()} ({conf_pct}% confidence{insight_note}; {actionability_pct}% actionable)"

    summary_tail = {
        "duplicate": "These files appear to be near-duplicates. Review and merge into one canonical location.",
        "reference": "One cluster intentionally references or extends the other. Verify cross-references are explicit and up-to-date.",
        "related": "Content is similar in topic but serves different purposes. Consider documenting the relationship to avoid future confusion.",
    }.get(verdict, "Review these files for duplication and consolidate where appropriate.")

    proposed_action = req.triage_action if req.triage_action else (
        f"Review and consolidate overlapping content between '{req.cluster_a}' and '{req.cluster_b}'. "
        f"Focus on the {len(req.top_pairs)} highest-similarity node pairs listed above."
    )

    confidence = round(req.triage_confidence or min(0.95, req.avg_similarity), 2)

    action_plan = _overlap_action_plan(req, verdict, proposed_action)
    try:
        scope_context = _build_scope_context(graph_summary())
    except Exception:
        scope_context = _build_scope_context({"nodes": [], "edges": [], "total_nodes": 0})

    rec: dict = {
        "id": str(uuid.uuid4()),
        "mode": "duplicates",
        "title": title,
        "summary": (
            f"Semantic analysis detected {req.edge_count} cross-repo similarity connections between "
            f"'{req.cluster_a}' and '{req.cluster_b}' (avg {round(req.avg_similarity * 100)}% similar).{triage_note}\n\n"
            f"{decision_impact + chr(10) + chr(10) if decision_impact else ''}"
            f"Top overlapping content:\n{pairs_text}\n\n"
            f"{summary_tail}"
        ),
        "evidence": [
            f"{p.get('label_a', '?')} ↔ {p.get('label_b', '?')} ({round(p.get('similarity', 0) * 100)}%)"
            for p in req.top_pairs[:5]
        ],
        "confidence": confidence,
        "risk": "low",
        "effort": effort,
        "proposed_action": proposed_action,
        "action_plan": action_plan,
        "overlap": {
            "cluster_a": req.cluster_a,
            "cluster_b": req.cluster_b,
            "edge_count": req.edge_count,
            "avg_similarity": req.avg_similarity,
            "top_pairs": req.top_pairs[:5],
        },
        "overlap_dossier": req.triage_result if isinstance(req.triage_result, dict) else None,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "model": "overlap-analysis" if not req.triage_verdict else f"overlap-analysis+triage",
        "created_by": getattr(request.state, "user_id", "local"),
        "context": scope_context,
    }
    _save_recommendation(rec)
    return _annotate_recommendation_scope(rec)


# ---------------------------------------------------------------------------
# Chunk Sixteen — Knowledge Base Cluster Selector
# ---------------------------------------------------------------------------

def _clear_summary_cache() -> None:
    global _summary_cache
    _summary_cache = {}


def _cluster_selection_deps() -> ClusterSelectionDeps:
    return ClusterSelectionDeps(
        load_cluster_selection=_load_cluster_selection,
        save_cluster_selection=_save_cluster_selection,
        load_graph=_load_graph,
        workspace_state=lambda: WORKSPACE_STATE,
        is_microsoft_authenticated=is_microsoft_authenticated,
        clear_summary_cache=_clear_summary_cache,
    )


(
    _cluster_selection_router,
    get_cluster_selection,
    update_cluster_selection,
) = create_cluster_selection_router(_cluster_selection_deps)
app.include_router(_cluster_selection_router)


# ---------------------------------------------------------------------------
# Chunk Fourteen — Cloud Knowledge Base Connectors
# ---------------------------------------------------------------------------

_SYNC_STATUS = SYNC_STATUS
_SYNC_LOCK = SYNC_LOCK
_CONNECTOR_CONFIG_PATH = CONNECTOR_CONFIG_PATH


def _connector_deps() -> ConnectorDeps:
    return ConnectorDeps(
        workspace_state=lambda: WORKSPACE_STATE,
        connectors_dir=lambda: CONNECTORS_DIR,
        graphs_dir=lambda: GRAPHS_DIR,
        settings_file=lambda: SETTINGS_FILE,
        graph_path=_graph_path,
        write_json_atomic=write_json_atomic,
        clear_graph_caches=_clear_graph_caches,
    )


def _clear_graph_caches() -> None:
    global _graph_cache, _summary_cache
    _graph_cache = None
    _summary_cache = {}


def _load_connector_config() -> dict:
    return _route_load_connector_config()


def _connector_status_path() -> Path:
    return _route_connector_status_path(_connector_deps())


def _load_sync_status() -> dict:
    return _route_load_sync_status(_connector_deps())


def _save_sync_status(status: dict) -> None:
    _route_save_sync_status(status, _connector_deps())


def _run_connector_sync(connector_id: str) -> None:
    _route_run_connector_sync(connector_id, _connector_deps())


def list_connectors() -> list[dict]:
    """List configured connectors with authentication and sync status."""
    return _route_list_connectors(_connector_deps())


def start_microsoft_auth() -> dict:
    """Initiate Microsoft device code flow. Returns user_code + verification_uri."""
    return _route_start_microsoft_auth(_connector_deps())


def poll_microsoft_auth() -> dict:
    """Poll for device code completion. Returns {status: pending|complete|error}."""
    return _route_poll_microsoft_auth(_connector_deps())


def sync_connector(connector_id: str) -> dict:
    """Trigger a background sync for the given connector."""
    return _route_sync_connector(connector_id, _connector_deps())


def connector_sync_status(connector_id: str) -> dict:
    """Return the last sync status for a connector."""
    return _route_connector_sync_status(connector_id, _connector_deps())


def revoke_connector_auth(connector_id: str) -> dict:
    """Revoke Microsoft token and clear cache. Re-auth required afterward."""
    return _route_revoke_connector_auth(connector_id, _connector_deps())


app.include_router(create_connectors_router(_connector_deps))


# ---------------------------------------------------------------------------
# Chunk Seventeen — In-Cockpit AI Assistant
# ---------------------------------------------------------------------------


def _chat_deps() -> ChatDeps:
    return ChatDeps(
        load_chat_config=_load_chat_config,
        chat_config_file=lambda: CHAT_CONFIG_FILE,
        chat_sessions_dir=lambda: CHAT_SESSIONS_DIR,
        write_json_atomic=write_json_atomic,
        prune_chat_sessions=_prune_chat_sessions,
        recommend_model_default=lambda: RECOMMEND_MODEL_DEFAULT,
        default_system_prompt=lambda: _CHAT_DEFAULT_SYSTEM_PROMPT,
        graph_summary=graph_summary,
        build_graph_context=_build_graph_context,
        ollama_url=lambda: os.environ.get("OLLAMA_URL", "http://localhost:11434"),
    )


(
    _chat_router,
    get_chat_config,
    update_chat_config,
    chat_stream,
) = create_chat_router(_chat_deps)
app.include_router(_chat_router)
