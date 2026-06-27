"""
CNS store query layer — six query patterns for GAIL OS and Freedom.

All queries are read-only SQL against SQLite with proper index coverage.
Speed target: <100ms for single-entity queries, <250ms for neighborhood traversal.
"""
import json
from typing import Optional
from cns_store.db import get_connection
from cns_store.models import (
    ConnectorValidation,
    NeighborhoodNode,
    NeighborhoodResult,
    AuthorityLink,
    AuthorityChain,
    EntityContext,
    MissionEvent,
    MissionHistory,
    DomainInfo,
)

# Relationship kinds that indicate a node acts as a connector/integration point
_CONNECTOR_KINDS = frozenset({"connector", "integration", "adapter", "service", "api"})

# Relationship kinds that indicate governance/authority chains
_AUTHORITY_REL_KINDS = frozenset({
    "governed_by", "authorized_by", "authority", "domain", "governs", "enforces"
})

# Relationship kinds used as mission/action evidence
_MISSION_REL_KINDS = frozenset({
    "mission_target", "action_target", "evidence_for", "resulted_in",
    "executed_on", "observed"
})


# ---------------------------------------------------------------------------
# GAIL OS query 1: Connector scope validation
# ---------------------------------------------------------------------------

def validate_connector(
    connector_id: str,
    domain: str,
    db_path: str,
) -> ConnectorValidation:
    """
    Is connector [connector_id] registered and active for domain [domain]?

    'Active' means: the entity exists and has outbound relationships to any
    entity whose label or cluster matches the domain parameter.
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, label, kind, repo, path FROM entities WHERE id=?",
            (connector_id,),
        ).fetchone()

        if row is None:
            return ConnectorValidation(
                connector_id=connector_id,
                found=False,
                is_active=False,
                domain=domain,
                kind="",
                repo="",
                path="",
            )

        # Check domain match: any outbound relationship to a node in that domain
        domain_match = conn.execute(
            """SELECT COUNT(*) FROM relationships r
               JOIN entities e ON e.id = r.target_id
               WHERE r.source_id = ?
                 AND (e.cluster = ? OR e.label = ? OR e.repo = ?)""",
            (connector_id, domain, domain, domain),
        ).fetchone()[0]

        return ConnectorValidation(
            connector_id=connector_id,
            found=True,
            is_active=domain_match > 0,
            domain=domain,
            kind=row["kind"],
            repo=row["repo"],
            path=row["path"],
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GAIL OS query 2: Entity neighborhood traversal
# ---------------------------------------------------------------------------

def entity_neighborhood(
    entity_id: str,
    db_path: str,
    depth: int = 1,
) -> NeighborhoodResult:
    """
    What entities are adjacent to action target [entity_id]?

    Returns direct neighbors (depth=1). depth>1 not yet supported.
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, label, kind FROM entities WHERE id=?",
            (entity_id,),
        ).fetchone()

        if row is None:
            return NeighborhoodResult(
                entity_id=entity_id,
                found=False,
                label="",
                kind="",
                neighbors=[],
            )

        neighbors = []

        # Outbound: source_id = entity_id
        out_rows = conn.execute(
            """SELECT r.kind AS rel_kind, r.weight, e.id, e.label, e.kind, e.repo, e.path
               FROM relationships r
               JOIN entities e ON e.id = r.target_id
               WHERE r.source_id = ?""",
            (entity_id,),
        ).fetchall()
        for r in out_rows:
            neighbors.append(NeighborhoodNode(
                id=r["id"],
                label=r["label"],
                kind=r["kind"],
                repo=r["repo"],
                path=r["path"],
                relation_kind=r["rel_kind"],
                direction="outbound",
                weight=r["weight"],
            ))

        # Inbound: target_id = entity_id
        in_rows = conn.execute(
            """SELECT r.kind AS rel_kind, r.weight, e.id, e.label, e.kind, e.repo, e.path
               FROM relationships r
               JOIN entities e ON e.id = r.source_id
               WHERE r.target_id = ?""",
            (entity_id,),
        ).fetchall()
        for r in in_rows:
            neighbors.append(NeighborhoodNode(
                id=r["id"],
                label=r["label"],
                kind=r["kind"],
                repo=r["repo"],
                path=r["path"],
                relation_kind=r["rel_kind"],
                direction="inbound",
                weight=r["weight"],
            ))

        return NeighborhoodResult(
            entity_id=entity_id,
            found=True,
            label=row["label"],
            kind=row["kind"],
            neighbors=neighbors,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GAIL OS query 3: Authority chain traceability
# ---------------------------------------------------------------------------

def authority_chain(
    connector_id: str,
    db_path: str,
) -> AuthorityChain:
    """
    What authority chain produced the R-level for this connector?

    Follows authority-kind relationships outbound from the connector.
    """
    conn = get_connection(db_path)
    try:
        exists = conn.execute(
            "SELECT 1 FROM entities WHERE id=?", (connector_id,)
        ).fetchone()

        if exists is None:
            return AuthorityChain(connector_id=connector_id, found=False, chain=[])

        # Walk authority relationships (non-recursive for Phase 2 — depth 3 max)
        chain = []
        seen = {connector_id}
        current_ids = [connector_id]

        for _ in range(3):
            if not current_ids:
                break
            placeholders = ",".join("?" * len(current_ids))
            rows = conn.execute(
                f"""SELECT r.kind AS rel_kind, e.id, e.label, e.kind
                    FROM relationships r
                    JOIN entities e ON e.id = r.target_id
                    WHERE r.source_id IN ({placeholders})
                      AND r.kind IN ({",".join("?" * len(_AUTHORITY_REL_KINDS))})""",
                current_ids + list(_AUTHORITY_REL_KINDS),
            ).fetchall()
            next_ids = []
            for r in rows:
                if r["id"] not in seen:
                    chain.append(AuthorityLink(
                        entity_id=r["id"],
                        label=r["label"],
                        kind=r["kind"],
                        relation_kind=r["rel_kind"],
                    ))
                    seen.add(r["id"])
                    next_ids.append(r["id"])
            current_ids = next_ids

        return AuthorityChain(connector_id=connector_id, found=True, chain=chain)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Freedom query 1: Entity context
# ---------------------------------------------------------------------------

def entity_context(
    entity_id: str,
    db_path: str,
) -> EntityContext:
    """
    What do I know about [entity]? What is it connected to?
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """SELECT id, label, kind, repo, path, cluster, importance_tier,
                      metadata_json
               FROM entities WHERE id=?""",
            (entity_id,),
        ).fetchone()

        if row is None:
            return EntityContext(
                entity_id=entity_id,
                found=False,
                label="",
                kind="",
                repo="",
                path="",
                cluster="",
                importance_tier="",
            )

        # Collect all connected entity IDs (both directions)
        out_ids = [
            r[0] for r in conn.execute(
                "SELECT target_id FROM relationships WHERE source_id=?", (entity_id,)
            ).fetchall()
        ]
        in_ids = [
            r[0] for r in conn.execute(
                "SELECT source_id FROM relationships WHERE target_id=?", (entity_id,)
            ).fetchall()
        ]
        connected_ids = list({*out_ids, *in_ids})

        try:
            metadata = json.loads(row["metadata_json"])
        except (json.JSONDecodeError, TypeError):
            metadata = {}

        return EntityContext(
            entity_id=entity_id,
            found=True,
            label=row["label"],
            kind=row["kind"],
            repo=row["repo"],
            path=row["path"],
            cluster=row["cluster"],
            importance_tier=row["importance_tier"],
            connected_ids=connected_ids,
            metadata=metadata,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Freedom query 2: Recent mission context
# ---------------------------------------------------------------------------

def recent_mission_context(
    entity_id: str,
    db_path: str,
    limit: int = 10,
) -> MissionHistory:
    """
    Has a mission targeting [entity] been attempted recently?

    Pulls entities connected to entity_id via mission/action relationship kinds.
    Returns empty list if no mission relationships exist (not an error).
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            f"""SELECT r.kind AS rel_kind, e.id, e.label, e.kind
                FROM relationships r
                JOIN entities e ON e.id = r.source_id
                WHERE r.target_id = ?
                  AND r.kind IN ({",".join("?" * len(_MISSION_REL_KINDS))})
                LIMIT ?""",
            [entity_id] + list(_MISSION_REL_KINDS) + [limit],
        ).fetchall()

        events = [
            MissionEvent(
                entity_id=r["id"],
                label=r["label"],
                kind=r["kind"],
                relation_kind=r["rel_kind"],
            )
            for r in rows
        ]
        return MissionHistory(entity_id=entity_id, events=events)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Freedom query 3: Domain mapping
# ---------------------------------------------------------------------------

def domain_mapping(
    entity_id: str,
    db_path: str,
) -> DomainInfo:
    """
    Which domain does [entity] belong to? Who governs it?
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, label, repo, cluster FROM entities WHERE id=?",
            (entity_id,),
        ).fetchone()

        if row is None:
            return DomainInfo(
                entity_id=entity_id,
                found=False,
                label="",
                domain_id=None,
                domain_label=None,
                repo="",
                cluster="",
            )

        # Find domain: follow governed_by or authority outbound links to domain-kind nodes
        domain_row = conn.execute(
            f"""SELECT e.id, e.label
                FROM relationships r
                JOIN entities e ON e.id = r.target_id
                WHERE r.source_id = ?
                  AND r.kind IN ({",".join("?" * len(_AUTHORITY_REL_KINDS))})
                LIMIT 1""",
            [entity_id] + list(_AUTHORITY_REL_KINDS),
        ).fetchone()

        return DomainInfo(
            entity_id=entity_id,
            found=True,
            label=row["label"],
            domain_id=domain_row["id"] if domain_row else None,
            domain_label=domain_row["label"] if domain_row else None,
            repo=row["repo"],
            cluster=row["cluster"],
        )
    finally:
        conn.close()
