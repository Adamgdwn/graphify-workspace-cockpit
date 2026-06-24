"""Backend runtime configuration for Graphify Workspace Cockpit."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def repo_relative_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


STATE_DIR_ENV = os.environ.get("STATE_DIR", "")
WORKSPACE_STATE = (
    repo_relative_path(STATE_DIR_ENV)
    if STATE_DIR_ENV
    else REPO_ROOT / "workspace" / "state"
)

SESSIONS_DIR = WORKSPACE_STATE / "sessions"
SETTINGS_FILE = WORKSPACE_STATE / "settings.json"
DECISIONS_FILE = WORKSPACE_STATE / "decisions.json"
GRAPHS_DIR = WORKSPACE_STATE / "graphs"
DEVICES_FILE = WORKSPACE_STATE / "devices.json"
CONNECTORS_DIR = WORKSPACE_STATE / "connectors"
CLUSTER_SELECTION_FILE = WORKSPACE_STATE / "cluster-selection.json"
CHAT_CONFIG_FILE = WORKSPACE_STATE / "chat-config.json"
CHAT_SESSIONS_DIR = WORKSPACE_STATE / "chat-sessions"
SCAN_DIRS_FILE = WORKSPACE_STATE / "scan-dirs.json"
WORKSPACE_SCOPE_FILE = WORKSPACE_STATE / "workspace-scope.json"
SEMANTIC_EDGES_FILE = WORKSPACE_STATE / "semantic-edges.json"
OVERLAP_STATUS_FILE = WORKSPACE_STATE / "overlap-status.json"

CHAT_DEFAULT_SYSTEM_PROMPT = (
    "You are an assistant with access to the user's knowledge graph. "
    "Answer based on the provided graph context. "
    "If the answer is not in the graph, say so. "
    "When the user asks about semantic overlap or connections, give a concise action queue: "
    "what to merge or consolidate, what needs an explicit reference or bridge, what should be compared, "
    "and what can be dismissed as low-value."
)

USERS_FILE = REPO_ROOT / "config" / "users.json"
DEMO_GRAPH = str(REPO_ROOT / "workspace" / "demo" / "graph.json")
GRAPH_PATH_ENV = os.environ.get("GRAPH_PATH", "")
DEFAULT_GRAPH = str(repo_relative_path(GRAPH_PATH_ENV)) if GRAPH_PATH_ENV else ""
API_KEY = os.environ.get("API_KEY", "")
GRAPH_UPLOAD_MAX_BYTES = 10 * 1024 * 1024
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "file")

RECOMMEND_MODEL_DEFAULT = (
    os.environ.get("RECOMMEND_MODEL_DEFAULT")
    or os.environ.get("OLLAMA_MODEL")
    or "local-balanced:latest"
).strip() or "local-balanced:latest"
SEMANTIC_MODEL_DEFAULT = (
    os.environ.get("SEMANTIC_MODEL_DEFAULT") or "nomic-embed-text:latest"
).strip() or "nomic-embed-text:latest"

GRAPH_ESCALATION_ENABLED = env_bool("GRAPH_ESCALATION_ENABLED", False)
GRAPH_ESCALATION_BACKEND = os.environ.get("GRAPH_ESCALATION_BACKEND", "").strip()
GRAPH_ESCALATION_MODEL = os.environ.get("GRAPH_ESCALATION_MODEL", "").strip()
GRAPH_ESCALATION_MODE = os.environ.get("GRAPH_ESCALATION_MODE", "deep").strip()
GRAPH_ESCALATION_FILE_THRESHOLD = env_int("GRAPH_ESCALATION_FILE_THRESHOLD", 1500)
GRAPH_ESCALATION_ROOT_THRESHOLD = env_int("GRAPH_ESCALATION_ROOT_THRESHOLD", 2)
GRAPH_ESCALATION_DECIDER_MODEL = (
    os.environ.get("GRAPH_ESCALATION_DECIDER_MODEL") or RECOMMEND_MODEL_DEFAULT
).strip() or RECOMMEND_MODEL_DEFAULT
GRAPH_ESCALATION_DECIDER_TIMEOUT = env_int("GRAPH_ESCALATION_DECIDER_TIMEOUT", 12)
GRAPH_ESCALATION_TIMEOUT = env_int("GRAPH_ESCALATION_TIMEOUT", 1800)
GRAPH_ESCALATION_API_TIMEOUT = env_int("GRAPH_ESCALATION_API_TIMEOUT", 600)
GRAPH_ESCALATION_MAX_CONCURRENCY = env_int("GRAPH_ESCALATION_MAX_CONCURRENCY", 2)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

SECRET_PATH_MARKERS = (
    ".env",
    ".pem",
    ".key",
    "secret",
    "credential",
    "password",
    "private-key",
    "api-key",
    "api_key",
    "access_token",
    "refresh_token",
    "token",
    "users.json",
)
