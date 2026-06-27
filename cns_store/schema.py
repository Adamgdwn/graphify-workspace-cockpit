"""
Schema definitions for the CNS SQLite store.

Tables are created via SQL DDL (not an ORM) to keep the store portable and
cloud-migration friendly. Embedding columns are reserved for Phase 3+ but
not populated in Phase 2.
"""
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Python type representations (used for typing query results)
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    id: str
    label: str
    kind: str
    repo: str
    path: str
    cluster: str
    importance_tier: str
    metadata_json: str
    created_at: str
    updated_at: str


@dataclass
class Relationship:
    id: str
    source_id: str
    target_id: str
    kind: str
    weight: float
    metadata_json: str
    created_at: str


@dataclass
class StoreMetadata:
    key: str
    value: str
    updated_at: str


# ---------------------------------------------------------------------------
# DDL — tables
# ---------------------------------------------------------------------------

ENTITIES_DDL = """
CREATE TABLE IF NOT EXISTS entities (
    id              TEXT NOT NULL PRIMARY KEY,
    label           TEXT NOT NULL,
    kind            TEXT NOT NULL DEFAULT '',
    repo            TEXT NOT NULL DEFAULT '',
    path            TEXT NOT NULL DEFAULT '',
    cluster         TEXT NOT NULL DEFAULT '',
    importance_tier TEXT NOT NULL DEFAULT 'evidence',
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
)
"""

RELATIONSHIPS_DDL = """
CREATE TABLE IF NOT EXISTS relationships (
    id            TEXT NOT NULL PRIMARY KEY,
    source_id     TEXT NOT NULL REFERENCES entities(id),
    target_id     TEXT NOT NULL REFERENCES entities(id),
    kind          TEXT NOT NULL DEFAULT '',
    weight        REAL NOT NULL DEFAULT 1.0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL
)
"""

STORE_METADATA_DDL = """
CREATE TABLE IF NOT EXISTS store_metadata (
    key        TEXT NOT NULL PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

# Reserved for Phase 3+ semantic queries — not populated in Phase 2.
ENTITY_EMBEDDINGS_DDL = """
CREATE TABLE IF NOT EXISTS entity_embeddings (
    entity_id   TEXT NOT NULL PRIMARY KEY REFERENCES entities(id),
    embedding_blob BLOB,
    model       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
)
"""

ALL_TABLES_DDL = [
    ENTITIES_DDL,
    RELATIONSHIPS_DDL,
    STORE_METADATA_DDL,
    ENTITY_EMBEDDINGS_DDL,
]

# ---------------------------------------------------------------------------
# DDL — indexes (for speed SLA: <100ms single relationship query)
# ---------------------------------------------------------------------------

INDEXES_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_entities_kind    ON entities(kind)",
    "CREATE INDEX IF NOT EXISTS idx_entities_repo    ON entities(repo)",
    "CREATE INDEX IF NOT EXISTS idx_entities_label   ON entities(label)",
    "CREATE INDEX IF NOT EXISTS idx_rel_source       ON relationships(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_rel_target       ON relationships(target_id)",
    "CREATE INDEX IF NOT EXISTS idx_rel_kind         ON relationships(kind)",
    "CREATE INDEX IF NOT EXISTS idx_rel_source_kind  ON relationships(source_id, kind)",
    "CREATE INDEX IF NOT EXISTS idx_rel_target_kind  ON relationships(target_id, kind)",
]
