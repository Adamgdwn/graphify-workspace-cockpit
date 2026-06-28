"""
CNS store write path for EvidencePacket entities.

Ingests a governed action's EvidencePacket as a graph entity and creates
relationship edges to Mission and Connector entities when they already
exist in the store. Never creates placeholder entities.

Call sites: cns_api/routes/evidence.py (POST /api/cns/evidence)
"""
from __future__ import annotations

import json

from cns_store.db import get_connection, init_db


def ingest_evidence_entity(
    db_path: str,
    *,
    evidence_id: str,
    mission_id: str,
    action_id: str,
    actor: str,
    action_type: str,
    authority_basis: str,
    result: str,
    execution_mode: str,
    created_at: str,
    outcome_summary: str,
    connector_id: str | None = None,
) -> dict:
    """
    Write an EvidencePacket as a graph entity to the CNS store.

    Upserts the entity on conflict (evidence_id is the primary key).
    Creates relationship edges only when target entities exist:
      - 'produced_by_mission': evidence → mission entity
      - 'via_connector':       evidence → connector entity

    Returns a summary dict: entity_id, relationships_created,
    relationships_skipped.
    """
    init_db(db_path)
    label = f"{action_type} — {mission_id}"
    metadata: dict = {
        "mission_id": mission_id,
        "action_id": action_id,
        "actor": actor,
        "action_type": action_type,
        "authority_basis": authority_basis,
        "result": result,
        "execution_mode": execution_mode,
        "outcome_summary": outcome_summary,
    }
    if connector_id:
        metadata["connector_id"] = connector_id

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
                VALUES (?, ?, 'EvidencePacket', 'gail-ai-operating-system-rev-2',
                        ?, 'evidence', 'evidence', ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    label         = excluded.label,
                    metadata_json = excluded.metadata_json,
                    updated_at    = excluded.updated_at
                """,
                (
                    evidence_id,
                    label,
                    f"local_store/evidence/{evidence_id}.json",
                    json.dumps(metadata),
                    created_at,
                    created_at,
                ),
            )

            mission_exists = conn.execute(
                "SELECT 1 FROM entities WHERE id = ?", (mission_id,)
            ).fetchone()
            if mission_exists:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO relationships
                        (id, source_id, target_id, kind, weight, metadata_json, created_at)
                    VALUES (?, ?, ?, 'produced_by_mission', 1.0, '{}', ?)
                    """,
                    (f"rel-{evidence_id}-mission", evidence_id, mission_id, created_at),
                )
                rels_created.append("to_mission")
            else:
                rels_skipped.append("to_mission")

            if connector_id:
                connector_exists = conn.execute(
                    "SELECT 1 FROM entities WHERE id = ?", (connector_id,)
                ).fetchone()
                if connector_exists:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (id, source_id, target_id, kind, weight, metadata_json, created_at)
                        VALUES (?, ?, ?, 'via_connector', 1.0, '{}', ?)
                        """,
                        (
                            f"rel-{evidence_id}-connector",
                            evidence_id,
                            connector_id,
                            created_at,
                        ),
                    )
                    rels_created.append("to_connector")
                else:
                    rels_skipped.append("to_connector")
    finally:
        conn.close()

    return {
        "entity_id": evidence_id,
        "relationships_created": rels_created,
        "relationships_skipped": rels_skipped,
    }


def get_evidence_entity(db_path: str, evidence_id: str) -> dict | None:
    """
    Retrieve an EvidencePacket entity from the CNS store by evidence_id.

    Returns None if not found.
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, label, kind, metadata_json, created_at "
            "FROM entities WHERE id = ?",
            (evidence_id,),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return {
        "entity_id": row["id"],
        "found": True,
        "kind": row["kind"],
        "label": row["label"],
        "metadata": json.loads(row["metadata_json"]),
        "created_at": row["created_at"],
    }


__all__ = ["ingest_evidence_entity", "get_evidence_entity"]
