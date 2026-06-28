"""Tests for POST /api/cns/evidence and GET /api/cns/evidence/{evidence_id}."""
import json
import pytest
from fastapi.testclient import TestClient
from cns_api.app import create_app
from cns_store.db import get_connection, init_db

VALID_BODY = {
    "evidence_id": "evidence-4ab7c9e2f301",
    "mission_id": "mission-planner-001",
    "action_id": "action-create-task",
    "actor": "svc-gail-os-graph",
    "action_type": "m365.write.planner-task",
    "authority_basis": "R2_INTERNAL_WRITE — m365-graph-api-bridge (registry-only) — dry-run",
    "result": "success",
    "execution_mode": "dry-run",
    "created_at": "2026-06-28T12:00:00Z",
    "outcome_summary": "Dry-run Planner task planned. No live Graph call made.",
    "connector_id": "m365-graph-api-bridge",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "evidence_test.db")
    init_db(db_path)
    monkeypatch.setenv("CNS_STORE_PATH", db_path)
    monkeypatch.delenv("CNS_API_KEY", raising=False)
    return TestClient(create_app()), db_path


def _seed_entity(db_path: str, entity_id: str, label: str, kind: str) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO entities "
            "(id, label, kind, repo, path, cluster, importance_tier, "
            " metadata_json, created_at, updated_at) "
            "VALUES (?, ?, ?, 'gail-ai-operating-system-rev-2', '', ?, ?, "
            "        '{}', '2026-06-28T12:00:00Z', '2026-06-28T12:00:00Z')",
            (entity_id, label, kind, kind.lower(), "business"),
        )
    conn.close()


class TestEvidenceIngest:
    def test_ingest_returns_201(self, client):
        c, _ = client
        resp = c.post("/api/cns/evidence", json=VALID_BODY)
        assert resp.status_code == 201

    def test_ingest_response_shape(self, client):
        c, _ = client
        resp = c.post("/api/cns/evidence", json=VALID_BODY)
        data = resp.json()
        assert data["ok"] is True
        assert data["entity_id"] == VALID_BODY["evidence_id"]
        assert isinstance(data["relationships_created"], list)
        assert isinstance(data["relationships_skipped"], list)

    def test_ingest_creates_entity_in_store(self, client):
        c, db_path = client
        c.post("/api/cns/evidence", json=VALID_BODY)
        conn = get_connection(db_path)
        row = conn.execute(
            "SELECT id, kind FROM entities WHERE id = ?",
            (VALID_BODY["evidence_id"],),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["kind"] == "EvidencePacket"

    def test_ingest_entity_metadata_contains_mission_id(self, client):
        c, db_path = client
        c.post("/api/cns/evidence", json=VALID_BODY)
        conn = get_connection(db_path)
        row = conn.execute(
            "SELECT metadata_json FROM entities WHERE id = ?",
            (VALID_BODY["evidence_id"],),
        ).fetchone()
        conn.close()
        meta = json.loads(row["metadata_json"])
        assert meta["mission_id"] == VALID_BODY["mission_id"]
        assert meta["result"] == VALID_BODY["result"]

    def test_ingest_skips_to_mission_when_mission_absent(self, client):
        c, _ = client
        resp = c.post("/api/cns/evidence", json=VALID_BODY)
        data = resp.json()
        assert "to_mission" in data["relationships_skipped"]
        assert "to_mission" not in data["relationships_created"]

    def test_ingest_creates_to_mission_when_mission_exists(self, client):
        c, db_path = client
        _seed_entity(db_path, VALID_BODY["mission_id"], "Mission planner-001", "Mission")
        resp = c.post("/api/cns/evidence", json=VALID_BODY)
        data = resp.json()
        assert "to_mission" in data["relationships_created"]
        assert "to_mission" not in data["relationships_skipped"]

    def test_ingest_upsert_idempotent(self, client):
        c, db_path = client
        c.post("/api/cns/evidence", json=VALID_BODY)
        c.post("/api/cns/evidence", json=VALID_BODY)
        conn = get_connection(db_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE id = ?",
            (VALID_BODY["evidence_id"],),
        ).fetchone()[0]
        conn.close()
        assert count == 1


class TestEvidenceGet:
    def test_get_evidence_returns_entity(self, client):
        c, _ = client
        c.post("/api/cns/evidence", json=VALID_BODY)
        resp = c.get(f"/api/cns/evidence/{VALID_BODY['evidence_id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["kind"] == "EvidencePacket"

    def test_get_evidence_returns_404_when_not_found(self, client):
        c, _ = client
        resp = c.get("/api/cns/evidence/evidence-doesnotexist")
        assert resp.status_code == 404

    def test_get_evidence_entity_has_correct_fields(self, client):
        c, _ = client
        c.post("/api/cns/evidence", json=VALID_BODY)
        resp = c.get(f"/api/cns/evidence/{VALID_BODY['evidence_id']}")
        data = resp.json()
        assert data["entity_id"] == VALID_BODY["evidence_id"]
        assert "m365.write.planner-task" in data["label"]
        assert data["metadata"]["actor"] == VALID_BODY["actor"]
        assert data["created_at"] == VALID_BODY["created_at"]
