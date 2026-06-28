"""CP-5 Dry-Run Proof — Graphify layer.

Demonstrates the Graphify segment of the operating knowledge flow:
  OperatingKnowledgePacket (evidence.created)
    -> ingest_okp_entity()       -> entity in CNS graph
    -> SignalGravityL2Enricher   -> all 9 factors scored
    -> get_okp_proof_chain stub  -> machine-readable chain data

Uses an isolated SQLite database; no live HTTP, no M365, no Supabase writes.
"""
from __future__ import annotations

import pytest

from cns_store.db import init_db
from cns_store.operating_knowledge_writer import (
    SignalGravityL2Enricher,
    get_okp_entity,
    get_okp_neighborhood,
    ingest_okp_entity,
)

# ---------------------------------------------------------------------------
# Synthetic OKP matching the CP-4 EvidencePacket conversion output
# ---------------------------------------------------------------------------

CP5_OKP = {
    "okp_id": "okp-cp5-proof-001",
    "source_system": "gail-os-evidence",
    "source_ref": "evidence-cp4-planner-001",
    "record_type": "evidence.created",
    "summary": (
        "CP-4 dry-run: GAIL OS wrote a Planner task record to the OS evidence "
        "store via the M365 connector (dry-run mode). No live M365 write occurred."
    ),
    "authority_level": "R1",
    "autonomy_level": "A1",
    "risk_tier": 2,
    "data_classification": "internal",
    "status": "observed",
    "created_at": "2026-06-28T00:00:00+00:00",
    "observed_at": "2026-06-28T00:00:00+00:00",
    "confidence": 0.9,
    "fingerprint": "a1b2c3d4e5f67890a1b2c3d4e5f67890",
    "gravity_score_l1": 0.54,
    "related_mission_id": None,
    "related_action_id": None,
    "related_evidence_id": "evidence-cp4-planner-001",
    "related_connector_id": None,
    "related_agent_id": None,
}


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "cp5_test.db")
    init_db(db_path)
    return db_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_okp_ingested_as_graph_entity(db):
    """OKP ingest creates an OperatingKnowledgePacket entity in the CNS graph."""
    result = ingest_okp_entity(db, okp_data=CP5_OKP)
    assert result["entity_id"] == "okp-cp5-proof-001"
    entity = get_okp_entity(db, "okp-cp5-proof-001")
    assert entity is not None
    assert entity["kind"] == "OperatingKnowledgePacket"


def test_okp_entity_preserves_metadata(db):
    """Ingested entity metadata contains key proof-chain fields."""
    ingest_okp_entity(db, okp_data=CP5_OKP)
    entity = get_okp_entity(db, "okp-cp5-proof-001")
    meta = entity["metadata"]
    assert meta["source_system"] == "gail-os-evidence"
    assert meta["source_ref"] == "evidence-cp4-planner-001"
    assert meta["record_type"] == "evidence.created"
    assert meta["confidence"] == 0.9
    assert meta["gravity_score_l1"] == 0.54


def test_l2_gravity_covers_all_9_factors(db):
    """Signal Gravity L2 enrichment returns scores for all 9 factors."""
    ingest_okp_entity(db, okp_data=CP5_OKP)
    gravity = SignalGravityL2Enricher.enrich(db, "okp-cp5-proof-001")
    factors = gravity["factor_scores"]
    required = [
        "recent_evidence", "unresolved_risk", "operational_value",
        "repeated_recurrence", "pending_authority", "connected_blockers",
        "client_impact", "prior_failure_relation", "strategic_alignment",
    ]
    for name in required:
        assert name in factors, f"Missing factor: {name}"
        assert 0.0 <= factors[name] <= 1.0, f"Factor {name} out of [0,1]"


def test_l2_gravity_score_in_valid_range(db):
    """gravity_score_l2 is clamped to [0.0, 1.0]."""
    ingest_okp_entity(db, okp_data=CP5_OKP)
    gravity = SignalGravityL2Enricher.enrich(db, "okp-cp5-proof-001")
    assert 0.0 <= gravity["gravity_score_l2"] <= 1.0


def test_l2_factor_weights_sum_to_one(db):
    """factor_weights_used sum to 1.0 (equal-weight default)."""
    ingest_okp_entity(db, okp_data=CP5_OKP)
    gravity = SignalGravityL2Enricher.enrich(db, "okp-cp5-proof-001")
    weights = gravity["factor_weights_used"]
    assert len(weights) == 9
    assert abs(sum(weights.values()) - 1.0) < 0.001


def test_no_orphan_edges_for_missing_related_entities(db):
    """Edges to missing related entities are skipped; no placeholder nodes created."""
    result = ingest_okp_entity(db, okp_data=CP5_OKP)
    # related_evidence_id is set but that EvidencePacket entity is not in graph
    # All other related IDs are None
    skipped = result["relationships_skipped"]
    assert len(skipped) > 0  # at least evidence (not in graph) is skipped
    # No entities other than the OKP itself should exist
    from cns_store.db import get_connection
    conn = get_connection(db)
    count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    conn.close()
    assert count == 1  # only the OKP entity


def test_proof_chain_stub_has_gravity_data(db):
    """Proof-chain stub built from Graphify data contains L2 gravity and factor scores."""
    ingest_okp_entity(db, okp_data=CP5_OKP)
    gravity = SignalGravityL2Enricher.enrich(db, "okp-cp5-proof-001")
    entity = get_okp_entity(db, "okp-cp5-proof-001")
    # Assemble stub (matches what the API route returns)
    chain = {
        "okp_id": "okp-cp5-proof-001",
        "entity_id": entity["entity_id"],
        "source_ref": entity["metadata"]["source_ref"],
        "record_type": entity["metadata"]["record_type"],
        "fingerprint": entity["metadata"]["fingerprint"],
        "gravity_score_l2": gravity["gravity_score_l2"],
        "factor_scores": gravity["factor_scores"],
        "proof_chain_version": "v1-l2",
    }
    assert chain["okp_id"] == "okp-cp5-proof-001"
    assert chain["gravity_score_l2"] is not None
    assert len(chain["factor_scores"]) == 9


def test_neighborhood_returns_entity(db):
    """get_okp_neighborhood returns entity data for an existing OKP."""
    ingest_okp_entity(db, okp_data=CP5_OKP)
    result = get_okp_neighborhood(db, "okp-cp5-proof-001")
    assert result.get("found") is not False
    assert "entity" in result


def test_get_entity_returns_none_for_missing(db):
    """get_okp_entity returns None for an OKP that has not been ingested."""
    result = get_okp_entity(db, "okp-does-not-exist")
    assert result is None


def test_upsert_is_idempotent(db):
    """Ingesting the same OKP twice does not create duplicate entities."""
    ingest_okp_entity(db, okp_data=CP5_OKP)
    ingest_okp_entity(db, okp_data=CP5_OKP)
    from cns_store.db import get_connection
    conn = get_connection(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM entities WHERE id = 'okp-cp5-proof-001'"
    ).fetchone()[0]
    conn.close()
    assert count == 1
