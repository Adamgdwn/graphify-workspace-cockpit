from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import main


FIXTURES = Path(__file__).parent / "fixtures"


def _valid_graph() -> bytes:
    return (FIXTURES / "demo_graph_edges.json").read_bytes()


def _patch_graph_state(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    state_dir = tmp_path / "state"
    graphs_dir = state_dir / "graphs"
    settings_file = state_dir / "settings.json"
    demo_graph = tmp_path / "demo" / "graph.json"
    demo_graph.parent.mkdir(parents=True, exist_ok=True)
    demo_graph.write_bytes((FIXTURES / "demo_graph_links.json").read_bytes())
    state_dir.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps({"graph_path": str(demo_graph)}))

    monkeypatch.setattr(main, "WORKSPACE_STATE", state_dir)
    monkeypatch.setattr(main, "GRAPHS_DIR", graphs_dir)
    monkeypatch.setattr(main, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(main, "_DEMO_GRAPH", str(demo_graph))
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(demo_graph))
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    return demo_graph, graphs_dir, settings_file


def _upload(client: TestClient, filename: str, content: bytes):
    return client.post(
        "/graph/upload",
        files={"file": (filename, content, "application/json")},
    )


def _active_graph(settings_file: Path) -> str:
    return json.loads(settings_file.read_text())["graph_path"]


def test_upload_valid_graph_normalizes_writes_and_activates(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _, graphs_dir, settings_file = _patch_graph_state(monkeypatch, tmp_path)
    client = TestClient(main.app)

    response = _upload(client, "uploaded graph.json", _valid_graph())

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "uploaded graph.json"
    assert body["node_count"] == 2
    assert body["link_count"] == 1
    assert body["active"] is True

    saved_path = graphs_dir / "uploaded graph.json"
    assert _active_graph(settings_file) == str(saved_path)
    saved_graph = json.loads(saved_path.read_text())
    assert "edges" not in saved_graph
    assert saved_graph["links"][0]["relation"] == "uses"


@pytest.mark.parametrize(
    ("filename", "content", "status_code", "detail"),
    [
        ("../escape.json", _valid_graph(), 400, "path separators"),
        ("..\\escape.json", _valid_graph(), 400, "path separators"),
        ("graph.txt", _valid_graph(), 400, ".json file"),
        ("broken.json", b"{not-json", 422, "Invalid JSON"),
        (
            "missing-nodes.json",
            json.dumps({"links": []}).encode(),
            422,
            "nodes array",
        ),
        (
            "bad-link.json",
            json.dumps({"nodes": [{"id": "a"}], "links": [{"source": "a"}]}).encode(),
            422,
            "source and target",
        ),
        (
            "unknown-link-target.json",
            json.dumps(
                {
                    "nodes": [{"id": "a"}],
                    "links": [{"source": "a", "target": "missing"}],
                }
            ).encode(),
            422,
            "reference existing nodes",
        ),
    ],
)
def test_upload_rejects_invalid_graphs_without_activating(
    monkeypatch,
    tmp_path: Path,
    filename: str,
    content: bytes,
    status_code: int,
    detail: str,
) -> None:
    demo_graph, graphs_dir, settings_file = _patch_graph_state(monkeypatch, tmp_path)
    client = TestClient(main.app)

    response = _upload(client, filename, content)

    assert response.status_code == status_code
    assert detail in response.json()["detail"]
    assert _active_graph(settings_file) == str(demo_graph)
    assert list(graphs_dir.glob("*.json")) == []


def test_upload_rejects_empty_filename_before_storage() -> None:
    with pytest.raises(HTTPException) as exc:
        main._safe_graph_upload_name("")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Graph filename is required."


def test_upload_rejects_oversized_graph_without_activating(
    monkeypatch,
    tmp_path: Path,
) -> None:
    demo_graph, graphs_dir, settings_file = _patch_graph_state(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "GRAPH_UPLOAD_MAX_BYTES", 16)
    client = TestClient(main.app)

    response = _upload(client, "too-large.json", _valid_graph())

    assert response.status_code == 413
    assert "exceeds" in response.json()["detail"]
    assert _active_graph(settings_file) == str(demo_graph)
    assert list(graphs_dir.glob("*.json")) == []


def test_activate_rejects_invalid_existing_graph_without_switching(
    monkeypatch,
    tmp_path: Path,
) -> None:
    demo_graph, graphs_dir, settings_file = _patch_graph_state(monkeypatch, tmp_path)
    graphs_dir.mkdir(parents=True, exist_ok=True)
    invalid_graph = graphs_dir / "invalid.json"
    invalid_graph.write_text(json.dumps({"nodes": [{"id": "a"}], "links": [{"source": "a"}]}))
    client = TestClient(main.app)

    response = client.post("/graphs/invalid.json/activate")

    assert response.status_code == 422
    assert "Invalid graph" in response.json()["detail"]
    assert _active_graph(settings_file) == str(demo_graph)
