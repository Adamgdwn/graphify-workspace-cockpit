"""
Tests for OKP API routes:
  POST   /api/cns/okp
  GET    /api/cns/okp/{okp_id}
  GET    /api/cns/okp/{okp_id}/proof-chain
  GET    /api/cns/okp/{okp_id}/neighborhood
"""
import pytest
from fastapi.testclient import TestClient
from cns_api.app import create_app
from cns_store.db import init_db

VALID_OKP_BODY = {
    "okp_id": "okp-api-test-001",
    "source_system": "planner",
    "source_ref": "task-api-xyz",
    "record_type": "TaskObservation",
    "summary": "API-level OKP ingest test.",
    "authority_level": "R2_INTERNAL_READ",
    "autonomy_level": "supervised",
    "risk_tier": "low",
    "data_classification": "internal",
    "status": "active",
    "created_at": "2026-06-28T11:00:00Z",
    "observed_at": "2026-06-28T11:01:00Z",
    "confidence": 0.75,
    "fingerprint": "fp-api-001",
    "gravity_score_l1": 0.4,
    "related_mission_id": None,
    "related_action_id": None,
    "related_evidence_id": None,
    "related_connector_id": None,
    "related_agent_id": None,
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "okp_api_test.db")
    init_db(db_path)
    monkeypatch.setenv("CNS_STORE_PATH", db_path)
    monkeypatch.delenv("CNS_API_KEY", raising=False)
    return TestClient(create_app()), db_path


class TestOKPIngestRoute:
    def test_post_okp_returns_201(self, client):
        """POST /api/cns/okp returns 201."""
        c, _ = client
        resp = c.post("/api/cns/okp", json=VALID_OKP_BODY)
        assert resp.status_code == 201

    def test_post_okp_response_has_entity_id_and_gravity_l2(self, client):
        """POST /api/cns/okp returns entity_id and gravity_score_l2."""
        c, _ = client
        resp = c.post("/api/cns/okp", json=VALID_OKP_BODY)
        data = resp.json()
        assert data["ok"] is True
        assert data["entity_id"] == VALID_OKP_BODY["okp_id"]
        assert "gravity_score_l2" in data
        assert isinstance(data["gravity_score_l2"], float)
        assert "factor_scores" in data
        assert len(data["factor_scores"]) == 9


class TestOKPGetRoute:
    def test_get_okp_returns_200_with_entity(self, client):
        """GET /api/cns/okp/{id} returns 200 with entity data."""
        c, _ = client
        c.post("/api/cns/okp", json=VALID_OKP_BODY)
        resp = c.get(f"/api/cns/okp/{VALID_OKP_BODY['okp_id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["kind"] == "OperatingKnowledgePacket"
        assert data["entity_id"] == VALID_OKP_BODY["okp_id"]

    def test_get_okp_missing_id_returns_404(self, client):
        """GET /api/cns/okp/missing-id returns 404."""
        c, _ = client
        resp = c.get("/api/cns/okp/okp-does-not-exist")
        assert resp.status_code == 404


class TestOKPProofChainRoute:
    def test_proof_chain_returns_200_with_version_field(self, client):
        """GET /api/cns/okp/{id}/proof-chain returns 200 with proof_chain_version."""
        c, _ = client
        c.post("/api/cns/okp", json=VALID_OKP_BODY)
        resp = c.get(f"/api/cns/okp/{VALID_OKP_BODY['okp_id']}/proof-chain")
        assert resp.status_code == 200
        data = resp.json()
        assert data["proof_chain_version"] == "stub-l2"
        assert data["okp_id"] == VALID_OKP_BODY["okp_id"]
        assert "gravity_score_l2" in data
        assert "factor_scores" in data


class TestOKPNeighborhoodRoute:
    def test_neighborhood_returns_200(self, client):
        """GET /api/cns/okp/{id}/neighborhood returns 200."""
        c, _ = client
        c.post("/api/cns/okp", json=VALID_OKP_BODY)
        resp = c.get(f"/api/cns/okp/{VALID_OKP_BODY['okp_id']}/neighborhood")
        assert resp.status_code == 200
        data = resp.json()
        assert "entity" in data
        assert "neighbors" in data
