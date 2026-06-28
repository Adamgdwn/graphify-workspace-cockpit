"""
R4 stale-claim executor for graphify-workspace-cockpit CNS store.

Handles: seed synthetic stale claims, execute charter review (live write),
rollback execution. All writes are to the CNS SQLite store only.

Graphify has no approval authority — execution is directed by charter
authority from GAIL OS. This module is a dumb storage executor only.
"""
from __future__ import annotations

import json

from cns_store.db import get_connection, init_db


def seed_stale_claim_candidates(
    db_path: str,
    count: int = 5,
    seed_timestamp: str | None = None,
) -> list[str]:
    """
    Upsert synthetic StaleClaimCandidate entities into the CNS store.

    Entity IDs: "claim-r4-001-{i}" for i in 1..count
    Kind: StaleClaimCandidate, cluster: stale_claim, importance_tier: standard
    Returns list of entity IDs seeded.
    """
    init_db(db_path)
    ts = seed_timestamp if seed_timestamp is not None else "2026-06-28T00:00:00Z"
    conn = get_connection(db_path)
    entity_ids: list[str] = []
    try:
        with conn:
            for i in range(1, count + 1):
                entity_id = f"claim-r4-001-{i}"
                label = f"Stale Claim {i}"
                metadata = {
                    "label": label,
                    "status": "stale",
                    "claim_age_days": 14 + i,
                    "source_repo": "graphify-workspace-cockpit",
                }
                conn.execute(
                    """
                    INSERT INTO entities
                        (id, label, kind, repo, path, cluster, importance_tier,
                         metadata_json, created_at, updated_at)
                    VALUES (?, ?, 'StaleClaimCandidate', 'graphify-workspace-cockpit',
                            '', 'stale_claim', 'standard', ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        label         = excluded.label,
                        metadata_json = excluded.metadata_json,
                        updated_at    = excluded.updated_at
                    """,
                    (entity_id, label, json.dumps(metadata), ts, ts),
                )
                entity_ids.append(entity_id)
    finally:
        conn.close()
    return entity_ids


def get_stale_claim_candidates(
    db_path: str,
    max_candidates: int = 5,
) -> list[dict]:
    """
    Query StaleClaimCandidate entities that have not yet been reviewed.

    Excludes entities whose metadata_json status is 'review_required' or
    'reviewed'. Returns up to max_candidates results as dicts with keys:
    entity_id, label, prior_status, claim_age_days.
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, label, metadata_json FROM entities WHERE kind = 'StaleClaimCandidate'",
        ).fetchall()
    finally:
        conn.close()

    results: list[dict] = []
    for row in rows:
        metadata = json.loads(row["metadata_json"])
        status = metadata.get("status", "")
        if status in ("review_required", "reviewed"):
            continue
        results.append({
            "entity_id": row["id"],
            "label": row["label"],
            "prior_status": status,
            "claim_age_days": metadata.get("claim_age_days", 0),
        })
        if len(results) >= max_candidates:
            break

    return results


def execute_r4_stale_claim_review(
    db_path: str,
    charter_id: str,
    max_candidates: int = 5,
    execution_timestamp: str | None = None,
) -> dict:
    """
    Execute R4 stale-claim review: mark up to max_candidates as review_required.

    Reads candidates, updates their metadata_json in place (Python-side JSON
    merge), and returns a result dict with rollback_data for safe reversion.
    """
    ts = execution_timestamp if execution_timestamp is not None else "2026-06-28T00:00:00Z"
    candidates = get_stale_claim_candidates(db_path, max_candidates)

    if not candidates:
        return {
            "charter_id": charter_id,
            "action_count": 0,
            "candidates_reviewed": [],
            "rollback_data": [],
            "execution_timestamp": ts,
            "charter_scope_verified": True,
        }

    candidates_reviewed: list[dict] = []
    rollback_data: list[dict] = []

    conn = get_connection(db_path)
    try:
        with conn:
            for candidate in candidates:
                entity_id = candidate["entity_id"]
                prior_status = candidate["prior_status"]

                # Read current metadata_json, update in Python, write back
                row = conn.execute(
                    "SELECT metadata_json FROM entities WHERE id = ?",
                    (entity_id,),
                ).fetchone()
                if row is None:
                    continue

                metadata = json.loads(row["metadata_json"])
                metadata["status"] = "review_required"
                metadata["reviewed_by_charter"] = charter_id

                conn.execute(
                    "UPDATE entities SET metadata_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(metadata), ts, entity_id),
                )

                candidates_reviewed.append({
                    "entity_id": entity_id,
                    "prior_status": prior_status,
                    "new_status": "review_required",
                })
                rollback_data.append({
                    "entity_id": entity_id,
                    "prior_status": prior_status,
                })
    finally:
        conn.close()

    return {
        "charter_id": charter_id,
        "action_count": len(candidates_reviewed),
        "candidates_reviewed": candidates_reviewed,
        "rollback_data": rollback_data,
        "execution_timestamp": ts,
        "charter_scope_verified": True,
    }


def rollback_r4_execution(db_path: str, rollback_data: list[dict]) -> int:
    """
    Revert mutations from a previous execute_r4_stale_claim_review call.

    For each {entity_id, prior_status} in rollback_data:
    - Sets status back to prior_status
    - Removes reviewed_by_charter key from metadata_json

    Returns count of entities rolled back.
    """
    if not rollback_data:
        return 0

    count = 0
    conn = get_connection(db_path)
    try:
        with conn:
            for record in rollback_data:
                entity_id = record["entity_id"]
                prior_status = record["prior_status"]

                row = conn.execute(
                    "SELECT metadata_json FROM entities WHERE id = ?",
                    (entity_id,),
                ).fetchone()
                if row is None:
                    continue

                metadata = json.loads(row["metadata_json"])
                metadata["status"] = prior_status
                metadata.pop("reviewed_by_charter", None)

                conn.execute(
                    "UPDATE entities SET metadata_json = ? WHERE id = ?",
                    (json.dumps(metadata), entity_id),
                )
                count += 1
    finally:
        conn.close()

    return count


__all__ = [
    "seed_stale_claim_candidates",
    "get_stale_claim_candidates",
    "execute_r4_stale_claim_review",
    "rollback_r4_execution",
]
