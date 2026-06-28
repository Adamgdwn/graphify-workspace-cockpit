"""
Tests for cns_store/operating_knowledge_writer.py.

Covers: ingest_okp_entity, get_okp_entity, get_okp_neighborhood,
and SignalGravityL2Enricher.
"""
import pytest
from cns_store.db import get_connection, init_db
from cns_store.operating_knowledge_writer import (
    SignalGravityL2Enricher,
    get_okp_entity,
    get_okp_neighborhood,
    ingest_okp_entity,
)

BASE_OKP = {
    "okp_id": "okp-test-001",
    "source_system": "planner",
    "source_ref": "task-abc123",
    "record_type": "TaskObservation",
    "summary": "Task observed in Planner for mission Alpha.",
    "authority_level": "R2_INTERNAL_READ",
    "autonomy_level": "supervised",
    "risk_tier": "medium",
    "data_classification": "internal",
    "status": "active",
    "created_at": "2026-06-28T10:00:00Z",
    "observed_at": "2026-06-28T10:01:00Z",
    "confidence": 0.8,
    "fingerprint": "fp-001",
    "gravity_score_l1": 0.55,
    "related_mission_id": None,
    "related_action_id": None,
    "related_evidence_id": None,
    "related_connector_id": None,
    "related_agent_id": None,
}


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "okp_test.db")
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


# ---------------------------------------------------------------------------
# ingest_okp_entity tests
# ---------------------------------------------------------------------------

def test_okp_entity_created_and_retrievable(db):
    """OKP entity is created and retrievable by okp_id."""
    result = ingest_okp_entity(db, okp_data=BASE_OKP)
    assert result["entity_id"] == "okp-test-001"
    entity = get_okp_entity(db, "okp-test-001")
    assert entity is not None
    assert entity["kind"] == "OperatingKnowledgePacket"


def test_edge_to_mission_created_when_mission_exists(db):
    """Edge to mission is created when mission entity exists."""
    _seed_entity(db, "mission-alpha", "Mission Alpha", "Mission")
    okp = {**BASE_OKP, "related_mission_id": "mission-alpha"}
    result = ingest_okp_entity(db, okp_data=okp)
    assert "to_mission" in result["relationships_created"]
    assert "to_mission" not in result["relationships_skipped"]


def test_edge_to_evidence_created_when_evidence_exists(db):
    """Edge to evidence is created when evidence entity exists."""
    _seed_entity(db, "evidence-xyz", "Evidence XYZ", "EvidencePacket")
    okp = {**BASE_OKP, "related_evidence_id": "evidence-xyz"}
    result = ingest_okp_entity(db, okp_data=okp)
    assert "to_evidence" in result["relationships_created"]


def test_missing_related_entity_does_not_create_placeholder(db):
    """Missing related entity does NOT create placeholder; goes to relationships_skipped."""
    okp = {**BASE_OKP, "related_mission_id": "mission-nonexistent"}
    result = ingest_okp_entity(db, okp_data=okp)
    # The mission entity does not exist — must be skipped, never created
    assert "to_mission" in result["relationships_skipped"]
    conn = get_connection(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM entities WHERE id = ?", ("mission-nonexistent",)
    ).fetchone()[0]
    conn.close()
    assert count == 0


def test_get_okp_entity_returns_none_for_unknown(db):
    """get_okp_entity() returns None for unknown ID."""
    assert get_okp_entity(db, "okp-does-not-exist") is None


def test_ingest_okp_upsert_idempotent(db):
    """Upserting the same OKP twice results in exactly one entity."""
    ingest_okp_entity(db, okp_data=BASE_OKP)
    ingest_okp_entity(db, okp_data=BASE_OKP)
    conn = get_connection(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM entities WHERE id = ?", ("okp-test-001",)
    ).fetchone()[0]
    conn.close()
    assert count == 1


# ---------------------------------------------------------------------------
# get_okp_neighborhood tests
# ---------------------------------------------------------------------------

def test_get_okp_neighborhood_returns_entity_and_neighbors(db):
    """get_okp_neighborhood() returns entity and 1-hop neighbors."""
    _seed_entity(db, "mission-beta", "Mission Beta", "Mission")
    okp = {**BASE_OKP, "related_mission_id": "mission-beta"}
    ingest_okp_entity(db, okp_data=okp)
    result = get_okp_neighborhood(db, "okp-test-001")
    assert "entity" in result
    assert "neighbors" in result
    assert len(result["neighbors"]) >= 1
    neighbor_ids = [n["entity_id"] for n in result["neighbors"]]
    assert "mission-beta" in neighbor_ids


def test_get_okp_neighborhood_returns_found_false_for_missing(db):
    """get_okp_neighborhood() returns {found: False} for unknown OKP."""
    result = get_okp_neighborhood(db, "okp-unknown")
    assert result == {"found": False}


# ---------------------------------------------------------------------------
# SignalGravityL2Enricher tests
# ---------------------------------------------------------------------------

def test_l2_gravity_score_in_range(db):
    """L2 gravity score is in range 0.0-1.0."""
    ingest_okp_entity(db, okp_data=BASE_OKP)
    result = SignalGravityL2Enricher.enrich(db, "okp-test-001")
    assert 0.0 <= result["gravity_score_l2"] <= 1.0


def test_l2_factor_scores_has_all_9_keys(db):
    """L2 factor_scores has all 9 factor keys."""
    ingest_okp_entity(db, okp_data=BASE_OKP)
    result = SignalGravityL2Enricher.enrich(db, "okp-test-001")
    expected_keys = {
        "recent_evidence",
        "unresolved_risk",
        "operational_value",
        "repeated_recurrence",
        "pending_authority",
        "connected_blockers",
        "client_impact",
        "prior_failure_relation",
        "strategic_alignment",
    }
    assert set(result["factor_scores"].keys()) == expected_keys


def test_l2_factor_weights_used_returned(db):
    """factor_weights_used is returned in L2 enricher response."""
    ingest_okp_entity(db, okp_data=BASE_OKP)
    result = SignalGravityL2Enricher.enrich(db, "okp-test-001")
    assert "factor_weights_used" in result
    assert len(result["factor_weights_used"]) == 9
