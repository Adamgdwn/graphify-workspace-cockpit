"""Tests for CNS API Freedom endpoints (Chunk 2.6)."""
import time
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from cns_api.app import create_app
from cns_store.db import init_db
from cns_store.importer import import_graph

FIXTURES = Path(__file__).parent / "fixtures"
MINI_GRAPH = str(FIXTURES / "mini_graph.json")


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "freedom_test.db")
    init_db(db_path)
    import_graph(MINI_GRAPH, db_path)
    monkeypatch.setenv("CNS_STORE_PATH", db_path)
    return TestClient(create_app())


class TestEntityContextEndpoint:
    def test_found_returns_200(self, client):
        response = client.get("/api/cns/entity/n1/context")
        assert response.status_code == 200

    def test_response_shape(self, client):
        response = client.get("/api/cns/entity/n1/context")
        data = response.json()
        assert data["entity_id"] == "n1"
        assert data["found"] is True
        assert data["label"] == "main.py"
        assert data["kind"] == "file"
        assert data["repo"] == "my-repo"
        assert "connected_count" in data
        assert "connected_ids" in data
        assert "metadata" in data

    def test_connected_ids_populated(self, client):
        response = client.get("/api/cns/entity/n1/context")
        data = response.json()
        assert data["connected_count"] == len(data["connected_ids"])
        assert data["connected_count"] > 0

    def test_not_found_returns_404(self, client):
        response = client.get("/api/cns/entity/MISSING/context")
        assert response.status_code == 404

    def test_importance_tier_returned(self, client):
        response = client.get("/api/cns/entity/n1/context")
        data = response.json()
        assert data["importance_tier"] == "anchor"

    def test_latency_under_100ms(self, client):
        t0 = time.perf_counter()
        response = client.get("/api/cns/entity/n2/context")
        elapsed = time.perf_counter() - t0
        assert response.status_code == 200
        assert elapsed < 0.1, f"Entity context took {elapsed*1000:.1f}ms"


class TestMissionHistoryEndpoint:
    def test_always_returns_200(self, client):
        # Even for unknown entities — empty list is not an error
        response = client.get("/api/cns/entity/n1/mission-history")
        assert response.status_code == 200

    def test_empty_events_for_entity_with_no_mission_rels(self, client):
        response = client.get("/api/cns/entity/n1/mission-history")
        data = response.json()
        assert data["entity_id"] == "n1"
        assert isinstance(data["events"], list)
        assert data["event_count"] == len(data["events"])

    def test_missing_entity_returns_empty_not_404(self, client):
        # Mission history never 404s — no prior context is a valid state
        response = client.get("/api/cns/entity/MISSING/mission-history")
        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []

    def test_limit_parameter_accepted(self, client):
        response = client.get("/api/cns/entity/n1/mission-history?limit=5")
        assert response.status_code == 200

    def test_limit_out_of_range_returns_422(self, client):
        response = client.get("/api/cns/entity/n1/mission-history?limit=0")
        assert response.status_code == 422


class TestDomainMappingEndpoint:
    def test_found_with_domain(self, client):
        # n5 (ConnectorA) → governed_by → n9 (R3-domain)
        response = client.get("/api/cns/entity/n5/domain")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["entity_id"] == "n5"
        assert data["domain_id"] == "n9"
        assert data["domain_label"] == "R3-domain"

    def test_found_null_domain_when_no_governance(self, client):
        # n10 (README.md) has no governed_by link
        response = client.get("/api/cns/entity/n10/domain")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["domain_id"] is None
        assert data["domain_label"] is None

    def test_not_found_returns_404(self, client):
        response = client.get("/api/cns/entity/MISSING/domain")
        assert response.status_code == 404

    def test_response_includes_repo_and_cluster(self, client):
        response = client.get("/api/cns/entity/n1/domain")
        data = response.json()
        assert data["repo"] == "my-repo"
        assert data["cluster"] == "core"

    def test_all_six_endpoints_reachable(self, client):
        endpoints = [
            "/api/cns/connector/n5/validate?domain=authority",
            "/api/cns/entity/n1/neighborhood",
            "/api/cns/connector/n5/authority-chain",
            "/api/cns/entity/n1/context",
            "/api/cns/entity/n1/mission-history",
            "/api/cns/entity/n1/domain",
        ]
        for url in endpoints:
            r = client.get(url)
            assert r.status_code == 200, f"Endpoint {url} returned {r.status_code}"
