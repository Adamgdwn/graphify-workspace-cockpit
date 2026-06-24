from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend import main
from backend.state_store import write_json_atomic


FIXTURES = Path(__file__).parent / "fixtures"


def _patch_empty_state(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    state_dir = tmp_path / "state"
    demo_graph = tmp_path / "demo" / "graph.json"
    demo_graph.parent.mkdir(parents=True, exist_ok=True)
    demo_graph.write_bytes((FIXTURES / "demo_graph_links.json").read_bytes())

    monkeypatch.setattr(main, "WORKSPACE_STATE", state_dir)
    monkeypatch.setattr(main, "SESSIONS_DIR", state_dir / "sessions")
    monkeypatch.setattr(main, "SETTINGS_FILE", state_dir / "settings.json")
    monkeypatch.setattr(main, "DECISIONS_FILE", state_dir / "decisions.json")
    monkeypatch.setattr(main, "GRAPHS_DIR", state_dir / "graphs")
    monkeypatch.setattr(main, "DEVICES_FILE", state_dir / "devices.json")
    monkeypatch.setattr(main, "CONNECTORS_DIR", state_dir / "connectors")
    monkeypatch.setattr(main, "CLUSTER_SELECTION_FILE", state_dir / "cluster-selection.json")
    monkeypatch.setattr(main, "CHAT_CONFIG_FILE", state_dir / "chat-config.json")
    monkeypatch.setattr(main, "CHAT_SESSIONS_DIR", state_dir / "chat-sessions")
    monkeypatch.setattr(main, "SCAN_DIRS_FILE", state_dir / "scan-dirs.json")
    monkeypatch.setattr(main, "SEMANTIC_EDGES_FILE", state_dir / "semantic-edges.json")
    monkeypatch.setattr(main, "OVERLAP_STATUS_FILE", state_dir / "overlap-status.json")
    monkeypatch.setattr(main, "RECOMMENDATIONS_DIR", state_dir / "recommendations")
    monkeypatch.setattr(main, "ACTION_QUEUE_DIR", state_dir / "action-queue")
    monkeypatch.setattr(main, "_DEMO_GRAPH", str(demo_graph))
    monkeypatch.setattr(main, "DEFAULT_GRAPH", "")
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "_supabase_client", None)
    return state_dir, demo_graph


def test_write_json_atomic_creates_parent_replaces_and_cleans_temp(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "state.json"

    write_json_atomic(path, {"version": 1})
    write_json_atomic(path, {"version": 2, "items": ["fresh"]})

    assert json.loads(path.read_text()) == {"version": 2, "items": ["fresh"]}
    assert list(path.parent.glob("*.tmp")) == []


def test_clean_empty_state_can_write_local_json_surfaces(monkeypatch, tmp_path: Path) -> None:
    state_dir, _ = _patch_empty_state(monkeypatch, tmp_path)
    client = TestClient(main.app)
    scan_dir = tmp_path / "scan-root"
    scan_dir.mkdir()

    assert not state_dir.exists()

    upload = client.post(
        "/graph/upload",
        files={
            "file": (
                "clean-upload.json",
                (FIXTURES / "demo_graph_edges.json").read_bytes(),
                "application/json",
            )
        },
    )
    assert upload.status_code == 201

    decision = client.post(
        "/decisions",
        json={
            "target_id": "clean-state",
            "label": "Clean state",
            "classification": "monitor",
            "rationale": "Verify parent-safe state writes.",
        },
    )
    assert decision.status_code == 201
    assert client.get("/decisions").status_code == 200

    main._save_recommendation({
        "id": "rec-clean",
        "title": "Clean recommendation",
        "status": "pending",
        "created_at": "2026-06-16T19:32:01-06:00",
    })
    main._save_action({
        "id": "action-clean",
        "description": "Clean action",
        "status": "proposed",
        "created_at": "2026-06-16T19:32:01-06:00",
    })
    main._save_cluster_selection({"sources": ["local"], "clusters": None})

    scan = client.post("/graph/scan-dirs", json={"path": str(scan_dir)})
    assert scan.status_code == 201

    overlap = client.patch(
        "/overlap/status/alpha::beta",
        json={"status": "triaged", "cluster_a": "alpha", "cluster_b": "beta"},
    )
    assert overlap.status_code == 200

    main._save_semantic_edges(
        [{"source": "alpha", "target": "beta", "relation": "semantic_similar"}],
        "test-model",
        0.75,
        "2026-06-16T19:32:01-06:00",
    )
    main._save_sync_status({"sharepoint": {"status": "complete", "item_count": 1}})

    monkeypatch.setattr(
        main,
        "run_graphify_ask",
        lambda **_: SimpleNamespace(
            command="graphify query",
            output="Clean answer\nNODE Clean [src=clean.py loc=L1 community=test]",
        ),
    )
    ask = client.post("/ask", json={"question": "What is clean?", "mode": "query"})
    assert ask.status_code == 200
    session_file = main.SESSIONS_DIR / f"{ask.json()['session_id']}.json"

    chat_config = main.update_chat_config(
        main.ChatConfigBody(system_prompt="Stay grounded.", model="local-balanced:latest")
    )
    assert chat_config["system_prompt"] == "Stay grounded."

    expected_json_files = [
        main.SETTINGS_FILE,
        main.GRAPHS_DIR / "clean-upload.json",
        main.DECISIONS_FILE,
        main.DEVICES_FILE,
        main.RECOMMENDATIONS_DIR / "rec-clean.json",
        main.ACTION_QUEUE_DIR / "action-clean.json",
        main.CLUSTER_SELECTION_FILE,
        main.SCAN_DIRS_FILE,
        main.OVERLAP_STATUS_FILE,
        main.SEMANTIC_EDGES_FILE,
        main.CONNECTORS_DIR / "sync-status.json",
        session_file,
        main.CHAT_CONFIG_FILE,
    ]
    for path in expected_json_files:
        assert path.exists(), f"missing {path}"
        json.loads(path.read_text())

    assert json.loads(main.SETTINGS_FILE.read_text())["graph_path"] == str(
        main.GRAPHS_DIR / "clean-upload.json"
    )
    assert list(state_dir.rglob("*.tmp")) == []
