from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.services import graphify_service as service


def test_graphify_status_reports_missing_cli(monkeypatch) -> None:
    monkeypatch.setattr(service.shutil, "which", lambda _name: None)
    monkeypatch.setattr(service.sys, "executable", "/tmp/no-graphify-venv/python")

    status = service.get_graphify_status()

    assert status["available"] is False
    assert status["code"] == service.GRAPHIFY_MISSING


def test_run_graphify_ask_raises_structured_missing_error(monkeypatch) -> None:
    monkeypatch.setattr(service.shutil, "which", lambda _name: None)
    monkeypatch.setattr(service.sys, "executable", "/tmp/no-graphify-venv/python")

    with pytest.raises(service.GraphifyServiceError) as exc:
        service.run_graphify_ask(
            mode="query",
            question="What projects exist?",
            graph_path="graph.json",
        )

    assert exc.value.code == service.GRAPHIFY_MISSING
    assert exc.value.status_code == 503
    assert exc.value.to_detail()["code"] == service.GRAPHIFY_MISSING


def test_graphify_detection_checks_active_venv_sibling(monkeypatch, tmp_path: Path) -> None:
    graphify = tmp_path / "bin" / "graphify"
    graphify.parent.mkdir()
    graphify.write_text("#!/usr/bin/env bash\n")
    monkeypatch.setattr(service.shutil, "which", lambda _name: None)
    monkeypatch.setattr(service.sys, "executable", str(tmp_path / "bin" / "python"))

    assert service.is_graphify_available() is True


def test_run_graphify_update_maps_timeout(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(service.shutil, "which", lambda _name: "/usr/bin/graphify")

    def fake_run(*_args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=kwargs.get("args", "graphify"), timeout=300)

    monkeypatch.setattr(service.subprocess, "run", fake_run)

    with pytest.raises(service.GraphifyServiceError) as exc:
        service.run_graphify_update(tmp_path, cwd=tmp_path)

    assert exc.value.code == service.GRAPHIFY_TIMEOUT
    assert exc.value.status_code == 504


def test_run_graphify_update_maps_command_failure(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(service.shutil, "which", lambda _name: "/usr/bin/graphify")

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["graphify", "update"],
            returncode=2,
            stdout="",
            stderr="bad graph path",
        )

    monkeypatch.setattr(service.subprocess, "run", fake_run)

    with pytest.raises(service.GraphifyServiceError) as exc:
        service.run_graphify_update(tmp_path, cwd=tmp_path)

    assert exc.value.code == service.GRAPHIFY_COMMAND_FAILED
    assert exc.value.to_detail()["stderr"] == "bad graph path"


def test_ask_endpoint_returns_structured_graphify_error(monkeypatch, tmp_path: Path) -> None:
    graph = tmp_path / "graph.json"
    graph.write_text('{"nodes": [], "links": []}')
    settings = tmp_path / "settings.json"
    settings.write_text(f'{{"graph_path": "{graph}"}}')
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})

    def fake_run_graphify_ask(**_kwargs):
        raise service.GraphifyServiceError(
            service.GRAPHIFY_MISSING,
            "Graphify CLI is not installed or is not on PATH.",
            status_code=503,
        )

    monkeypatch.setattr(main, "run_graphify_ask", fake_run_graphify_ask)
    client = TestClient(main.app)

    response = client.post("/ask", json={"question": "What projects exist?", "mode": "query"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == service.GRAPHIFY_MISSING


def test_settings_includes_graphify_status(monkeypatch, tmp_path: Path) -> None:
    graph = tmp_path / "graph.json"
    graph.write_text('{"nodes": [], "links": []}')
    settings = tmp_path / "settings.json"
    settings.write_text(f'{{"graph_path": "{graph}"}}')
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(
        main,
        "get_graphify_status",
        lambda include_version=True: {
            "available": False,
            "version": None,
            "code": service.GRAPHIFY_MISSING,
            "message": "Graphify CLI is not installed or is not on PATH.",
        },
    )

    settings_response = main.get_settings()

    assert settings_response["graphify"]["available"] is False
    assert settings_response["graphify"]["code"] == service.GRAPHIFY_MISSING


def test_rebuild_rejects_missing_graphify_before_background_thread(monkeypatch) -> None:
    monkeypatch.setattr(main, "_REBUILD_STATUS", {"status": "idle", "last_run": None})
    monkeypatch.setattr(
        main,
        "get_graphify_status",
        lambda include_version=False: {
            "available": False,
            "version": None,
            "code": service.GRAPHIFY_MISSING,
            "message": "Graphify CLI is not installed or is not on PATH.",
        },
    )
    client = TestClient(main.app)

    response = client.post("/graph/rebuild")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == service.GRAPHIFY_MISSING
