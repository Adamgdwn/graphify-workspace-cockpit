"""Health endpoint for the CNS API service."""
import os
from fastapi import APIRouter
from pydantic import BaseModel
from cns_store.db import get_connection

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    store: str
    node_count: int


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Returns service liveness and store connectivity.

    store: "connected" if the SQLite store is reachable and has an entities
    table; "missing" if CNS_STORE_PATH is not set or the DB is unreachable.
    """
    store_path = os.environ.get("CNS_STORE_PATH", "")
    if not store_path:
        return HealthResponse(status="ok", store="missing", node_count=0)

    try:
        conn = get_connection(store_path)
        count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        conn.close()
        return HealthResponse(status="ok", store="connected", node_count=count)
    except Exception:
        return HealthResponse(status="ok", store="missing", node_count=0)
