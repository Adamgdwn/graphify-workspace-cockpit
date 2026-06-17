"""Decision ledger route group."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

DecisionClassification = Literal["invest", "client-ready", "monitor", "archive", "paused"]


class CreateDecisionRequest(BaseModel):
    target_id: str
    label: str = ""
    classification: DecisionClassification
    rationale: str = ""


class PatchDecisionRequest(BaseModel):
    classification: Optional[DecisionClassification] = None
    rationale: Optional[str] = None
    label: Optional[str] = None
    status: Optional[Literal["active", "retired"]] = None


@dataclass(frozen=True)
class DecisionDeps:
    supabase_client: Callable[[], object | None]
    decisions_file: Callable[[], Path]
    write_json_atomic: Callable[[Path, list[dict]], None]


def load_decisions(deps: DecisionDeps) -> list[dict]:
    client = deps.supabase_client()
    if client:
        resp = client.table("decisions").select("*").order("created_at", desc=True).execute()
        return resp.data or []
    decisions_file = deps.decisions_file()
    if decisions_file.exists():
        try:
            return json.loads(decisions_file.read_text())
        except Exception:
            return []
    return []


def save_decisions(decisions: list[dict], deps: DecisionDeps) -> None:
    if deps.supabase_client():
        return
    deps.write_json_atomic(deps.decisions_file(), decisions)


def upsert_decision(record: dict, deps: DecisionDeps) -> None:
    client = deps.supabase_client()
    if client:
        client.table("decisions").upsert(record).execute()
        return
    decisions = load_decisions(deps)
    for i, decision in enumerate(decisions):
        if decision["id"] == record["id"]:
            decisions[i] = record
            save_decisions(decisions, deps)
            return
    decisions.append(record)
    save_decisions(decisions, deps)


def list_decisions_response(
    request: Request,
    *,
    load_records: Callable[[], list[dict]],
    etag: Callable[[list | dict], str],
    track_device: Callable[[str], None],
):
    decisions = load_records()
    tag = etag(decisions)
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304)
    track_device(getattr(request.state, "user_id", "local"))
    return JSONResponse(content=decisions, headers={"ETag": tag})


def create_decision_record(
    req: CreateDecisionRequest,
    request: Request,
    *,
    upsert_record: Callable[[dict], None],
) -> dict:
    if not req.target_id.strip():
        raise HTTPException(status_code=422, detail="target_id must not be blank.")
    now = datetime.now(tz=timezone.utc).isoformat()
    record = {
        "id": str(uuid.uuid4()),
        "target_type": "project",
        "target_id": req.target_id.strip(),
        "label": req.label.strip() or req.target_id.strip(),
        "classification": req.classification,
        "rationale": req.rationale,
        "created_at": now,
        "updated_at": now,
        "status": "active",
        "created_by": getattr(request.state, "user_id", "local"),
    }
    upsert_record(record)
    return record


def patch_decision_record(
    decision_id: str,
    req: PatchDecisionRequest,
    *,
    load_records: Callable[[], list[dict]],
    upsert_record: Callable[[dict], None],
) -> dict:
    decisions = load_records()
    for decision in decisions:
        if decision["id"] == decision_id:
            now = datetime.now(tz=timezone.utc).isoformat()
            if req.classification is not None:
                decision["classification"] = req.classification
            if req.rationale is not None:
                decision["rationale"] = req.rationale
            if req.label is not None:
                decision["label"] = req.label
            if req.status is not None:
                decision["status"] = req.status
            decision["updated_at"] = now
            upsert_record(decision)
            return decision
    raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found.")


def create_decisions_router(
    *,
    load_records: Callable[[], list[dict]],
    upsert_record: Callable[[dict], None],
    etag: Callable[[list | dict], str],
    track_device: Callable[[str], None],
) -> APIRouter:
    router = APIRouter()

    @router.get("/decisions")
    def list_decisions(request: Request):
        return list_decisions_response(
            request,
            load_records=load_records,
            etag=etag,
            track_device=track_device,
        )

    @router.post("/decisions", status_code=201)
    def create_decision(req: CreateDecisionRequest, request: Request) -> dict:
        return create_decision_record(req, request, upsert_record=upsert_record)

    @router.patch("/decisions/{decision_id}")
    def patch_decision(decision_id: str, req: PatchDecisionRequest) -> dict:
        return patch_decision_record(
            decision_id,
            req,
            load_records=load_records,
            upsert_record=upsert_record,
        )

    return router
