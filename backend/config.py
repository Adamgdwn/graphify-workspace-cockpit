"""Backend runtime configuration for Graphify Workspace Cockpit."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

STATE_DIR_ENV = os.environ.get("STATE_DIR", "")
WORKSPACE_STATE = (
    Path(STATE_DIR_ENV)
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
SEMANTIC_EDGES_FILE = WORKSPACE_STATE / "semantic-edges.json"
OVERLAP_STATUS_FILE = WORKSPACE_STATE / "overlap-status.json"

CHAT_DEFAULT_SYSTEM_PROMPT = (
    "You are an assistant with access to the user's knowledge graph. "
    "Answer based on the provided graph context. "
    "If the answer is not in the graph, say so."
)

USERS_FILE = REPO_ROOT / "config" / "users.json"
DEMO_GRAPH = str(REPO_ROOT / "workspace" / "demo" / "graph.json")
DEFAULT_GRAPH = os.environ.get("GRAPH_PATH", DEMO_GRAPH)
API_KEY = os.environ.get("API_KEY", "")
GRAPH_UPLOAD_MAX_BYTES = 10 * 1024 * 1024
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "file")

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
