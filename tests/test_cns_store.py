"""Tests for cns_store schema and connection layer (Chunk 2.1)."""
import os
import sqlite3
import tempfile
import pytest
from cns_store.db import init_db, get_connection, get_store_path


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test_cns.db")
    init_db(db_path)
    return db_path


class TestInitDb:
    def test_creates_entities_table(self, tmp_db):
        conn = get_connection(tmp_db)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entities'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1

    def test_creates_relationships_table(self, tmp_db):
        conn = get_connection(tmp_db)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='relationships'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1

    def test_creates_store_metadata_table(self, tmp_db):
        conn = get_connection(tmp_db)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='store_metadata'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1

    def test_creates_entity_embeddings_table(self, tmp_db):
        conn = get_connection(tmp_db)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entity_embeddings'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1

    def test_creates_indexes(self, tmp_db):
        conn = get_connection(tmp_db)
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        conn.close()
        expected = {
            "idx_entities_kind",
            "idx_entities_repo",
            "idx_entities_label",
            "idx_rel_source",
            "idx_rel_target",
            "idx_rel_kind",
            "idx_rel_source_kind",
            "idx_rel_target_kind",
        }
        assert expected.issubset(indexes)

    def test_idempotent(self, tmp_path):
        db_path = str(tmp_path / "idempotent.db")
        init_db(db_path)
        init_db(db_path)  # second call must not raise


class TestGetConnection:
    def test_row_factory_set(self, tmp_db):
        conn = get_connection(tmp_db)
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_foreign_keys_enabled(self, tmp_db):
        conn = get_connection(tmp_db)
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        conn.close()
        assert result[0] == 1

    def test_wal_mode(self, tmp_db):
        conn = get_connection(tmp_db)
        result = conn.execute("PRAGMA journal_mode").fetchone()
        conn.close()
        assert result[0] == "wal"


class TestEntityRoundtrip:
    def test_insert_and_query_entity(self, tmp_db):
        conn = get_connection(tmp_db)
        now = "2026-06-27T00:00:00"
        conn.execute(
            """INSERT INTO entities
               (id, label, kind, repo, path, cluster, importance_tier,
                metadata_json, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            ("e1", "MyClass", "class", "my-repo", "src/my.py",
             "core", "anchor", "{}", now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM entities WHERE id='e1'").fetchone()
        conn.close()
        assert row["label"] == "MyClass"
        assert row["kind"] == "class"
        assert row["repo"] == "my-repo"

    def test_insert_and_query_relationship(self, tmp_db):
        conn = get_connection(tmp_db)
        now = "2026-06-27T00:00:00"
        for eid, lbl in [("e1", "A"), ("e2", "B")]:
            conn.execute(
                """INSERT INTO entities
                   (id, label, kind, repo, path, cluster, importance_tier,
                    metadata_json, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (eid, lbl, "module", "repo", "", "", "evidence", "{}", now, now),
            )
        conn.execute(
            """INSERT INTO relationships
               (id, source_id, target_id, kind, weight, metadata_json, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            ("r1", "e1", "e2", "imports", 1.0, "{}", now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM relationships WHERE source_id='e1' AND target_id='e2'"
        ).fetchone()
        conn.close()
        assert row["kind"] == "imports"
        assert row["weight"] == 1.0

    def test_store_metadata_roundtrip(self, tmp_db):
        conn = get_connection(tmp_db)
        now = "2026-06-27T00:00:00"
        conn.execute(
            "INSERT INTO store_metadata (key, value, updated_at) VALUES (?,?,?)",
            ("node_count", "42", now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT value FROM store_metadata WHERE key='node_count'"
        ).fetchone()
        conn.close()
        assert row["value"] == "42"


class TestGetStorePath:
    def test_raises_when_not_set(self, monkeypatch):
        monkeypatch.delenv("CNS_STORE_PATH", raising=False)
        with pytest.raises(RuntimeError, match="CNS_STORE_PATH"):
            get_store_path()

    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("CNS_STORE_PATH", "/data/cns.db")
        assert get_store_path() == "/data/cns.db"
