"""
Evidence ingest and retrieval endpoints for the CNS API.

POST /api/cns/evidence          — ingest an EvidencePacket as a graph entity
GET  /api/cns/evidence/{id}     — retrieve an EvidencePacket entity by id

Requires X-Api-Key if CNS_API_KEY env var is set (same pattern as admin.py).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from cns_api.auth import require_api_key
from cns_api.config import get_store_path
from cns_store.evidence_writer import get_evidence_entity, ingest_evidence_entity

router = APIRouter(prefix="/api/cns", tags=["evidence"])


class EvidenceIngestRequest(BaseModel):
    evidence_id: str
    mission_id: str
    action_id: str
    actor: str
    action_type: str
    authority_basis: str
    result: str
    execution_mode: str
    created_at: str
    outcome_summary: str
    connector_id: Optional[str] = None


class EvidenceIngestResponse(BaseModel):
    ok: bool
    entity_id: str
    relationships_created: list[str]
    relationships_skipped: list[str]


class EvidenceEntityResponse(BaseModel):
    entity_id: str
    found: bool
    kind: str
    label: str
    metadata: dict
    created_at: str


@router.post("/evidence", response_model=EvidenceIngestResponse, status_code=201)
def ingest_evidence(
    req: EvidenceIngestRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> EvidenceIngestResponse:
    """
    Ingest a governed action's EvidencePacket as a graph entity.

    Creates an EvidencePacket entity (upsert). Creates relationship edges
    to Mission and Connector entities only when they exist in the store.
    """
    require_api_key(x_api_key)
    db_path = get_store_path()
    summary = ingest_evidence_entity(
        db_path,
        evidence_id=req.evidence_id,
        mission_id=req.mission_id,
        action_id=req.action_id,
        actor=req.actor,
        action_type=req.action_type,
        authority_basis=req.authority_basis,
        result=req.result,
        execution_mode=req.execution_mode,
        created_at=req.created_at,
        outcome_summary=req.outcome_summary,
        connector_id=req.connector_id,
    )
    return EvidenceIngestResponse(
        ok=True,
        entity_id=summary["entity_id"],
        relationships_created=summary["relationships_created"],
        relationships_skipped=summary["relationships_skipped"],
    )


@router.get("/evidence/{evidence_id}", response_model=EvidenceEntityResponse)
def get_evidence(
    evidence_id: str,
    x_api_key: Optional[str] = Header(default=None),
) -> EvidenceEntityResponse:
    """Retrieve an EvidencePacket entity from the graph by evidence_id."""
    require_api_key(x_api_key)
    db_path = get_store_path()
    entity = get_evidence_entity(db_path, evidence_id)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence entity '{evidence_id}' not found in CNS store",
        )
    return EvidenceEntityResponse(**entity)
