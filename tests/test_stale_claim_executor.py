"""
Tests for cns_store.stale_claim_executor — R4 stale-claim live execution.

All tests use tmp_path SQLite directly — no HTTP calls except for the
FastAPI TestClient test at the end.
"""
from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from cns_api.app import create_app
from cns_store.db import get_connection, init_db
from cns_store.stale_claim_executor import (
    execute_r4_stale_claim_review,
    get_stale_claim_candidates,
    rollback_r4_execution,
    seed_stale_claim_candidates,
)

FIXED_TS = "2026-06-28T12:00:00Z"
CHARTER_ID = "charter-r4-001-graphify-stale-claim"


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


# ---------------------------------------------------------------------------
# seed_stale_claim_candidates
# ---------------------------------------------------------------------------

class TestSeedStaleClaimCandidates:
    def test_seeds_correct_count(self, tmp_db):
        ids = seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        assert len(ids) == 5

    def test_seeds_correct_count_custom(self, tmp_db):
        ids = seed_stale_claim_candidates(tmp_db, count=3, seed_timestamp=FIXED_TS)
        assert len(ids) == 3

    def test_entities_have_correct_kind(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        conn = get_connection(tmp_db)
        rows = conn.execute(
            "SELECT kind FROM entities WHERE kind = 'StaleClaimCandidate'"
        ).fetchall()
        conn.close()
        assert len(rows) == 5
        assert all(r["kind"] == "StaleClaimCandidate" for r in rows)

    def test_metadata_has_correct_status_stale(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        conn = get_connection(tmp_db)
        rows = conn.execute(
            "SELECT metadata_json FROM entities WHERE kind = 'StaleClaimCandidate'"
        ).fetchall()
        conn.close()
        for row in rows:
            metadata = json.loads(row["metadata_json"])
            assert metadata["status"] == "stale"

    def test_entity_ids_are_correct(self, tmp_db):
        ids = seed_stale_claim_candidates(tmp_db, count=3, seed_timestamp=FIXED_TS)
        assert ids == ["claim-r4-001-1", "claim-r4-001-2", "claim-r4-001-3"]

    def test_seed_is_idempotent(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        conn = get_connection(tmp_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE kind = 'StaleClaimCandidate'"
        ).fetchone()[0]
        conn.close()
        assert count == 5


# ---------------------------------------------------------------------------
# get_stale_claim_candidates
# ---------------------------------------------------------------------------

class TestGetStaleClaimCandidates:
    def test_returns_seeded_candidates(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        candidates = get_stale_claim_candidates(tmp_db, max_candidates=5)
        assert len(candidates) == 5
        entity_ids = [c["entity_id"] for c in candidates]
        for i in range(1, 6):
            assert f"claim-r4-001-{i}" in entity_ids

    def test_already_reviewed_claims_excluded(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        # Manually mark one as review_required
        conn = get_connection(tmp_db)
        with conn:
            row = conn.execute(
                "SELECT metadata_json FROM entities WHERE id = 'claim-r4-001-1'"
            ).fetchone()
            metadata = json.loads(row["metadata_json"])
            metadata["status"] = "review_required"
            conn.execute(
                "UPDATE entities SET metadata_json = ? WHERE id = 'claim-r4-001-1'",
                (json.dumps(metadata),),
            )
        conn.close()

        candidates = get_stale_claim_candidates(tmp_db, max_candidates=5)
        ids = [c["entity_id"] for c in candidates]
        assert "claim-r4-001-1" not in ids
        assert len(candidates) == 4

    def test_reviewed_status_excluded(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=3, seed_timestamp=FIXED_TS)
        conn = get_connection(tmp_db)
        with conn:
            row = conn.execute(
                "SELECT metadata_json FROM entities WHERE id = 'claim-r4-001-2'"
            ).fetchone()
            metadata = json.loads(row["metadata_json"])
            metadata["status"] = "reviewed"
            conn.execute(
                "UPDATE entities SET metadata_json = ? WHERE id = 'claim-r4-001-2'",
                (json.dumps(metadata),),
            )
        conn.close()

        candidates = get_stale_claim_candidates(tmp_db, max_candidates=5)
        ids = [c["entity_id"] for c in candidates]
        assert "claim-r4-001-2" not in ids

    def test_max_candidates_limit_respected(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        candidates = get_stale_claim_candidates(tmp_db, max_candidates=3)
        assert len(candidates) <= 3


# ---------------------------------------------------------------------------
# execute_r4_stale_claim_review
# ---------------------------------------------------------------------------

class TestExecuteR4StaleClaimReview:
    def test_action_count_matches_candidate_count(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        assert result["action_count"] == 5

    def test_candidates_reviewed_have_new_status_review_required(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=3, seed_timestamp=FIXED_TS)
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        for reviewed in result["candidates_reviewed"]:
            assert reviewed["new_status"] == "review_required"

    def test_rollback_data_has_prior_status_stale(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        for entry in result["rollback_data"]:
            assert entry["prior_status"] == "stale"

    def test_mutations_persist_in_sqlite(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        conn = get_connection(tmp_db)
        rows = conn.execute(
            "SELECT metadata_json FROM entities WHERE kind = 'StaleClaimCandidate'"
        ).fetchall()
        conn.close()
        for row in rows:
            metadata = json.loads(row["metadata_json"])
            assert metadata["status"] == "review_required"
            assert metadata["reviewed_by_charter"] == CHARTER_ID

    def test_empty_store_returns_action_count_0(self, tmp_db):
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        assert result["action_count"] == 0
        assert result["candidates_reviewed"] == []
        assert result["rollback_data"] == []

    def test_charter_scope_verified_always_true(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        assert result["charter_scope_verified"] is True

    def test_charter_id_in_result(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        assert result["charter_id"] == CHARTER_ID

    def test_max_candidates_limits_action_count(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=3, execution_timestamp=FIXED_TS
        )
        assert result["action_count"] == 3


# ---------------------------------------------------------------------------
# rollback_r4_execution
# ---------------------------------------------------------------------------

class TestRollbackR4Execution:
    def test_reverts_mutations(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        rollback_r4_execution(tmp_db, result["rollback_data"])

        conn = get_connection(tmp_db)
        rows = conn.execute(
            "SELECT metadata_json FROM entities WHERE kind = 'StaleClaimCandidate'"
        ).fetchall()
        conn.close()
        for row in rows:
            metadata = json.loads(row["metadata_json"])
            assert metadata["status"] == "stale"
            assert "reviewed_by_charter" not in metadata

    def test_entities_return_to_prior_status(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=3, seed_timestamp=FIXED_TS)
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        rollback_r4_execution(tmp_db, result["rollback_data"])

        remaining = get_stale_claim_candidates(tmp_db, max_candidates=10)
        assert len(remaining) == 3
        for c in remaining:
            assert c["prior_status"] == "stale"

    def test_returns_correct_count(self, tmp_db):
        seed_stale_claim_candidates(tmp_db, count=5, seed_timestamp=FIXED_TS)
        result = execute_r4_stale_claim_review(
            tmp_db, CHARTER_ID, max_candidates=5, execution_timestamp=FIXED_TS
        )
        rolled_back = rollback_r4_execution(tmp_db, result["rollback_data"])
        assert rolled_back == 5

    def test_rollback_empty_list_returns_0(self, tmp_db):
        rolled_back = rollback_r4_execution(tmp_db, [])
        assert rolled_back == 0


# ---------------------------------------------------------------------------
# HTTP endpoint
# ---------------------------------------------------------------------------

class TestCharterExecuteEndpoint:
    def test_post_execute_returns_200(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        monkeypatch.setenv("CNS_STORE_PATH", db_path)
        monkeypatch.delenv("CNS_API_KEY", raising=False)

        # Seed candidates so the endpoint has something to review
        seed_stale_claim_candidates(db_path, count=5, seed_timestamp=FIXED_TS)

        client = TestClient(create_app())
        resp = client.post(
            f"/api/cns/charters/{CHARTER_ID}/execute",
            json={"max_candidates": 5, "execution_timestamp": FIXED_TS},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_count"] == 5
        assert data["charter_id"] == CHARTER_ID
        assert data["charter_scope_verified"] is True

    def test_post_execute_returns_400_when_no_candidates(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "test.db")
        init_db(db_path)
        monkeypatch.setenv("CNS_STORE_PATH", db_path)
        monkeypatch.delenv("CNS_API_KEY", raising=False)

        client = TestClient(create_app())
        resp = client.post(
            f"/api/cns/charters/{CHARTER_ID}/execute",
            json={"max_candidates": 5},
        )
        assert resp.status_code == 400
