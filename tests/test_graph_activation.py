from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import main


FIXTURES = Path(__file__).parent / "fixtures"


def _write_graph(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((FIXTURES / "demo_graph_links.json").read_text())
    return path


def _patch_graph_state(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    state_dir = tmp_path / "state"
    graphs_dir = state_dir / "graphs"
    settings_file = state_dir / "settings.json"
    demo_graph = _write_graph(tmp_path / "demo" / "graph.json")
    uploaded_graph = _write_graph(graphs_dir / "uploaded graph.json")

    state_dir.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps({"graph_path": str(demo_graph)}))

    monkeypatch.setattr(main, "WORKSPACE_STATE", state_dir)
    monkeypatch.setattr(main, "GRAPHS_DIR", graphs_dir)
    monkeypatch.setattr(main, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(main, "_DEMO_GRAPH", str(demo_graph))
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(demo_graph))
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    return demo_graph, uploaded_graph, settings_file


def test_activate_demo_graph_by_listed_name(monkeypatch, tmp_path: Path) -> None:
    demo_graph, uploaded_graph, settings_file = _patch_graph_state(monkeypatch, tmp_path)
    client = TestClient(main.app)
    activate_uploaded = client.post(f"/graphs/{quote(uploaded_graph.name)}/activate")
    assert activate_uploaded.status_code == 200

    response = client.post(f"/graphs/{quote(demo_graph.name)}/activate")

    assert response.status_code == 200
    assert response.json() == {"activated": demo_graph.name, "path": str(demo_graph)}
    assert json.loads(settings_file.read_text())["graph_path"] == str(demo_graph)


def test_activate_uploaded_graph_by_listed_name(monkeypatch, tmp_path: Path) -> None:
    _, uploaded_graph, settings_file = _patch_graph_state(monkeypatch, tmp_path)
    client = TestClient(main.app)

    graphs = client.get("/graphs").json()
    assert any(g["name"] == uploaded_graph.name for g in graphs)

    response = client.post(f"/graphs/{quote(uploaded_graph.name)}/activate")

    assert response.status_code == 200
    assert response.json() == {"activated": uploaded_graph.name, "path": str(uploaded_graph)}
    assert json.loads(settings_file.read_text())["graph_path"] == str(uploaded_graph)


def test_activate_missing_graph_returns_useful_detail(monkeypatch, tmp_path: Path) -> None:
    _patch_graph_state(monkeypatch, tmp_path)
    client = TestClient(main.app)

    response = client.post("/graphs/missing.json/activate")

    assert response.status_code == 404
    assert response.json()["detail"] == "Graph 'missing.json' not found."


def test_activate_rejects_non_list_file_name(monkeypatch, tmp_path: Path) -> None:
    _patch_graph_state(monkeypatch, tmp_path)

    with pytest.raises(HTTPException) as exc:
        main.activate_graph("..")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Graph name must match a file name from the graph list."
