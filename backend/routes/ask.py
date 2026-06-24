"""Ask route group and Graphify output parsing."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

Mode = Literal["query", "path", "explain"]


class AskRequest(BaseModel):
    question: str
    mode: Mode = "query"
    node_a: str | None = None
    node_b: str | None = None


class EvidenceNode(BaseModel):
    label: str
    src: str | None = None
    loc: str | None = None
    community: str | None = None
    relation: str | None = None
    direction: str | None = None


class AskResponse(BaseModel):
    session_id: str
    question: str
    mode_used: Mode
    answer: str
    evidence: list[dict]
    suggestions: list[str]


@dataclass(frozen=True)
class AskDeps:
    graph_path: Callable[[], str]
    run_graphify_ask: Callable[..., object]
    load_cluster_selection: Callable[[], dict]
    scope_evidence: Callable[[list[dict]], list[dict]]
    sessions_dir: Callable[[], Path]
    write_json_atomic: Callable[[Path, dict], None]
    prune_sessions: Callable[[], None]
    graphify_error: type[Exception]


def parse_query_output(raw: str) -> tuple[str, list[dict]]:
    """Parse `graphify query` stdout into (summary_line, evidence_nodes)."""
    lines = raw.strip().splitlines()
    header = lines[0] if lines else raw
    evidence: list[dict] = []
    pattern = re.compile(
        r"^NODE\s+(.+?)\s+\[src=(.*?)\s+loc=([^\s\]]*)\s+community=([^\]]*)\]"
    )
    for line in lines[1:]:
        m = pattern.match(line.strip())
        if m:
            evidence.append(
                {
                    "label": m.group(1).strip(),
                    "src": m.group(2),
                    "loc": m.group(3) or None,
                    "community": m.group(4).strip(),
                }
            )
    if not evidence:
        start_match = re.search(r"Start:\s*\[(.*?)\]", header)
        if start_match:
            for item in re.findall(r"'([^']+)'|\"([^\"]+)\"", start_match.group(1)):
                label = item[0] or item[1]
                if label:
                    evidence.append({"label": label.strip()})
    return header, evidence


def parse_explain_output(raw: str) -> tuple[str, list[dict]]:
    """Parse `graphify explain` stdout into (summary, connections)."""
    evidence: list[dict] = []
    conn_re = re.compile(r"^\s+(<--|-->)\s+(.+?)\s+\[(.+?)\]")
    for line in raw.splitlines():
        m = conn_re.match(line)
        if m:
            evidence.append(
                {
                    "label": m.group(2).strip(),
                    "relation": m.group(3),
                    "direction": m.group(1),
                }
            )
    return raw.strip(), evidence


def parse_path_output(raw: str) -> tuple[str, list[dict]]:
    """Parse `graphify path` stdout into (path_description, hop_list)."""
    hops: list[dict] = []
    for token in re.split(r"\s+(?:<--|-->)\s+", raw):
        token = token.strip()
        if token:
            hops.append({"label": token})
    return raw.strip(), hops


def suggestions(question: str, mode: Mode, evidence: list[dict]) -> list[str]:
    labels = [e["label"] for e in evidence[:3] if e.get("label")]
    base: list[str] = []
    if mode == "query" and labels:
        base.append(f"Explain {labels[0]}")
        if len(labels) >= 2:
            base.append(f"How are {labels[0]} and {labels[1]} related?")
    if mode == "explain":
        base.append(f"What connects to {question.replace('Explain', '').strip()}")
    if mode == "path":
        base.append("What are the main projects in this workspace?")
    return base


def answer_question(req: AskRequest, deps: AskDeps) -> AskResponse:
    graph = deps.graph_path()
    if not graph:
        raise HTTPException(
            status_code=503,
            detail="This instance does not have a workspace graph yet.",
        )
    if not Path(graph).exists():
        raise HTTPException(
            status_code=503,
            detail=f"Graph not found at {graph}. Run graphify update first.",
        )

    if req.mode == "path" and (not req.node_a or not req.node_b):
        raise HTTPException(
            status_code=422,
            detail="Path mode requires node_a and node_b.",
        )

    try:
        result = deps.run_graphify_ask(
            mode=req.mode,
            question=req.question,
            graph_path=graph,
            node_a=req.node_a,
            node_b=req.node_b,
            timeout=30,
        )
    except deps.graphify_error as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc

    cmd = result.command
    raw = result.output

    if req.mode == "query":
        answer, evidence = parse_query_output(raw)
    elif req.mode == "explain":
        answer, evidence = parse_explain_output(raw)
    else:
        answer, evidence = parse_path_output(raw)

    evidence = deps.scope_evidence(evidence)

    suggestion_list = suggestions(req.question, req.mode, evidence)
    session_id = str(uuid.uuid4())

    transcript = {
        "session_id": session_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "question": req.question,
        "mode": req.mode,
        "node_a": req.node_a,
        "node_b": req.node_b,
        "cmd": cmd,
        "raw_output": raw,
        "answer": answer,
        "evidence": evidence,
        "suggestions": suggestion_list,
    }
    deps.write_json_atomic(deps.sessions_dir() / f"{session_id}.json", transcript)
    deps.prune_sessions()

    return AskResponse(
        session_id=session_id,
        question=req.question,
        mode_used=req.mode,
        answer=answer,
        evidence=evidence,
        suggestions=suggestion_list,
    )


def create_ask_router(deps_factory: Callable[[], AskDeps]) -> tuple[APIRouter, Callable[[AskRequest], AskResponse]]:
    router = APIRouter()

    @router.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest) -> AskResponse:
        return answer_question(req, deps_factory())

    return router, ask
