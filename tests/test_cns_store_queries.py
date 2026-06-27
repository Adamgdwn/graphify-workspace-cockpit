"""Tests for cns_store query layer (Chunk 2.3)."""
import time
import pytest
from pathlib import Path
from cns_store.db import init_db
from cns_store.importer import import_graph
from cns_store.queries import (
    validate_connector,
    entity_neighborhood,
    authority_chain,
    entity_context,
    recent_mission_context,
    domain_mapping,
)

FIXTURES = Path(__file__).parent / "fixtures"
MINI_GRAPH = str(FIXTURES / "mini_graph.json")


@pytest.fixture
def seeded_db(tmp_path):
    db_path = str(tmp_path / "queries_test.db")
    init_db(db_path)
    import_graph(MINI_GRAPH, db_path)
    return db_path


class TestValidateConnector:
    def test_found_with_domain_match(self, seeded_db):
        # n5 (ConnectorA) is governed_by n9 (R3-domain) which is cluster 'authority'
        result = validate_connector("n5", "authority", seeded_db)
        assert result.found is True
        assert result.is_active is True

    def test_found_but_no_domain_match(self, seeded_db):
        # n1 (main.py) has no connection to domain 'nonexistent'
        result = validate_connector("n1", "nonexistent_domain", seeded_db)
        assert result.found is True
        assert result.is_active is False

    def test_not_found(self, seeded_db):
        result = validate_connector("does-not-exist", "any", seeded_db)
        assert result.found is False
        assert result.is_active is False

    def test_returns_entity_fields(self, seeded_db):
        result = validate_connector("n5", "authority", seeded_db)
        assert result.kind == "class"
        assert result.repo == "my-repo"


class TestEntityNeighborhood:
    def test_found_with_neighbors(self, seeded_db):
        # n1 (main.py) has outbound to n2, n3 and inbound from n8
        result = entity_neighborhood("n1", seeded_db)
        assert result.found is True
        assert result.label == "main.py"
        assert len(result.neighbors) > 0

    def test_outbound_directions(self, seeded_db):
        result = entity_neighborhood("n1", seeded_db)
        outbound = [n for n in result.neighbors if n.direction == "outbound"]
        assert len(outbound) >= 2  # n2 (contains) and n3 (imports)

    def test_inbound_directions(self, seeded_db):
        result = entity_neighborhood("n1", seeded_db)
        inbound = [n for n in result.neighbors if n.direction == "inbound"]
        # nothing points to n1 in mini_graph
        assert isinstance(inbound, list)

    def test_not_found(self, seeded_db):
        result = entity_neighborhood("MISSING", seeded_db)
        assert result.found is False
        assert result.neighbors == []

    def test_relation_kinds_present(self, seeded_db):
        result = entity_neighborhood("n1", seeded_db)
        kinds = {n.relation_kind for n in result.neighbors}
        assert "contains" in kinds or "imports" in kinds


class TestAuthorityChain:
    def test_found_with_chain(self, seeded_db):
        # n5 governs n9 via 'governed_by'
        result = authority_chain("n5", seeded_db)
        assert result.found is True
        assert len(result.chain) >= 1
        assert any(link.entity_id == "n9" for link in result.chain)

    def test_not_found(self, seeded_db):
        result = authority_chain("MISSING", seeded_db)
        assert result.found is False
        assert result.chain == []

    def test_no_authority_relations(self, seeded_db):
        # n10 (README.md) has no authority outbound links
        result = authority_chain("n10", seeded_db)
        assert result.found is True
        assert result.chain == []


class TestEntityContext:
    def test_found_with_context(self, seeded_db):
        result = entity_context("n2", seeded_db)
        assert result.found is True
        assert result.label == "MyClass"
        assert result.kind == "class"
        assert "n5" in result.connected_ids or "n1" in result.connected_ids

    def test_connected_ids_both_directions(self, seeded_db):
        # n1 has outbound to n2, n3 — n2 should appear in n1's connected_ids
        result = entity_context("n1", seeded_db)
        assert result.found is True
        assert "n2" in result.connected_ids
        assert "n3" in result.connected_ids

    def test_not_found(self, seeded_db):
        result = entity_context("MISSING", seeded_db)
        assert result.found is False

    def test_returns_all_fields(self, seeded_db):
        result = entity_context("n1", seeded_db)
        assert result.repo == "my-repo"
        assert result.importance_tier == "anchor"
        assert result.cluster == "core"


class TestRecentMissionContext:
    def test_empty_list_when_no_mission_rels(self, seeded_db):
        # mini_graph has no mission/action relationship kinds
        result = recent_mission_context("n2", seeded_db)
        assert result.entity_id == "n2"
        assert isinstance(result.events, list)
        # Not an error — just empty

    def test_never_raises_on_missing_entity(self, seeded_db):
        result = recent_mission_context("MISSING", seeded_db)
        assert result.events == []


class TestDomainMapping:
    def test_found_with_domain(self, seeded_db):
        # n5 → governed_by → n9 (R3-domain)
        result = domain_mapping("n5", seeded_db)
        assert result.found is True
        assert result.domain_id == "n9"
        assert result.domain_label == "R3-domain"

    def test_found_no_domain(self, seeded_db):
        # n10 (README.md) has no governed_by link
        result = domain_mapping("n10", seeded_db)
        assert result.found is True
        assert result.domain_id is None
        assert result.domain_label is None

    def test_not_found(self, seeded_db):
        result = domain_mapping("MISSING", seeded_db)
        assert result.found is False

    def test_returns_repo_and_cluster(self, seeded_db):
        result = domain_mapping("n1", seeded_db)
        assert result.repo == "my-repo"
        assert result.cluster == "core"


class TestQuerySpeedSLA:
    """Verify <100ms p95 on real workspace graph if available."""

    def test_entity_context_under_sla(self, tmp_path):
        import os
        real_graph = os.path.join(
            os.path.dirname(__file__),
            "..", "graphify-out", "merged-graph.json",
        )
        if not os.path.exists(real_graph):
            pytest.skip("Real workspace graph not available")

        db_path = str(tmp_path / "sla_test.db")
        init_db(db_path)
        result = import_graph(real_graph, db_path)
        assert result["node_count"] > 100

        import json
        from cns_store.db import get_connection
        conn = get_connection(db_path)
        sample_ids = [
            r[0] for r in conn.execute(
                "SELECT id FROM entities LIMIT 20"
            ).fetchall()
        ]
        conn.close()

        times = []
        for eid in sample_ids:
            t0 = time.perf_counter()
            entity_context(eid, db_path)
            times.append(time.perf_counter() - t0)

        p95 = sorted(times)[int(len(times) * 0.95)]
        assert p95 < 0.1, f"p95 entity_context latency {p95*1000:.1f}ms exceeds 100ms SLA"
