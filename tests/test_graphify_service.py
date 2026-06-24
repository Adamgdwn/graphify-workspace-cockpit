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


def test_run_graphify_extract_builds_provider_command(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(service.shutil, "which", lambda _name: "/usr/bin/graphify")
    calls: list[dict] = []

    def fake_run(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(service.subprocess, "run", fake_run)

    result = service.run_graphify_extract(
        tmp_path,
        cwd=tmp_path,
        backend="openai",
        model="gpt-4.1",
        timeout=42,
        api_timeout=30,
        max_concurrency=1,
    )

    assert result.returncode == 0
    assert calls[0]["args"][0] == [
        "/usr/bin/graphify",
        "extract",
        str(tmp_path),
        "--backend",
        "openai",
        "--model",
        "gpt-4.1",
        "--mode",
        "deep",
        "--max-concurrency",
        "1",
        "--api-timeout",
        "30",
        "--no-cluster",
    ]
    assert calls[0]["kwargs"]["cwd"] == str(tmp_path)
    assert calls[0]["kwargs"]["timeout"] == 42


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
    assert active_graph["_meta"]["workspace_scope"]["included_paths"] == [str(app), str(excluded)]
    assert active_graph["_meta"]["workspace_scope"]["excluded_paths"] == [str(excluded)]
    assert active_graph["_meta"]["workspace_scope"]["scanned_root_count"] == 1
    assert active_graph["nodes"][0]["source_root"] == str(app)
    assert active_graph["nodes"][0]["scope_profile"] == "Scoped Test"
    assert "not returned" not in Path(active_path).read_text()
    assert "graphify-out/cache" not in Path(active_path).read_text()
    assert not semantic_file.exists()
    assert main._graph_cache is None
    assert main._summary_cache == {}

    summary = main.graph_summary(min_weight=1)
    assert summary["workspace_scope"]["profile_name"] == "Scoped Test"
    assert summary["workspace_scope"]["included_paths"] == [str(app), str(excluded)]
    assert summary["workspace_scope"]["excluded_paths"] == [str(excluded)]
    assert main._REBUILD_STATUS["status"] == "complete"


def test_scoped_rebuild_elevates_when_local_decider_requests_it(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    state_dir = tmp_path / "state"
    workspace_root = tmp_path / "code"
    app = workspace_root / "app"
    app.mkdir(parents=True)
    (app / "src").mkdir()
    (app / "src" / "main.py").write_text("print('ok')")
    repo_root.mkdir()
    state_dir.mkdir()

    scope_file = state_dir / "workspace-scope.json"
    settings_file = state_dir / "settings.json"
    scope_file.write_text(json.dumps({
        "root": str(workspace_root),
        "profile_name": "Elevated Scope",
        "included_paths": [str(app)],
        "excluded_paths": [],
    }))

    monkeypatch.setattr(main, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", scope_file)
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", state_dir / "scan-dirs.json")
    monkeypatch.setattr(main, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(main, "_REBUILD_STATUS", {"status": "idle", "last_run": None})
    monkeypatch.setattr(main, "GRAPH_ESCALATION_ENABLED", True)
    monkeypatch.setattr(main, "GRAPH_ESCALATION_BACKEND", "openai")
    monkeypatch.setattr(main, "GRAPH_ESCALATION_MODEL", "gpt-4.1")
    monkeypatch.setattr(
        main,
        "_call_ollama",
        lambda *_args, **_kwargs: '{"route":"elevated","reason":"needs semantic extraction"}',
    )

    update_calls: list[tuple[str, str]] = []
    extract_calls: list[tuple[str, str, str, str]] = []

    def fake_run_graphify_update(target, *, cwd=None, timeout=300):
        update_calls.append((str(target), str(cwd)))
        return service.GraphifyCommandResult(["graphify", "update"], 0, "", "")

    def fake_run_graphify_extract(
        target,
        *,
        cwd=None,
        backend,
        model=None,
        mode="deep",
        timeout=1800,
        api_timeout=600,
        max_concurrency=2,
        no_cluster=True,
    ):
        extract_calls.append((str(target), str(cwd), backend, model or ""))
        graph_path = Path(cwd) / "graphify-out" / "graph.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(json.dumps({
            "nodes": [{"id": "keep", "label": "main.py", "source_file": "src/main.py"}],
            "links": [],
        }))
        return service.GraphifyCommandResult(["graphify", "extract"], 0, "", "")

    monkeypatch.setattr(main, "run_graphify_update", fake_run_graphify_update)
    monkeypatch.setattr(main, "run_graphify_extract", fake_run_graphify_extract)

    main._run_rebuild()

    assert update_calls == []
    assert extract_calls == [(str(app), str(app), "openai", "gpt-4.1")]
    assert main._REBUILD_STATUS["status"] == "complete"
    assert main._REBUILD_STATUS["route"] == "elevated"
    assert main._REBUILD_STATUS["escalation"]["decision_source"] == "ollama"
    active_path = json.loads(settings_file.read_text())["graph_path"]
    active_graph = json.loads(Path(active_path).read_text())
    assert [node["id"] for node in active_graph["nodes"]] == ["keep"]


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


def test_semantic_pass_nodes_follow_visible_signal_scope() -> None:
    graph = {
        "nodes": [
            {
                "id": "important",
                "label": "README",
                "source_file": "README.md",
                "file_type": "document",
                "importance_tier": "important",
                "signal_tier": "important",
            },
            {
                "id": "hidden",
                "label": "generated",
                "source_file": "next-env.d.ts",
                "file_type": "code",
                "importance_tier": "hidden",
                "signal_tier": "hidden",
            },
            {
                "id": "excluded",
                "label": "vendor",
                "source_file": "vendor/bundle.js",
                "file_type": "code",
                "importance_tier": "excluded",
                "signal_tier": "excluded",
            },
        ],
        "links": [],
    }

    default_nodes = main._semantic_nodes_for_pass(graph)
    expanded_nodes = main._semantic_nodes_for_pass(graph, include_low_signal=True)
    explicit_nodes = main._semantic_nodes_for_pass(
        graph,
        include_low_signal=True,
        node_ids=["hidden"],
    )

    assert [node["id"] for node in default_nodes] == ["important"]
    assert [node["id"] for node in expanded_nodes] == ["important", "hidden"]
    assert [node["id"] for node in explicit_nodes] == ["hidden"]


def test_semantic_edges_from_embeddings_keeps_mutual_top_neighbors() -> None:
    embeddings = [
        ("alpha", [1.0, 0.0]),
        ("alpha-copy", [0.99, 0.01]),
        ("beta", [0.0, 1.0]),
        ("beta-copy", [0.01, 0.99]),
    ]

    edges = main._semantic_edges_from_embeddings(
        embeddings,
        threshold=0.86,
        max_neighbors_per_node=1,
        mutual_top_neighbors=True,
        max_edges=10,
    )

    pairs = {frozenset((edge["source"], edge["target"])) for edge in edges}
    assert pairs == {
        frozenset(("alpha", "alpha-copy")),
        frozenset(("beta", "beta-copy")),
    }
    assert all(edge["similarity"] >= 0.86 for edge in edges)


def test_semantic_source_window_prefers_node_source_root(monkeypatch, tmp_path: Path) -> None:
    app_repo = tmp_path / "cockpit"
    source_repo = tmp_path / "code" / "project"
    app_repo.mkdir()
    source_repo.mkdir(parents=True)
    (app_repo / "README.md").write_text("wrong cockpit readme\n")
    (source_repo / "README.md").write_text("right project readme\n")
    monkeypatch.setattr(main, "_configured_source_roots", lambda: [app_repo, source_repo])

    text = main._read_source_window("README.md", str(source_repo))

    assert text == "right project readme"


def test_embed_text_batch_ollama_uses_batch_endpoint(monkeypatch) -> None:
    calls: list[tuple[str, dict, int]] = []

    def fake_post(url: str, payload: dict, timeout: int) -> dict:
        calls.append((url, payload, timeout))
        return {"embeddings": [[1, "2"], [3.5, 4]]}

    monkeypatch.setattr(main, "_post_ollama_json", fake_post)

    vectors = main._embed_text_batch_ollama("embedder", ["alpha", "beta"], "http://ollama")

    assert vectors == [[1.0, 2.0], [3.5, 4.0]]
    assert calls == [
        ("http://ollama/api/embed", {"model": "embedder", "input": ["alpha", "beta"]}, 180)
    ]


def test_embed_text_batch_ollama_falls_back_to_legacy_endpoint(monkeypatch) -> None:
    calls: list[tuple[str, dict, int]] = []

    def fake_post(url: str, payload: dict, timeout: int) -> dict:
        calls.append((url, payload, timeout))
        if url.endswith("/api/embed"):
            raise OSError("batch endpoint unavailable")
        return {"embedding": [len(str(payload["prompt"])), 1]}

    monkeypatch.setattr(main, "_post_ollama_json", fake_post)

    vectors = main._embed_text_batch_ollama("embedder", ["alpha", "beta"], "http://ollama")

    assert vectors == [[5.0, 1.0], [4.0, 1.0]]
    assert calls == [
        ("http://ollama/api/embed", {"model": "embedder", "input": ["alpha", "beta"]}, 180),
        ("http://ollama/api/embeddings", {"model": "embedder", "prompt": "alpha"}, 90),
        ("http://ollama/api/embeddings", {"model": "embedder", "prompt": "beta"}, 90),
    ]


def test_graph_endpoints_preserve_scoped_signal_metadata(monkeypatch, tmp_path: Path) -> None:
    app = tmp_path / "code" / "app"
    graph = tmp_path / "scoped-graph.json"
    graph.write_text(json.dumps({
        "_meta": {
            "workspace_scope": {
                "profile_name": "Single App",
                "root": str(tmp_path / "code"),
                "included_paths": [str(app)],
                "excluded_paths": [],
                "scanned_root_count": 1,
                "removed_node_count": 3,
            },
        },
        "nodes": [
            {
                "id": "worker",
                "label": "worker.py",
                "source_file": "worker.py",
                "file_type": "code",
                "source_root": str(app),
                "source_root_name": "app",
                "repo_project_name": "app",
                "signal_tier": "important",
                "signal_reason": "scoped rebuild classification",
                "importance_tier": "important",
                "importance_reason": "scoped rebuild classification",
            },
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

    summary = client.get("/graph/summary").json()
    full = client.get("/graph/full").json()

    assert summary["total_nodes"] == 1
    assert [node["label"] for node in summary["nodes"]] == ["app"]
    assert summary["workspace_scope"]["profile_name"] == "Single App"
    assert [node["id"] for node in full["nodes"]] == ["worker"]
    assert full["signal_counts"]["important"] == 1


def test_graph_full_resolves_duplicate_relative_source_files_per_node_root(monkeypatch, tmp_path: Path) -> None:
    app_a = tmp_path / "code" / "app-a"
    app_b = tmp_path / "code" / "app-b"
    app_a.mkdir(parents=True)
    app_b.mkdir(parents=True)
    (app_a / "shared.py").write_text("APP_A = True\n")
    (app_b / "shared.py").write_text("APP_B = True\n")
    graph = tmp_path / "scoped-graph.json"
    graph.write_text(json.dumps({
        "nodes": [
            {
                "id": "a-shared",
                "label": "shared.py",
                "source_file": "shared.py",
                "source_location": "L1",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
                "signal_tier": "important",
                "importance_tier": "important",
            },
            {
                "id": "b-shared",
                "label": "shared.py",
                "source_file": "shared.py",
                "source_location": "L1",
                "source_root": str(app_b),
                "source_root_name": "app-b",
                "repo_project_name": "app-b",
                "signal_tier": "important",
                "importance_tier": "important",
            },
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

    response = client.get("/graph/full")

    assert response.status_code == 200
    nodes = {node["id"]: node for node in response.json()["nodes"]}
    assert nodes["a-shared"]["source_root"] == str(app_a)
    assert nodes["b-shared"]["source_root"] == str(app_b)
    assert nodes["a-shared"]["relative_path"] == "shared.py"
    assert nodes["b-shared"]["relative_path"] == "shared.py"
    assert nodes["a-shared"]["source_excerpt"]["lines"] == ["APP_A = True"]
    assert nodes["b-shared"]["source_excerpt"]["lines"] == ["APP_B = True"]


def test_graph_full_workspace_knowledge_lens_prioritizes_decision_files(monkeypatch, tmp_path: Path) -> None:
    graph = tmp_path / "knowledge-graph.json"
    graph.write_text(json.dumps({
        "nodes": [
            {"id": "readme", "label": "README", "source_file": "README.md", "file_type": "document"},
            {"id": "contract", "label": "PublicApi", "source_file": "src/contracts/public-api.d.ts"},
            {"id": "route", "label": "users route", "source_file": "src/routes/users.ts"},
            {"id": "worker", "label": "worker", "source_file": "src/components/worker.ts"},
            {"id": "react-types", "label": "React types", "source_file": "node_modules/@types/react/index.d.ts"},
            {"id": "generated", "label": "next-env", "source_file": "next-env.d.ts"},
        ],
        "links": [
            {"source": "readme", "target": "contract", "relation": "documents"},
            {"source": "route", "target": "worker", "relation": "calls"},
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

    response = client.get("/graph/full?knowledge_only=true")

    assert response.status_code == 200
    body = response.json()
    assert body["knowledge_only"] is True
    assert [node["id"] for node in body["nodes"]] == ["readme", "contract", "route"]
    by_id = {node["id"]: node for node in body["nodes"]}
    assert by_id["readme"]["importance_tier"] == "anchor"
    assert by_id["contract"]["importance_tier"] == "interface"
    assert by_id["contract"]["importance_reason"] == "workspace-owned type contract"
    assert by_id["route"]["importance_tier"] == "interface"
    assert body["importance_counts"]["hidden"] == 2
    assert body["importance_counts"]["evidence"] == 1
    assert body["signal_counts"]["hidden"] == 2
    assert body["signal_counts"]["evidence"] == 1


def test_graph_map_decision_overlay_marks_summary_and_full_nodes(monkeypatch, tmp_path: Path) -> None:
    app_a = tmp_path / "code" / "app-a"
    app_b = tmp_path / "code" / "app-b"
    state_dir = tmp_path / "state"
    rec_dir = state_dir / "recommendations"
    action_dir = state_dir / "action-queue"
    rec_dir.mkdir(parents=True)
    action_dir.mkdir(parents=True)
    graph = tmp_path / "decision-overlay-graph.json"
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
                "label": "users route",
                "source_file": "src/routes/users.py",
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
        ],
        "links": [
            {"source": "a-readme", "target": "a-route", "relation": "documents"},
            {"source": "a-route", "target": "b-readme", "relation": "references"},
        ],
    }))
    graph_payload = json.loads(graph.read_text())
    map_context = {
        "graph_fingerprint": main._graph_fingerprint(graph_payload),
        "graph_name": graph.name,
        "graph_node_count": len(graph_payload["nodes"]),
    }
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"graph_path": str(graph)}))
    decisions = state_dir / "decisions.json"
    decisions.write_text(json.dumps([
        {
            "id": "decision-app-a",
            "target_id": "app-a",
            "label": "App A",
            "classification": "invest",
            "rationale": "This is the canonical route boundary.",
            "status": "active",
            "created_at": "2026-06-18T12:00:00+00:00",
            "updated_at": "2026-06-18T12:00:00+00:00",
        }
    ]))
    (rec_dir / "rec-app-a.json").write_text(json.dumps({
        "id": "rec-app-a",
        "mode": "next-build",
        "title": "Document app-a route boundary",
        "summary": "App A should become the canonical route boundary.",
        "evidence": ["app-a", "src/routes/users.py"],
        "status": "accepted",
        "proposed_action": "Document the app-a route boundary before merging adjacent work.",
        "created_at": "2026-06-18T12:05:00+00:00",
        "updated_at": "2026-06-18T12:05:00+00:00",
        "context": {"map": map_context},
    }))
    (action_dir / "action-app-a.json").write_text(json.dumps({
        "id": "action-app-a",
        "source_recommendation_id": "rec-app-a",
        "status": "pending",
        "action_type": "create_note",
        "description": "Create note: app-a route boundary",
        "proposed_action_text": "Create a note for app-a route boundary ownership.",
        "evidence": ["app-a", "src/routes/users.py"],
        "created_at": "2026-06-18T12:10:00+00:00",
        "updated_at": "2026-06-18T12:10:00+00:00",
    }))
    monkeypatch.setattr(main, "SETTINGS_FILE", settings)
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(graph))
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", tmp_path / "missing-scope.json")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", tmp_path / "missing-scan-dirs.json")
    monkeypatch.setattr(main, "DECISIONS_FILE", decisions)
    monkeypatch.setattr(main, "RECOMMENDATIONS_DIR", rec_dir)
    monkeypatch.setattr(main, "ACTION_QUEUE_DIR", action_dir)
    monkeypatch.setattr(main, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "API_KEY", "")
    client = TestClient(main.app)

    overview = client.get("/graph/summary", params={"min_weight": 1}).json()
    by_label = {node["label"]: node for node in overview["nodes"]}

    assert by_label["app-a"]["decision_classification"] == "invest"
    assert by_label["app-a"]["decision_overlay"]["decision_count"] == 1
    assert by_label["app-a"]["decision_overlay"]["recommendation_count"] == 1
    assert by_label["app-a"]["decision_overlay"]["queued_action_count"] == 1
    assert by_label["app-a"]["decision_overlay"]["recommendations"][0]["id"] == "rec-app-a"
    assert by_label["app-a"]["decision_overlay"]["queued_actions"][0]["id"] == "action-app-a"
    assert by_label["app-b"]["decision_overlay"]["decision_count"] == 0

    full = client.get("/graph/full").json()
    full_by_id = {node["id"]: node for node in full["nodes"]}

    assert full_by_id["a-route"]["decision_classification"] == "invest"
    assert full_by_id["a-route"]["decision_overlay"]["decision_count"] == 1
    assert full_by_id["a-route"]["decision_overlay"]["recommendation_count"] == 1
    assert full_by_id["a-route"]["decision_overlay"]["queued_action_count"] == 1
    assert full_by_id["b-readme"]["decision_overlay"]["decision_count"] == 0


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


def test_graph_summary_expands_broad_scope_from_relative_paths(monkeypatch, tmp_path: Path) -> None:
    code_root = tmp_path / "code"
    graph = tmp_path / "broad-workspace-graph.json"
    shared_meta = {
        "source_root": str(code_root),
        "source_root_name": "code",
        "repo_project_name": "code",
        "file_type": "document",
    }
    graph.write_text(json.dumps({
        "nodes": [
            {
                **shared_meta,
                "id": "clean-readme",
                "label": "Clean PDF README",
                "source_file": "Applications/Clean_pdf_build/README.md",
            },
            {
                **shared_meta,
                "id": "timeshare-readme",
                "label": "Timeshare README",
                "source_file": "Applications/Timeshare-Connect/README.md",
            },
            {
                **shared_meta,
                "id": "cockpit-readme",
                "label": "Cockpit README",
                "source_file": "agents/graphify-workspace-cockpit/README.md",
            },
            {
                **shared_meta,
                "id": "graphify-readme",
                "label": "Graphify README",
                "source_file": "Tools/graphify/README.md",
            },
            {
                **shared_meta,
                "id": "agents-md",
                "label": "AGENTS",
                "source_file": "AGENTS.md",
            },
        ],
        "links": [
            {"source": "clean-readme", "target": "cockpit-readme", "relation": "references"},
            {"source": "cockpit-readme", "target": "timeshare-readme", "relation": "references"},
            {"source": "timeshare-readme", "target": "graphify-readme", "relation": "references"},
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

    overview = client.get("/graph/summary", params={"min_weight": 1}).json()

    assert overview["level"] == "top"
    assert {node["label"] for node in overview["nodes"]} == {
        "Applications",
        "agents",
        "Tools",
        "Workspace Docs",
    }
    assert len(overview["nodes"]) == 4
    by_label = {node["label"]: node for node in overview["nodes"]}
    assert by_label["Applications"]["connection_count"] == 2
    assert by_label["Applications"]["connection_weight"] == 3
    assert by_label["Applications"]["connections"] == [
        {"id": "agents", "label": "agents", "weight": 2, "relations": ["references"]},
        {"id": "Tools", "label": "Tools", "weight": 1, "relations": ["references"]},
    ]
    assert by_label["Workspace Docs"]["is_gap"] is True
    assert by_label["Workspace Docs"]["gap_reason"]
    assert by_label["Workspace Docs"]["connections"] == []
    assert {
        (edge["source"], edge["target"], edge["weight"])
        for edge in overview["edges"]
    } == {
        ("Applications", "agents", 2),
        ("Applications", "Tools", 1),
    }

    applications_detail = client.get(
        "/graph/summary",
        params={"project": "Applications", "min_weight": 1},
    ).json()

    assert applications_detail["level"] == "project"
    assert applications_detail["project"] == "Applications"
    assert {node["label"] for node in applications_detail["nodes"]} == {
        "Clean_pdf_build",
        "Timeshare-Connect",
    }
    assert {node["group_type"] for node in applications_detail["nodes"]} == {"module"}


def test_graph_summary_classifies_gap_triage(monkeypatch, tmp_path: Path) -> None:
    graph = tmp_path / "gap-triage-graph.json"
    shared_meta = {"source_root": str(tmp_path), "source_root_name": "workspace"}
    graph.write_text(json.dumps({
        "nodes": [
            {
                **shared_meta,
                "id": "root-doc",
                "label": "AGENTS",
                "source_file": "AGENTS.md",
                "file_type": "document",
            },
            {
                **shared_meta,
                "id": "hidden-readme",
                "label": "Hidden App README",
                "source_file": "hidden-app/README.md",
                "file_type": "document",
            },
            {
                **shared_meta,
                "id": "hidden-worker",
                "label": "hidden worker",
                "source_file": "hidden-app/src/worker.py",
                "file_type": "code",
            },
            {
                **shared_meta,
                "id": "target-readme",
                "label": "Target README",
                "source_file": "target-app/README.md",
                "file_type": "document",
            },
            {
                **shared_meta,
                "id": "code-main",
                "label": "main",
                "source_file": "code-app/src/main.py",
                "file_type": "code",
            },
            {
                **shared_meta,
                "id": "lone-readme",
                "label": "Lone README",
                "source_file": "lone-doc/README.md",
                "file_type": "document",
            },
        ],
        "links": [
            {"source": "hidden-worker", "target": "target-readme", "relation": "references"},
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

    overview = TestClient(main.app).get("/graph/summary", params={"min_weight": 1}).json()
    by_label = {node["label"]: node for node in overview["nodes"]}

    assert by_label["Workspace Docs"]["gap_type"] == "root_level_docs_only"
    assert by_label["hidden-app"]["gap_type"] == "hidden_by_low_signal_filters"
    assert by_label["target-app"]["gap_type"] == "hidden_by_low_signal_filters"
    assert "references" in " ".join(by_label["hidden-app"]["gap_evidence"])
    assert by_label["code-app"]["gap_type"] == "missing_semantic_extraction"
    assert by_label["lone-doc"]["gap_type"] == "truly_isolated"
    assert by_label["lone-doc"]["gap_actions"] == ["drill_in", "ask", "monitor", "archive"]


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
                "importance_tier": "evidence",
                "signal_tier": "evidence",
            },
            {
                "id": "lock",
                "label": "Lockfile",
                "source_file": "package-lock.json",
                "file_type": "document",
                "source_root": str(app_a),
                "source_root_name": "app-a",
                "repo_project_name": "app-a",
                "importance_tier": "hidden",
                "signal_tier": "hidden",
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
    assert evidence[0]["signal_tier"] == "evidence"


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
    assert packet["map"]["graph_name"] == graph.name
    assert packet["map"]["graph_node_count"] == 2
    assert packet["map"]["graph_fingerprint"]

    current_rec = {"id": "rec-current", "context": {"map": packet["map"]}}
    old_rec = {"id": "rec-old", "context": {"map": {"graph_fingerprint": "older", "graph_name": "old.json"}}}
    system_rec = {"id": "rec-system", "context": {"scope_name": "Legacy"}}
    assert main._recommendation_scope(current_rec, current_map=packet["map"])["kind"] == "current_map"
    assert main._recommendation_scope(old_rec, current_map=packet["map"])["kind"] == "other_map"
    assert main._recommendation_scope(system_rec, current_map=packet["map"])["kind"] == "system"


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
        "edge_policy_version": main.SEMANTIC_EDGE_POLICY_VERSION,
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
        "edge_policy_version": main.SEMANTIC_EDGE_POLICY_VERSION,
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


def test_overlap_summary_uses_visible_summary_groups(monkeypatch, tmp_path: Path) -> None:
    code_root = tmp_path / "code"
    graph = tmp_path / "broad-workspace-graph.json"
    shared_meta = {
        "source_root": str(code_root),
        "source_root_name": "code",
        "repo_project_name": "code",
        "file_type": "document",
    }
    graph.write_text(json.dumps({
        "nodes": [
            {
                **shared_meta,
                "id": "app-readme",
                "label": "README",
                "source_file": "Applications/Timeshare-Connect/README.md",
            },
            {
                **shared_meta,
                "id": "agent-readme",
                "label": "README",
                "source_file": "agents/graphify-workspace-cockpit/README.md",
            },
            {
                **shared_meta,
                "id": "tool-plan",
                "label": "Plan",
                "source_file": "Tools/graphify/docs/plan.md",
            },
            {
                **shared_meta,
                "id": "lockfile",
                "label": "Lock",
                "source_file": "Applications/Timeshare-Connect/package-lock.json",
                "signal_tier": "excluded",
            },
        ],
        "links": [],
    }))
    semantic_file = tmp_path / "semantic-edges.json"
    semantic_file.write_text(json.dumps({
        "edge_policy_version": main.SEMANTIC_EDGE_POLICY_VERSION,
        "created_at": "2026-06-17T17:44:00-06:00",
        "edges": [
            {"source": "app-readme", "target": "agent-readme", "similarity": 0.92},
            {"source": "app-readme", "target": "tool-plan", "similarity": 0.82},
            {"source": "lockfile", "target": "agent-readme", "similarity": 0.99},
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

    report = TestClient(main.app).get("/graph/overlap-summary").json()

    assert report["level"] == "top"
    assert report["total_cross_edges"] == 2
    assert {
        (group["cluster_a"], group["cluster_b"], group["edge_count"])
        for group in report["groups"]
    } == {
        ("Applications", "Tools", 1),
        ("Applications", "agents", 1),
    }
    agents_group = next(
        group for group in report["groups"]
        if group["cluster_b"] == "agents"
    )
    assert agents_group["same_name_count"] == 1
    assert agents_group["top_pairs"][0]["same_name"] is True
    assert agents_group["insight_kind"] == "waste_duplicate"
    assert agents_group["actionability_score"] >= 0.7
    assert "same-name" in " ".join(agents_group["decision_signals"])

    context = main._build_graph_context(main.graph_summary(min_weight=1))
    assert "Semantic overlap action queue" in context
    assert "Applications <-> agents" in context
