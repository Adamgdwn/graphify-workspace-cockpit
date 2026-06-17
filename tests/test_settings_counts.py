from __future__ import annotations

import json
from pathlib import Path

from backend import main


FIXTURES = Path(__file__).parent / "fixtures"


def _write_active_graph(tmp_path: Path, fixture_name: str) -> Path:
    graph_path = tmp_path / fixture_name
    graph_path.write_text((FIXTURES / fixture_name).read_text())
    return graph_path


def _patch_graph_state(monkeypatch, tmp_path: Path, graph_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"graph_path": str(graph_path)}))
    monkeypatch.setattr(main, "WORKSPACE_STATE", tmp_path)
    monkeypatch.setattr(main, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph_path))
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})


def test_settings_counts_links_graph_relationships(monkeypatch, tmp_path: Path) -> None:
    graph_path = _write_active_graph(tmp_path, "demo_graph_links.json")
    _patch_graph_state(monkeypatch, tmp_path, graph_path)

    settings = main.get_settings()

    assert settings["node_count"] == 2
    assert settings["edge_count"] == 1


def test_settings_counts_legacy_edges_graph_relationships(monkeypatch, tmp_path: Path) -> None:
    graph_path = _write_active_graph(tmp_path, "demo_graph_edges.json")
    _patch_graph_state(monkeypatch, tmp_path, graph_path)

    settings = main.get_settings()

    assert settings["node_count"] == 2
    assert settings["edge_count"] == 1
