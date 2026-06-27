"""Tests for cns_store importer (Chunk 2.2)."""
import json
import os
import tempfile
import pytest
from pathlib import Path
from cns_store.db import get_connection, init_db
from cns_store.importer import import_graph

FIXTURES = Path(__file__).parent / "fixtures"
MINI_GRAPH = str(FIXTURES / "mini_graph.json")


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test_cns.db")
    init_db(db_path)
    return db_path


class TestImportGraph:
    def test_returns_summary_counts(self, tmp_db):
        result = import_graph(MINI_GRAPH, tmp_db)
        assert result["node_count"] == 10
        assert result["link_count"] == 8

    def test_entities_count_matches(self, tmp_db):
        import_graph(MINI_GRAPH, tmp_db)
        conn = get_connection(tmp_db)
        count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        conn.close()
        assert count == 10

    def test_relationships_count_matches(self, tmp_db):
        import_graph(MINI_GRAPH, tmp_db)
        conn = get_connection(tmp_db)
        count = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        conn.close()
        assert count == 8

    def test_known_entity_is_queryable(self, tmp_db):
        import_graph(MINI_GRAPH, tmp_db)
        conn = get_connection(tmp_db)
        row = conn.execute("SELECT * FROM entities WHERE id='n1'").fetchone()
        conn.close()
        assert row is not None
        assert row["label"] == "main.py"
        assert row["kind"] == "file"
        assert row["repo"] == "my-repo"

    def test_known_relationship_is_queryable(self, tmp_db):
        import_graph(MINI_GRAPH, tmp_db)
        conn = get_connection(tmp_db)
        row = conn.execute(
            "SELECT * FROM relationships WHERE source_id='n1' AND target_id='n2'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["kind"] == "contains"

    def test_store_metadata_written(self, tmp_db):
        import_graph(MINI_GRAPH, tmp_db)
        conn = get_connection(tmp_db)
        meta = {
            row["key"]: row["value"]
            for row in conn.execute("SELECT key, value FROM store_metadata").fetchall()
        }
        conn.close()
        assert meta["node_count"] == "10"
        assert meta["link_count"] == "8"
        assert "imported_at" in meta
        assert meta["imported_from"] == MINI_GRAPH

    def test_idempotent_reimport(self, tmp_db):
        import_graph(MINI_GRAPH, tmp_db)
        import_graph(MINI_GRAPH, tmp_db)
        conn = get_connection(tmp_db)
        count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        conn.close()
        assert count == 10  # not doubled

    def test_importance_tier_preserved(self, tmp_db):
        import_graph(MINI_GRAPH, tmp_db)
        conn = get_connection(tmp_db)
        row = conn.execute(
            "SELECT importance_tier FROM entities WHERE id='n1'"
        ).fetchone()
        conn.close()
        assert row["importance_tier"] == "anchor"

    def test_cross_repo_entity_imported(self, tmp_db):
        import_graph(MINI_GRAPH, tmp_db)
        conn = get_connection(tmp_db)
        row = conn.execute(
            "SELECT repo FROM entities WHERE id='n6'"
        ).fetchone()
        conn.close()
        assert row["repo"] == "other-repo"

    def test_skips_links_with_unknown_nodes(self, tmp_path, tmp_db):
        bad_graph = {
            "nodes": [{"id": "a", "label": "A"}],
            "links": [
                {"source": "a", "target": "a", "relation": "self"},
                {"source": "a", "target": "MISSING", "relation": "broken"},
            ],
        }
        graph_path = str(tmp_path / "bad.json")
        with open(graph_path, "w") as f:
            json.dump(bad_graph, f)

        result = import_graph(graph_path, tmp_db)
        assert result["link_count"] == 1  # only the valid self-link


class TestImportFromRealGraph:
    """Smoke test against the real workspace graph if available."""

    def test_real_graph_import(self, tmp_db):
        real_graph = os.path.join(
            os.path.dirname(__file__),
            "..", "graphify-out", "merged-graph.json"
        )
        if not os.path.exists(real_graph):
            pytest.skip("Real workspace graph not available")

        result = import_graph(real_graph, tmp_db)
        # Real graph should have at least a few hundred nodes
        assert result["node_count"] > 100
        assert result["link_count"] > 0

        conn = get_connection(tmp_db)
        meta = {
            row["key"]: row["value"]
            for row in conn.execute("SELECT key, value FROM store_metadata").fetchall()
        }
        conn.close()
        assert int(meta["node_count"]) == result["node_count"]
