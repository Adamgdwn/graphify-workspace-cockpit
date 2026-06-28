"""
Charter execution endpoint for the CNS API.

POST /api/cns/charters/{charter_id}/execute

Directs the CNS store stale-claim executor to run a live R4 review. Graphify
is a dumb storage executor only — approval authority lives in GAIL OS.

Requires X-Api-Key if CNS_API_KEY env var is set (same pattern as evidence.py).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from cns_api.config import get_api_key, get_store_path
from cns_store.db import init_db
from cns_store.stale_claim_executor import execute_r4_stale_claim_review

router = APIRouter(prefix="/api/cns", tags=["charter-execute"])


def _require_api_key(x_api_key: Optional[str]) -> None:
    configured_key = get_api_key()
    if not configured_key:
        return
    if not x_api_key or x_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Api-Key header")


class CharterExecuteRequest(BaseModel):
    max_candidates: int = 5
    execution_timestamp: Optional[str] = None


@router.post("/charters/{charter_id}/execute")
def execute_charter(
    charter_id: str,
    req: CharterExecuteRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> dict:
    """
    Execute a charter's stale-claim review against the CNS store.

    Marks up to max_candidates StaleClaimCandidate entities as review_required.
    Returns 200 with the execution result on success, or 400 if no candidates
    are available.

    Graphify has no approval authority — this endpoint only writes to the CNS
    SQLite store as directed by the charter authority.
    """
    _require_api_key(x_api_key)
    db_path = get_store_path()
    init_db(db_path)

    result = execute_r4_stale_claim_review(
        db_path,
        charter_id=charter_id,
        max_candidates=req.max_candidates,
        execution_timestamp=req.execution_timestamp,
    )

    if result["action_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No stale claim candidates available for review.",
                "charter_id": charter_id,
                "action_count": 0,
            },
        )

    return result
