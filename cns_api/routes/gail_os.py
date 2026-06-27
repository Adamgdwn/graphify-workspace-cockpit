"""
GAIL OS query endpoints for the CNS API.

Three read-only endpoints that GAIL OS calls at action decision time:
1. Connector scope validation
2. Entity neighborhood traversal
3. Authority chain traceability
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from cns_api.config import get_store_path
from cns_store.queries import validate_connector, entity_neighborhood, authority_chain

router = APIRouter(prefix="/api/cns", tags=["gail-os"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ConnectorValidationResponse(BaseModel):
    connector_id: str
    found: bool
    is_active: bool
    domain: str
    kind: str
    repo: str
    path: str


class NeighborItem(BaseModel):
    id: str
    label: str
    kind: str
    repo: str
    path: str
    relation_kind: str
    direction: str
    weight: float


class NeighborhoodResponse(BaseModel):
    entity_id: str
    found: bool
    label: str
    kind: str
    neighbor_count: int
    neighbors: list[NeighborItem]


class AuthorityLinkItem(BaseModel):
    entity_id: str
    label: str
    kind: str
    relation_kind: str


class AuthorityChainResponse(BaseModel):
    connector_id: str
    found: bool
    chain_length: int
    chain: list[AuthorityLinkItem]


# ---------------------------------------------------------------------------
# Endpoint 1: Connector scope validation
# ---------------------------------------------------------------------------

@router.get(
    "/connector/{connector_id}/validate",
    response_model=ConnectorValidationResponse,
)
def validate_connector_endpoint(
    connector_id: str,
    domain: str = Query(..., description="Domain name to validate against"),
) -> ConnectorValidationResponse:
    """
    Is connector [connector_id] registered and active for domain [domain]?

    Returns 404 if the connector entity is not in the store.
    """
    result = validate_connector(connector_id, domain, get_store_path())
    if not result.found:
        raise HTTPException(
            status_code=404,
            detail=f"Connector '{connector_id}' not found in CNS store",
        )
    return ConnectorValidationResponse(
        connector_id=result.connector_id,
        found=result.found,
        is_active=result.is_active,
        domain=result.domain,
        kind=result.kind,
        repo=result.repo,
        path=result.path,
    )


# ---------------------------------------------------------------------------
# Endpoint 2: Entity neighborhood traversal
# ---------------------------------------------------------------------------

@router.get(
    "/entity/{entity_id}/neighborhood",
    response_model=NeighborhoodResponse,
)
def entity_neighborhood_endpoint(
    entity_id: str,
    depth: int = Query(default=1, ge=1, le=2, description="Traversal depth (1–2)"),
) -> NeighborhoodResponse:
    """
    What entities are adjacent to action target [entity_id]?

    Returns immediate neighbors. depth=2 supported for blast-radius assessment.
    Returns 404 if the entity is not in the store.
    """
    result = entity_neighborhood(entity_id, get_store_path(), depth=depth)
    if not result.found:
        raise HTTPException(
            status_code=404,
            detail=f"Entity '{entity_id}' not found in CNS store",
        )
    return NeighborhoodResponse(
        entity_id=result.entity_id,
        found=result.found,
        label=result.label,
        kind=result.kind,
        neighbor_count=len(result.neighbors),
        neighbors=[
            NeighborItem(
                id=n.id,
                label=n.label,
                kind=n.kind,
                repo=n.repo,
                path=n.path,
                relation_kind=n.relation_kind,
                direction=n.direction,
                weight=n.weight,
            )
            for n in result.neighbors
        ],
    )


# ---------------------------------------------------------------------------
# Endpoint 3: Authority chain traceability
# ---------------------------------------------------------------------------

@router.get(
    "/connector/{connector_id}/authority-chain",
    response_model=AuthorityChainResponse,
)
def authority_chain_endpoint(connector_id: str) -> AuthorityChainResponse:
    """
    What authority chain produced the R-level for this connector?

    Returns 404 if the connector entity is not in the store.
    """
    result = authority_chain(connector_id, get_store_path())
    if not result.found:
        raise HTTPException(
            status_code=404,
            detail=f"Connector '{connector_id}' not found in CNS store",
        )
    return AuthorityChainResponse(
        connector_id=result.connector_id,
        found=result.found,
        chain_length=len(result.chain),
        chain=[
            AuthorityLinkItem(
                entity_id=link.entity_id,
                label=link.label,
                kind=link.kind,
                relation_kind=link.relation_kind,
            )
            for link in result.chain
        ],
    )
