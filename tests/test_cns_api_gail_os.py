"""Tests for CNS API GAIL OS endpoints (Chunk 2.5)."""
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
    db_path = str(tmp_path / "gail_os_test.db")
    init_db(db_path)
    import_graph(MINI_GRAPH, db_path)
    monkeypatch.setenv("CNS_STORE_PATH", db_path)
    return TestClient(create_app())


class TestConnectorValidateEndpoint:
    def test_found_active(self, client):
        # n5 (ConnectorA) → governed_by → n9 (authority cluster)
        response = client.get("/api/cns/connector/n5/validate?domain=authority")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["is_active"] is True
        assert data["connector_id"] == "n5"
        assert data["domain"] == "authority"

    def test_found_inactive(self, client):
        response = client.get("/api/cns/connector/n1/validate?domain=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["is_active"] is False

    def test_not_found_returns_404(self, client):
        response = client.get("/api/cns/connector/MISSING/validate?domain=any")
        assert response.status_code == 404

    def test_missing_domain_query_param(self, client):
        response = client.get("/api/cns/connector/n5/validate")
        assert response.status_code == 422  # FastAPI validation error

    def test_response_includes_kind_and_repo(self, client):
        response = client.get("/api/cns/connector/n5/validate?domain=authority")
        data = response.json()
        assert data["kind"] == "class"
        assert data["repo"] == "my-repo"


class TestEntityNeighborhoodEndpoint:
    def test_found_with_neighbors(self, client):
        response = client.get("/api/cns/entity/n1/neighborhood")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["entity_id"] == "n1"
        assert data["neighbor_count"] > 0
        assert len(data["neighbors"]) == data["neighbor_count"]

    def test_neighbor_has_direction(self, client):
        response = client.get("/api/cns/entity/n1/neighborhood")
        data = response.json()
        directions = {n["direction"] for n in data["neighbors"]}
        assert directions.issubset({"outbound", "inbound"})

    def test_not_found_returns_404(self, client):
        response = client.get("/api/cns/entity/MISSING/neighborhood")
        assert response.status_code == 404

    def test_depth_parameter_accepted(self, client):
        response = client.get("/api/cns/entity/n1/neighborhood?depth=1")
        assert response.status_code == 200

    def test_depth_out_of_range_returns_422(self, client):
        response = client.get("/api/cns/entity/n1/neighborhood?depth=5")
        assert response.status_code == 422

    def test_response_latency_under_100ms(self, client):
        t0 = time.perf_counter()
        response = client.get("/api/cns/entity/n1/neighborhood")
        elapsed = time.perf_counter() - t0
        assert response.status_code == 200
        assert elapsed < 0.1, f"Neighborhood endpoint took {elapsed*1000:.1f}ms"


class TestAuthorityChainEndpoint:
    def test_found_with_chain(self, client):
        response = client.get("/api/cns/connector/n5/authority-chain")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["connector_id"] == "n5"
        assert data["chain_length"] >= 1
        chain_ids = [link["entity_id"] for link in data["chain"]]
        assert "n9" in chain_ids

    def test_found_empty_chain(self, client):
        # n10 (README) has no authority relationships
        response = client.get("/api/cns/connector/n10/authority-chain")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["chain_length"] == 0

    def test_not_found_returns_404(self, client):
        response = client.get("/api/cns/connector/MISSING/authority-chain")
        assert response.status_code == 404

    def test_chain_item_shape(self, client):
        response = client.get("/api/cns/connector/n5/authority-chain")
        data = response.json()
        if data["chain"]:
            item = data["chain"][0]
            assert "entity_id" in item
            assert "label" in item
            assert "kind" in item
            assert "relation_kind" in item
