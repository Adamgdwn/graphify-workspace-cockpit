"""
OperatingKnowledgePacket (OKP) ingest and retrieval endpoints for the CNS API.

POST   /api/cns/okp                        — ingest OKP, run L2 gravity
GET    /api/cns/okp/{okp_id}               — retrieve OKP entity
GET    /api/cns/okp/{okp_id}/proof-chain   — Synaptic Proof Chain (L2, v1)
GET    /api/cns/okp/{okp_id}/neighborhood  — 1-hop neighborhood

Requires X-Api-Key if CNS_API_KEY env var is set.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from cns_api.config import get_api_key, get_store_path
from cns_store.operating_knowledge_writer import (
    SignalGravityL2Enricher,
    get_okp_entity,
    get_okp_neighborhood,
    ingest_okp_entity,
)

router = APIRouter(prefix="/api/cns", tags=["operating_knowledge"])


def _require_api_key(x_api_key: Optional[str]) -> None:
    configured_key = get_api_key()
    if not configured_key:
        return
    if not x_api_key or x_api_key != configured_key:
        raise HTTPException(
            status_code=401, detail="Invalid or missing X-Api-Key header"
        )


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class OKPIngestRequest(BaseModel):
    okp_id: str
    source_system: str
    source_ref: str
    record_type: str
    summary: str
    authority_level: Optional[str] = None
    autonomy_level: Optional[str] = None
    risk_tier: Optional[str] = None
    data_classification: Optional[str] = None
    status: Optional[str] = None
    created_at: str
    observed_at: Optional[str] = None
    confidence: Optional[float] = None
    fingerprint: Optional[str] = None
    gravity_score_l1: Optional[float] = None
    related_mission_id: Optional[str] = None
    related_action_id: Optional[str] = None
    related_evidence_id: Optional[str] = None
    related_connector_id: Optional[str] = None
    related_agent_id: Optional[str] = None


class OKPIngestResponse(BaseModel):
    ok: bool
    entity_id: str
    gravity_score_l2: float
    edge_count: int
    relationships_created: list[str]
    factor_scores: dict[str, float]


class OKPEntityResponse(BaseModel):
    entity_id: str
    found: bool
    kind: str
    label: str
    metadata: dict[str, Any]
    created_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/okp", response_model=OKPIngestResponse, status_code=201)
def ingest_okp(
    req: OKPIngestRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> OKPIngestResponse:
    """
    Ingest an OperatingKnowledgePacket as a graph entity.

    Upserts the entity, creates relationship edges to Mission, Evidence,
    Action, Connector, and Agent entities only when they exist. Then runs
    Signal Gravity L2 enrichment and returns the combined result.
    """
    _require_api_key(x_api_key)
    db_path = get_store_path()
    summary = ingest_okp_entity(db_path, okp_data=req.model_dump())
    gravity = SignalGravityL2Enricher.enrich(db_path, req.okp_id)
    return OKPIngestResponse(
        ok=True,
        entity_id=summary["entity_id"],
        gravity_score_l2=gravity["gravity_score_l2"],
        edge_count=summary["edge_count"],
        relationships_created=summary["relationships_created"],
        factor_scores=gravity["factor_scores"],
    )


@router.get("/okp/{okp_id}", response_model=OKPEntityResponse)
def get_okp(
    okp_id: str,
    x_api_key: Optional[str] = Header(default=None),
) -> OKPEntityResponse:
    """Retrieve an OKP entity from the graph by okp_id."""
    _require_api_key(x_api_key)
    db_path = get_store_path()
    entity = get_okp_entity(db_path, okp_id)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"OKP entity '{okp_id}' not found in CNS store",
        )
    return OKPEntityResponse(**entity)


@router.get("/okp/{okp_id}/proof-chain")
def get_okp_proof_chain(
    okp_id: str,
    x_api_key: Optional[str] = Header(default=None),
) -> dict:
    """
    Return the Synaptic Proof Chain (Graphify L2 layer) for this OKP.

    Full chain layers:
      L1 — GAIL OS: GET /api/v1/okp/{okp_id}/proof-chain
      L2 — Graphify: this endpoint
      Brief — Freedom: generateOperatingKnowledgeBrief()

    CP-5 closed. proof_chain_version: v1-l2.
    """
    _require_api_key(x_api_key)
    db_path = get_store_path()
    entity = get_okp_entity(db_path, okp_id)
    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"OKP entity '{okp_id}' not found in CNS store",
        )
    neighborhood = get_okp_neighborhood(db_path, okp_id)
    gravity = SignalGravityL2Enricher.enrich(db_path, okp_id)
    meta = entity["metadata"]
    return {
        "okp_id": okp_id,
        "entity_id": entity["entity_id"],
        "source_system": meta.get("source_system"),
        "source_ref": meta.get("source_ref"),
        "record_type": meta.get("record_type"),
        "fingerprint": meta.get("fingerprint"),
        "gravity_score_l1": meta.get("gravity_score_l1"),
        "gravity_score_l2": gravity["gravity_score_l2"],
        "factor_scores": gravity["factor_scores"],
        "factor_weights_used": gravity["factor_weights_used"],
        "edge_count": len(neighborhood.get("neighbors", [])),
        "relationships": neighborhood.get("neighbors", []),
        "proof_chain_version": "v1-l2",
        "note": (
            "Full chain: GAIL OS L1 via GET /api/v1/okp/{okp_id}/proof-chain, "
            "Graphify L2 here, Freedom brief via generateOperatingKnowledgeBrief(). "
            "CP-5 closed."
        ),
    }


@router.get("/okp/{okp_id}/neighborhood")
def get_okp_neighborhood_route(
    okp_id: str,
    x_api_key: Optional[str] = Header(default=None),
) -> dict:
    """Return the OKP entity and all 1-hop neighbors (both directions)."""
    _require_api_key(x_api_key)
    db_path = get_store_path()
    result = get_okp_neighborhood(db_path, okp_id)
    if result.get("found") is False:
        raise HTTPException(
            status_code=404,
            detail=f"OKP entity '{okp_id}' not found in CNS store",
        )
    return result
