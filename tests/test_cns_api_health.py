"""Tests for CNS API health endpoint (Chunk 2.4)."""
import pytest
from fastapi.testclient import TestClient
from cns_api.app import create_app
from cns_store.db import init_db
from cns_store.importer import import_graph
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
MINI_GRAPH = str(FIXTURES / "mini_graph.json")


@pytest.fixture
def client_no_store(monkeypatch):
    monkeypatch.delenv("CNS_STORE_PATH", raising=False)
    app = create_app()
    return TestClient(app)


@pytest.fixture
def client_with_store(tmp_path, monkeypatch):
    db_path = str(tmp_path / "health_test.db")
    init_db(db_path)
    import_graph(MINI_GRAPH, db_path)
    monkeypatch.setenv("CNS_STORE_PATH", db_path)
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    def test_returns_200(self, client_no_store):
        response = client_no_store.get("/health")
        assert response.status_code == 200

    def test_store_missing_when_no_env(self, client_no_store):
        response = client_no_store.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["store"] == "missing"
        assert data["node_count"] == 0

    def test_store_connected_with_seeded_db(self, client_with_store):
        response = client_with_store.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["store"] == "connected"
        assert data["node_count"] == 10

    def test_response_shape(self, client_with_store):
        response = client_with_store.get("/health")
        data = response.json()
        assert "status" in data
        assert "store" in data
        assert "node_count" in data
