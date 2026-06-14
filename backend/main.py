"""Graphify Workspace Cockpit — backend API."""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

WORKSPACE_STATE = Path(__file__).parent.parent / "workspace" / "state"
SESSIONS_DIR = WORKSPACE_STATE / "sessions"
SETTINGS_FILE = WORKSPACE_STATE / "settings.json"
DECISIONS_FILE = WORKSPACE_STATE / "decisions.json"

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


# ---------------------------------------------------------------------------
# Decision ledger
# ---------------------------------------------------------------------------

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


def _load_decisions() -> list[dict]:
    if DECISIONS_FILE.exists():
        try:
            return json.loads(DECISIONS_FILE.read_text())
        except Exception:
            return []
    return []


def _save_decisions(decisions: list[dict]) -> None:
    DECISIONS_FILE.write_text(json.dumps(decisions, indent=2))


@app.get("/decisions")
def list_decisions() -> list[dict]:
    return _load_decisions()


@app.post("/decisions", status_code=201)
def create_decision(req: CreateDecisionRequest) -> dict:
    if not req.target_id.strip():
        raise HTTPException(status_code=422, detail="target_id must not be blank.")
    decisions = _load_decisions()
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
    }
    decisions.append(record)
    _save_decisions(decisions)
    return record


@app.patch("/decisions/{decision_id}")
def patch_decision(decision_id: str, req: PatchDecisionRequest) -> dict:
    decisions = _load_decisions()
    for d in decisions:
        if d["id"] == decision_id:
            now = datetime.now(tz=timezone.utc).isoformat()
            if req.classification is not None:
                d["classification"] = req.classification
            if req.rationale is not None:
                d["rationale"] = req.rationale
            if req.label is not None:
                d["label"] = req.label
            if req.status is not None:
                d["status"] = req.status
            d["updated_at"] = now
            _save_decisions(decisions)
            return d
    raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found.")


# ---------------------------------------------------------------------------
# Recommendation queue
# ---------------------------------------------------------------------------

RECOMMENDATIONS_DIR = WORKSPACE_STATE / "recommendations"
ACTION_QUEUE_DIR     = WORKSPACE_STATE / "action-queue"
NOTES_DIR            = WORKSPACE_STATE / "notes"
RECOMMEND_MODEL_DEFAULT = "phi4:latest"

MODE_PROMPT_FILES: dict[str, str] = {
    "next-build": "recommend_ranked.txt",
    "archive-candidates": "recommend_archive.txt",
    "duplicates": "recommend_duplicates.txt",
}

RecommendationStatus = Literal["pending", "accepted", "rejected", "deferred"]


class GenerateRecommendationRequest(BaseModel):
    mode: Literal["next-build", "archive-candidates", "duplicates"]
    model: Optional[str] = None


class PatchRecommendationRequest(BaseModel):
    status: Optional[RecommendationStatus] = None


def _load_recommendations() -> list[dict]:
    if not RECOMMENDATIONS_DIR.exists():
        return []
    recs: list[dict] = []
    for f in RECOMMENDATIONS_DIR.glob("*.json"):
        try:
            recs.append(json.loads(f.read_text()))
        except Exception:
            pass
    return sorted(recs, key=lambda r: r.get("created_at", ""), reverse=True)


def _save_recommendation(rec: dict) -> None:
    RECOMMENDATIONS_DIR.mkdir(parents=True, exist_ok=True)
    (RECOMMENDATIONS_DIR / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2))


def _load_recommendation(rec_id: str) -> dict | None:
    path = RECOMMENDATIONS_DIR / f"{rec_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


def _build_graph_context(summary: dict) -> str:
    nodes = summary.get("nodes", [])
    edges = summary.get("edges", [])
    lines = [
        f"Workspace: {len(nodes)} project areas, {summary.get('total_nodes', '?')} total nodes.",
        "",
        "Project areas (largest first):",
    ]
    for n in nodes[:20]:
        lines.append(
            f"  - {n['id']}: {n.get('node_count', 0)} nodes, type={n.get('dominant_type', 'code')}"
        )
    if edges:
        lines.append("")
        lines.append(f"Top connections ({min(len(edges), 10)} of {len(edges)}):")
        for e in edges[:10]:
            lines.append(f"  - {e['source']} <-> {e['target']} ({e.get('weight', 0)} links)")
    return "\n".join(lines)


def _build_decisions_context(decisions: list[dict]) -> str:
    active = [d for d in decisions if d.get("status") == "active"]
    if not active:
        return "No workspace decisions recorded yet."
    lines = ["Current decisions:"]
    for d in active:
        note = f" — {d['rationale']}" if d.get("rationale") else ""
        lines.append(f"  - {d['target_id']}: {d['classification']}{note}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
    return {}


def _call_ollama(prompt: str, model: str, timeout: int = 120) -> str:
    import urllib.request as _req
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }).encode("utf-8")
    request = _req.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _req.urlopen(request, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "")


@app.get("/recommendations")
def list_recommendations() -> list[dict]:
    return _load_recommendations()


@app.post("/recommendations/generate", status_code=201)
def generate_recommendation(req: GenerateRecommendationRequest) -> dict:
    try:
        summary = graph_summary()
    except HTTPException:
        summary = {"nodes": [], "edges": [], "total_nodes": 0}
    decisions = _load_decisions()

    graph_ctx = _build_graph_context(summary)
    dec_ctx = _build_decisions_context(decisions)

    prompt_file = Path(__file__).parent / "prompts" / MODE_PROMPT_FILES[req.mode]
    if not prompt_file.exists():
        raise HTTPException(status_code=500, detail=f"Prompt template missing: {prompt_file.name}")

    template = prompt_file.read_text()
    prompt = template.replace("{graph_context}", graph_ctx).replace("{decisions_context}", dec_ctx)

    model = (req.model or RECOMMEND_MODEL_DEFAULT).strip()
    model_used = model
    parsed: dict = {}

    try:
        raw = _call_ollama(prompt, model)
        parsed = _extract_json(raw)
    except Exception:
        model_used = "graph-only"

    now = datetime.now(tz=timezone.utc).isoformat()
    rec: dict = {
        "id": str(uuid.uuid4()),
        "mode": req.mode,
        "title": parsed.get("title") or f"Recommendation: {req.mode}",
        "summary": parsed.get("summary") or "Ollama unavailable — graph context loaded but no synthesis available.",
        "evidence": parsed.get("evidence") if isinstance(parsed.get("evidence"), list) else [],
        "confidence": float(parsed.get("confidence") or 0.0),
        "risk": parsed.get("risk") or "unknown",
        "effort": parsed.get("effort") or "unknown",
        "proposed_action": parsed.get("proposed_action") or "",
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "model": model_used,
    }
    _save_recommendation(rec)
    return rec


@app.patch("/recommendations/{rec_id}")
def patch_recommendation(rec_id: str, req: PatchRecommendationRequest) -> dict:
    rec = _load_recommendation(rec_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")
    now = datetime.now(tz=timezone.utc).isoformat()
    if req.status is not None:
        rec["status"] = req.status
    rec["updated_at"] = now
    _save_recommendation(rec)
    return rec


# ── Missions (Steady Work Mode — AG-003) ──────────────────────────────────

import threading as _threading  # noqa: E402

MISSIONS: dict[str, dict] = {}
_CANCEL_FLAGS: dict[str, _threading.Event] = {}
_MISSIONS_LOCK = _threading.Lock()

MISSION_PROMPT_MAP: dict[str, str] = {
    "archive-candidates": "recommend_archive.txt",
    "rank-builds":        "steady_rank_builds.txt",
    "weak-coverage":      "steady_weak_coverage.txt",
    "duplicates":         "recommend_duplicates.txt",
}

MISSION_MODE_MAP: dict[str, str] = {
    "archive-candidates": "archive-candidates",
    "rank-builds":        "next-build",
    "weak-coverage":      "next-build",
    "duplicates":         "duplicates",
}


def _mission_log(mission_id: str, msg: str) -> None:
    with _MISSIONS_LOCK:
        MISSIONS[mission_id]["log"].append(msg)


def _run_mission(mission_id: str, mission_type: str) -> None:
    cancel = _CANCEL_FLAGS[mission_id]

    def log(msg: str) -> None:
        _mission_log(mission_id, msg)

    def finish(status: str) -> None:
        with _MISSIONS_LOCK:
            MISSIONS[mission_id]["status"]      = status
            MISSIONS[mission_id]["finished_at"] = datetime.now(tz=timezone.utc).isoformat()

    try:
        log(f"Started mission: {mission_type}")

        if cancel.is_set():
            finish("cancelled")
            log("Cancelled before context load.")
            return

        log("Loading graph context…")
        try:
            summary = graph_summary()
        except HTTPException:
            summary = {"nodes": [], "edges": [], "total_nodes": 0}

        decisions = _load_decisions()
        graph_ctx = _build_graph_context(summary)
        dec_ctx   = _build_decisions_context(decisions)
        log(f"Context loaded: {summary.get('total_nodes', 0)} nodes, {len(decisions)} decisions.")

        if cancel.is_set():
            finish("cancelled")
            log("Cancelled before Ollama call.")
            return

        prompt_file = Path(__file__).parent / "prompts" / MISSION_PROMPT_MAP[mission_type]
        if not prompt_file.exists():
            finish("failed")
            log(f"Prompt template missing: {prompt_file.name}")
            return

        template = prompt_file.read_text()
        prompt   = template.replace("{graph_context}", graph_ctx).replace("{decisions_context}", dec_ctx)

        log(f"Calling Ollama ({RECOMMEND_MODEL_DEFAULT})…")
        model_used = RECOMMEND_MODEL_DEFAULT
        parsed: dict = {}
        try:
            raw    = _call_ollama(prompt, RECOMMEND_MODEL_DEFAULT, timeout=60)
            parsed = _extract_json(raw)
            log("Ollama returned structured output.")
        except Exception as exc:
            model_used = "graph-only"
            log(f"Ollama unavailable ({type(exc).__name__}); using graph-only card.")

        if cancel.is_set():
            finish("cancelled")
            log("Cancelled after Ollama call (card not saved).")
            return

        mode = MISSION_MODE_MAP.get(mission_type, "next-build")
        now  = datetime.now(tz=timezone.utc).isoformat()
        rec: dict = {
            "id":              str(uuid.uuid4()),
            "mode":            mode,
            "title":           parsed.get("title") or f"Mission: {mission_type}",
            "summary":         parsed.get("summary") or "Analysis complete; Ollama synthesis unavailable.",
            "evidence":        parsed.get("evidence") if isinstance(parsed.get("evidence"), list) else [],
            "confidence":      float(parsed.get("confidence") or 0.0),
            "risk":            parsed.get("risk") or "unknown",
            "effort":          parsed.get("effort") or "unknown",
            "proposed_action": parsed.get("proposed_action") or "",
            "status":          "pending",
            "created_at":      now,
            "updated_at":      now,
            "model":           model_used,
        }
        _save_recommendation(rec)

        with _MISSIONS_LOCK:
            MISSIONS[mission_id]["cards_generated"] += 1

        log(f"Card saved: {rec['title']}")
        finish("completed")

    except Exception as exc:
        with _MISSIONS_LOCK:
            MISSIONS[mission_id]["log"].append(f"Unexpected error: {exc}")
            MISSIONS[mission_id]["status"]      = "failed"
            MISSIONS[mission_id]["finished_at"] = datetime.now(tz=timezone.utc).isoformat()


MissionType = Literal["archive-candidates", "rank-builds", "weak-coverage", "duplicates"]


class StartMissionRequest(BaseModel):
    type: MissionType


@app.get("/missions")
def list_missions() -> list[dict]:
    with _MISSIONS_LOCK:
        return sorted(
            [{**m} for m in MISSIONS.values()],
            key=lambda m: m["started_at"],
            reverse=True,
        )


@app.post("/missions", status_code=201)
def start_mission(req: StartMissionRequest) -> dict:
    mission_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc).isoformat()
    mission: dict = {
        "id":              mission_id,
        "type":            req.type,
        "status":          "running",
        "log":             [],
        "cards_generated": 0,
        "started_at":      now,
        "finished_at":     None,
    }
    cancel = _threading.Event()
    with _MISSIONS_LOCK:
        MISSIONS[mission_id]      = mission
        _CANCEL_FLAGS[mission_id] = cancel
    thread = _threading.Thread(
        target=_run_mission, args=(mission_id, req.type), daemon=True
    )
    thread.start()
    with _MISSIONS_LOCK:
        return {**MISSIONS[mission_id]}


@app.get("/missions/{mission_id}")
def get_mission(mission_id: str) -> dict:
    with _MISSIONS_LOCK:
        if mission_id not in MISSIONS:
            raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found.")
        return {**MISSIONS[mission_id]}


@app.post("/missions/{mission_id}/cancel")
def cancel_mission(mission_id: str) -> dict:
    with _MISSIONS_LOCK:
        if mission_id not in MISSIONS:
            raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found.")
        cancel = _CANCEL_FLAGS.get(mission_id)
        if cancel is not None:
            cancel.set()
        if MISSIONS[mission_id]["status"] == "running":
            MISSIONS[mission_id]["status"]      = "cancelled"
            MISSIONS[mission_id]["finished_at"] = datetime.now(tz=timezone.utc).isoformat()
            MISSIONS[mission_id]["log"].append("Cancellation requested.")
        return {**MISSIONS[mission_id]}


# ── Action Queue (Approved Actions — AG-004) ──────────────────────────────


def _save_action(action: dict) -> None:
    ACTION_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    (ACTION_QUEUE_DIR / f"{action['id']}.json").write_text(json.dumps(action, indent=2))


def _load_action(action_id: str) -> dict | None:
    path = ACTION_QUEUE_DIR / f"{action_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _load_all_actions() -> list[dict]:
    if not ACTION_QUEUE_DIR.exists():
        return []
    actions = []
    for p in sorted(ACTION_QUEUE_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            actions.append(json.loads(p.read_text()))
        except Exception:
            pass
    return actions


def _build_note_content(action: dict) -> str:
    lines = [
        f"# {action['rec_title']}",
        "",
        f"> Generated by Graphify Workspace Cockpit — {action['created_at'][:10]}",
        "",
        "## Summary",
        "",
        action.get("rec_summary", ""),
        "",
        "## Proposed Action",
        "",
        action.get("proposed_action_text", ""),
        "",
    ]
    if action.get("evidence"):
        lines += ["## Evidence", ""]
        for ev in action["evidence"]:
            lines.append(f"- {ev}")
        lines.append("")
    lines += [
        "---",
        "",
        f"*Action type: `{action['action_type']}`*  ",
        f"*Source recommendation: `{action['source_recommendation_id']}`*",
    ]
    return "\n".join(lines)


def _build_action_from_rec(rec: dict) -> dict:
    mode         = rec.get("mode", "")
    action_type  = "tag_for_archive" if mode == "archive-candidates" else "create_note"
    action_id    = str(uuid.uuid4())
    safe_title   = re.sub(r"[^a-zA-Z0-9_-]", "_", rec.get("title", "note")[:40]).strip("_") or "note"
    filename     = f"{safe_title}_{action_id[:8]}.md"
    target_path  = str(NOTES_DIR / filename)
    target_rel   = f"workspace/state/notes/{filename}"
    now          = datetime.now(tz=timezone.utc).isoformat()
    return {
        "id":                        action_id,
        "source_recommendation_id":  rec["id"],
        "action_type":               action_type,
        "description":               f"{action_type.replace('_', ' ').title()}: {rec.get('title', '')}",
        "target_path":               target_path,
        "dry_run_command":           f"mkdir -p workspace/state/notes && cat > {target_rel}",
        "proposed_action_text":      rec.get("proposed_action", "").strip() or rec.get("title", ""),
        "evidence":                  rec.get("evidence", []),
        "rec_title":                 rec.get("title", ""),
        "rec_summary":               rec.get("summary", ""),
        "dry_run_preview":           None,
        "dry_run_at":                None,
        "approval_required":         True,
        "approved_at":               None,
        "executed_at":               None,
        "result":                    None,
        "rollback_note":             f"To undo: delete {target_rel}",
        "status":                    "pending",
        "created_at":                now,
        "updated_at":                now,
    }


@app.post("/recommendations/{rec_id}/queue", status_code=201)
def queue_recommendation(rec_id: str) -> dict:
    rec = _load_recommendation(rec_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")
    if rec.get("status") != "accepted":
        raise HTTPException(status_code=422, detail="Only accepted recommendations can be queued.")
    action = _build_action_from_rec(rec)
    _save_action(action)
    return action


@app.get("/actions")
def list_actions() -> list[dict]:
    return _load_all_actions()


@app.get("/actions/{action_id}")
def get_action(action_id: str) -> dict:
    action = _load_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found.")
    return action


@app.post("/actions/{action_id}/dry-run")
def dry_run_action(action_id: str) -> dict:
    action = _load_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found.")
    if action["status"] == "executed":
        raise HTTPException(status_code=422, detail="Action already executed.")

    target       = Path(action["target_path"])
    file_exists  = target.exists()
    content      = _build_note_content(action)

    now = datetime.now(tz=timezone.utc).isoformat()
    action["dry_run_preview"] = {
        "target_path":    str(target),
        "file_exists":    file_exists,
        "would_create":   not file_exists,
        "preview_content": content,
        "summary": (
            f"Would create {target.name} in workspace/state/notes/"
            if not file_exists
            else f"WARNING: {target.name} already exists — would overwrite."
        ),
    }
    action["dry_run_at"] = now
    action["status"]     = "dry-run-ready"
    action["updated_at"] = now
    _save_action(action)
    return action


class ExecuteActionRequest(BaseModel):
    confirmed: bool


@app.post("/actions/{action_id}/execute")
def execute_action(action_id: str, req: ExecuteActionRequest) -> dict:
    action = _load_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found.")
    if action["status"] != "dry-run-ready":
        raise HTTPException(status_code=422, detail="Dry-run must be completed before execution.")
    if not req.confirmed:
        raise HTTPException(status_code=422, detail="confirmed must be true to execute.")

    now = datetime.now(tz=timezone.utc).isoformat()
    action["approved_at"] = now

    target  = Path(action["target_path"])
    preview = action.get("dry_run_preview") or {}
    content = preview.get("preview_content", _build_note_content(action))

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        action["result"] = {
            "success":      True,
            "file_created": str(target),
            "message":      f"Created {target.name}",
        }
        action["status"] = "executed"
    except Exception as exc:
        action["result"] = {
            "success": False,
            "message": str(exc),
        }
        action["status"] = "failed"

    action["executed_at"] = now
    action["updated_at"]  = now
    _save_action(action)
    return action
