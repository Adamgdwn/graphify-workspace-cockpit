from __future__ import annotations

import importlib

from backend import config


def test_relative_env_paths_resolve_from_repo_root(monkeypatch) -> None:
    monkeypatch.setenv("STATE_DIR", "workspace/state")
    monkeypatch.setenv("GRAPH_PATH", "workspace/demo/graph.json")

    reloaded = importlib.reload(config)
    try:
        assert reloaded.WORKSPACE_STATE == reloaded.REPO_ROOT / "workspace" / "state"
        assert reloaded.DEFAULT_GRAPH == str(
            reloaded.REPO_ROOT / "workspace" / "demo" / "graph.json"
        )
    finally:
        monkeypatch.delenv("STATE_DIR", raising=False)
        monkeypatch.delenv("GRAPH_PATH", raising=False)
        importlib.reload(config)


def test_default_graph_is_blank_when_graph_path_is_unset(monkeypatch) -> None:
    monkeypatch.delenv("GRAPH_PATH", raising=False)

    reloaded = importlib.reload(config)
    try:
        assert reloaded.DEFAULT_GRAPH == ""
    finally:
        importlib.reload(config)
