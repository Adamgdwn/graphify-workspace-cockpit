"""Tests for GAIL OS GraphFact extraction pipeline (20E)."""
import json
import pytest
from cns_store.db import get_connection, init_db
from cns_store.gail_os_fact_importer import (
    ingest_graph_fact,
    run_extraction,
    validate_graph_fact,
)

TS = "2026-06-28T00:00:00Z"


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def _fact(**overrides):
    base = {
        "fact_id": "gfact-test-001",
        "fact_type": "entity_observed",
        "subject_entity_id": "entity-test-001",
        "subject_entity_type": "Module",
        "emitted_by": "mission_lifecycle",
        "emitted_at": TS,
        "status": "emitted",
        "object_entity_id": None,
        "relationship_kind": None,
        "mission_id": None,
        "action_id": None,
        "evidence_id": None,
        "source_ref_id": None,
        "graph_ref_id": None,
        "sanitized_payload": None,
        "ingestion_notes": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# validate_graph_fact
# ---------------------------------------------------------------------------

class TestValidateGraphFact:
    def test_valid_fact_passes(self):
        ok, reason = validate_graph_fact(_fact())
        assert ok is True
        assert reason == ""

    def test_rejects_missing_fact_id_prefix(self):
        ok, reason = validate_graph_fact(_fact(fact_id="bad-001"))
        assert ok is False
        assert "gfact-" in reason

    def test_rejects_unknown_fact_type(self):
        ok, reason = validate_graph_fact(_fact(fact_type="unknown_type"))
        assert ok is False
        assert "fact_type" in reason

    def test_rejects_empty_subject_entity_id(self):
        ok, reason = validate_graph_fact(_fact(subject_entity_id=""))
        assert ok is False
        assert "subject_entity_id" in reason

    def test_rejects_unregistered_emitter(self):
        ok, reason = validate_graph_fact(_fact(emitted_by="rogue_module"))
        assert ok is False
        assert "emitter" in reason

    def test_rejects_ingested_status(self):
        ok, reason = validate_graph_fact(_fact(status="ingested"))
        assert ok is False
        assert "ingested" in reason or "queued" in reason

    def test_rejects_rejected_status(self):
        ok, reason = validate_graph_fact(_fact(status="rejected"))
        assert ok is False

    def test_accepts_queued_status(self):
        ok, _ = validate_graph_fact(_fact(status="queued"))
        assert ok is True

    def test_rejects_secret_key_in_payload(self):
        ok, reason = validate_graph_fact(_fact(sanitized_payload={"api_key": "abc123"}))
        assert ok is False
        assert "forbidden key" in reason

    def test_rejects_password_key_in_payload(self):
        ok, reason = validate_graph_fact(_fact(sanitized_payload={"db_password": "x"}))
        assert ok is False

    def test_allows_clean_payload(self):
        ok, _ = validate_graph_fact(_fact(sanitized_payload={"label": "My Module", "domain": "auth"}))
        assert ok is True

    def test_rejects_non_dict_payload(self):
        ok, reason = validate_graph_fact(_fact(sanitized_payload=["not", "a", "dict"]))
        assert ok is False
        assert "dict" in reason


# ---------------------------------------------------------------------------
# entity_observed
# ---------------------------------------------------------------------------

class TestEntityObserved:
    def test_creates_entity(self, db):
        result = ingest_graph_fact(db, _fact(
            sanitized_payload={"label": "Auth Module", "domain": "auth"},
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        conn = get_connection(db)
        row = conn.execute(
            "SELECT label, kind FROM entities WHERE id = 'entity-test-001'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["label"] == "Auth Module"
        assert row["kind"] == "Module"

    def test_upserts_on_second_call(self, db):
        ingest_graph_fact(db, _fact(sanitized_payload={"label": "v1"}), ingest_timestamp=TS)
        ingest_graph_fact(db, _fact(
            fact_id="gfact-test-002",
            sanitized_payload={"label": "v2"},
        ), ingest_timestamp=TS)
        conn = get_connection(db)
        count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE id = 'entity-test-001'"
        ).fetchone()[0]
        row = conn.execute(
            "SELECT label FROM entities WHERE id = 'entity-test-001'"
        ).fetchone()
        conn.close()
        assert count == 1
        assert row["label"] == "v2"

    def test_stores_source_fact_id_in_metadata(self, db):
        ingest_graph_fact(db, _fact(), ingest_timestamp=TS)
        conn = get_connection(db)
        row = conn.execute(
            "SELECT metadata_json FROM entities WHERE id = 'entity-test-001'"
        ).fetchone()
        conn.close()
        metadata = json.loads(row["metadata_json"])
        assert metadata["source_fact_id"] == "gfact-test-001"


# ---------------------------------------------------------------------------
# relationship_observed
# ---------------------------------------------------------------------------

class TestRelationshipObserved:
    def test_creates_relationship_when_both_entities_exist(self, db):
        ingest_graph_fact(db, _fact(
            fact_id="gfact-src", subject_entity_id="ent-src",
        ), ingest_timestamp=TS)
        ingest_graph_fact(db, _fact(
            fact_id="gfact-tgt", subject_entity_id="ent-tgt",
        ), ingest_timestamp=TS)
        result = ingest_graph_fact(db, _fact(
            fact_id="gfact-rel-001",
            fact_type="relationship_observed",
            subject_entity_id="ent-src",
            object_entity_id="ent-tgt",
            relationship_kind="DEPENDS_ON",
            emitted_by="connector_registry",
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        conn = get_connection(db)
        row = conn.execute(
            "SELECT kind FROM relationships WHERE source_id = 'ent-src' AND target_id = 'ent-tgt'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["kind"] == "DEPENDS_ON"

    def test_skips_when_object_missing(self, db):
        ingest_graph_fact(db, _fact(fact_id="gfact-src2", subject_entity_id="ent-src2"), ingest_timestamp=TS)
        result = ingest_graph_fact(db, _fact(
            fact_id="gfact-rel-002",
            fact_type="relationship_observed",
            subject_entity_id="ent-src2",
            object_entity_id="ent-missing",
            relationship_kind="DEPENDS_ON",
            emitted_by="connector_registry",
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        assert "skipped" in result["ingestion_notes"]

    def test_skips_when_no_object_entity_id(self, db):
        result = ingest_graph_fact(db, _fact(
            fact_id="gfact-rel-003",
            fact_type="relationship_observed",
            subject_entity_id="ent-x",
            object_entity_id=None,
            relationship_kind="DEPENDS_ON",
            emitted_by="connector_registry",
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        assert "skipped" in result["ingestion_notes"]


# ---------------------------------------------------------------------------
# mission_completed
# ---------------------------------------------------------------------------

class TestMissionCompleted:
    def test_updates_mission_entity(self, db):
        # Seed mission entity
        ingest_graph_fact(db, _fact(
            fact_id="gfact-m1", subject_entity_id="mission-001",
            subject_entity_type="Mission", emitted_by="mission_lifecycle",
        ), ingest_timestamp=TS)
        result = ingest_graph_fact(db, _fact(
            fact_id="gfact-mc-001",
            fact_type="mission_completed",
            subject_entity_id="mission-001",
            mission_id="mission-001",
            emitted_by="mission_lifecycle",
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        conn = get_connection(db)
        row = conn.execute(
            "SELECT metadata_json FROM entities WHERE id = 'mission-001'"
        ).fetchone()
        conn.close()
        metadata = json.loads(row["metadata_json"])
        assert metadata["mission_status"] == "completed"

    def test_links_evidenced_by(self, db):
        ingest_graph_fact(db, _fact(
            fact_id="gfact-m2", subject_entity_id="mission-002",
            subject_entity_type="Mission", emitted_by="mission_lifecycle",
        ), ingest_timestamp=TS)
        # Seed evidence entity
        ingest_graph_fact(db, _fact(
            fact_id="gfact-ev1", subject_entity_id="evidence-001",
            subject_entity_type="EvidencePacket", emitted_by="evidence_recorder",
        ), ingest_timestamp=TS)
        ingest_graph_fact(db, _fact(
            fact_id="gfact-mc-002",
            fact_type="mission_completed",
            subject_entity_id="mission-002",
            mission_id="mission-002",
            evidence_id="evidence-001",
            emitted_by="mission_lifecycle",
        ), ingest_timestamp=TS)
        conn = get_connection(db)
        row = conn.execute(
            "SELECT kind FROM relationships WHERE source_id='mission-002' AND target_id='evidence-001'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["kind"] == "EVIDENCED_BY"


# ---------------------------------------------------------------------------
# evidence_recorded
# ---------------------------------------------------------------------------

class TestEvidenceRecorded:
    def test_creates_evidence_entity(self, db):
        result = ingest_graph_fact(db, _fact(
            fact_id="gfact-evr-001",
            fact_type="evidence_recorded",
            subject_entity_id="evidence-evr-001",
            subject_entity_type="EvidencePacket",
            evidence_id="evidence-evr-001",
            emitted_by="evidence_recorder",
            sanitized_payload={"label": "Test Evidence"},
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        conn = get_connection(db)
        row = conn.execute(
            "SELECT kind, label FROM entities WHERE id = 'evidence-evr-001'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["kind"] == "EvidencePacket"
        assert row["label"] == "Test Evidence"

    def test_links_to_mission_and_action(self, db):
        # Seed mission and action
        ingest_graph_fact(db, _fact(
            fact_id="gfact-m3", subject_entity_id="mission-003",
            subject_entity_type="Mission", emitted_by="mission_lifecycle",
        ), ingest_timestamp=TS)
        ingest_graph_fact(db, _fact(
            fact_id="gfact-a3", subject_entity_id="action-003",
            subject_entity_type="Action", emitted_by="approval_actions",
        ), ingest_timestamp=TS)
        ingest_graph_fact(db, _fact(
            fact_id="gfact-evr-002",
            fact_type="evidence_recorded",
            subject_entity_id="evidence-evr-002",
            evidence_id="evidence-evr-002",
            mission_id="mission-003",
            action_id="action-003",
            emitted_by="evidence_recorder",
        ), ingest_timestamp=TS)
        conn = get_connection(db)
        ev_rel = conn.execute(
            "SELECT kind FROM relationships WHERE source_id='mission-003' AND target_id='evidence-evr-002'"
        ).fetchone()
        act_rel = conn.execute(
            "SELECT kind FROM relationships WHERE source_id='action-003' AND target_id='evidence-evr-002'"
        ).fetchone()
        conn.close()
        assert ev_rel is not None and ev_rel["kind"] == "EVIDENCED_BY"
        assert act_rel is not None and act_rel["kind"] == "PRODUCED_EVIDENCE"


# ---------------------------------------------------------------------------
# connector_registered
# ---------------------------------------------------------------------------

class TestConnectorRegistered:
    def test_creates_connector_entity(self, db):
        result = ingest_graph_fact(db, _fact(
            fact_id="gfact-cr-001",
            fact_type="connector_registered",
            subject_entity_id="connector-001",
            subject_entity_type="Connector",
            emitted_by="connector_registry",
            sanitized_payload={"label": "GitHub Connector"},
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        conn = get_connection(db)
        row = conn.execute(
            "SELECT kind, label FROM entities WHERE id = 'connector-001'"
        ).fetchone()
        conn.close()
        assert row["kind"] == "Connector"
        assert row["label"] == "GitHub Connector"

    def test_creates_governs_edges(self, db):
        # Seed governed entity
        ingest_graph_fact(db, _fact(
            fact_id="gfact-gov1", subject_entity_id="repo-001",
            subject_entity_type="Repository", emitted_by="connector_registry",
        ), ingest_timestamp=TS)
        ingest_graph_fact(db, _fact(
            fact_id="gfact-cr-002",
            fact_type="connector_registered",
            subject_entity_id="connector-002",
            subject_entity_type="Connector",
            emitted_by="connector_registry",
            sanitized_payload={"governed_entity_ids": ["repo-001"]},
        ), ingest_timestamp=TS)
        conn = get_connection(db)
        row = conn.execute(
            "SELECT kind FROM relationships WHERE source_id='connector-002' AND target_id='repo-001'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["kind"] == "GOVERNS"


# ---------------------------------------------------------------------------
# authority_granted
# ---------------------------------------------------------------------------

class TestAuthorityGranted:
    def test_updates_connector_authority_level(self, db):
        ingest_graph_fact(db, _fact(
            fact_id="gfact-ag-seed",
            fact_type="connector_registered",
            subject_entity_id="connector-auth-001",
            subject_entity_type="Connector",
            emitted_by="connector_registry",
        ), ingest_timestamp=TS)
        result = ingest_graph_fact(db, _fact(
            fact_id="gfact-ag-001",
            fact_type="authority_granted",
            subject_entity_id="connector-auth-001",
            emitted_by="authority_engine",
            sanitized_payload={"authority_level": "A2_MEDIUM"},
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        conn = get_connection(db)
        row = conn.execute(
            "SELECT metadata_json FROM entities WHERE id = 'connector-auth-001'"
        ).fetchone()
        conn.close()
        metadata = json.loads(row["metadata_json"])
        assert metadata["authority_level"] == "A2_MEDIUM"

    def test_skips_when_connector_not_found(self, db):
        result = ingest_graph_fact(db, _fact(
            fact_id="gfact-ag-002",
            fact_type="authority_granted",
            subject_entity_id="connector-missing",
            emitted_by="authority_engine",
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        assert "skipped" in result["ingestion_notes"]


# ---------------------------------------------------------------------------
# action_executed
# ---------------------------------------------------------------------------

class TestActionExecuted:
    def test_updates_action_entity(self, db):
        ingest_graph_fact(db, _fact(
            fact_id="gfact-ae-seed",
            subject_entity_id="action-exec-001",
            subject_entity_type="Action",
            emitted_by="approval_actions",
        ), ingest_timestamp=TS)
        result = ingest_graph_fact(db, _fact(
            fact_id="gfact-ae-001",
            fact_type="action_executed",
            subject_entity_id="action-exec-001",
            action_id="action-exec-001",
            emitted_by="approval_actions",
        ), ingest_timestamp=TS)
        assert result["status"] == "ingested"
        conn = get_connection(db)
        row = conn.execute(
            "SELECT metadata_json FROM entities WHERE id = 'action-exec-001'"
        ).fetchone()
        conn.close()
        metadata = json.loads(row["metadata_json"])
        assert metadata["action_status"] == "executed"


# ---------------------------------------------------------------------------
# run_extraction (batch)
# ---------------------------------------------------------------------------

class TestRunExtraction:
    def test_returns_summary(self, db):
        facts = [
            _fact(fact_id=f"gfact-batch-{i:03d}", subject_entity_id=f"ent-batch-{i:03d}")
            for i in range(5)
        ]
        summary = run_extraction(db, facts, ingest_timestamp=TS)
        assert summary["total"] == 5
        assert summary["ingested"] == 5
        assert summary["rejected"] == 0
        assert len(summary["results"]) == 5

    def test_rejects_invalid_facts_in_batch(self, db):
        facts = [
            _fact(fact_id="gfact-good-001"),
            _fact(fact_id="bad-no-prefix"),  # invalid
            _fact(fact_id="gfact-good-002", subject_entity_id="ent-002"),
        ]
        summary = run_extraction(db, facts, ingest_timestamp=TS)
        assert summary["total"] == 3
        assert summary["ingested"] == 2
        assert summary["rejected"] == 1

    def test_idempotent_on_repeated_run(self, db):
        facts = [_fact()]
        run_extraction(db, facts, ingest_timestamp=TS)
        run_extraction(db, facts, ingest_timestamp=TS)
        conn = get_connection(db)
        count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE id = 'entity-test-001'"
        ).fetchone()[0]
        conn.close()
        assert count == 1

    def test_empty_batch(self, db):
        summary = run_extraction(db, [], ingest_timestamp=TS)
        assert summary["total"] == 0
        assert summary["ingested"] == 0
        assert summary["rejected"] == 0
