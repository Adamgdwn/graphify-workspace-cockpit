from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend import main


FIXTURES = Path(__file__).parent / "fixtures"
TEST_API_KEY = "test-secret-key"


def _patch_auth_state(monkeypatch, tmp_path: Path, *, api_key: str = TEST_API_KEY) -> Path:
    state_dir = tmp_path / "state"
    demo_graph = tmp_path / "demo" / "graph.json"
    settings_file = state_dir / "settings.json"
    users_file = tmp_path / "users.json"

    demo_graph.parent.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    demo_graph.write_bytes((FIXTURES / "demo_graph_links.json").read_bytes())
    settings_file.write_text(json.dumps({"graph_path": str(demo_graph)}))
    users_file.write_text(json.dumps({TEST_API_KEY: "adam-test"}))

    monkeypatch.setattr(main, "WORKSPACE_STATE", state_dir)
    monkeypatch.setattr(main, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(main, "DECISIONS_FILE", state_dir / "decisions.json")
    monkeypatch.setattr(main, "DEVICES_FILE", state_dir / "devices.json")
    monkeypatch.setattr(main, "_USERS_FILE", users_file)
    monkeypatch.setattr(main, "_DEMO_GRAPH", str(demo_graph))
    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(demo_graph))
    monkeypatch.setattr(main, "API_KEY", api_key)
    monkeypatch.setattr(main, "_graph_cache", None)
    monkeypatch.setattr(main, "_summary_cache", {})
    monkeypatch.setattr(main, "_supabase_client", None)
    return state_dir


def test_api_key_disabled_allows_settings_without_header(monkeypatch, tmp_path: Path) -> None:
    _patch_auth_state(monkeypatch, tmp_path, api_key="")
    client = TestClient(main.app)

    response = client.get("/settings")

    assert response.status_code == 200
    assert response.json()["api_key_required"] is False


def test_api_key_required_blocks_protected_routes_but_not_health(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_auth_state(monkeypatch, tmp_path)
    client = TestClient(main.app)

    health = client.get("/health")
    missing = client.get("/settings")
    wrong = client.get("/settings", headers={"X-API-Key": "wrong-key"})

    assert health.status_code == 200
    assert missing.status_code == 401
    assert missing.json() == {"detail": "Unauthorized"}
    assert wrong.status_code == 401
    assert wrong.json() == {"detail": "Unauthorized"}


def test_api_key_accepts_x_api_key_and_bearer_user_mapping(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_auth_state(monkeypatch, tmp_path)
    client = TestClient(main.app)

    settings = client.get("/settings", headers={"X-API-Key": TEST_API_KEY})
    decision = client.post(
        "/decisions",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={
            "target_id": "auth-contract",
            "label": "Auth contract",
            "classification": "monitor",
            "rationale": "Verify API key middleware accepts bearer auth.",
        },
    )

    assert settings.status_code == 200
    assert settings.json()["api_key_required"] is True
    assert decision.status_code == 201
    assert decision.json()["created_by"] == "adam-test"
