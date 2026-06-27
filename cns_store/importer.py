"""
JSON graph importer for the CNS SQLite store.

Reads a Graphify graph.json and writes entities + relationships into SQLite.
Import is idempotent: re-importing clears and replaces the store contents.
"""
import json
import hashlib
import os
import sys
from datetime import datetime, timezone
from typing import Any

from cns_store.db import get_connection, init_db


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _node_to_entity_row(node: dict[str, Any], now: str) -> tuple:
    """Map a Graphify JSON node to an entities table row tuple."""
    node_id = str(node["id"])
    label = str(node.get("label") or node.get("name") or node_id)
    kind = str(
        node.get("type")
        or node.get("kind")
        or node.get("node_type")
        or ""
    )
    repo = str(
        node.get("repo")
        or node.get("source_root")
        or node.get("repository")
        or ""
    )
    path = str(node.get("path") or node.get("file") or "")
    cluster = str(node.get("cluster") or node.get("community") or "")
    importance_tier = str(
        node.get("importance_tier")
        or node.get("signal_tier")
        or "evidence"
    )
    # Store remaining fields as metadata JSON
    reserved = {"id", "label", "name", "type", "kind", "node_type",
                 "repo", "source_root", "repository", "path", "file",
                 "cluster", "community", "importance_tier", "signal_tier"}
    metadata = {k: v for k, v in node.items() if k not in reserved}
    metadata_json = json.dumps(metadata, default=str)

    return (node_id, label, kind, repo, path, cluster,
            importance_tier, metadata_json, now, now)


def _link_to_relationship_row(link: dict[str, Any], index: int, now: str) -> tuple:
    """Map a Graphify JSON link to a relationships table row tuple."""
    source = str(link["source"])
    target = str(link["target"])
    kind = str(
        link.get("relation")
        or link.get("type")
        or link.get("kind")
        or link.get("label")
        or "related"
    )
    weight = float(link.get("weight") or link.get("strength") or 1.0)

    # Deterministic ID from source+target+kind to survive re-import
    rel_id = hashlib.md5(
        f"{source}|{target}|{kind}".encode(), usedforsecurity=False
    ).hexdigest()

    reserved = {"source", "target", "relation", "type", "kind", "label", "weight", "strength"}
    metadata = {k: v for k, v in link.items() if k not in reserved}
    metadata_json = json.dumps(metadata, default=str)

    return (rel_id, source, target, kind, weight, metadata_json, now)


def import_graph(graph_json_path: str, db_path: str) -> dict[str, int]:
    """
    Import a Graphify graph.json file into the CNS SQLite store.

    The store is cleared before import (idempotent replace, not append).
    Returns a summary dict with node_count and link_count.
    """
    init_db(db_path)

    with open(graph_json_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    nodes: list[dict] = graph.get("nodes", [])
    links: list[dict] = graph.get("links", []) + graph.get("edges", [])

    now = _now_iso()
    entity_rows = [_node_to_entity_row(n, now) for n in nodes]

    # Build entity id set for FK validation — skip links referencing unknown nodes
    entity_ids = {row[0] for row in entity_rows}
    rel_rows = []
    skipped_links = 0
    for i, link in enumerate(links):
        src = str(link.get("source", ""))
        tgt = str(link.get("target", ""))
        if src not in entity_ids or tgt not in entity_ids:
            skipped_links += 1
            continue
        rel_rows.append(_link_to_relationship_row(link, i, now))

    conn = get_connection(db_path)
    try:
        with conn:
            # Clear existing data before re-import
            conn.execute("DELETE FROM entity_embeddings")
            conn.execute("DELETE FROM relationships")
            conn.execute("DELETE FROM entities")

            conn.executemany(
                """INSERT INTO entities
                   (id, label, kind, repo, path, cluster, importance_tier,
                    metadata_json, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                entity_rows,
            )
            conn.executemany(
                """INSERT INTO relationships
                   (id, source_id, target_id, kind, weight, metadata_json, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                rel_rows,
            )

            # Update store metadata
            for key, value in [
                ("imported_from", graph_json_path),
                ("imported_at", now),
                ("node_count", str(len(entity_rows))),
                ("link_count", str(len(rel_rows))),
                ("skipped_links", str(skipped_links)),
            ]:
                conn.execute(
                    """INSERT INTO store_metadata (key, value, updated_at)
                       VALUES (?,?,?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                       updated_at=excluded.updated_at""",
                    (key, value, now),
                )
    finally:
        conn.close()

    if skipped_links:
        print(
            f"[cns_store] import_graph: {len(entity_rows)} entities, "
            f"{len(rel_rows)} relationships imported "
            f"({skipped_links} links skipped — unknown nodes)",
            file=sys.stderr,
        )
    else:
        print(
            f"[cns_store] import_graph: {len(entity_rows)} entities, "
            f"{len(rel_rows)} relationships imported from {graph_json_path}",
        )

    return {"node_count": len(entity_rows), "link_count": len(rel_rows)}
