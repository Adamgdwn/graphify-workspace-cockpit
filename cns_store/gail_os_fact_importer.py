"""
GAIL OS GraphFact extraction pipeline for the CNS store.

Reads GraphFact records emitted by GAIL OS and writes them into the CNS SQLite
store. This is the only write path for GAIL OS → Graphify data. No HTTP
endpoint accepts GraphFact payloads — extraction pipeline only.

Spec: docs/specs/2026-06-28 - GAIL Graph Fact Import Boundary.md (20E)
Schema: gail-ai-operating-system-rev-2/contracts/json-schema/graph-fact.schema.json
"""
from __future__ import annotations

import json
from typing import Any

from cns_store.db import get_connection, init_db


# ---------------------------------------------------------------------------
# Accepted emitters and fact types (mirror graph-fact.schema.json)
# ---------------------------------------------------------------------------

_ACCEPTED_EMITTERS: frozenset[str] = frozenset({
    "approval_actions",
    "evidence_recorder",
    "mission_lifecycle",
    "connector_registry",
    "policy_gate",
    "authority_engine",
})

_ACCEPTED_FACT_TYPES: frozenset[str] = frozenset({
    "entity_observed",
    "relationship_observed",
    "mission_completed",
    "action_executed",
    "evidence_recorded",
    "connector_registered",
    "authority_granted",
})

_INGESTIBLE_STATUSES: frozenset[str] = frozenset({"emitted", "queued"})

# Keys that signal secrets in sanitized_payload — rejected at the boundary.
# Fragments are matched as substrings of lowercased key names.
# Kept specific to avoid false positives on legitimate fields like "authority_level".
_SECRET_KEY_FRAGMENTS: tuple[str, ...] = (
    "secret", "password", "api_key", "private_key", "credential", "access_token", "bearer",
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_graph_fact(fact: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate a GraphFact dict against the extraction boundary rules.

    Returns (True, "") on success or (False, reason) on failure.
    Does not use the jsonschema package — validates structural rules only.
    """
    if not isinstance(fact, dict):
        return False, "fact must be a dict"

    fact_id = fact.get("fact_id", "")
    if not isinstance(fact_id, str) or not fact_id.startswith("gfact-"):
        return False, f"fact_id must start with 'gfact-', got: {fact_id!r}"

    fact_type = fact.get("fact_type", "")
    if fact_type not in _ACCEPTED_FACT_TYPES:
        return False, f"unknown fact_type: {fact_type!r}"

    subject = fact.get("subject_entity_id", "")
    if not isinstance(subject, str) or not subject:
        return False, "subject_entity_id must be a non-empty string"

    emitted_by = fact.get("emitted_by", "")
    if emitted_by not in _ACCEPTED_EMITTERS:
        return False, f"unregistered emitter: {emitted_by!r}"

    status = fact.get("status", "")
    if status not in _INGESTIBLE_STATUSES:
        return False, f"only 'emitted' or 'queued' facts are accepted, got: {status!r}"

    emitted_at = fact.get("emitted_at", "")
    if not isinstance(emitted_at, str) or not emitted_at:
        return False, "emitted_at must be a non-empty string"

    payload = fact.get("sanitized_payload")
    if payload is not None:
        ok, reason = _sanitization_check(payload)
        if not ok:
            return False, reason

    return True, ""


def _sanitization_check(payload: Any) -> tuple[bool, str]:
    """Reject any payload that contains secret-looking keys."""
    if not isinstance(payload, dict):
        return False, "sanitized_payload must be a dict or null"
    for key in payload:
        key_lower = str(key).lower()
        for fragment in _SECRET_KEY_FRAGMENTS:
            if fragment in key_lower:
                return False, f"sanitized_payload contains forbidden key: {key!r}"
    return True, ""


# ---------------------------------------------------------------------------
# Per-fact-type store handlers
# ---------------------------------------------------------------------------

def _upsert_entity(
    conn: Any,
    entity_id: str,
    label: str,
    kind: str,
    repo: str,
    cluster: str,
    importance_tier: str,
    metadata: dict,
    ts: str,
) -> None:
    conn.execute(
        """
        INSERT INTO entities
            (id, label, kind, repo, path, cluster, importance_tier,
             metadata_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, '', ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            label         = excluded.label,
            metadata_json = excluded.metadata_json,
            updated_at    = excluded.updated_at
        """,
        (entity_id, label, kind, repo, cluster, importance_tier,
         json.dumps(metadata), ts, ts),
    )


def _upsert_relationship(
    conn: Any,
    rel_id: str,
    source_id: str,
    target_id: str,
    kind: str,
    weight: float,
    ts: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO relationships
            (id, source_id, target_id, kind, weight, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, '{}', ?)
        """,
        (rel_id, source_id, target_id, kind, weight, ts),
    )


def _entity_exists(conn: Any, entity_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM entities WHERE id = ?", (entity_id,)
    ).fetchone() is not None


def _handle_entity_observed(conn: Any, fact: dict, ts: str) -> str:
    payload = fact.get("sanitized_payload") or {}
    entity_id = fact["subject_entity_id"]
    kind = fact.get("subject_entity_type", "GailOsEntity")
    label = payload.get("label") or entity_id
    repo = payload.get("repo") or "gail-ai-operating-system-rev-2"
    cluster = payload.get("cluster") or "gail_os"
    importance_tier = payload.get("importance_tier") or "evidence"
    metadata: dict = {k: v for k, v in payload.items()
                      if k not in ("label", "repo", "cluster", "importance_tier")}
    metadata["source_fact_id"] = fact["fact_id"]
    metadata["emitted_by"] = fact["emitted_by"]
    _upsert_entity(conn, entity_id, label, kind, repo, cluster, importance_tier, metadata, ts)
    return f"upserted entity {entity_id}"


def _handle_relationship_observed(conn: Any, fact: dict, ts: str) -> str:
    source_id = fact["subject_entity_id"]
    target_id = fact.get("object_entity_id") or ""
    rel_kind = fact.get("relationship_kind") or "RELATED_TO"
    if not target_id:
        return "skipped: relationship_observed requires object_entity_id"
    if not _entity_exists(conn, source_id) or not _entity_exists(conn, target_id):
        return f"skipped: one or both entities missing ({source_id}, {target_id})"
    rel_id = f"rel-gfact-{source_id}-{rel_kind.lower()}-{target_id}"[:200]
    _upsert_relationship(conn, rel_id, source_id, target_id, rel_kind, 1.0, ts)
    return f"upserted relationship {source_id} -{rel_kind}-> {target_id}"


def _handle_mission_completed(conn: Any, fact: dict, ts: str) -> str:
    mission_id = fact.get("mission_id") or fact["subject_entity_id"]
    payload = fact.get("sanitized_payload") or {}
    notes: list[str] = []

    # Update mission entity if it exists
    row = conn.execute(
        "SELECT metadata_json FROM entities WHERE id = ?", (mission_id,)
    ).fetchone()
    if row:
        metadata = json.loads(row["metadata_json"])
        metadata["mission_status"] = "completed"
        metadata["completed_at"] = ts
        metadata.update({k: v for k, v in payload.items()
                         if k not in ("label",)})
        conn.execute(
            "UPDATE entities SET metadata_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(metadata), ts, mission_id),
        )
        notes.append(f"updated mission {mission_id}")

    # EVIDENCED_BY edge if evidence entity exists
    evidence_id = fact.get("evidence_id")
    if evidence_id and _entity_exists(conn, evidence_id):
        rel_id = f"rel-gfact-{mission_id}-evidenced_by-{evidence_id}"[:200]
        _upsert_relationship(conn, rel_id, mission_id, evidence_id, "EVIDENCED_BY", 1.0, ts)
        notes.append(f"linked EVIDENCED_BY {evidence_id}")

    return "; ".join(notes) if notes else "skipped: mission entity not found"


def _handle_action_executed(conn: Any, fact: dict, ts: str) -> str:
    action_id = fact.get("action_id") or fact["subject_entity_id"]
    payload = fact.get("sanitized_payload") or {}
    notes: list[str] = []

    row = conn.execute(
        "SELECT metadata_json FROM entities WHERE id = ?", (action_id,)
    ).fetchone()
    if row:
        metadata = json.loads(row["metadata_json"])
        metadata["action_status"] = "executed"
        metadata["executed_at"] = ts
        metadata.update({k: v for k, v in payload.items()
                         if k not in ("label",)})
        conn.execute(
            "UPDATE entities SET metadata_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(metadata), ts, action_id),
        )
        notes.append(f"updated action {action_id}")

    mission_id = fact.get("mission_id")
    if mission_id and _entity_exists(conn, mission_id):
        rel_id = f"rel-gfact-{mission_id}-acted_on-{action_id}"[:200]
        _upsert_relationship(conn, rel_id, mission_id, action_id, "ACTED_ON", 1.0, ts)
        notes.append(f"linked ACTED_ON from {mission_id}")

    return "; ".join(notes) if notes else "skipped: action entity not found"


def _handle_evidence_recorded(conn: Any, fact: dict, ts: str) -> str:
    evidence_id = fact.get("evidence_id") or fact["subject_entity_id"]
    payload = fact.get("sanitized_payload") or {}
    notes: list[str] = []

    label = payload.get("label") or evidence_id
    metadata = {k: v for k, v in payload.items() if k != "label"}
    metadata["source_fact_id"] = fact["fact_id"]
    _upsert_entity(
        conn, evidence_id, label, "EvidencePacket",
        "gail-ai-operating-system-rev-2", "evidence", "evidence", metadata, ts,
    )
    notes.append(f"upserted evidence {evidence_id}")

    mission_id = fact.get("mission_id")
    if mission_id and _entity_exists(conn, mission_id):
        rel_id = f"rel-gfact-{mission_id}-evidenced_by-{evidence_id}"[:200]
        _upsert_relationship(conn, rel_id, mission_id, evidence_id, "EVIDENCED_BY", 1.0, ts)
        notes.append(f"linked EVIDENCED_BY from {mission_id}")

    action_id = fact.get("action_id")
    if action_id and _entity_exists(conn, action_id):
        rel_id = f"rel-gfact-{action_id}-produced_evidence-{evidence_id}"[:200]
        _upsert_relationship(conn, rel_id, action_id, evidence_id, "PRODUCED_EVIDENCE", 1.0, ts)
        notes.append(f"linked PRODUCED_EVIDENCE from {action_id}")

    return "; ".join(notes)


def _handle_connector_registered(conn: Any, fact: dict, ts: str) -> str:
    connector_id = fact["subject_entity_id"]
    payload = fact.get("sanitized_payload") or {}
    notes: list[str] = []

    label = payload.get("label") or connector_id
    metadata = {k: v for k, v in payload.items() if k != "label"}
    metadata["source_fact_id"] = fact["fact_id"]
    _upsert_entity(
        conn, connector_id, label, "Connector",
        "gail-ai-operating-system-rev-2", "connector", "authority", metadata, ts,
    )
    notes.append(f"upserted connector {connector_id}")

    governed_ids: list[str] = payload.get("governed_entity_ids") or []
    for governed_id in governed_ids:
        if _entity_exists(conn, governed_id):
            rel_id = f"rel-gfact-{connector_id}-governs-{governed_id}"[:200]
            _upsert_relationship(conn, rel_id, connector_id, governed_id, "GOVERNS", 1.0, ts)
            notes.append(f"linked GOVERNS {governed_id}")

    return "; ".join(notes)


def _handle_authority_granted(conn: Any, fact: dict, ts: str) -> str:
    connector_id = fact["subject_entity_id"]
    payload = fact.get("sanitized_payload") or {}
    notes: list[str] = []

    row = conn.execute(
        "SELECT metadata_json FROM entities WHERE id = ?", (connector_id,)
    ).fetchone()
    if row:
        metadata = json.loads(row["metadata_json"])
        if "authority_level" in payload:
            metadata["authority_level"] = payload["authority_level"]
        metadata["authority_granted_at"] = ts
        metadata["source_fact_id"] = fact["fact_id"]
        conn.execute(
            "UPDATE entities SET metadata_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(metadata), ts, connector_id),
        )
        notes.append(f"updated authority on {connector_id}")

    source_ref_id = fact.get("source_ref_id")
    if source_ref_id and _entity_exists(conn, source_ref_id):
        rel_id = f"rel-gfact-{connector_id}-authorized_by-{source_ref_id}"[:200]
        _upsert_relationship(conn, rel_id, connector_id, source_ref_id, "AUTHORIZED_BY", 1.0, ts)
        notes.append(f"linked AUTHORIZED_BY {source_ref_id}")

    return "; ".join(notes) if notes else "skipped: connector entity not found"


_HANDLERS = {
    "entity_observed": _handle_entity_observed,
    "relationship_observed": _handle_relationship_observed,
    "mission_completed": _handle_mission_completed,
    "action_executed": _handle_action_executed,
    "evidence_recorded": _handle_evidence_recorded,
    "connector_registered": _handle_connector_registered,
    "authority_granted": _handle_authority_granted,
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def ingest_graph_fact(
    db_path: str,
    fact: dict[str, Any],
    ingest_timestamp: str | None = None,
) -> dict[str, Any]:
    """
    Validate and ingest a single GraphFact into the CNS store.

    Returns a result dict:
      fact_id, status ("ingested" | "rejected"), ingestion_notes
    """
    ts = ingest_timestamp or "2026-06-28T00:00:00Z"

    ok, reason = validate_graph_fact(fact)
    if not ok:
        return {
            "fact_id": fact.get("fact_id", "<unknown>"),
            "status": "rejected",
            "ingestion_notes": reason,
        }

    fact_id = fact["fact_id"]
    fact_type = fact["fact_type"]
    handler = _HANDLERS[fact_type]

    conn = get_connection(db_path)
    try:
        with conn:
            notes = handler(conn, fact, ts)
    finally:
        conn.close()

    return {
        "fact_id": fact_id,
        "status": "ingested",
        "ingestion_notes": notes,
    }


def run_extraction(
    db_path: str,
    facts: list[dict[str, Any]],
    ingest_timestamp: str | None = None,
) -> dict[str, Any]:
    """
    Batch-ingest a list of GraphFact records into the CNS store.

    Initializes the store if needed. Returns a summary dict:
      total, ingested, rejected, results (per-fact list)
    """
    ts = ingest_timestamp or "2026-06-28T00:00:00Z"
    init_db(db_path)

    results: list[dict] = []
    for fact in facts:
        result = ingest_graph_fact(db_path, fact, ingest_timestamp=ts)
        results.append(result)

    ingested = sum(1 for r in results if r["status"] == "ingested")
    rejected = sum(1 for r in results if r["status"] == "rejected")

    return {
        "total": len(facts),
        "ingested": ingested,
        "rejected": rejected,
        "results": results,
    }


__all__ = ["validate_graph_fact", "ingest_graph_fact", "run_extraction"]
