from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend import main
from backend.workspace_scope import (
    apply_signal_tiers_to_graph,
    filter_workspace_scope_graph,
    inspect_workspace_scope,
    workspace_scope_scan_roots,
)


def _touch(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _flatten(node: dict) -> dict[str, dict]:
    items = {node["relative_path"]: node}
    for child in node.get("children", []):
        items.update(_flatten(child))
    return items


def test_inspect_workspace_scope_reports_default_exclusions_without_file_contents(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / "graphify-out" / "cache").mkdir(parents=True)
    (root / "workspace" / "state").mkdir(parents=True)
    _touch(root / "package.json", "{}")
    _touch(root / "package-lock.json", "{}")
    _touch(root / "src" / "app.py", "print('hello')")
    _touch(root / ".env", "SUPER_SECRET_VALUE=do-not-return")
    _touch(root / "credentials" / "api-key.txt", "do-not-return-either")

    summary = inspect_workspace_scope(root, max_depth=3)

    flat = _flatten(summary["tree"])
    assert summary["root"]["path"] == str(root.resolve())
    assert summary["tree"]["project_type"] == "git-repo"
    assert summary["tree"]["state"] == "partial"
    assert flat[".git"]["state"] == "excluded"
    assert flat["node_modules"]["state"] == "excluded"
    assert flat["graphify-out"]["state"] == "excluded"
    assert flat["workspace/state"]["state"] == "excluded"
    assert flat["package-lock.json"]["state"] == "excluded"
    assert flat[".env"]["state"] == "excluded"
    assert flat["credentials"]["state"] == "excluded"
    assert "Secret-like path detected" in flat[".env"]["reasons"][0]
    assert "SUPER_SECRET_VALUE" not in str(summary)
    assert "do-not-return-either" not in str(summary)


def test_inspect_workspace_scope_stops_expansion_at_child_repo_boundary(tmp_path: Path) -> None:
    root = tmp_path / "code"
    app = root / "Applications" / "demo-app"
    (app / ".git").mkdir(parents=True)
    _touch(app / "package.json", "{}")
    _touch(app / "src" / "main.ts", "console.log('hidden from tree summary')")

    summary = inspect_workspace_scope(root, max_depth=5)
    flat = _flatten(summary["tree"])

    assert flat["Applications"]["state"] == "included"
    assert flat["Applications/demo-app"]["project_type"] == "git-repo"
    assert flat["Applications/demo-app"]["children"] == []
    assert flat["Applications/demo-app"]["estimated_file_count"] == 2


def test_workspace_scope_inspect_endpoint_returns_safe_tree(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    _touch(root / ".env.local", "PRIVATE_TOKEN=do-not-leak")
    _touch(root / "project" / "pyproject.toml", "[project]\nname = 'demo'\n")
    monkeypatch.setattr(main, "API_KEY", "")
    client = TestClient(main.app)

    response = client.post(
        "/workspace-scope/inspect",
        json={"root": str(root), "max_depth": 3},
    )

    assert response.status_code == 200
    body = response.json()
    flat = _flatten(body["tree"])
    assert body["root"]["path"] == str(root.resolve())
    assert ".env.local" in flat
    assert flat[".env.local"]["state"] == "excluded"
    assert "PRIVATE_TOKEN" not in response.text


def test_workspace_scope_inspect_endpoint_rejects_missing_root() -> None:
    client = TestClient(main.app)

    response = client.post(
        "/workspace-scope/inspect",
        json={"root": "/definitely/not/a/workspace/root"},
    )

    assert response.status_code == 422
    assert "Root does not exist" in response.json()["detail"]


def test_workspace_scope_profile_endpoint_persists_normalized_scope(monkeypatch, tmp_path: Path) -> None:
    state_file = tmp_path / "state" / "workspace-scope.json"
    root = tmp_path / "code"
    included = root / "agents"
    excluded = root / ".claude"
    included.mkdir(parents=True)
    excluded.mkdir(parents=True)
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", state_file)
    monkeypatch.setattr(main, "API_KEY", "")
    client = TestClient(main.app)

    save_response = client.put(
        "/workspace-scope",
        json={
            "root": str(root),
            "profile_name": "All Code",
            "included_paths": [str(included)],
            "excluded_paths": [str(excluded)],
            "signal": {"hide_low_signal": True, "show_generated": False},
        },
    )

    assert save_response.status_code == 200
    saved = save_response.json()["profile"]
    assert saved["root"] == str(root.resolve())
    assert saved["profile_name"] == "All Code"
    assert saved["included_paths"] == [str(included.resolve())]
    assert saved["excluded_paths"] == [str(excluded.resolve())]
    assert saved["signal"]["min_visible_signal"] == "important"

    load_response = client.get("/workspace-scope")
    assert load_response.status_code == 200
    assert load_response.json()["profile"] == saved
    assert state_file.exists()


def test_workspace_scope_profile_rejects_paths_outside_root(monkeypatch, tmp_path: Path) -> None:
    state_file = tmp_path / "state" / "workspace-scope.json"
    root = tmp_path / "code"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", state_file)
    client = TestClient(main.app)

    response = client.put(
        "/workspace-scope",
        json={
            "root": str(root),
            "included_paths": [str(outside)],
        },
    )

    assert response.status_code == 422
    assert "must stay within root" in response.json()["detail"]
    assert not state_file.exists()


def test_workspace_scope_profile_rejects_empty_selection(monkeypatch, tmp_path: Path) -> None:
    state_file = tmp_path / "state" / "workspace-scope.json"
    root = tmp_path / "code"
    root.mkdir()
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", state_file)
    client = TestClient(main.app)

    response = client.put(
        "/workspace-scope",
        json={
            "root": str(root),
            "profile_name": "Empty Scope",
            "included_paths": [],
        },
    )

    assert response.status_code == 422
    assert "Select at least one included folder" in response.json()["detail"]
    assert not state_file.exists()


def test_workspace_scope_profile_rejects_default_ignored_included_path(monkeypatch, tmp_path: Path) -> None:
    state_file = tmp_path / "state" / "workspace-scope.json"
    root = tmp_path / "code"
    ignored = root / "node_modules"
    ignored.mkdir(parents=True)
    monkeypatch.setattr(main, "WORKSPACE_SCOPE_FILE", state_file)
    client = TestClient(main.app)

    response = client.put(
        "/workspace-scope",
        json={
            "root": str(root),
            "profile_name": "Ignored Scope",
            "included_paths": [str(ignored)],
        },
    )

    assert response.status_code == 422
    assert "default-ignored paths" in response.json()["detail"]
    assert not state_file.exists()


def test_workspace_scope_scan_roots_uses_only_selected_includes(tmp_path: Path) -> None:
    root = tmp_path / "code"
    agents = root / "agents"
    app = root / "Applications" / "demo"
    nested = agents / "child"
    ignored = root / "node_modules"
    for path in (agents, app, nested, ignored):
        path.mkdir(parents=True)

    roots = workspace_scope_scan_roots({
        "root": str(root),
        "included_paths": [str(nested), str(agents), str(app), str(ignored)],
        "excluded_paths": [],
    })

    assert roots == [agents.resolve(), app.resolve()]


def test_signal_tiering_demotes_low_signal_and_keeps_source_of_truth(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Demo")
    (repo / "src").mkdir()
    (repo / "src" / "worker.py").write_text("print('ok')")
    (repo / "next-env.d.ts").write_text("/// generated")
    (repo / "package-lock.json").write_text("{}")
    graph = {
        "nodes": [
            {"id": "readme", "label": "README", "source_file": "README.md", "file_type": "document"},
            {"id": "worker", "label": "worker", "source_file": "src/worker.py"},
            {"id": "next", "label": "next-env", "source_file": "next-env.d.ts"},
            {"id": "lock", "label": "lock", "source_file": "package-lock.json"},
        ],
        "links": [
            {"source": "readme", "target": "worker", "relation": "mentions"},
            {"source": "worker", "target": "next", "relation": "related"},
        ],
    }

    tiered = apply_signal_tiers_to_graph(graph, scan_root=repo)
    tiers = {node["id"]: node["signal_tier"] for node in tiered["nodes"]}

    assert tiers["readme"] == "important"
    assert tiers["worker"] == "evidence"
    assert tiers["next"] == "hidden"
    assert tiers["lock"] == "hidden"


def test_scope_filter_adds_signal_metadata_and_counts(tmp_path: Path) -> None:
    root = tmp_path / "code"
    app = root / "app"
    app.mkdir(parents=True)
    (app / "README.md").write_text("# App")
    (app / "next-env.d.ts").write_text("/// generated")
    graph = {
        "nodes": [
            {"id": "readme", "label": "README", "source_file": "README.md", "file_type": "document"},
            {"id": "generated", "label": "next-env", "source_file": "next-env.d.ts"},
        ],
        "links": [{"source": "readme", "target": "generated", "relation": "mentions"}],
    }
    profile = {"root": str(root), "profile_name": "Scoped", "included_paths": [str(app)]}

    filtered, stats = filter_workspace_scope_graph(graph, profile, app)

    assert [node["signal_tier"] for node in filtered["nodes"]] == ["important", "hidden"]
    assert filtered["nodes"][0]["signal_reason"] == "source-of-truth file"
    assert stats["signal_counts"]["important"] == 1
    assert stats["signal_counts"]["hidden"] == 1
