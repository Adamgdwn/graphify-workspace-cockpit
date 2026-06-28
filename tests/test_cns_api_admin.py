"""Tests for CNS API admin (ingest trigger) endpoints — Chunk 2.7."""
import json
import os
import tempfile
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from cns_api.app import create_app
from cns_store.db import init_db

FIXTURES = Path(__file__).parent / "fixtures"
MINI_GRAPH = str(FIXTURES / "mini_graph.json")


def _make_graphify_stub() -> str:
    """Platform-native script that copies mini_graph.json to the --output argument."""
    import stat
    suffix = ".cmd" if os.name == "nt" else ".sh"
    stub = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    if os.name == "nt":
        stub.write("@echo off\n")
        stub.write(f'copy /Y "{MINI_GRAPH}" "%~5" >nul\n')
        stub.write("exit /b 0\n")
    else:
        stub.write("#!/bin/bash\n")
        stub.write(f'cp "{MINI_GRAPH}" "${{@: -1}}"\n')
        stub.write("exit 0\n")
    stub.flush()
    os.chmod(stub.name, stat.S_IRWXU)
    stub.close()
    return stub.name


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "admin_test.db")
    init_db(db_path)
    monkeypatch.setenv("CNS_STORE_PATH", db_path)
    monkeypatch.delenv("CNS_API_KEY", raising=False)
    return TestClient(create_app()), str(tmp_path)


@pytest.fixture
def client_with_key(tmp_path, monkeypatch):
    db_path = str(tmp_path / "admin_key_test.db")
    init_db(db_path)
    monkeypatch.setenv("CNS_STORE_PATH", db_path)
    monkeypatch.setenv("CNS_API_KEY", "test-secret-key")
    return TestClient(create_app()), str(tmp_path)


class TestIngestTrigger:
    def test_trigger_returns_202(self, client):
        c, src = client
        stub = _make_graphify_stub()
        try:
            response = c.post("/api/cns/admin/ingest", json={
                "source_path": src,
                "graphify_cmd": stub,
            })
            assert response.status_code == 202
        finally:
            os.unlink(stub)

    def test_trigger_response_shape(self, client):
        c, src = client
        stub = _make_graphify_stub()
        try:
            response = c.post("/api/cns/admin/ingest", json={
                "source_path": src,
                "graphify_cmd": stub,
            })
            data = response.json()
            assert "job_id" in data
            assert data["status"] in ("running", "complete")
            assert data["source_path"] == src
            assert "started_at" in data
        finally:
            os.unlink(stub)

    def test_job_completes_and_is_queryable(self, client):
        c, src = client
        stub = _make_graphify_stub()
        try:
            post_resp = c.post("/api/cns/admin/ingest", json={
                "source_path": src,
                "graphify_cmd": stub,
            })
            job_id = post_resp.json()["job_id"]

            # Poll until complete (max 5s)
            for _ in range(25):
                status_resp = c.get(f"/api/cns/admin/ingest/{job_id}")
                data = status_resp.json()
                if data["status"] in ("complete", "failed"):
                    break
                time.sleep(0.2)

            assert data["status"] == "complete"
            assert data["node_count"] == 10
            assert data["link_count"] == 8
        finally:
            os.unlink(stub)

    def test_unknown_job_returns_404(self, client):
        c, _ = client
        response = c.get("/api/cns/admin/ingest/nonexistent-job-id")
        assert response.status_code == 404

    def test_invalid_source_path_job_fails(self, client):
        c, _ = client
        stub = _make_graphify_stub()
        try:
            post_resp = c.post("/api/cns/admin/ingest", json={
                "source_path": "/does/not/exist",
                "graphify_cmd": stub,
            })
            job_id = post_resp.json()["job_id"]
            # Poll until fail
            for _ in range(15):
                data = c.get(f"/api/cns/admin/ingest/{job_id}").json()
                if data["status"] in ("complete", "failed"):
                    break
                time.sleep(0.2)
            assert data["status"] == "failed"
            assert data["error"] is not None
        finally:
            os.unlink(stub)


class TestAdminApiKeyAuth:
    def test_without_key_returns_401_when_key_configured(self, client_with_key):
        c, src = client_with_key
        response = c.post("/api/cns/admin/ingest", json={"source_path": src})
        assert response.status_code == 401

    def test_with_wrong_key_returns_401(self, client_with_key):
        c, src = client_with_key
        response = c.post(
            "/api/cns/admin/ingest",
            json={"source_path": src},
            headers={"X-Api-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_with_correct_key_returns_202(self, client_with_key):
        c, src = client_with_key
        stub = _make_graphify_stub()
        try:
            response = c.post(
                "/api/cns/admin/ingest",
                json={"source_path": src, "graphify_cmd": stub},
                headers={"X-Api-Key": "test-secret-key"},
            )
            assert response.status_code == 202
        finally:
            os.unlink(stub)
