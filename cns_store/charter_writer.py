"""
CNS store write path for CharterProfile entities.

Ingests a charter as a graph entity and creates relationship edges to Mission,
Agent, Evidence, SourceRef, OKP, and affected-node entities when they already
exist in the store. Never creates placeholder entities.

Graphify is a read/store layer only — it has NO approval or execution authority
over charters.

Call sites: cns_api/routes/charters.py (POST /api/cns/charters)
"""
from __future__ import annotations

import json

from cns_store.db import get_connection, init_db


def ingest_charter_entity(
    db_path: str,
    *,
    charter_id: str,
    title: str,
    authority_level: str,
    autonomy_level: str,
    allowed_action_types: list[str],
    target_resources: str,
    max_actions: int,
    expiry: str,
    stop_conditions: list[str],
    rollback_path: str,
    review_cadence: str,
    evidence_requirements: str,
    connector_scope: list[str] | None = None,
    agent_scope: list[str] | None = None,
    envelope_id: str | None = None,
    charter_status: str = "active",
    mission_id: str | None = None,
    agent_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
    source_ref_ids: list[str] | None = None,
    okp_ids: list[str] | None = None,
    affected_node_ids: list[str] | None = None,
) -> dict:
    """
    Write a CharterProfile as a graph entity to the CNS store.

    Upserts the entity on conflict (charter_id is the primary key).
    Creates relationship edges only when target entities exist:
      - 'authorizes_mission':  charter → mission entity
      - 'scopes_agent':        charter → each agent entity
      - 'requires_evidence':   charter → each evidence entity
      - 'has_source_ref':      charter → each source-ref entity
      - 'produces_okp':        charter → each OKP entity
      - 'affects':             charter → each affected-node entity

    Returns a summary dict: entity_id, relationships_created,
    relationships_skipped.
    """
    init_db(db_path)
    label = f"{title} [{authority_level}]"
    metadata: dict = {
        "title": title,
        "authority_level": authority_level,
        "autonomy_level": autonomy_level,
        "allowed_action_types": allowed_action_types,
        "target_resources": target_resources,
        "max_actions": max_actions,
        "expiry": expiry,
        "stop_conditions": stop_conditions,
        "rollback_path": rollback_path,
        "review_cadence": review_cadence,
        "evidence_requirements": evidence_requirements,
        "charter_status": charter_status,
    }
    if connector_scope is not None:
        metadata["connector_scope"] = connector_scope
    if agent_scope is not None:
        metadata["agent_scope"] = agent_scope
    if envelope_id is not None:
        metadata["envelope_id"] = envelope_id

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = get_connection(db_path)
    rels_created: list[str] = []
    rels_skipped: list[str] = []
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO entities
                    (id, label, kind, repo, path, cluster, importance_tier,
                     metadata_json, created_at, updated_at)
                VALUES (?, ?, 'CharterProfile', 'gail-ai-operating-system-rev-2',
                        ?, 'charter', 'authority', ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    label         = excluded.label,
                    metadata_json = excluded.metadata_json,
                    updated_at    = excluded.updated_at
                """,
                (
                    charter_id,
                    label,
                    "packages/uaos-core/src/gail_ai_operating_system/charter_profile.py",
                    json.dumps(metadata),
                    now,
                    now,
                ),
            )

            # Edge: charter → mission
            if mission_id is not None:
                mission_exists = conn.execute(
                    "SELECT 1 FROM entities WHERE id = ?", (mission_id,)
                ).fetchone()
                if mission_exists:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (id, source_id, target_id, kind, weight, metadata_json, created_at)
                        VALUES (?, ?, ?, 'authorizes_mission', 1.0, '{}', ?)
                        """,
                        (f"rel-{charter_id}-mission", charter_id, mission_id, now),
                    )
                    rels_created.append("to_mission")
                else:
                    rels_skipped.append("to_mission")

            # Edges: charter → agents
            for agent_id in (agent_ids or []):
                agent_exists = conn.execute(
                    "SELECT 1 FROM entities WHERE id = ?", (agent_id,)
                ).fetchone()
                if agent_exists:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (id, source_id, target_id, kind, weight, metadata_json, created_at)
                        VALUES (?, ?, ?, 'scopes_agent', 1.0, '{}', ?)
                        """,
                        (f"rel-{charter_id}-agent-{agent_id}", charter_id, agent_id, now),
                    )
                    rels_created.append(f"to_agent:{agent_id}")
                else:
                    rels_skipped.append(f"to_agent:{agent_id}")

            # Edges: charter → evidence
            for evidence_id in (evidence_ids or []):
                evidence_exists = conn.execute(
                    "SELECT 1 FROM entities WHERE id = ?", (evidence_id,)
                ).fetchone()
                if evidence_exists:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (id, source_id, target_id, kind, weight, metadata_json, created_at)
                        VALUES (?, ?, ?, 'requires_evidence', 1.0, '{}', ?)
                        """,
                        (f"rel-{charter_id}-evidence-{evidence_id}", charter_id, evidence_id, now),
                    )
                    rels_created.append(f"to_evidence:{evidence_id}")
                else:
                    rels_skipped.append(f"to_evidence:{evidence_id}")

            # Edges: charter → source refs
            for source_ref_id in (source_ref_ids or []):
                source_ref_exists = conn.execute(
                    "SELECT 1 FROM entities WHERE id = ?", (source_ref_id,)
                ).fetchone()
                if source_ref_exists:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (id, source_id, target_id, kind, weight, metadata_json, created_at)
                        VALUES (?, ?, ?, 'has_source_ref', 1.0, '{}', ?)
                        """,
                        (f"rel-{charter_id}-srcref-{source_ref_id}", charter_id, source_ref_id, now),
                    )
                    rels_created.append(f"to_source_ref:{source_ref_id}")
                else:
                    rels_skipped.append(f"to_source_ref:{source_ref_id}")

            # Edges: charter → OKPs
            for okp_id in (okp_ids or []):
                okp_exists = conn.execute(
                    "SELECT 1 FROM entities WHERE id = ?", (okp_id,)
                ).fetchone()
                if okp_exists:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (id, source_id, target_id, kind, weight, metadata_json, created_at)
                        VALUES (?, ?, ?, 'produces_okp', 1.0, '{}', ?)
                        """,
                        (f"rel-{charter_id}-okp-{okp_id}", charter_id, okp_id, now),
                    )
                    rels_created.append(f"to_okp:{okp_id}")
                else:
                    rels_skipped.append(f"to_okp:{okp_id}")

            # Edges: charter → affected nodes
            for affected_node_id in (affected_node_ids or []):
                node_exists = conn.execute(
                    "SELECT 1 FROM entities WHERE id = ?", (affected_node_id,)
                ).fetchone()
                if node_exists:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (id, source_id, target_id, kind, weight, metadata_json, created_at)
                        VALUES (?, ?, ?, 'affects', 1.0, '{}', ?)
                        """,
                        (f"rel-{charter_id}-affects-{affected_node_id}", charter_id, affected_node_id, now),
                    )
                    rels_created.append(f"to_affected_node:{affected_node_id}")
                else:
                    rels_skipped.append(f"to_affected_node:{affected_node_id}")

    finally:
        conn.close()

    return {
        "entity_id": charter_id,
        "relationships_created": rels_created,
        "relationships_skipped": rels_skipped,
    }


def get_charter_entity(db_path: str, charter_id: str) -> dict | None:
    """
    Retrieve a CharterProfile entity from the CNS store by charter_id.

    Returns None if not found.
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, label, kind, metadata_json, created_at "
            "FROM entities WHERE id = ?",
            (charter_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    metadata = json.loads(row["metadata_json"])
    return {
        "entity_id": row["id"],
        "found": True,
        "kind": row["kind"],
        "label": row["label"],
        "authority_level": metadata.get("authority_level", ""),
        "charter_status": metadata.get("charter_status", ""),
        "metadata": metadata,
        "created_at": row["created_at"],
    }


def list_charter_entities(
    db_path: str,
    authority_level: str | None = None,
    charter_status: str | None = None,
) -> list[dict]:
    """
    List CharterProfile entities from the CNS store.

    Optional filter by authority_level and/or charter_status (read from
    metadata_json). Returns a list of summary dicts.
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, label, metadata_json, created_at "
            "FROM entities WHERE kind = 'CharterProfile'",
        ).fetchall()
    finally:
        conn.close()

    results: list[dict] = []
    for row in rows:
        metadata = json.loads(row["metadata_json"])
        row_authority = metadata.get("authority_level", "")
        row_status = metadata.get("charter_status", "")

        if authority_level is not None and row_authority != authority_level:
            continue
        if charter_status is not None and row_status != charter_status:
            continue

        results.append({
            "entity_id": row["id"],
            "label": row["label"],
            "authority_level": row_authority,
            "charter_status": row_status,
            "created_at": row["created_at"],
        })

    return results


__all__ = ["ingest_charter_entity", "get_charter_entity", "list_charter_entities"]
