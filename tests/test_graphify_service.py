from __future__ import annotations

import json
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


def test_rebuild_without_workspace_scope_keeps_local_repo_fallback(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(main, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", tmp_path / "state" / "workspace-scope.json")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "state" / "scan-dirs.json")
    monkeypatch.setattr(main, "SETTINGS_FILE", tmp_path / "state" / "settings.json")
    monkeypatch.setattr(main, "_REBUILD_STATUS", {"status": "idle", "last_run": None})

    calls: list[tuple[str, str]] = []

    def fake_run_graphify_update(target, *, cwd=None, timeout=300):
        calls.append((str(target), str(cwd)))
        return service.GraphifyCommandResult(["graphify", "update"], 0, "", "")

    monkeypatch.setattr(main, "run_graphify_update", fake_run_graphify_update)

    main._run_rebuild()

    assert calls == [(".", str(repo_root))]
    assert main._REBUILD_STATUS["status"] == "complete"


def test_rebuild_with_workspace_scope_scans_and_activates_filtered_graph(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    state_dir = tmp_path / "state"
    workspace_root = tmp_path / "code"
    app = workspace_root / "app"
    excluded = workspace_root / "ignored"
    app.mkdir(parents=True)
    excluded.mkdir(parents=True)
    (app / "src").mkdir()
    (app / "graphify-out" / "cache").mkdir(parents=True)
    (app / ".env.local").write_text("SECRET=not returned")
    (app / "src" / "main.py").write_text("print('ok')")
    (app / "graphify-out" / "cache" / "stale.json").write_text("{}")
    (excluded / "skip.py").write_text("print('skip')")
    repo_root.mkdir()
    state_dir.mkdir()

    scope_file = state_dir / "workspace-scope.json"
    settings_file = state_dir / "settings.json"
    semantic_file = state_dir / "semantic-edges.json"
    semantic_file.write_text('{"edges": [{"source": "old", "target": "graph"}]}')
    scope_file.write_text(json.dumps({
        "root": str(workspace_root),
        "profile_name": "Scoped Test",
        "included_paths": [str(app), str(excluded)],
        "excluded_paths": [str(excluded)],
    }))

    monkeypatch.setattr(main, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", scope_file)
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", state_dir / "scan-dirs.json")
    monkeypatch.setattr(main, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(main, "SEMANTIC_EDGES_FILE", semantic_file)
    monkeypatch.setattr(main, "_graph_cache", {"stale": True})
    monkeypatch.setattr(main, "_summary_cache", {"stale": {}})
    monkeypatch.setattr(main, "_REBUILD_STATUS", {"status": "idle", "last_run": None})

    calls: list[tuple[str, str]] = []

    def fake_run_graphify_update(target, *, cwd=None, timeout=300):
        scan_root = Path(cwd)
        calls.append((str(target), str(scan_root)))
        graph_path = scan_root / "graphify-out" / "graph.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(json.dumps({
            "nodes": [
                {"id": "keep", "label": "main.py", "source_file": "src/main.py"},
                {"id": "generated", "label": "stale.json", "source_file": "graphify-out/cache/stale.json"},
                {"id": "secret", "label": ".env.local", "source_file": ".env.local"},
            ],
            "links": [
                {"source": "keep", "target": "generated", "relation": "related"},
                {"source": "keep", "target": "secret", "relation": "related"},
            ],
        }))
        return service.GraphifyCommandResult(["graphify", "update"], 0, "", "")

    monkeypatch.setattr(main, "run_graphify_update", fake_run_graphify_update)

    main._run_rebuild()

    assert calls == [(str(app), str(app))]
    active_path = json.loads(settings_file.read_text())["graph_path"]
    assert active_path == str(repo_root / "graphify-out" / "merged-graph.json")
    active_graph = json.loads(Path(active_path).read_text())
    assert [node["id"] for node in active_graph["nodes"]] == ["keep"]
    assert active_graph["links"] == []
    assert active_graph["_meta"]["workspace_scope"]["profile_name"] == "Scoped Test"
    assert active_graph["_meta"]["workspace_scope"]["scanned_root_count"] == 1
    assert active_graph["nodes"][0]["source_root"] == str(app)
    assert active_graph["nodes"][0]["scope_profile"] == "Scoped Test"
    assert "not returned" not in Path(active_path).read_text()
    assert "graphify-out/cache" not in Path(active_path).read_text()
    assert not semantic_file.exists()
    assert main._graph_cache is None
    assert main._summary_cache == {}
    assert main._REBUILD_STATUS["status"] == "complete"


def test_scoped_rebuild_repairs_duplicate_graphify_node_ids(tmp_path: Path) -> None:
    workspace_root = tmp_path / "code"
    app = workspace_root / "app"
    app.mkdir(parents=True)
    (app / "README.md").write_text("# App")
    (app / "runtime.py").write_text("class RuntimeError(Exception): pass")
    (app / "worker.py").write_text("def worker(): pass")

    source_graph = app / "graphify-out" / "graph.json"
    source_graph.parent.mkdir(parents=True)
    source_graph.write_text(json.dumps({
        "nodes": [
            {"id": "runtimeerror", "label": "RuntimeError", "source_file": "README.md"},
            {"id": "runtimeerror", "label": "RuntimeError", "source_file": "runtime.py"},
            {"id": "worker", "label": "worker", "source_file": "worker.py"},
        ],
        "links": [{"source": "runtimeerror", "target": "worker", "relation": "mentions"}],
    }))
    profile = {
        "root": str(workspace_root),
        "profile_name": "Duplicate Repair",
        "included_paths": [str(app)],
    }
    destination = tmp_path / "scoped" / "graph.json"

    main._filtered_scoped_graph_path(
        source_graph_path=source_graph,
        destination_path=destination,
        profile=profile,
        scan_root=app,
    )

    graph = json.loads(destination.read_text())
    ids = [node["id"] for node in graph["nodes"]]
    duplicate = next(node for node in graph["nodes"] if node["source_file"] == "runtime.py")

    assert ids == ["runtimeerror", "runtimeerror__duplicate_2", "worker"]
    assert duplicate["original_graphify_id"] == "runtimeerror"
    assert graph["links"] == [{"source": "runtimeerror", "target": "worker", "relation": "mentions"}]


def test_merge_graph_outputs_repairs_cross_root_duplicate_ids(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    out_path = tmp_path / "merged.json"
    first.write_text(json.dumps({
        "nodes": [
            {"id": "main", "label": "main.py", "source_root": "/workspace/app-a"},
            {"id": "config", "label": "config.py", "source_root": "/workspace/app-a"},
        ],
        "links": [{"source": "main", "target": "config", "relation": "imports"}],
    }))
    second.write_text(json.dumps({
        "nodes": [
            {"id": "main", "label": "main.py", "source_root": "/workspace/app-b"},
            {"id": "worker", "label": "worker.py", "source_root": "/workspace/app-b"},
        ],
        "links": [{"source": "main", "target": "worker", "relation": "imports"}],
    }))

    main._merge_graph_outputs([str(first), str(second)], out_path)

    merged = json.loads(out_path.read_text())
    assert [node["id"] for node in merged["nodes"]] == [
        "main",
        "config",
        "main__duplicate_2",
        "worker",
    ]
    duplicate = next(node for node in merged["nodes"] if node["source_root"] == "/workspace/app-b")
    assert duplicate["original_graphify_id"] == "main"
    assert merged["links"] == [
        {"source": "main", "target": "config", "relation": "imports"},
        {"source": "main__duplicate_2", "target": "worker", "relation": "imports"},
    ]


def test_graph_full_hides_low_signal_nodes_by_default(monkeypatch, tmp_path: Path) -> None:
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({
        "_meta": {"workspace_scope": {"removed_node_count": 4}},
        "nodes": [
            {"id": "readme", "label": "README", "source_file": "README.md", "file_type": "document"},
            {"id": "worker", "label": "worker", "source_file": "src/worker.py"},
            {"id": "generated", "label": "next-env", "source_file": "next-env.d.ts"},
        ],
        "links": [
            {"source": "readme", "target": "worker", "relation": "mentions"},
            {"source": "worker", "target": "generated", "relation": "related"},
        ],
    }))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"graph_path": str(graph)}))
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", tmp_path / "missing-scope.json")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "missing-scan-dirs.json")
    monkeypatch.setattr(main, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "API_KEY", "")
    client = TestClient(main.app)

    default_response = client.get("/graph/full")

    assert default_response.status_code == 200
    default_body = default_response.json()
    assert [node["id"] for node in default_body["nodes"]] == ["readme"]
    assert default_body["signal_counts"]["important"] == 1
    assert default_body["signal_counts"]["evidence"] == 1
    assert default_body["signal_counts"]["hidden"] == 1
    assert default_body["hidden_node_count"] == 2
    assert default_body["excluded_node_count"] == 4
    assert default_body["edges"] == []

    expanded_response = client.get("/graph/full?include_low_signal=true")

    assert expanded_response.status_code == 200
    expanded_body = expanded_response.json()
    assert {node["id"] for node in expanded_body["nodes"]} == {"readme", "worker", "generated"}
    assert expanded_body["hidden_node_count"] == 0
    assert expanded_body["include_low_signal"] is True


def test_graph_full_rejects_oversized_default_payload(monkeypatch, tmp_path: Path) -> None:
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({
        "nodes": [
            {
                "id": f"readme-{index}",
                "label": f"main {index}",
                "source_file": f"src/main-{index}.py",
                "file_type": "code",
            }
            for index in range(101)
        ],
        "links": [],
    }))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"graph_path": str(graph)}))
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", tmp_path / "missing-scope.json")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "missing-scan-dirs.json")
    monkeypatch.setattr(main, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "API_KEY", "")
    client = TestClient(main.app)

    response = client.get("/graph/full?max_nodes=100")

    assert response.status_code == 413
    detail = response.json()["detail"]
    assert detail["code"] == "GRAPH_FULL_TOO_LARGE"
    assert detail["visible_node_count"] == 101
    assert detail["max_nodes"] == 100


def test_graph_summary_uses_workspace_projects_then_modules(monkeypatch, tmp_path: Path) -> None:
    app_a = tmp_path / "code" / "app-a"
    app_b = tmp_path / "code" / "app-b"
    graph = tmp_path / "workspace-graph.json"
    graph.write_text(json.dumps({
        "nodes": [
            {
                "id": "a-readme",
                "label": "README",
                "source_file": "README.md",
                "file_type": "document",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
            },
            {
                "id": "a-route",
                "label": "routes",
                "source_file": "src/routes.py",
                "file_type": "code",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
            },
            {
                "id": "b-readme",
                "label": "README",
                "source_file": "README.md",
                "file_type": "document",
                "source_root": str(app_b),
                "source_root_name": "app-b",
                "repo_project_name": "app-b",
            },
            {
                "id": "b-config",
                "label": "config",
                "source_file": "backend/config.py",
                "file_type": "code",
                "source_root": str(app_b),
                "source_root_name": "app-b",
                "repo_project_name": "app-b",
            },
        ],
        "links": [
            {"source": "a-readme", "target": "b-readme", "relation": "references"},
            {"source": "a-route", "target": "b-config", "relation": "imports"},
        ],
    }))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"graph_path": str(graph)}))
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", tmp_path / "missing-scope.json")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "missing-scan-dirs.json")
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "API_KEY", "")
    client = TestClient(main.app)

    overview = client.get("/graph/summary").json()

    assert overview["level"] == "top"
    assert {node["label"] for node in overview["nodes"]} == {"app-a", "app-b"}
    assert {node["group_type"] for node in overview["nodes"]} == {"repo"}
    assert {(edge["source"], edge["target"]) for edge in overview["edges"]} == {
        (str(app_a), str(app_b)),
    }

    app_a_detail = client.get(
        "/graph/summary",
        params={"project": str(app_a), "min_weight": 1},
    ).json()

    assert app_a_detail["level"] == "project"
    assert app_a_detail["project"] == str(app_a)
    assert {node["label"] for node in app_a_detail["nodes"]} == {"(root)", "src"}
    assert {node["group_type"] for node in app_a_detail["nodes"]} == {"module"}


def test_graph_full_clusters_nodes_by_workspace_project(monkeypatch, tmp_path: Path) -> None:
    app_a = tmp_path / "code" / "app-a"
    app_b = tmp_path / "code" / "app-b"
    graph = tmp_path / "workspace-graph.json"
    graph.write_text(json.dumps({
        "nodes": [
            {
                "id": "a-readme",
                "label": "README",
                "source_file": "README.md",
                "file_type": "document",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
            },
            {
                "id": "b-readme",
                "label": "README",
                "source_file": "README.md",
                "file_type": "document",
                "source_root": str(app_b),
                "source_root_name": "app-b",
                "repo_project_name": "app-b",
            },
        ],
        "links": [{"source": "a-readme", "target": "b-readme", "relation": "references"}],
    }))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"graph_path": str(graph)}))
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", tmp_path / "missing-scope.json")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "missing-scan-dirs.json")
    monkeypatch.setattr(main, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "API_KEY", "")
    client = TestClient(main.app)

    body = client.get("/graph/full").json()

    assert {node["cluster"] for node in body["nodes"]} == {"app-a", "app-b"}
    assert {node["repo"] for node in body["nodes"]} == {"app-a", "app-b"}
    assert {node["container"] for node in body["nodes"]} == {"root"}


def test_ask_evidence_is_enriched_from_scoped_visible_graph(monkeypatch, tmp_path: Path) -> None:
    app_a = tmp_path / "code" / "app-a"
    app_a.mkdir(parents=True)
    graph = tmp_path / "workspace-graph.json"
    graph.write_text(json.dumps({
        "nodes": [
            {
                "id": "readme",
                "label": "README",
                "source_file": "README.md",
                "file_type": "document",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
            },
            {
                "id": "lock",
                "label": "Lockfile",
                "source_file": "package-lock.json",
                "file_type": "document",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
            },
        ],
        "links": [{"source": "readme", "target": "lock", "relation": "mentions"}],
    }))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"graph_path": str(graph)}))
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", tmp_path / "missing-scope.json")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "missing-scan-dirs.json")
    monkeypatch.setattr(main, "CLUSTER_SELECTION_FILE", tmp_path / "missing-clusters.json")
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "API_KEY", "")

    def fake_run_graphify_ask(**_kwargs):
        return service.GraphifyCommandResult(
            ["graphify", "query"],
            0,
            "\n".join([
                "Found scoped context",
                "NODE README [src=README.md loc=L1 community=legacy]",
                "NODE Lockfile [src=package-lock.json loc=L1 community=legacy]",
            ]),
            "",
        )

    monkeypatch.setattr(main, "run_graphify_ask", fake_run_graphify_ask)
    client = TestClient(main.app)

    response = client.post("/ask", json={"question": "What matters?", "mode": "query"})

    assert response.status_code == 200
    evidence = response.json()["evidence"]
    assert [item["label"] for item in evidence] == ["README"]
    assert evidence[0]["repo"] == "app-a"
    assert evidence[0]["community"] == "app-a"
    assert evidence[0]["signal_tier"] == "important"


def test_graph_context_describes_scope_exclusions_and_token_savings(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "code"
    app_a = workspace / "app-a"
    excluded = workspace / "archive"
    app_a.mkdir(parents=True)
    excluded.mkdir()
    graph = tmp_path / "workspace-graph.json"
    graph.write_text(json.dumps({
        "nodes": [
            {
                "id": "readme",
                "label": "README",
                "source_file": "README.md",
                "file_type": "document",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
            },
            {
                "id": "lock",
                "label": "Lockfile",
                "source_file": "package-lock.json",
                "file_type": "document",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
            },
        ],
        "links": [{"source": "readme", "target": "lock", "relation": "mentions"}],
    }))
    scope_file = tmp_path / "workspace-scope.json"
    scope_file.write_text(json.dumps({
        "root": str(workspace),
        "profile_name": "Adam Code",
        "included_paths": [str(app_a)],
        "excluded_paths": [str(excluded)],
    }))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"graph_path": str(graph)}))
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", scope_file)
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "missing-scan-dirs.json")
    monkeypatch.setattr(main, "CLUSTER_SELECTION_FILE", tmp_path / "missing-clusters.json")
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "API_KEY", "")

    summary = main.graph_summary(min_weight=1)
    context = main._build_graph_context(summary)
    packet = main._build_scope_context(summary)

    assert "Workspace scope: Adam Code" in context
    assert "Included context: 1 project/module groups" in context
    assert "Explicitly excluded paths" in context
    assert "archive" in context
    assert packet["major_exclusions"]["hidden_low_signal_nodes"] == 1
    assert packet["token_savings"]["estimated_hidden_tokens_per_query"] >= 80


def test_overlap_report_ignores_low_signal_nodes(monkeypatch, tmp_path: Path) -> None:
    app_a = tmp_path / "code" / "app-a"
    app_b = tmp_path / "code" / "app-b"
    graph = tmp_path / "workspace-graph.json"
    graph.write_text(json.dumps({
        "nodes": [
            {
                "id": "a-readme",
                "label": "README",
                "source_file": "README.md",
                "file_type": "document",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
            },
            {
                "id": "b-readme",
                "label": "README",
                "source_file": "README.md",
                "file_type": "document",
                "source_root": str(app_b),
                "source_root_name": "app-b",
                "repo_project_name": "app-b",
            },
            {
                "id": "b-lock",
                "label": "Lockfile",
                "source_file": "package-lock.json",
                "file_type": "document",
                "source_root": str(app_b),
                "source_root_name": "app-b",
                "repo_project_name": "app-b",
            },
        ],
        "links": [],
    }))
    semantic_file = tmp_path / "semantic-edges.json"
    semantic_file.write_text(json.dumps({
        "created_at": "2026-06-17T11:09:43-06:00",
        "edges": [
            {"source": "a-readme", "target": "b-readme", "similarity": 0.91},
            {"source": "a-readme", "target": "b-lock", "similarity": 0.99},
        ],
    }))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"graph_path": str(graph)}))
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "SEMANTIC_EDGES_FILE", semantic_file)
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", tmp_path / "missing-scope.json")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "missing-scan-dirs.json")
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "API_KEY", "")

    report = TestClient(main.app).get("/graph/overlap-report").json()

    assert report["total_cross_edges"] == 1
    assert report["groups"][0]["cluster_a"] == "app-a"
    assert report["groups"][0]["cluster_b"] == "app-b"
    assert [pair["target"] for pair in report["groups"][0]["top_pairs"]] == ["b-readme"]


def test_overlap_report_groups_single_repo_edges_by_module(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "code" / "cockpit"
    graph = tmp_path / "workspace-graph.json"
    graph.write_text(json.dumps({
        "nodes": [
            {
                "id": "backend-main",
                "label": "main.py",
                "source_file": "backend/main.py",
                "source_root": str(repo),
                "source_root_name": "cockpit",
                "repo_project_name": "cockpit",
            },
            {
                "id": "docs-plan",
                "label": "plan.md",
                "source_file": "docs/plan.md",
                "source_root": str(repo),
                "source_root_name": "cockpit",
                "repo_project_name": "cockpit",
            },
        ],
        "links": [],
    }))
    semantic_file = tmp_path / "semantic-edges.json"
    semantic_file.write_text(json.dumps({
        "created_at": "2026-06-17T11:33:00-06:00",
        "edges": [{"source": "backend-main", "target": "docs-plan", "similarity": 0.88}],
    }))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"graph_path": str(graph)}))
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "SEMANTIC_EDGES_FILE", semantic_file)
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", tmp_path / "missing-scope.json")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "missing-scan-dirs.json")
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "API_KEY", "")

    report = TestClient(main.app).get("/graph/overlap-report").json()

    assert report["total_cross_edges"] == 1
    assert report["groups"][0]["cluster_a"] == "cockpit::backend"
    assert report["groups"][0]["cluster_b"] == "cockpit::docs"
