"""Graphify Workspace Cockpit — backend API."""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

WORKSPACE_STATE = Path(__file__).parent.parent / "workspace" / "state"
SESSIONS_DIR = WORKSPACE_STATE / "sessions"
SETTINGS_FILE = WORKSPACE_STATE / "settings.json"

DEFAULT_GRAPH = "/home/adamgoodwin/code/Tools/graphify/workspace/out/graph.json"

app = FastAPI(title="Graphify Workspace Cockpit", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _graph_path() -> str:
    if SETTINGS_FILE.exists():
        try:
            s = json.loads(SETTINGS_FILE.read_text())
            return s.get("graph_path", DEFAULT_GRAPH)
        except Exception:
            pass
    return DEFAULT_GRAPH


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------

def _parse_query_output(raw: str) -> tuple[str, list[dict]]:
    """Parse `graphify query` stdout into (summary_line, evidence_nodes)."""
    lines = raw.strip().splitlines()
    header = lines[0] if lines else raw
    evidence: list[dict] = []
    pattern = re.compile(
        r"^NODE\s+(.+?)\s+\[src=(.+?)\s+loc=(L\d+)\s+community=([^\]]*)\]"
    )
    for line in lines[1:]:
        m = pattern.match(line.strip())
        if m:
            evidence.append(
                {
                    "label": m.group(1).strip(),
                    "src": m.group(2),
                    "loc": m.group(3),
                    "community": m.group(4).strip(),
                }
            )
    return header, evidence


def _parse_explain_output(raw: str) -> tuple[str, list[dict]]:
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


def _parse_path_output(raw: str) -> tuple[str, list[dict]]:
    """Parse `graphify path` stdout into (path_description, hop_list)."""
    hops: list[dict] = []
    # e.g. "FastAPI <--imports_from [EXTRACTED]-- main.py --contains [EXTRACTED]--> health()"
    hop_re = re.compile(r"([^\s<>-][^<>-]*?)\s+(?:<--|-->)")
    for token in re.split(r"\s+(?:<--|-->)\s+", raw):
        token = token.strip()
        if token:
            hops.append({"label": token})
    return raw.strip(), hops


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Suggestion generator
# ---------------------------------------------------------------------------

def _suggestions(question: str, mode: Mode, evidence: list[dict]) -> list[str]:
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    graph = _graph_path()
    if not Path(graph).exists():
        raise HTTPException(
            status_code=503,
            detail=f"Graph not found at {graph}. Run graphify update first.",
        )

    # Build CLI command
    if req.mode == "path":
        if not req.node_a or not req.node_b:
            raise HTTPException(
                status_code=422,
                detail="Path mode requires node_a and node_b.",
            )
        cmd = ["graphify", "path", req.node_a, req.node_b, "--graph", graph]
    elif req.mode == "explain":
        target = req.node_a or req.question
        cmd = ["graphify", "explain", target, "--graph", graph]
    else:
        cmd = ["graphify", "query", req.question, "--graph", graph]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Graphify CLI timed out.")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="graphify CLI not found in PATH.")

    raw = (result.stdout or "") + (result.stderr or "")

    # Parse by mode
    if req.mode == "query":
        answer, evidence = _parse_query_output(raw)
    elif req.mode == "explain":
        answer, evidence = _parse_explain_output(raw)
    else:
        answer, evidence = _parse_path_output(raw)

    suggestions = _suggestions(req.question, req.mode, evidence)
    session_id = str(uuid.uuid4())

    # Save session transcript
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
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
        "suggestions": suggestions,
    }
    (SESSIONS_DIR / f"{session_id}.json").write_text(
        json.dumps(transcript, indent=2)
    )

    return AskResponse(
        session_id=session_id,
        question=req.question,
        mode_used=req.mode,
        answer=answer,
        evidence=evidence,
        suggestions=suggestions,
    )
