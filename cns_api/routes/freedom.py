"""
Freedom query endpoints for the CNS API.

Three read-only endpoints that Freedom calls before proposing missions:
1. Entity context enrichment
2. Recent mission context
3. Domain mapping
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from cns_api.config import get_store_path
from cns_store.queries import entity_context, recent_mission_context, domain_mapping

router = APIRouter(prefix="/api/cns", tags=["freedom"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class EntityContextResponse(BaseModel):
    entity_id: str
    found: bool
    label: str
    kind: str
    repo: str
    path: str
    cluster: str
    importance_tier: str
    connected_count: int
    connected_ids: list[str]
    metadata: dict


class MissionEventItem(BaseModel):
    entity_id: str
    label: str
    kind: str
    relation_kind: str


class MissionHistoryResponse(BaseModel):
    entity_id: str
    event_count: int
    events: list[MissionEventItem]


class DomainInfoResponse(BaseModel):
    entity_id: str
    found: bool
    label: str
    domain_id: Optional[str]
    domain_label: Optional[str]
    repo: str
    cluster: str


# ---------------------------------------------------------------------------
# Endpoint 4: Entity context
# ---------------------------------------------------------------------------

@router.get(
    "/entity/{entity_id}/context",
    response_model=EntityContextResponse,
)
def entity_context_endpoint(entity_id: str) -> EntityContextResponse:
    """
    What do I know about [entity]? What is it connected to?

    Returns 404 if the entity is not in the store.
    """
    result = entity_context(entity_id, get_store_path())
    if not result.found:
        raise HTTPException(
            status_code=404,
            detail=f"Entity '{entity_id}' not found in CNS store",
        )
    return EntityContextResponse(
        entity_id=result.entity_id,
        found=result.found,
        label=result.label,
        kind=result.kind,
        repo=result.repo,
        path=result.path,
        cluster=result.cluster,
        importance_tier=result.importance_tier,
        connected_count=len(result.connected_ids),
        connected_ids=result.connected_ids,
        metadata=result.metadata,
    )


# ---------------------------------------------------------------------------
# Endpoint 5: Recent mission context
# ---------------------------------------------------------------------------

@router.get(
    "/entity/{entity_id}/mission-history",
    response_model=MissionHistoryResponse,
)
def mission_history_endpoint(
    entity_id: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> MissionHistoryResponse:
    """
    Has a mission targeting [entity] been attempted recently?

    Always returns 200 — empty list when no mission relationships exist.
    This is not an error condition; it means Freedom has no prior context.
    """
    result = recent_mission_context(entity_id, get_store_path(), limit=limit)
    return MissionHistoryResponse(
        entity_id=result.entity_id,
        event_count=len(result.events),
        events=[
            MissionEventItem(
                entity_id=e.entity_id,
                label=e.label,
                kind=e.kind,
                relation_kind=e.relation_kind,
            )
            for e in result.events
        ],
    )


# ---------------------------------------------------------------------------
# Endpoint 6: Domain mapping
# ---------------------------------------------------------------------------

@router.get(
    "/entity/{entity_id}/domain",
    response_model=DomainInfoResponse,
)
def domain_mapping_endpoint(entity_id: str) -> DomainInfoResponse:
    """
    Which domain does [entity] belong to? Who governs it?

    Returns 404 if the entity is not in the store.
    domain_id and domain_label are null when no governance relationship exists.
    """
    result = domain_mapping(entity_id, get_store_path())
    if not result.found:
        raise HTTPException(
            status_code=404,
            detail=f"Entity '{entity_id}' not found in CNS store",
        )
    return DomainInfoResponse(
        entity_id=result.entity_id,
        found=result.found,
        label=result.label,
        domain_id=result.domain_id,
        domain_label=result.domain_label,
        repo=result.repo,
        cluster=result.cluster,
    )
