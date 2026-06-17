from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend import main
from backend.services import graphify_service


FIXTURES = Path(__file__).parent / "fixtures"


def _patch_runtime_graph(monkeypatch, tmp_path: Path, *, missing: bool = False) -> Path:
    state_dir = tmp_path / "state"
    graph_path = tmp_path / "demo" / "graph.json"
    active_path = tmp_path / "demo" / "missing.json" if missing else graph_path
    settings_file = state_dir / "settings.json"

    graph_path.parent.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    graph_path.write_bytes((FIXTURES / "demo_graph_links.json").read_bytes())
    settings_file.write_text(json.dumps({"graph_path": str(active_path)}))

    monkeypatch.setattr(main, "WORKSPACE_STATE", state_dir)
    monkeypatch.setattr(main, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph_path))
    monkeypatch.setattr(main, "_DEMO_GRAPH", str(graph_path))
    monkeypatch.setattr(main, "API_KEY", "")
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    return graph_path


def _patch_ready_dependencies(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "get_graphify_status",
        lambda include_version=False: {
            "available": True,
            "version": "0.8.40" if include_version else None,
            "code": None,
            "message": None,
        },
    )
    monkeypatch.setattr(
        main,
        "ollama_status",
        lambda: {
            "connected": True,
            "models": ["nomic-embed-text:latest"],
            "url": "http://localhost:11434",
        },
    )
    monkeypatch.setattr(
        main,
        "_storage_status",
        lambda force_check=False: {
            "backend": "file",
            "ready": True,
            "schema_checked": False,
            "required_migration": None,
            "required_columns": {},
            "missing_or_unverified_columns": {},
            "warning": None,
            "errors": [],
        },
    )
    monkeypatch.setattr(
        main,
        "_connector_readiness",
        lambda: {
            "items": [],
            "configured_count": 0,
            "authenticated_count": 0,
            "syncing_count": 0,
            "error_count": 0,
            "error": None,
        },
    )


def test_runtime_status_ready_reports_core_runtime(monkeypatch, tmp_path: Path) -> None:
    _patch_runtime_graph(monkeypatch, tmp_path)
    _patch_ready_dependencies(monkeypatch)
    client = TestClient(main.app)

    response = client.get("/runtime/status")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ready"
    assert body["backend"] == {"online": True, "version": "0.1.0"}
    assert body["graph"]["valid"] is True
    assert body["graph"]["node_count"] == 2
    assert body["graph"]["link_count"] == 1
    assert body["graphify"]["available"] is True
    assert body["ollama"]["connected"] is True
    assert body["auth"]["api_key_required"] is False
    assert body["warnings"] == []
    assert body["next_best_action"] == {"label": "Open graph map", "destination": "map"}


def test_runtime_status_marks_missing_active_graph_not_ready(monkeypatch, tmp_path: Path) -> None:
    _patch_runtime_graph(monkeypatch, tmp_path, missing=True)
    _patch_ready_dependencies(monkeypatch)
    client = TestClient(main.app)

    response = client.get("/runtime/status")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "not_ready"
    assert body["graph"]["valid"] is False
    assert body["graph"]["exists"] is False
    assert body["warnings"][0]["code"] == "GRAPH_INVALID"
    assert body["warnings"][0]["severity"] == "error"
    assert body["next_best_action"]["destination"] == "settings"


def test_runtime_status_marks_missing_optional_runtime_partial(monkeypatch, tmp_path: Path) -> None:
    _patch_runtime_graph(monkeypatch, tmp_path)
    _patch_ready_dependencies(monkeypatch)
    monkeypatch.setattr(
        main,
        "get_graphify_status",
        lambda include_version=False: {
            "available": False,
            "version": None,
            "code": graphify_service.GRAPHIFY_MISSING,
            "message": "Graphify CLI is not installed or is not on PATH.",
        },
    )
    monkeypatch.setattr(
        main,
        "ollama_status",
        lambda: {"connected": False, "models": [], "url": "http://localhost:11434"},
    )
    monkeypatch.setattr(
        main,
        "_connector_readiness",
        lambda: {
            "items": [{
                "id": "sharepoint",
                "display_name": "SharePoint",
                "configured": True,
                "authenticated": False,
                "sync_status": "never_synced",
                "sync_error": None,
            }],
            "configured_count": 1,
            "authenticated_count": 0,
            "syncing_count": 0,
            "error_count": 0,
            "error": None,
        },
    )
    client = TestClient(main.app)

    response = client.get("/runtime/status")

    assert response.status_code == 200
    body = response.json()
    codes = {warning["code"] for warning in body["warnings"]}
    assert body["state"] == "partial"
    assert graphify_service.GRAPHIFY_MISSING in codes
    assert "OLLAMA_UNAVAILABLE" in codes
    assert "CONNECTOR_AUTH_REQUIRED" in codes
    assert body["next_best_action"]["label"] == "Review Graphify setup"


def test_runtime_status_reports_auth_requirement_after_authorized_request(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_runtime_graph(monkeypatch, tmp_path)
    _patch_ready_dependencies(monkeypatch)
    monkeypatch.setattr(main, "API_KEY", "test-secret")
    client = TestClient(main.app)

    missing = client.get("/runtime/status")
    authorized = client.get("/runtime/status", headers={"X-API-Key": "test-secret"})

    assert missing.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json()["auth"]["api_key_required"] is True
