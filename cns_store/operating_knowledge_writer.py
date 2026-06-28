"""
CNS store write path for OperatingKnowledgePacket (OKP) entities.

Ingests an OKP as a graph entity (kind='OperatingKnowledgePacket',
cluster='operating_knowledge') and creates relationship edges to Mission,
Evidence, Action, Connector, and Agent entities when they already exist in
the store. Never creates placeholder entities.

Also provides SignalGravityL2Enricher — a topology-aware, 9-factor gravity
score calculator that operates on the graph after an OKP is ingested.

Call sites: cns_api/routes/operating_knowledge.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from cns_store.db import get_connection, init_db


# ---------------------------------------------------------------------------
# Writer helpers
# ---------------------------------------------------------------------------

def ingest_okp_entity(db_path: str, *, okp_data: dict) -> dict:
    """
    Upsert an OKP as a graph entity.

    kind='OperatingKnowledgePacket', cluster='operating_knowledge'.

    Expected okp_data keys:
        okp_id, source_system, source_ref, record_type (str), summary,
        authority_level, autonomy_level, risk_tier, data_classification,
        status, created_at (ISO str), observed_at (ISO str), confidence,
        fingerprint, gravity_score_l1 (float|None),
        related_mission_id, related_action_id, related_evidence_id,
        related_connector_id, related_agent_id (all str|None)

    Relationship edges created ONLY when target entity exists:
        'produced_by_mission': okp -> mission
        'wraps_evidence':      okp -> evidence
        'for_action':          okp -> action
        'via_connector':       okp -> connector
        'by_agent':            okp -> agent

    Returns:
        {entity_id, relationships_created, relationships_skipped, edge_count}
    """
    init_db(db_path)

    okp_id = okp_data["okp_id"]
    source_system = okp_data.get("source_system", "")
    source_ref = okp_data.get("source_ref", "")
    record_type = okp_data.get("record_type", "")
    summary = okp_data.get("summary", "")
    created_at = okp_data.get("created_at", datetime.now(timezone.utc).isoformat())

    label = f"{record_type} — {source_system} / {source_ref}"

    metadata: dict = {
        "source_system": source_system,
        "source_ref": source_ref,
        "record_type": record_type,
        "summary": summary,
        "authority_level": okp_data.get("authority_level"),
        "autonomy_level": okp_data.get("autonomy_level"),
        "risk_tier": okp_data.get("risk_tier"),
        "data_classification": okp_data.get("data_classification"),
        "status": okp_data.get("status"),
        "observed_at": okp_data.get("observed_at"),
        "confidence": okp_data.get("confidence"),
        "fingerprint": okp_data.get("fingerprint"),
        "gravity_score_l1": okp_data.get("gravity_score_l1"),
    }

    # Related IDs (optional)
    related_mission_id = okp_data.get("related_mission_id")
    related_action_id = okp_data.get("related_action_id")
    related_evidence_id = okp_data.get("related_evidence_id")
    related_connector_id = okp_data.get("related_connector_id")
    related_agent_id = okp_data.get("related_agent_id")

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
                VALUES (?, ?, 'OperatingKnowledgePacket',
                        'gail-ai-operating-system-rev-2',
                        ?, 'operating_knowledge', 'business', ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    label         = excluded.label,
                    metadata_json = excluded.metadata_json,
                    updated_at    = excluded.updated_at
                """,
                (
                    okp_id,
                    label,
                    f"local_store/operating_knowledge/{okp_id}.json",
                    json.dumps(metadata),
                    created_at,
                    created_at,
                ),
            )

            # Helper: create edge if target exists, else skip
            def _try_edge(
                rel_label: str,
                target_id: Optional[str],
                edge_kind: str,
                rel_id_suffix: str,
            ) -> None:
                if not target_id:
                    rels_skipped.append(rel_label)
                    return
                exists = conn.execute(
                    "SELECT 1 FROM entities WHERE id = ?", (target_id,)
                ).fetchone()
                if exists:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO relationships
                            (id, source_id, target_id, kind, weight,
                             metadata_json, created_at)
                        VALUES (?, ?, ?, ?, 1.0, '{}', ?)
                        """,
                        (
                            f"rel-{okp_id}-{rel_id_suffix}",
                            okp_id,
                            target_id,
                            edge_kind,
                            created_at,
                        ),
                    )
                    rels_created.append(rel_label)
                else:
                    rels_skipped.append(rel_label)

            _try_edge("to_mission", related_mission_id, "produced_by_mission", "mission")
            _try_edge("to_evidence", related_evidence_id, "wraps_evidence", "evidence")
            _try_edge("to_action", related_action_id, "for_action", "action")
            _try_edge("to_connector", related_connector_id, "via_connector", "connector")
            _try_edge("to_agent", related_agent_id, "by_agent", "agent")

    finally:
        conn.close()

    return {
        "entity_id": okp_id,
        "relationships_created": rels_created,
        "relationships_skipped": rels_skipped,
        "edge_count": len(rels_created),
    }


def get_okp_entity(db_path: str, okp_id: str) -> dict | None:
    """Retrieve an OKP entity by okp_id. Returns None if not found."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, label, kind, metadata_json, created_at "
            "FROM entities WHERE id = ?",
            (okp_id,),
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


def get_okp_neighborhood(db_path: str, okp_id: str) -> dict:
    """
    Return OKP entity + all 1-hop relationships (both directions).

    Returns:
        {entity: {...}, neighbors: [{entity_id, kind, relationship_kind}]}
    Returns {"found": False} if OKP does not exist.
    """
    entity = get_okp_entity(db_path, okp_id)
    if entity is None:
        return {"found": False}

    conn = get_connection(db_path)
    neighbors: list[dict] = []
    try:
        # Outbound edges: okp_id is source
        rows = conn.execute(
            """
            SELECT e.id AS entity_id, e.kind, r.kind AS relationship_kind
            FROM relationships r
            JOIN entities e ON e.id = r.target_id
            WHERE r.source_id = ?
            """,
            (okp_id,),
        ).fetchall()
        for row in rows:
            neighbors.append({
                "entity_id": row["entity_id"],
                "kind": row["kind"],
                "relationship_kind": row["relationship_kind"],
                "direction": "outbound",
            })

        # Inbound edges: okp_id is target
        rows = conn.execute(
            """
            SELECT e.id AS entity_id, e.kind, r.kind AS relationship_kind
            FROM relationships r
            JOIN entities e ON e.id = r.source_id
            WHERE r.target_id = ?
            """,
            (okp_id,),
        ).fetchall()
        for row in rows:
            neighbors.append({
                "entity_id": row["entity_id"],
                "kind": row["kind"],
                "relationship_kind": row["relationship_kind"],
                "direction": "inbound",
            })
    finally:
        conn.close()

    return {"entity": entity, "neighbors": neighbors}


# ---------------------------------------------------------------------------
# Signal Gravity L2 Enricher
# ---------------------------------------------------------------------------

_FACTOR_NAMES = [
    "recent_evidence",
    "unresolved_risk",
    "operational_value",
    "repeated_recurrence",
    "pending_authority",
    "connected_blockers",
    "client_impact",
    "prior_failure_relation",
    "strategic_alignment",
]


class SignalGravityL2Enricher:
    """Graph-topology-aware Signal Gravity L2 calculator for OKP entities."""

    @staticmethod
    def enrich(db_path: str, okp_id: str, weights: dict | None = None) -> dict:
        """
        Calculate all 9 Signal Gravity factors from graph topology.

        weights: dict of factor_name -> weight (9 keys, must sum to 1.0).
                 If None, equal weights (1/9 each) are used.

        Returns:
            {
              gravity_score_l2: float (0.0-1.0),
              factor_scores: {factor_name: float},
              factor_weights_used: {factor_name: float}
            }
        """
        # Build weights
        if weights is None:
            w = {k: 1.0 / 9.0 for k in _FACTOR_NAMES}
        else:
            w = {k: float(weights.get(k, 1.0 / 9.0)) for k in _FACTOR_NAMES}

        entity = get_okp_entity(db_path, okp_id)
        if entity is None:
            return {
                "gravity_score_l2": 0.0,
                "factor_scores": {k: 0.0 for k in _FACTOR_NAMES},
                "factor_weights_used": w,
            }

        meta = entity.get("metadata", {})
        conn = get_connection(db_path)
        factor_scores: dict[str, float] = {}

        try:
            # ------------------------------------------------------------------
            # 1. recent_evidence — time decay 1-week (same as L1)
            # ------------------------------------------------------------------
            try:
                created_str = entity.get("created_at", "")
                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                age_days = (now - created_dt).total_seconds() / 86400.0
                decay = max(0.0, 1.0 - age_days / 7.0)
            except (ValueError, TypeError):
                decay = 0.5
            factor_scores["recent_evidence"] = decay

            # ------------------------------------------------------------------
            # 2. unresolved_risk — from risk_tier metadata
            # ------------------------------------------------------------------
            risk_tier = str(meta.get("risk_tier") or "").lower()
            risk_map = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.2}
            factor_scores["unresolved_risk"] = risk_map.get(risk_tier, 0.3)

            # ------------------------------------------------------------------
            # 3. operational_value — from confidence
            # ------------------------------------------------------------------
            try:
                conf = float(meta.get("confidence") or 0.5)
                factor_scores["operational_value"] = max(0.0, min(1.0, conf))
            except (ValueError, TypeError):
                factor_scores["operational_value"] = 0.5

            # ------------------------------------------------------------------
            # 4. repeated_recurrence — edges from entities with same
            #    source_system + record_type cluster
            # ------------------------------------------------------------------
            source_system = meta.get("source_system", "")
            record_type = meta.get("record_type", "")
            peers = conn.execute(
                """
                SELECT COUNT(*) FROM relationships r
                JOIN entities e ON e.id = r.source_id
                WHERE r.target_id = ?
                  AND json_extract(e.metadata_json, '$.source_system') = ?
                  AND json_extract(e.metadata_json, '$.record_type') = ?
                """,
                (okp_id, source_system, record_type),
            ).fetchone()[0]
            factor_scores["repeated_recurrence"] = min(1.0, peers * 0.25)

            # ------------------------------------------------------------------
            # 5. pending_authority — from status / authority_level
            # ------------------------------------------------------------------
            status = str(meta.get("status") or "").lower()
            authority_level = str(meta.get("authority_level") or "").lower()
            pending_keywords = {"pending", "awaiting", "blocked", "review"}
            if any(kw in status for kw in pending_keywords) or any(
                kw in authority_level for kw in pending_keywords
            ):
                factor_scores["pending_authority"] = 0.9
            elif status in {"approved", "complete", "resolved"}:
                factor_scores["pending_authority"] = 0.1
            else:
                factor_scores["pending_authority"] = 0.4

            # ------------------------------------------------------------------
            # 6. connected_blockers — edges to blocker/ConnectorBlocker entities
            # ------------------------------------------------------------------
            blocker_count = conn.execute(
                """
                SELECT COUNT(*) FROM relationships r
                JOIN entities e ON e.id = r.target_id
                WHERE r.source_id = ?
                  AND (LOWER(e.kind) = 'blocker'
                    OR LOWER(e.kind) = 'connectorblocker')
                """,
                (okp_id,),
            ).fetchone()[0]
            factor_scores["connected_blockers"] = min(1.0, blocker_count * 0.5)

            # ------------------------------------------------------------------
            # 7. client_impact — source_system contains 'crm' or 'client'
            # ------------------------------------------------------------------
            ss_lower = source_system.lower()
            if "crm" in ss_lower or "client" in ss_lower:
                factor_scores["client_impact"] = 1.0
            else:
                factor_scores["client_impact"] = 0.3

            # ------------------------------------------------------------------
            # 8. prior_failure_relation — edges to EvidencePacket entities
            #    where result == 'failed' or 'blocked'
            # ------------------------------------------------------------------
            failure_count = conn.execute(
                """
                SELECT COUNT(*) FROM relationships r
                JOIN entities e ON e.id = r.target_id
                WHERE r.source_id = ?
                  AND e.kind = 'EvidencePacket'
                  AND (
                    LOWER(json_extract(e.metadata_json, '$.result')) = 'failed'
                    OR LOWER(json_extract(e.metadata_json, '$.result')) = 'blocked'
                  )
                """,
                (okp_id,),
            ).fetchone()[0]
            factor_scores["prior_failure_relation"] = min(1.0, failure_count * 0.5)

            # ------------------------------------------------------------------
            # 9. strategic_alignment — mission entity exists for
            #    related_mission_id
            # ------------------------------------------------------------------
            related_mission_id = meta.get("related_mission_id") or None
            if related_mission_id:
                mission_exists = conn.execute(
                    "SELECT 1 FROM entities WHERE id = ?", (related_mission_id,)
                ).fetchone()
                factor_scores["strategic_alignment"] = 1.0 if mission_exists else 0.3
            else:
                # Also check outbound produced_by_mission edges
                mission_edge = conn.execute(
                    """
                    SELECT 1 FROM relationships
                    WHERE source_id = ? AND kind = 'produced_by_mission'
                    """,
                    (okp_id,),
                ).fetchone()
                factor_scores["strategic_alignment"] = 1.0 if mission_edge else 0.3

        finally:
            conn.close()

        # Weighted sum -> clamp to [0, 1]
        gravity_l2 = sum(factor_scores[k] * w[k] for k in _FACTOR_NAMES)
        gravity_l2 = max(0.0, min(1.0, gravity_l2))

        return {
            "gravity_score_l2": round(gravity_l2, 6),
            "factor_scores": {k: round(factor_scores[k], 6) for k in _FACTOR_NAMES},
            "factor_weights_used": {k: round(w[k], 9) for k in _FACTOR_NAMES},
        }


__all__ = [
    "ingest_okp_entity",
    "get_okp_entity",
    "get_okp_neighborhood",
    "SignalGravityL2Enricher",
]
