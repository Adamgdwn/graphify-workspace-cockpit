"""Graphify Workspace Cockpit — backend API."""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from collections import Counter, defaultdict
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

# In-memory cache — loaded once per server lifetime
_graph_cache: dict | None = None
_summary_cache: dict[str, dict] = {}

app = FastAPI(title="Graphify Workspace Cockpit", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_graph() -> dict:
    global _graph_cache
    if _graph_cache is None:
        path = _graph_path()
        if not Path(path).exists():
            raise FileNotFoundError(path)
        with open(path) as f:
            _graph_cache = json.load(f)
    return _graph_cache


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


@app.get("/graph/summary")
def graph_summary(project: str | None = None, min_weight: int = 2) -> dict:
    """Return a project-level or sub-project-level graph summary.

    At top level (no project param): groups nodes by first path component.
    At project level (?project=agents): groups by second path component within that project.
    Results are cached in memory after first computation.
    """
    global _summary_cache
    cache_key = f"{project}:{min_weight}"
    if cache_key in _summary_cache:
        return _summary_cache[cache_key]

    try:
        graph = _load_graph()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Graph not found: {exc}. Run graphify update first.",
        ) from exc

    nodes_raw: list[dict] = graph["nodes"]
    links_raw: list[dict] = graph["links"]
    node_map: dict[str, dict] = {n["id"]: n for n in nodes_raw}

    def get_cluster(n: dict) -> str | None:
        sf = n.get("source_file", "")
        if not sf:
            return "(root)" if project is None else None
        parts = sf.split("/")
        if project is None:
            return parts[0] or "(root)"
        if parts[0] != project:
            return None
        return f"{parts[0]}/{parts[1]}" if len(parts) > 1 else parts[0]

    # Aggregate node counts per cluster
    cluster_stats: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "code": 0, "document": 0, "rationale": 0}
    )
    for n in nodes_raw:
        key = get_cluster(n)
        if key is None:
            continue
        ftype = n.get("file_type", "code")
        cluster_stats[key]["total"] += 1
        cluster_stats[key][ftype] = cluster_stats[key].get(ftype, 0) + 1

    # Build summary node list — filter tiny clusters and the synthetic (root) group
    EXCLUDED_CLUSTERS = {"(root)"}
    min_nodes = 2 if project else 20
    summary_nodes: list[dict] = []
    valid_ids: set[str] = set()
    for cluster_id, stats in sorted(
        cluster_stats.items(), key=lambda x: -x[1]["total"]
    ):
        if stats["total"] < min_nodes or cluster_id in EXCLUDED_CLUSTERS:
            continue
        label = cluster_id.split("/")[-1] if "/" in cluster_id else cluster_id
        code = stats.get("code", 0)
        doc = stats.get("document", 0)
        dominant = "code" if code >= doc else "document"
        summary_nodes.append(
            {
                "id": cluster_id,
                "label": label,
                "node_count": stats["total"],
                "code_count": code,
                "doc_count": doc,
                "rationale_count": stats.get("rationale", 0),
                "dominant_type": dominant,
                "is_drillable": project is None,
            }
        )
        valid_ids.add(cluster_id)

    # Aggregate inter-cluster edge weights
    edge_weights: Counter[tuple[str, str]] = Counter()
    edge_relations: dict[tuple[str, str], set[str]] = defaultdict(set)
    for link in links_raw:
        src_node = node_map.get(link["source"])
        tgt_node = node_map.get(link["target"])
        if not src_node or not tgt_node:
            continue
        src_cluster = get_cluster(src_node)
        tgt_cluster = get_cluster(tgt_node)
        if (
            src_cluster
            and tgt_cluster
            and src_cluster != tgt_cluster
            and src_cluster in valid_ids
            and tgt_cluster in valid_ids
        ):
            pair = (src_cluster, tgt_cluster)
            edge_weights[pair] += 1
            rel = link.get("relation", "")
            if rel:
                edge_relations[pair].add(rel)

    summary_edges: list[dict] = [
        {
            "source": src,
            "target": tgt,
            "weight": w,
            "relations": sorted(edge_relations[(src, tgt)])[:4],
        }
        for (src, tgt), w in edge_weights.most_common()
        if w >= min_weight
    ]

    result = {
        "level": "top" if project is None else "project",
        "project": project,
        "total_nodes": sum(s["total"] for s in cluster_stats.values()),
        "nodes": summary_nodes,
        "edges": summary_edges,
    }
    _summary_cache[cache_key] = result
    return result
