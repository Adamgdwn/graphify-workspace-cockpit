"""
Charter ingest and retrieval endpoints for the CNS API.

POST /api/cns/charters          — ingest a CharterProfile as a graph entity
GET  /api/cns/charters/{id}     — retrieve a CharterProfile entity by id
GET  /api/cns/charters          — list CharterProfile entities

Graphify is a read/store layer only — these endpoints have NO approval or
execution authority over charters.

Requires X-Api-Key if CNS_API_KEY env var is set (same pattern as evidence.py).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from cns_api.config import get_api_key, get_store_path
from cns_store.charter_writer import (
    get_charter_entity,
    ingest_charter_entity,
    list_charter_entities,
)

router = APIRouter(prefix="/api/cns", tags=["charters"])


def _require_api_key(x_api_key: Optional[str]) -> None:
    configured_key = get_api_key()
    if not configured_key:
        return
    if not x_api_key or x_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Api-Key header")


class CharterIngestRequest(BaseModel):
    charter_id: str
    title: str
    authority_level: str           # R0–R4 only
    autonomy_level: str
    allowed_action_types: list[str]
    target_resources: str
    max_actions: int
    expiry: str                    # ISO 8601
    stop_conditions: list[str]
    rollback_path: str
    review_cadence: str
    evidence_requirements: str
    connector_scope: Optional[list[str]] = None
    agent_scope: Optional[list[str]] = None
    envelope_id: Optional[str] = None
    charter_status: str = "active"
    # Optional graph edges
    mission_id: Optional[str] = None
    agent_ids: Optional[list[str]] = None
    evidence_ids: Optional[list[str]] = None
    source_ref_ids: Optional[list[str]] = None
    okp_ids: Optional[list[str]] = None
    affected_node_ids: Optional[list[str]] = None


class CharterIngestResponse(BaseModel):
    ok: bool
    entity_id: str
    relationships_created: list[str]
    relationships_skipped: list[str]


class CharterEntityResponse(BaseModel):
    entity_id: str
    found: bool
    kind: str
    label: str
    authority_level: str
    charter_status: str
    metadata: dict
    created_at: str


class CharterSummary(BaseModel):
    entity_id: str
    label: str
    authority_level: str
    charter_status: str
    created_at: str


class CharterListResponse(BaseModel):
    charters: list[CharterSummary]
    count: int


@router.post("/charters", response_model=CharterIngestResponse, status_code=201)
def ingest_charter(
    req: CharterIngestRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> CharterIngestResponse:
    """
    Ingest a CharterProfile as a graph entity.

    Creates a CharterProfile entity (upsert). Creates relationship edges to
    Mission, Agent, Evidence, SourceRef, OKP, and affected-node entities only
    when they exist in the store.

    Graphify stores the charter data only — it does NOT validate authority,
    approve charters, or execute chartered actions.
    """
    _require_api_key(x_api_key)
    db_path = get_store_path()
    summary = ingest_charter_entity(
        db_path,
        charter_id=req.charter_id,
        title=req.title,
        authority_level=req.authority_level,
        autonomy_level=req.autonomy_level,
        allowed_action_types=req.allowed_action_types,
        target_resources=req.target_resources,
        max_actions=req.max_actions,
        expiry=req.expiry,
        stop_conditions=req.stop_conditions,
        rollback_path=req.rollback_path,
        review_cadence=req.review_cadence,
        evidence_requirements=req.evidence_requirements,
        connector_scope=req.connector_scope,
        agent_scope=req.agent_scope,
        envelope_id=req.envelope_id,
        charter_status=req.charter_status,
        mission_id=req.mission_id,
        agent_ids=req.agent_ids,
        evidence_ids=req.evidence_ids,
        source_ref_ids=req.source_ref_ids,
        okp_ids=req.okp_ids,
        affected_node_ids=req.affected_node_ids,
    )
    return CharterIngestResponse(
        ok=True,
        entity_id=summary["entity_id"],
        relationships_created=summary["relationships_created"],
        relationships_skipped=summary["relationships_skipped"],
    )


@router.get("/charters/{charter_id}", response_model=CharterEntityResponse)
def get_charter(
    charter_id: str,
    x_api_key: Optional[str] = Header(default=None),
) -> CharterEntityResponse:
    """Retrieve a CharterProfile entity from the graph by charter_id."""
    _require_api_key(x_api_key)
    db_path = get_store_path()
    entity = get_charter_entity(db_path, charter_id)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Charter entity '{charter_id}' not found in CNS store",
        )
    return CharterEntityResponse(**entity)


@router.get("/charters", response_model=CharterListResponse)
def list_charters(
    authority_level: Optional[str] = Query(default=None),
    charter_status: Optional[str] = Query(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> CharterListResponse:
    """
    List CharterProfile entities from the graph.

    Optional query parameters:
    - authority_level: filter by authority level (e.g. R0, R1, R2, R3, R4)
    - charter_status: filter by charter status (e.g. active, expired, revoked)
    """
    _require_api_key(x_api_key)
    db_path = get_store_path()
    charters = list_charter_entities(
        db_path,
        authority_level=authority_level,
        charter_status=charter_status,
    )
    return CharterListResponse(
        charters=[CharterSummary(**c) for c in charters],
        count=len(charters),
    )
