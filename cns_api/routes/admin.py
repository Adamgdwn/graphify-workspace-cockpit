"""
Admin endpoints for the CNS API.

POST /api/cns/admin/ingest — trigger on-demand extraction for a source path
GET  /api/cns/admin/ingest/{job_id} — poll extraction job status

Requires CNS_API_KEY header if CNS_API_KEY env var is set.
No write path through the API for graph data — ingest is the sole exception
and it operates by running graphify extraction externally, not by accepting
graph data from callers.
"""
import threading
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from cns_api.auth import require_api_key
from cns_api.config import get_store_path
from cns_store.db import get_connection
from cns_store.ingest import run_extraction, ExtractionError

router = APIRouter(prefix="/api/cns/admin", tags=["admin"])

# In-memory job registry — acceptable for Phase 2 single-instance deployments.
# Phase 3 should move this to the SQLite store or a proper job queue.
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


class IngestRequest(BaseModel):
    source_path: str
    graphify_cmd: str = "graphify"
    timeout: int = 300


class IngestJobResponse(BaseModel):
    job_id: str
    status: str
    source_path: str
    started_at: str
    finished_at: Optional[str] = None
    node_count: Optional[int] = None
    link_count: Optional[int] = None
    error: Optional[str] = None


def _run_job(job_id: str, req: IngestRequest, db_path: str) -> None:
    """Background thread target: run extraction and update job status."""
    try:
        summary = run_extraction(
            req.source_path,
            db_path,
            graphify_cmd=req.graphify_cmd,
            timeout=req.timeout,
        )
        with _jobs_lock:
            _jobs[job_id].update(
                status="complete",
                finished_at=datetime.now(timezone.utc).isoformat(),
                node_count=summary["node_count"],
                link_count=summary["link_count"],
            )
    except (ExtractionError, ValueError) as exc:
        with _jobs_lock:
            _jobs[job_id].update(
                status="failed",
                finished_at=datetime.now(timezone.utc).isoformat(),
                error=str(exc),
            )


@router.post("/ingest", response_model=IngestJobResponse, status_code=202)
def trigger_ingest(
    req: IngestRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> IngestJobResponse:
    """
    Trigger on-demand graphify extraction for source_path.

    Returns immediately with a job_id. Poll /api/cns/admin/ingest/{job_id}
    to check completion. Accepts one job per source_path at a time — a second
    request for the same source_path while one is running starts a new job.
    """
    require_api_key(x_api_key)

    job_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    db_path = get_store_path()

    with _jobs_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "source_path": req.source_path,
            "started_at": started_at,
            "finished_at": None,
            "node_count": None,
            "link_count": None,
            "error": None,
        }

    thread = threading.Thread(
        target=_run_job,
        args=(job_id, req, db_path),
        daemon=True,
    )
    thread.start()

    with _jobs_lock:
        return IngestJobResponse(**_jobs[job_id])


@router.get("/ingest/{job_id}", response_model=IngestJobResponse)
def get_ingest_status(
    job_id: str,
    x_api_key: Optional[str] = Header(default=None),
) -> IngestJobResponse:
    """Poll the status of an ingest job."""
    require_api_key(x_api_key)

    with _jobs_lock:
        job = _jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return IngestJobResponse(**job)


class StoreInfoResponse(BaseModel):
    store_path: str
    entity_count: int
    relationship_count: int
    store_size_bytes: Optional[int] = None
    retrieved_at: str


@router.get("/store-info", response_model=StoreInfoResponse)
def get_store_info(
    x_api_key: Optional[str] = Header(default=None),
) -> StoreInfoResponse:
    """Return entity count, relationship count, and store metadata."""
    require_api_key(x_api_key)
    db_path = get_store_path()

    import os
    try:
        conn = get_connection(db_path)
        entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        rel_count = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        conn.close()
        size = os.path.getsize(db_path) if db_path and os.path.exists(db_path) else None
    except Exception:
        entity_count = 0
        rel_count = 0
        size = None

    return StoreInfoResponse(
        store_path=db_path or "",
        entity_count=entity_count,
        relationship_count=rel_count,
        store_size_bytes=size,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
