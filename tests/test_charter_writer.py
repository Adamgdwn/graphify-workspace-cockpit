"""Tests for cns_store.charter_writer — CharterProfile entity ingest/retrieval."""
import json
import pytest
from cns_store.db import get_connection, init_db
from cns_store.charter_writer import (
    get_charter_entity,
    ingest_charter_entity,
    list_charter_entities,
)

CHARTER_KWARGS = dict(
    charter_id="charter-r2-001",
    title="M365 Graph Write Charter",
    authority_level="R2",
    autonomy_level="supervised",
    allowed_action_types=["m365.write.planner-task"],
    target_resources="planner-tasks",
    max_actions=10,
    expiry="2026-12-31T23:59:59Z",
    stop_conditions=["error_rate > 5%", "human_revoke"],
    rollback_path="packages/uaos-core/src/rollback.py",
    review_cadence="weekly",
    evidence_requirements="EvidencePacket with result=success",
    charter_status="active",
)


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "charter_test.db")
    init_db(db_path)
    return db_path


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


class TestIngestCharterEntity:
    def test_ingest_creates_entity(self, tmp_db):
        result = ingest_charter_entity(tmp_db, **CHARTER_KWARGS)
        assert result["entity_id"] == CHARTER_KWARGS["charter_id"]
        conn = get_connection(tmp_db)
        row = conn.execute(
            "SELECT id, kind FROM entities WHERE id = ?",
            (CHARTER_KWARGS["charter_id"],),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["kind"] == "CharterProfile"

    def test_get_charter_returns_entity(self, tmp_db):
        ingest_charter_entity(tmp_db, **CHARTER_KWARGS)
        entity = get_charter_entity(tmp_db, CHARTER_KWARGS["charter_id"])
        assert entity is not None
        assert entity["found"] is True
        assert entity["kind"] == "CharterProfile"
        assert entity["authority_level"] == "R2"
        assert entity["charter_status"] == "active"

    def test_get_nonexistent_charter_returns_none(self, tmp_db):
        result = get_charter_entity(tmp_db, "charter-does-not-exist")
        assert result is None

    def test_list_charters_returns_all(self, tmp_db):
        ingest_charter_entity(tmp_db, **CHARTER_KWARGS)
        second = {**CHARTER_KWARGS, "charter_id": "charter-r3-002", "authority_level": "R3"}
        ingest_charter_entity(tmp_db, **second)
        charters = list_charter_entities(tmp_db)
        ids = [c["entity_id"] for c in charters]
        assert "charter-r2-001" in ids
        assert "charter-r3-002" in ids
        assert len(charters) == 2

    def test_list_charters_filtered_by_authority_level(self, tmp_db):
        ingest_charter_entity(tmp_db, **CHARTER_KWARGS)
        second = {**CHARTER_KWARGS, "charter_id": "charter-r3-002", "authority_level": "R3"}
        ingest_charter_entity(tmp_db, **second)
        r2_only = list_charter_entities(tmp_db, authority_level="R2")
        assert len(r2_only) == 1
        assert r2_only[0]["entity_id"] == "charter-r2-001"

    def test_list_charters_filtered_by_charter_status(self, tmp_db):
        ingest_charter_entity(tmp_db, **CHARTER_KWARGS)
        expired = {**CHARTER_KWARGS, "charter_id": "charter-exp-003", "charter_status": "expired"}
        ingest_charter_entity(tmp_db, **expired)
        active_only = list_charter_entities(tmp_db, charter_status="active")
        assert all(c["charter_status"] == "active" for c in active_only)
        expired_only = list_charter_entities(tmp_db, charter_status="expired")
        assert len(expired_only) == 1
        assert expired_only[0]["entity_id"] == "charter-exp-003"

    def test_ingest_with_mission_id_creates_relationship_when_mission_exists(self, tmp_db):
        _seed_entity(tmp_db, "mission-planner-001", "Mission planner-001", "Mission")
        result = ingest_charter_entity(
            tmp_db, **CHARTER_KWARGS, mission_id="mission-planner-001"
        )
        assert "to_mission" in result["relationships_created"]
        assert "to_mission" not in result["relationships_skipped"]
        conn = get_connection(tmp_db)
        rel = conn.execute(
            "SELECT kind FROM relationships WHERE source_id = ? AND target_id = ?",
            (CHARTER_KWARGS["charter_id"], "mission-planner-001"),
        ).fetchone()
        conn.close()
        assert rel is not None
        assert rel["kind"] == "authorizes_mission"

    def test_ingest_with_mission_id_skips_relationship_when_mission_missing(self, tmp_db):
        result = ingest_charter_entity(
            tmp_db, **CHARTER_KWARGS, mission_id="mission-does-not-exist"
        )
        assert "to_mission" in result["relationships_skipped"]
        assert "to_mission" not in result["relationships_created"]

    def test_charter_upsert_updates_existing_entity(self, tmp_db):
        ingest_charter_entity(tmp_db, **CHARTER_KWARGS)
        updated = {**CHARTER_KWARGS, "charter_status": "expired", "title": "Updated Charter"}
        ingest_charter_entity(tmp_db, **updated)
        conn = get_connection(tmp_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE id = ?",
            (CHARTER_KWARGS["charter_id"],),
        ).fetchone()[0]
        row = conn.execute(
            "SELECT metadata_json FROM entities WHERE id = ?",
            (CHARTER_KWARGS["charter_id"],),
        ).fetchone()
        conn.close()
        assert count == 1
        meta = json.loads(row["metadata_json"])
        assert meta["charter_status"] == "expired"
        assert meta["title"] == "Updated Charter"

    def test_ingest_with_agent_ids_creates_scopes_agent_edges(self, tmp_db):
        _seed_entity(tmp_db, "agent-gail-os", "GAIL OS Agent", "Agent")
        result = ingest_charter_entity(
            tmp_db, **CHARTER_KWARGS, agent_ids=["agent-gail-os", "agent-missing"]
        )
        assert any("agent-gail-os" in r for r in result["relationships_created"])
        assert any("agent-missing" in r for r in result["relationships_skipped"])
        conn = get_connection(tmp_db)
        rel = conn.execute(
            "SELECT kind FROM relationships WHERE source_id = ? AND target_id = ?",
            (CHARTER_KWARGS["charter_id"], "agent-gail-os"),
        ).fetchone()
        conn.close()
        assert rel is not None
        assert rel["kind"] == "scopes_agent"
