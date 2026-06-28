"""Tests for POST /api/cns/charters, GET /api/cns/charters/{id}, and GET /api/cns/charters."""
import pytest
from fastapi.testclient import TestClient
from cns_api.app import create_app
from cns_store.db import get_connection, init_db

VALID_BODY = {
    "charter_id": "charter-api-test-001",
    "title": "API Test Charter",
    "authority_level": "R2",
    "autonomy_level": "supervised",
    "allowed_action_types": ["m365.write.planner-task"],
    "target_resources": "planner-tasks",
    "max_actions": 5,
    "expiry": "2026-12-31T23:59:59Z",
    "stop_conditions": ["error_rate > 5%"],
    "rollback_path": "packages/uaos-core/src/rollback.py",
    "review_cadence": "weekly",
    "evidence_requirements": "EvidencePacket with result=success",
    "charter_status": "active",
}

SECOND_CHARTER = {
    **VALID_BODY,
    "charter_id": "charter-api-test-002",
    "title": "Second Test Charter",
    "authority_level": "R3",
    "charter_status": "active",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "charter_api_test.db")
    init_db(db_path)
    monkeypatch.setenv("CNS_STORE_PATH", db_path)
    monkeypatch.delenv("CNS_API_KEY", raising=False)
    return TestClient(create_app()), db_path


class TestCharterIngest:
    def test_post_charters_returns_201(self, client):
        c, _ = client
        resp = c.post("/api/cns/charters", json=VALID_BODY)
        assert resp.status_code == 201

    def test_post_charters_response_shape(self, client):
        c, _ = client
        resp = c.post("/api/cns/charters", json=VALID_BODY)
        data = resp.json()
        assert data["ok"] is True
        assert data["entity_id"] == VALID_BODY["charter_id"]
        assert isinstance(data["relationships_created"], list)
        assert isinstance(data["relationships_skipped"], list)

    def test_post_charters_creates_entity_in_store(self, client):
        c, db_path = client
        c.post("/api/cns/charters", json=VALID_BODY)
        conn = get_connection(db_path)
        row = conn.execute(
            "SELECT id, kind FROM entities WHERE id = ?",
            (VALID_BODY["charter_id"],),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["kind"] == "CharterProfile"

    def test_post_charters_upsert_idempotent(self, client):
        c, db_path = client
        c.post("/api/cns/charters", json=VALID_BODY)
        c.post("/api/cns/charters", json=VALID_BODY)
        conn = get_connection(db_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE id = ?",
            (VALID_BODY["charter_id"],),
        ).fetchone()[0]
        conn.close()
        assert count == 1


class TestCharterGet:
    def test_get_charter_returns_200(self, client):
        c, _ = client
        c.post("/api/cns/charters", json=VALID_BODY)
        resp = c.get(f"/api/cns/charters/{VALID_BODY['charter_id']}")
        assert resp.status_code == 200

    def test_get_charter_returns_correct_data(self, client):
        c, _ = client
        c.post("/api/cns/charters", json=VALID_BODY)
        resp = c.get(f"/api/cns/charters/{VALID_BODY['charter_id']}")
        data = resp.json()
        assert data["found"] is True
        assert data["entity_id"] == VALID_BODY["charter_id"]
        assert data["kind"] == "CharterProfile"
        assert data["authority_level"] == "R2"
        assert data["charter_status"] == "active"
        assert data["metadata"]["title"] == VALID_BODY["title"]

    def test_get_charter_returns_404_for_unknown(self, client):
        c, _ = client
        resp = c.get("/api/cns/charters/charter-does-not-exist")
        assert resp.status_code == 404


class TestCharterList:
    def test_get_charters_returns_list(self, client):
        c, _ = client
        c.post("/api/cns/charters", json=VALID_BODY)
        c.post("/api/cns/charters", json=SECOND_CHARTER)
        resp = c.get("/api/cns/charters")
        assert resp.status_code == 200
        data = resp.json()
        assert "charters" in data
        assert "count" in data
        assert data["count"] == 2
        ids = [ch["entity_id"] for ch in data["charters"]]
        assert VALID_BODY["charter_id"] in ids
        assert SECOND_CHARTER["charter_id"] in ids

    def test_get_charters_filter_by_authority_level(self, client):
        c, _ = client
        c.post("/api/cns/charters", json=VALID_BODY)
        c.post("/api/cns/charters", json=SECOND_CHARTER)
        resp = c.get("/api/cns/charters?authority_level=R2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["charters"][0]["entity_id"] == VALID_BODY["charter_id"]

    def test_get_charters_empty_list(self, client):
        c, _ = client
        resp = c.get("/api/cns/charters")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["charters"] == []

    def test_get_charters_filter_by_charter_status(self, client):
        c, _ = client
        c.post("/api/cns/charters", json=VALID_BODY)
        expired = {**VALID_BODY, "charter_id": "charter-expired-001", "charter_status": "expired"}
        c.post("/api/cns/charters", json=expired)
        resp = c.get("/api/cns/charters?charter_status=expired")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["charters"][0]["charter_status"] == "expired"
