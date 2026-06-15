"""Graphify Workspace Cockpit — backend API."""

from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import hashlib

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

_STATE_DIR_ENV = os.environ.get("STATE_DIR", "")
WORKSPACE_STATE = (
    Path(_STATE_DIR_ENV) if _STATE_DIR_ENV
    else Path(__file__).parent.parent / "workspace" / "state"
)
SESSIONS_DIR = WORKSPACE_STATE / "sessions"
SETTINGS_FILE = WORKSPACE_STATE / "settings.json"
DECISIONS_FILE = WORKSPACE_STATE / "decisions.json"
GRAPHS_DIR = WORKSPACE_STATE / "graphs"
DEVICES_FILE = WORKSPACE_STATE / "devices.json"
CONNECTORS_DIR = WORKSPACE_STATE / "connectors"
CLUSTER_SELECTION_FILE = WORKSPACE_STATE / "cluster-selection.json"
CHAT_CONFIG_FILE      = WORKSPACE_STATE / "chat-config.json"
CHAT_SESSIONS_DIR     = WORKSPACE_STATE / "chat-sessions"
SCAN_DIRS_FILE        = WORKSPACE_STATE / "scan-dirs.json"
SEMANTIC_EDGES_FILE   = WORKSPACE_STATE / "semantic-edges.json"
OVERLAP_STATUS_FILE   = WORKSPACE_STATE / "overlap-status.json"
_CHAT_DEFAULT_SYSTEM_PROMPT = (
    "You are an assistant with access to the user's knowledge graph. "
    "Answer based on the provided graph context. "
    "If the answer is not in the graph, say so."
)
_USERS_FILE = Path(__file__).parent.parent / "config" / "users.json"

_DEMO_GRAPH = str(Path(__file__).parent.parent / "workspace" / "demo" / "graph.json")
DEFAULT_GRAPH = os.environ.get("GRAPH_PATH", _DEMO_GRAPH)
API_KEY = os.environ.get("API_KEY", "")

STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "file")  # "file" | "supabase"

# Supabase client — initialised only when STORAGE_BACKEND=supabase
_supabase_client = None
if STORAGE_BACKEND == "supabase":
    _supabase_url = os.environ.get("SUPABASE_URL", "")
    _supabase_key = os.environ.get("SUPABASE_KEY", "")
    if not _supabase_url or not _supabase_key:
        raise RuntimeError("STORAGE_BACKEND=supabase requires SUPABASE_URL and SUPABASE_KEY env vars.")
    try:
        from supabase import create_client as _create_supabase_client
        _supabase_client = _create_supabase_client(_supabase_url, _supabase_key)
    except ImportError as _e:
        raise RuntimeError(f"STORAGE_BACKEND=supabase requires the 'supabase' package: {_e}")

# In-memory cache — loaded once per server lifetime
_graph_cache: dict | None = None
_summary_cache: dict[str, dict] = {}

_REPO_ROOT = Path(__file__).parent.parent
_SECRET_PATH_MARKERS = (
    ".env",
    ".pem",
    ".key",
    "secret",
    "credential",
    "password",
    "private-key",
    "api-key",
    "api_key",
    "access_token",
    "refresh_token",
    "token",
    "users.json",
)

app = FastAPI(title="Graphify Workspace Cockpit", version="0.1.0")

_limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = _limiter
app.add_middleware(SlowAPIMiddleware)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        {"error": "rate_limit_exceeded", "detail": str(exc.detail)},
        status_code=429,
        headers={"Retry-After": "60"},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]

_cors_origins = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _prune_sessions(max_count: int = 50) -> None:
    if not SESSIONS_DIR.exists():
        return
    files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[max_count:]:
        try:
            f.unlink()
        except Exception:
            pass


def _prune_chat_sessions(max_count: int = 50) -> None:
    if not CHAT_SESSIONS_DIR.exists():
        return
    files = sorted(CHAT_SESSIONS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[max_count:]:
        try:
            f.unlink()
        except Exception:
            pass


def _load_chat_config() -> dict:
    if CHAT_CONFIG_FILE.exists():
        try:
            return json.loads(CHAT_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {"system_prompt": _CHAT_DEFAULT_SYSTEM_PROMPT, "model": RECOMMEND_MODEL_DEFAULT}


# Rebuild graph state
_REBUILD_STATUS: dict = {"status": "idle", "last_run": None}

# Semantic similarity pass state
_SEMANTIC_STATUS: dict = {
    "status": "idle",   # idle | running | complete | error
    "progress": 0,
    "total": 0,
    "last_run": None,
    "error": None,
    "edge_count": 0,
    "model": None,
}


@app.on_event("startup")
async def _startup() -> None:
    _prune_sessions()
    _prune_chat_sessions()


def _resolve_user(api_key: str) -> str:
    """Map an API key to a human-readable user name via config/users.json.
    Falls back to 'adam' (single-user default) when no mapping exists."""
    if not api_key:
        return "local"
    if _USERS_FILE.exists():
        try:
            users = json.loads(_USERS_FILE.read_text())
            if api_key in users:
                return users[api_key]
        except Exception:
            pass
    return "adam"


def _etag(data: list | dict) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return '"' + hashlib.md5(payload.encode()).hexdigest() + '"'


def _track_device(user_id: str) -> None:
    """Record this user's last-seen timestamp in devices.json (best-effort)."""
    try:
        devices: dict = {}
        if DEVICES_FILE.exists():
            try:
                devices = json.loads(DEVICES_FILE.read_text())
            except Exception:
                pass
        devices[user_id] = datetime.now(tz=timezone.utc).isoformat()
        WORKSPACE_STATE.mkdir(parents=True, exist_ok=True)
        DEVICES_FILE.write_text(json.dumps(devices, indent=2))
    except Exception:
        pass


class _APIKeyMiddleware(BaseHTTPMiddleware):
    """When API_KEY is set, require Authorization: Bearer <key> or X-API-Key: <key>.
    OPTIONS requests and /health are always allowed so CORS preflight and health
    checks work without credentials."""

    async def dispatch(self, request: Request, call_next):
        provided = ""
        if (
            API_KEY
            and request.method != "OPTIONS"
            and request.url.path not in ("/health",)
        ):
            provided = (
                request.headers.get("authorization", "").removeprefix("Bearer ").strip()
                or request.headers.get("x-api-key", "")
            )
            if provided != API_KEY:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        request.state.user_id = _resolve_user(provided or API_KEY)
        return await call_next(request)


app.add_middleware(_APIKeyMiddleware)


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
# Cluster selection helpers (Chunk Sixteen)
# ---------------------------------------------------------------------------

def _load_cluster_selection() -> dict:
    if CLUSTER_SELECTION_FILE.exists():
        try:
            return json.loads(CLUSTER_SELECTION_FILE.read_text())
        except Exception:
            pass
    return {"sources": ["local", "sharepoint", "onenote"], "clusters": None}


def _save_cluster_selection(sel: dict) -> None:
    WORKSPACE_STATE.mkdir(parents=True, exist_ok=True)
    CLUSTER_SELECTION_FILE.write_text(json.dumps(sel, indent=2))


def _is_node_selected(n: dict, sel_sources: list[str], sel_clusters: list[str] | None) -> bool:
    """Return True if node passes the active source/cluster filter."""
    node_source = n.get("source", "local")
    if node_source not in sel_sources:
        return False
    if sel_clusters is not None:
        sf = n.get("source_file", "")
        cluster = sf.split("/")[0] if sf else ""
        if cluster and cluster not in sel_clusters:
            return False
    return True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
@_limiter.exempt
def health() -> dict:
    graph = _graph_path()
    demo_mode = Path(graph).resolve() == Path(_DEMO_GRAPH).resolve()
    return {"status": "ok", "version": "0.1.0", "demo_mode": demo_mode}


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

    # Post-filter evidence by active cluster selection
    _ask_sel = _load_cluster_selection()
    _ask_clusters = _ask_sel.get("clusters")
    if _ask_clusters is not None:
        evidence = [
            ev for ev in evidence
            if not ev.get("src", "").split("/")[0]
            or ev["src"].split("/")[0] in _ask_clusters
        ]

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
    _prune_sessions()

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
    selection = _load_cluster_selection()
    sel_sources = selection.get("sources", ["local", "sharepoint", "onenote"])
    sel_clusters = selection.get("clusters")
    sel_hash = hashlib.md5(json.dumps(selection, sort_keys=True).encode()).hexdigest()[:8]
    cache_key = f"{project}:{min_weight}:{sel_hash}"
    if cache_key in _summary_cache:
        return _summary_cache[cache_key]

    try:
        graph = _load_graph()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Graph not found: {exc}. Run graphify update first.",
        ) from exc

    nodes_raw: list[dict] = [
        n for n in graph["nodes"]
        if _is_node_selected(n, sel_sources, sel_clusters)
    ]
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


@app.get("/graph/full")
def graph_full() -> dict:
    """Return all raw nodes and links for full-graph rendering in the Map."""
    try:
        g = _load_graph()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Graph not loaded: {exc}")

    def _cluster(source_file: str) -> str:
        parts = [p for p in source_file.replace("\\", "/").split("/") if p]
        return parts[0] if parts else "other"

    def _safe_relative_path(path: Path, root: Path) -> str:
        try:
            return str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            return ""

    def _source_roots() -> list[Path]:
        roots = [_REPO_ROOT]
        for raw in _load_scan_dirs():
            try:
                root = Path(raw).expanduser().resolve()
            except Exception:
                continue
            if root not in roots:
                roots.append(root)
        return roots

    def _path_is_secret_like(source_file: str) -> bool:
        path = source_file.replace("\\", "/").lower()
        parts = [p for p in path.split("/") if p]
        return any(marker in parts or marker in path for marker in _SECRET_PATH_MARKERS)

    source_cache: dict[str, tuple[Path | None, Path | None, str]] = {}
    excerpt_cache: dict[tuple[str, str], dict] = {}

    def _resolve_source(source_file: str) -> tuple[Path | None, Path | None, str]:
        if source_file in source_cache:
            return source_cache[source_file]
        if not source_file:
            result = (None, None, "")
            source_cache[source_file] = result
            return result

        raw_path = Path(source_file).expanduser()
        for root in _source_roots():
            try:
                root_resolved = root.resolve()
                candidate = raw_path.resolve() if raw_path.is_absolute() else (root_resolved / raw_path).resolve()
            except Exception:
                continue

            relative = _safe_relative_path(candidate, root_resolved)
            if not relative and candidate != root_resolved:
                continue
            if candidate.exists() and candidate.is_file():
                result = (candidate, root_resolved, relative)
                source_cache[source_file] = result
                return result

        result = (None, None, "")
        source_cache[source_file] = result
        return result

    def _line_from_location(source_location: str) -> int | None:
        match = re.search(r"L(\d+)", source_location or "")
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    def _read_node_excerpt(source_file: str, source_location: str, radius: int = 4) -> dict:
        cache_key = (source_file, source_location)
        if cache_key in excerpt_cache:
            return excerpt_cache[cache_key]

        result: dict
        if not source_file:
            result = {"start_line": None, "lines": [], "unavailable_reason": "No source file recorded."}
        elif _path_is_secret_like(source_file):
            result = {"start_line": None, "lines": [], "unavailable_reason": "Source excerpt hidden for secret-like path."}
        else:
            source_path, _, _ = _resolve_source(source_file)
            if source_path is None:
                result = {"start_line": None, "lines": [], "unavailable_reason": "Source file is outside the active roots or unavailable."}
            else:
                try:
                    lines = source_path.read_text(errors="replace").splitlines()
                except Exception:
                    result = {"start_line": None, "lines": [], "unavailable_reason": "Source file could not be read."}
                else:
                    if not lines:
                        result = {"start_line": None, "lines": [], "unavailable_reason": "Source file is empty."}
                    else:
                        line_number = _line_from_location(source_location) or 1
                        index = max(0, min(len(lines) - 1, line_number - 1))
                        start = max(0, index - radius)
                        end = min(len(lines), index + radius + 1)
                        excerpt_lines = [line[:220] for line in lines[start:end]]
                        result = {
                            "start_line": start + 1,
                            "lines": excerpt_lines,
                            "unavailable_reason": "",
                        }
        excerpt_cache[cache_key] = result
        return result

    def _first_meaningful_excerpt_line(excerpt: dict) -> str:
        for raw in excerpt.get("lines", []):
            line = str(raw).strip()
            if not line or line in {"{", "}", ")", "];"}:
                continue
            return line[:160]
        return ""

    def _node_purpose(node: dict, excerpt: dict) -> str:
        label = node.get("label") or node.get("id", "This node")
        node_type = node.get("file_type", "code")
        source_file = node.get("source_file", "")
        metadata = node.get("metadata") or {}
        kind = str(metadata.get("kind", "")).replace("_", " ").strip()
        language = str(metadata.get("language", "")).strip()
        clue = _first_meaningful_excerpt_line(excerpt)

        if node_type == "document":
            base = f"{label} is a document node"
            if source_file:
                base += f" from {source_file}"
            if clue:
                base += f"; the nearby text starts with: {clue}"
            return base + "."

        if node_type == "rationale":
            base = f"{label} is a rationale or decision-context node"
            if source_file:
                base += f" from {source_file}"
            if clue:
                base += f"; the nearby evidence starts with: {clue}"
            return base + "."

        descriptor = kind or "code symbol"
        if language:
            descriptor = f"{language} {descriptor}"
        base = f"{label} appears to be a {descriptor}"
        if source_file:
            base += f" in {source_file}"
        if clue:
            base += f"; the source nearby starts with: {clue}"
        return base + "."

    nodes = []
    for n in g.get("nodes", []):
        source_file = n.get("source_file", "")
        source_location = n.get("source_location", "")
        _, source_root, relative_path = _resolve_source(source_file)
        excerpt = _read_node_excerpt(source_file, source_location)
        nodes.append({
            "id": n["id"],
            "label": n.get("label", n["id"]),
            "type": n.get("file_type", "code"),
            "cluster": _cluster(source_file),
            "source_file": source_file,
            "source_location": source_location,
            "source_root": str(source_root) if source_root else "",
            "source_root_name": source_root.name if source_root else "",
            "repo": source_root.name if source_root else "",
            "container": _cluster(source_file),
            "relative_path": relative_path or source_file,
            "origin": n.get("_origin", ""),
            "metadata": n.get("metadata") or {},
            "symbol": n.get("label", n["id"]),
            "purpose": _node_purpose(n, excerpt),
            "source_excerpt": excerpt,
        })

    seen: set[str] = set()
    edges = []
    for lnk in g.get("links", []):
        key = f"{lnk['source']}::{lnk['target']}"
        if key in seen:
            continue
        seen.add(key)
        edges.append({
            "source": lnk["source"],
            "target": lnk["target"],
            "relation": lnk.get("relation", ""),
            "weight": float(lnk.get("weight", 1.0)),
        })

    return {"node_count": len(nodes), "edge_count": len(edges), "nodes": nodes, "edges": edges}


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
    if _supabase_client:
        resp = _supabase_client.table("decisions").select("*").order("created_at", desc=True).execute()
        return resp.data or []
    if DECISIONS_FILE.exists():
        try:
            return json.loads(DECISIONS_FILE.read_text())
        except Exception:
            return []
    return []


def _save_decisions(decisions: list[dict]) -> None:
    if _supabase_client:
        return  # Supabase mode uses _upsert_decision per-record
    DECISIONS_FILE.write_text(json.dumps(decisions, indent=2))


def _upsert_decision(record: dict) -> None:
    """Persist a single decision record to the active backend."""
    if _supabase_client:
        _supabase_client.table("decisions").upsert(record).execute()
        return
    decisions = _load_decisions()
    for i, d in enumerate(decisions):
        if d["id"] == record["id"]:
            decisions[i] = record
            _save_decisions(decisions)
            return
    decisions.append(record)
    _save_decisions(decisions)


@app.get("/decisions")
def list_decisions(request: Request):
    decisions = _load_decisions()
    tag = _etag(decisions)
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304)
    _track_device(getattr(request.state, "user_id", "local"))
    return JSONResponse(content=decisions, headers={"ETag": tag})


@app.post("/decisions", status_code=201)
def create_decision(req: CreateDecisionRequest, request: Request) -> dict:
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
    _upsert_decision(record)
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
            _upsert_decision(d)
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
    if _supabase_client:
        resp = _supabase_client.table("recommendations").select("*").order("created_at", desc=True).execute()
        return resp.data or []
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
    if _supabase_client:
        _supabase_client.table("recommendations").upsert(rec).execute()
        return
    RECOMMENDATIONS_DIR.mkdir(parents=True, exist_ok=True)
    (RECOMMENDATIONS_DIR / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2))


def _load_recommendation(rec_id: str) -> dict | None:
    if _supabase_client:
        resp = _supabase_client.table("recommendations").select("*").eq("id", rec_id).execute()
        return resp.data[0] if resp.data else None
    path = RECOMMENDATIONS_DIR / f"{rec_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


def _recommendation_evidence_terms(rec: dict) -> list[str]:
    raw_items: list[object] = []
    raw_items.extend(rec.get("evidence") if isinstance(rec.get("evidence"), list) else [])
    action_plan = rec.get("action_plan") if isinstance(rec.get("action_plan"), dict) else {}
    raw_items.extend(action_plan.get("source_pairs") if isinstance(action_plan.get("source_pairs"), list) else [])
    overlap = rec.get("overlap") if isinstance(rec.get("overlap"), dict) else {}
    overlap_pairs = overlap.get("top_pairs", []) if isinstance(overlap.get("top_pairs"), list) else []
    for pair in overlap_pairs:
        raw_items.extend([pair.get("label_a"), pair.get("label_b"), pair.get("source"), pair.get("target")])

    terms: list[str] = []
    seen: set[str] = set()
    for raw in raw_items:
        text = str(raw or "").strip()
        if not text:
            continue
        for chunk in re.split(r"↔|<->|->|—", text):
            term = re.sub(r"\s*\(\d+%?\)\s*$", "", chunk).strip(" `[]")
            if term and term not in seen:
                terms.append(term)
                seen.add(term)
    return terms[:20]


def _compact_packet_node(node: dict) -> dict:
    return {
        "id": node.get("id", ""),
        "label": node.get("label", ""),
        "type": node.get("type", ""),
        "cluster": node.get("cluster", ""),
        "repo": node.get("repo", ""),
        "container": node.get("container", ""),
        "relative_path": node.get("relative_path", ""),
        "source_file": node.get("source_file", ""),
        "source_location": node.get("source_location", ""),
        "symbol": node.get("symbol", ""),
        "purpose": node.get("purpose", ""),
    }


def _packet_evidence_nodes(rec: dict) -> list[dict]:
    terms = _recommendation_evidence_terms(rec)
    if not terms:
        return []
    try:
        graph = graph_full()
    except Exception:
        return []

    nodes = graph.get("nodes", [])
    by_id = {str(n.get("id", "")): n for n in nodes}
    by_label = {str(n.get("label", "")): n for n in nodes}
    picked: list[dict] = []
    seen: set[str] = set()
    for term in terms:
        node = by_id.get(term) or by_label.get(term)
        if not node:
            continue
        node_id = str(node.get("id", ""))
        if node_id in seen:
            continue
        picked.append(_compact_packet_node(node))
        seen.add(node_id)
        if len(picked) >= 8:
            break
    return picked


def _related_packet_decisions(rec: dict, evidence_nodes: list[dict]) -> list[dict]:
    decisions = [d for d in _load_decisions() if d.get("status") == "active"]
    if not decisions:
        return []
    search_parts = [
        rec.get("title", ""),
        rec.get("summary", ""),
        rec.get("proposed_action", ""),
        rec.get("mode", ""),
    ]
    search_parts.extend(_recommendation_evidence_terms(rec))
    for node in evidence_nodes:
        search_parts.extend([node.get("id", ""), node.get("label", ""), node.get("cluster", ""), node.get("container", "")])
    haystack = " ".join(str(part).lower() for part in search_parts if part)

    related: list[dict] = []
    for decision in decisions:
        target = str(decision.get("target_id", "")).lower()
        label = str(decision.get("label", "")).lower()
        if target and (target in haystack or any(target == str(n.get("cluster", "")).lower() for n in evidence_nodes)):
            related.append(decision)
        elif label and label in haystack:
            related.append(decision)
    return related[:6]


def _packet_markdown(packet: dict) -> str:
    rec = packet["recommendation"]
    lines = [
        f"# Decision Packet: {rec.get('title', 'Recommendation')}",
        "",
        "## Evidence",
        "",
        rec.get("summary", ""),
        "",
    ]
    for node in packet["evidence"].get("nodes", []):
        path = node.get("relative_path") or node.get("source_file") or "unknown path"
        lines.append(f"- {node.get('label') or node.get('id')}: {node.get('repo') or 'unknown repo'} / {path}")
    dossier = packet["evidence"].get("overlap_dossier")
    if isinstance(dossier, dict) and dossier.get("evidence_summary"):
        lines += ["", "## Overlap Dossier", "", str(dossier["evidence_summary"])]
    lines += [
        "",
        "## Judgement",
        "",
        f"- Status: {packet['judgement'].get('recommendation_status')}",
        f"- Confidence: {packet['judgement'].get('confidence')}",
        f"- Risk: {packet['judgement'].get('risk')}",
        f"- Effort: {packet['judgement'].get('effort')}",
        "",
        "## Recommendation",
        "",
        rec.get("proposed_action", ""),
    ]
    plan = packet.get("recommendation_plan")
    if isinstance(plan, dict):
        lines += ["", f"Canonical target: {plan.get('canonical_target', 'not specified')}"]
        for step in plan.get("concrete_steps", []) if isinstance(plan.get("concrete_steps"), list) else []:
            lines.append(f"- {step}")
    lines += ["", "## Approval Gate", ""]
    for choice in packet.get("operator_choices", []):
        lines.append(f"- {choice}")
    return "\n".join(lines).strip() + "\n"


@app.get("/decision-packets/recommendations/{rec_id}")
def get_recommendation_decision_packet(rec_id: str) -> dict:
    rec = _load_recommendation(rec_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")

    actions = [
        action for action in _load_all_actions()
        if action.get("source_recommendation_id") == rec_id
    ]
    evidence_nodes = _packet_evidence_nodes(rec)
    related_decisions = _related_packet_decisions(rec, evidence_nodes)
    rec_status = rec.get("status", "pending")
    queued_status = actions[0].get("status") if actions else None
    next_gate = (
        "Action has executed; review the result and rollback note in Work Queue."
        if queued_status == "executed"
        else "Action failed; review the failure and recovery note in Work Queue."
        if queued_status == "failed"
        else
        "Review dry-run output in Work Queue before approving execution."
        if queued_status == "dry-run-ready"
        else "Run dry-run in Work Queue before approving execution."
        if queued_status == "pending"
        else "Accept this recommendation before queueing an action."
        if rec_status != "accepted"
        else "Queue an action, then use Work Queue dry-run before execution."
    )

    packet = {
        "schema_version": "1.0",
        "packet_type": "recommendation-decision",
        "id": f"packet-{rec_id}",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "recommendation": rec,
        "evidence": {
            "nodes": evidence_nodes,
            "overlap": rec.get("overlap") if isinstance(rec.get("overlap"), dict) else None,
            "overlap_dossier": rec.get("overlap_dossier") if isinstance(rec.get("overlap_dossier"), dict) else None,
        },
        "judgement": {
            "recommendation_status": rec_status,
            "confidence": rec.get("confidence", 0.0),
            "risk": rec.get("risk", "unknown"),
            "effort": rec.get("effort", "unknown"),
            "model": rec.get("model", ""),
        },
        "recommendation_plan": rec.get("action_plan") if isinstance(rec.get("action_plan"), dict) else None,
        "decisions": {
            "related": related_decisions,
            "count": len(related_decisions),
        },
        "approval": {
            "queued_actions": actions,
            "queued_action_count": len(actions),
            "next_gate": next_gate,
            "execution_locked_to_work_queue": True,
        },
        "operator_choices": [
            "Record or update the decision rationale in the Decisions tab.",
            "Accept, defer, or reject the recommendation in this card.",
            "Queue accepted recommendations from this card.",
            "Run dry-run and approve execution only in Work Queue.",
        ],
    }
    packet["markdown"] = _packet_markdown(packet)
    return packet


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
    _ollama_base = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    request = _req.Request(
        f"{_ollama_base}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _req.urlopen(request, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "")


@app.get("/recommendations")
def list_recommendations(request: Request):
    recs = _load_recommendations()
    tag = _etag(recs)
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304)
    _track_device(getattr(request.state, "user_id", "local"))
    return JSONResponse(content=recs, headers={"ETag": tag})


@app.post("/recommendations/generate", status_code=201)
def generate_recommendation(req: GenerateRecommendationRequest, request: Request) -> dict:
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
        "created_by": getattr(request.state, "user_id", "local"),
    }
    if isinstance(parsed.get("action_plan"), dict):
        rec["action_plan"] = parsed["action_plan"]
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
            "created_by":      "mission-agent",
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
    if _supabase_client:
        _supabase_client.table("actions").upsert(action).execute()
        return
    ACTION_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    (ACTION_QUEUE_DIR / f"{action['id']}.json").write_text(json.dumps(action, indent=2))


def _load_action(action_id: str) -> dict | None:
    if _supabase_client:
        resp = _supabase_client.table("actions").select("*").eq("id", action_id).execute()
        return resp.data[0] if resp.data else None
    path = ACTION_QUEUE_DIR / f"{action_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _load_all_actions(status_filter: str | None = None) -> list[dict]:
    if _supabase_client:
        query = _supabase_client.table("actions").select("*").order("created_at", desc=True)
        if status_filter:
            query = query.eq("status", status_filter)
        resp = query.execute()
        return resp.data or []
    if not ACTION_QUEUE_DIR.exists():
        return []
    actions = []
    for p in sorted(ACTION_QUEUE_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            actions.append(json.loads(p.read_text()))
        except Exception:
            pass
    if status_filter:
        actions = [a for a in actions if a.get("status") == status_filter]
    return actions


def _build_note_content(action: dict) -> str:
    action_plan = action.get("action_plan") if isinstance(action.get("action_plan"), dict) else None
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
    if action_plan:
        lines += ["## Action Plan", ""]
        if action_plan.get("canonical_target"):
            lines += ["### Where", "", str(action_plan["canonical_target"]), ""]
        merge_sources = action_plan.get("merge_sources") if isinstance(action_plan.get("merge_sources"), list) else []
        if merge_sources:
            lines += ["### Sources", ""]
            for source in merge_sources:
                lines.append(f"- {source}")
            lines.append("")
        concrete_steps = action_plan.get("concrete_steps") if isinstance(action_plan.get("concrete_steps"), list) else []
        if concrete_steps:
            lines += ["### How", ""]
            for step in concrete_steps:
                lines.append(f"- {step}")
            lines.append("")
        savings = action_plan.get("savings_estimate") if isinstance(action_plan.get("savings_estimate"), dict) else {}
        if savings:
            lines += ["### Savings Estimate", ""]
            for key in ("duplicate_node_count", "affected_files", "semantic_edge_reduction", "rough_context_savings", "caveat"):
                if savings.get(key) is not None:
                    lines.append(f"- {key.replace('_', ' ')}: {savings[key]}")
            lines.append("")
        risks = action_plan.get("risks") if isinstance(action_plan.get("risks"), list) else []
        if risks:
            lines += ["### Risks", ""]
            for risk in risks:
                lines.append(f"- {risk}")
            lines.append("")
        acceptance = action_plan.get("acceptance_criteria") if isinstance(action_plan.get("acceptance_criteria"), list) else []
        if acceptance:
            lines += ["### Done When", ""]
            for item in acceptance:
                lines.append(f"- {item}")
            lines.append("")
        questions = action_plan.get("open_questions") if isinstance(action_plan.get("open_questions"), list) else []
        if questions:
            lines += ["### Open Questions", ""]
            for question in questions:
                lines.append(f"- {question}")
            lines.append("")
        if action_plan.get("rollback_note"):
            lines += ["### Rollback", "", str(action_plan["rollback_note"]), ""]
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


def _build_action_from_rec(rec: dict, created_by: str = "local") -> dict:
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
        "action_plan":               rec.get("action_plan") if isinstance(rec.get("action_plan"), dict) else None,
        "confidence":                rec.get("confidence", 0.0),
        "risk":                      rec.get("risk", "unknown"),
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
        "created_by":                created_by,
    }


@app.post("/recommendations/{rec_id}/queue", status_code=201)
def queue_recommendation(rec_id: str, request: Request) -> dict:
    rec = _load_recommendation(rec_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")
    if rec.get("status") != "accepted":
        raise HTTPException(status_code=422, detail="Only accepted recommendations can be queued.")
    action = _build_action_from_rec(rec, created_by=getattr(request.state, "user_id", "local"))
    _save_action(action)
    return action


def _to_uaos_envelope(actions: list[dict]) -> dict:
    """Transform executed action records into the UAOS mission envelope format."""
    now = datetime.now(tz=timezone.utc).isoformat()
    items = []
    for a in actions:
        evidence = a.get("evidence", [])
        desc = a.get("description", "")
        items.append({
            "id": a["id"],
            "source_recommendation_id": a.get("source_recommendation_id"),
            "action_type": a.get("action_type"),
            "description": desc,
            "rec_title": a.get("rec_title", ""),
            "rec_summary": a.get("rec_summary", ""),
            "evidence": evidence,
            "confidence": a.get("confidence", 0.0),
            "risk": a.get("risk", "unknown"),
            "proposed_action_text": a.get("proposed_action_text", ""),
            "action_plan": a.get("action_plan") if isinstance(a.get("action_plan"), dict) else None,
            "result": a.get("result"),
            "rollback_note": a.get("rollback_note"),
            "approved_at": a.get("approved_at"),
            "executed_at": a.get("executed_at"),
            "created_by": a.get("created_by", "adam"),
            "uaos_mission_hint": {
                "proposed_mission_title": desc,
                "stop_triggers": [
                    "stop before deleting files",
                    "stop before external commits",
                    "stop before mutating source outside workspace/state/",
                ],
                "approval_level": "A2",
                "files_in_scope": [e for e in evidence if "/" in str(e)],
                "non_goals": ["destructive action", "external service calls"],
            },
        })
    return {
        "schema_version": "1.0",
        "exported_at": now,
        "actions": items,
    }


@app.get("/actions")
def list_actions(
    request: Request,
    status: str | None = Query(default=None),
    format: str | None = Query(default=None),
):
    actions = _load_all_actions(status_filter=status)
    if format == "uaos":
        executed = [a for a in actions if a.get("status") == "executed"]
        return _to_uaos_envelope(executed)
    tag = _etag(actions)
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304)
    _track_device(getattr(request.state, "user_id", "local"))
    return JSONResponse(content=actions, headers={"ETag": tag})


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


# ---------------------------------------------------------------------------
# Chunk Ten — Settings, Ollama status, graph upload
# ---------------------------------------------------------------------------

@app.get("/settings")
def get_settings() -> dict:
    graph_path = _graph_path()
    node_count = 0
    edge_count = 0
    try:
        data = _load_graph()
        node_count = len(data.get("nodes", []))
        edge_count = len(data.get("edges", []))
    except Exception:
        pass
    return {
        "version": app.version,
        "graph_path": graph_path,
        "graph_name": Path(graph_path).name,
        "node_count": node_count,
        "edge_count": edge_count,
        "state_dir": str(WORKSPACE_STATE),
        "api_key_required": bool(API_KEY),
    }


@app.get("/status/ollama")
def ollama_status() -> dict:
    import urllib.request as _req2
    _ollama_base = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    try:
        with _req2.urlopen(f"{_ollama_base}/api/tags", timeout=3) as r:
            data = json.load(r)
            models = [m["name"] for m in data.get("models", [])]
            return {"connected": True, "models": models, "url": _ollama_base}
    except Exception:
        return {"connected": False, "models": [], "url": _ollama_base}


@app.post("/graph/upload", status_code=201)
async def upload_graph(file: UploadFile = File(...)) -> dict:
    """Accept a graph.json file, validate it, store it, and activate it without restart."""
    global _graph_cache, _summary_cache
    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}")
    if not isinstance(data.get("nodes"), list):
        raise HTTPException(
            status_code=422, detail="graph.json must contain a 'nodes' array"
        )
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    name = file.filename or "uploaded_graph.json"
    dest = GRAPHS_DIR / name
    dest.write_bytes(content)
    settings: dict = {}
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    settings["graph_path"] = str(dest)
    WORKSPACE_STATE.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    _graph_cache = None
    _summary_cache = {}
    return {
        "filename": name,
        "node_count": len(data["nodes"]),
        "path": str(dest),
        "active": True,
    }


# ---------------------------------------------------------------------------
# Chunk Eleven — graph management, org settings
# ---------------------------------------------------------------------------

@app.get("/graphs")
def list_graphs() -> list[dict]:
    """Return all available graphs with their activation status."""
    active = _graph_path()
    graphs: list[dict] = []

    # Demo graph (always listed if it exists)
    demo = Path(_DEMO_GRAPH)
    if demo.exists():
        graphs.append({
            "name": demo.name,
            "path": str(demo),
            "active": str(demo) == active,
            "source": "demo",
            "uploaded_at": None,
        })

    # Uploaded graphs in GRAPHS_DIR
    if GRAPHS_DIR.exists():
        for p in sorted(GRAPHS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            graphs.append({
                "name": p.name,
                "path": str(p),
                "active": str(p) == active,
                "source": "uploaded",
                "uploaded_at": datetime.fromtimestamp(
                    p.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            })

    # Custom GRAPH_PATH env var not covered above
    active_path = Path(active)
    if not any(g["path"] == active for g in graphs) and active_path.exists():
        graphs.insert(0, {
            "name": active_path.name,
            "path": active,
            "active": True,
            "source": "configured",
            "uploaded_at": None,
        })

    return graphs


@app.post("/graphs/{name}/activate")
def activate_graph(name: str) -> dict:
    """Switch the active graph by name. Must exist in GRAPHS_DIR or be the demo graph."""
    global _graph_cache, _summary_cache
    candidate = GRAPHS_DIR / name
    if not candidate.exists():
        demo = Path(_DEMO_GRAPH)
        if demo.name == name and demo.exists():
            candidate = demo
        else:
            raise HTTPException(status_code=404, detail=f"Graph '{name}' not found.")
    settings: dict = {}
    if SETTINGS_FILE.exists():
        try:
            settings = json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    settings["graph_path"] = str(candidate)
    WORKSPACE_STATE.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    _graph_cache = None
    _summary_cache = {}
    return {"activated": name, "path": str(candidate)}


@app.get("/settings/org")
def get_org_settings() -> dict:
    """Organisation-level view: active graph, Ollama, storage backend, last-seen devices."""
    graph_path = _graph_path()
    devices: dict = {}
    if DEVICES_FILE.exists():
        try:
            devices = json.loads(DEVICES_FILE.read_text())
        except Exception:
            pass
    return {
        "active_graph": {
            "name": Path(graph_path).name,
            "path": graph_path,
        },
        "ollama_url": os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        "storage_backend": STORAGE_BACKEND,
        "last_seen_devices": [
            {"user": user, "last_seen": ts}
            for user, ts in sorted(devices.items(), key=lambda x: x[1], reverse=True)
        ],
        "graph_stats": _graph_stats(),
    }


def _graph_stats() -> dict:
    """Token savings estimate: (raw_node_count × avg_tokens_per_node) - graph_summary_size."""
    try:
        data = _load_graph()
        raw_node_count = len(data.get("nodes", []))
        avg_tokens_per_node = 80
        # Summary compresses the graph to ~20 cluster groups on average
        summary_token_cost = 20 * avg_tokens_per_node
        tokens_saved = max(0, raw_node_count * avg_tokens_per_node - summary_token_cost)
        return {
            "raw_node_count": raw_node_count,
            "avg_tokens_per_node": avg_tokens_per_node,
            "estimated_tokens_saved_per_query": tokens_saved,
        }
    except Exception:
        return {"raw_node_count": 0, "avg_tokens_per_node": 80, "estimated_tokens_saved_per_query": 0}


# ---------------------------------------------------------------------------
# Chunk Fifteen — Rebuild graph trigger
# ---------------------------------------------------------------------------

import threading as _rebuild_threading  # noqa: E402


def _run_rebuild() -> None:
    global _graph_cache, _summary_cache
    _REBUILD_STATUS.update({"status": "running"})
    try:
        repo_root = Path(__file__).parent.parent
        scan_dirs = _load_scan_dirs()

        if not scan_dirs:
            # Default: scan just this repo
            result = subprocess.run(
                ["graphify", "update", ".", "--no-cluster"],
                cwd=str(repo_root),
                capture_output=True, text=True, timeout=300,
            )
            ts = datetime.now(tz=timezone.utc).isoformat()
            if result.returncode != 0:
                _REBUILD_STATUS.update({"status": "error", "last_run": ts, "error": result.stderr[:500]})
                return
        else:
            # Scan each configured directory, then merge all graphs
            graph_paths: list[str] = []
            for d in scan_dirs:
                r = subprocess.run(
                    ["graphify", "update", d, "--no-cluster"],
                    cwd=d,
                    capture_output=True, text=True, timeout=300,
                )
                if r.returncode == 0:
                    candidate = Path(d) / "graphify-out" / "graph.json"
                    if candidate.exists():
                        graph_paths.append(str(candidate))
            ts = datetime.now(tz=timezone.utc).isoformat()
            if not graph_paths:
                _REBUILD_STATUS.update({"status": "error", "last_run": ts, "error": "No graphs produced by configured scan directories"})
                return
            out_path = repo_root / "graphify-out" / "merged-graph.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if len(graph_paths) == 1:
                import shutil
                shutil.copy(graph_paths[0], str(out_path))
            else:
                merge_result = subprocess.run(
                    ["graphify", "merge-graphs"] + graph_paths + ["--out", str(out_path)],
                    capture_output=True, text=True, timeout=300,
                )
                if merge_result.returncode != 0:
                    _REBUILD_STATUS.update({"status": "error", "last_run": ts, "error": merge_result.stderr[:500]})
                    return
            # Activate the merged graph
            settings: dict = {}
            if SETTINGS_FILE.exists():
                try:
                    settings = json.loads(SETTINGS_FILE.read_text())
                except Exception:
                    pass
            settings["graph_path"] = str(out_path)
            SETTINGS_FILE.write_text(json.dumps(settings, indent=2))

        _graph_cache = None
        _summary_cache = {}
        _REBUILD_STATUS.update({"status": "complete", "last_run": datetime.now(tz=timezone.utc).isoformat(), "error": None})
    except Exception as exc:
        ts = datetime.now(tz=timezone.utc).isoformat()
        _REBUILD_STATUS.update({"status": "error", "last_run": ts, "error": str(exc)})


@app.post("/graph/rebuild", status_code=202)
def trigger_rebuild() -> dict:
    """Trigger a background graphify update rebuild. Returns 202 immediately."""
    if _REBUILD_STATUS.get("status") == "running":
        raise HTTPException(status_code=409, detail="Rebuild already in progress.")
    t = _rebuild_threading.Thread(target=_run_rebuild, daemon=True)
    t.start()
    return {"status": "running"}


@app.get("/graph/rebuild/status")
def rebuild_status() -> dict:
    """Return current rebuild status and last run timestamp."""
    return {
        "status": _REBUILD_STATUS.get("status", "idle"),
        "last_run": _REBUILD_STATUS.get("last_run"),
        "error": _REBUILD_STATUS.get("error"),
    }


def _load_scan_dirs() -> list[str]:
    if SCAN_DIRS_FILE.exists():
        try:
            return json.loads(SCAN_DIRS_FILE.read_text())
        except Exception:
            pass
    return []


def _save_scan_dirs(dirs: list[str]) -> None:
    WORKSPACE_STATE.mkdir(parents=True, exist_ok=True)
    SCAN_DIRS_FILE.write_text(json.dumps(dirs, indent=2))


@app.get("/graph/scan-dirs")
def get_scan_dirs() -> dict:
    """Return the list of directories currently configured for graphify scanning."""
    return {"dirs": _load_scan_dirs()}


class ScanDirBody(BaseModel):
    path: str


@app.post("/graph/scan-dirs", status_code=201)
def add_scan_dir(body: ScanDirBody) -> dict:
    """Add a directory to the scan list. Path must exist on disk."""
    p = Path(body.path).expanduser().resolve()
    if not p.is_dir():
        raise HTTPException(status_code=422, detail=f"Not a directory: {p}")
    dirs = _load_scan_dirs()
    sp = str(p)
    if sp not in dirs:
        dirs.append(sp)
        _save_scan_dirs(dirs)
    return {"dirs": dirs}


@app.delete("/graph/scan-dirs")
def remove_scan_dir(body: ScanDirBody) -> dict:
    """Remove a directory from the scan list."""
    p = str(Path(body.path).expanduser().resolve())
    dirs = [d for d in _load_scan_dirs() if str(Path(d).resolve()) != p]
    _save_scan_dirs(dirs)
    return {"dirs": dirs}


# ---------------------------------------------------------------------------
# Semantic similarity pass
# ---------------------------------------------------------------------------

def _read_source_window(source_file: str, n_lines: int = 35) -> str:
    """Read up to n_lines from a node's source file, checking all known repo roots."""
    if not source_file:
        return ""
    roots = [Path(__file__).parent.parent] + [Path(d) for d in _load_scan_dirs()]
    for root in roots:
        p = root / source_file
        if p.exists():
            try:
                return "\n".join(p.read_text(errors="replace").splitlines()[:n_lines])
            except Exception:
                pass
    return ""


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag = (sum(x * x for x in a) ** 0.5) * (sum(x * x for x in b) ** 0.5)
    return dot / mag if mag else 0.0


def _run_semantic_pass(model: str, threshold: float) -> None:
    import urllib.request as _ureq
    global _SEMANTIC_STATUS
    _SEMANTIC_STATUS.update({
        "status": "running", "progress": 0, "total": 0,
        "error": None, "edge_count": 0, "model": model,
    })
    try:
        g = _load_graph()
        nodes = g.get("nodes", [])
        _SEMANTIC_STATUS["total"] = len(nodes)

        _ollama_base = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        embed_url = f"{_ollama_base}/api/embeddings"

        embeddings: list[tuple[str, list[float]]] = []

        for i, node in enumerate(nodes):
            nid = node["id"]
            label = node.get("label", nid)
            ftype = node.get("file_type", "code")
            window = _read_source_window(node.get("source_file", ""))
            text = f"{ftype}: {label}\n{window}".strip()[:2000]

            try:
                payload = json.dumps({"model": model, "prompt": text}).encode()
                req = _ureq.Request(embed_url, data=payload,
                                    headers={"Content-Type": "application/json"}, method="POST")
                with _ureq.urlopen(req, timeout=90) as resp:
                    vec = json.loads(resp.read()).get("embedding", [])
                if vec:
                    embeddings.append((nid, vec))
            except Exception:
                pass
            _SEMANTIC_STATUS["progress"] = i + 1

        semantic_edges: list[dict] = []
        m = len(embeddings)

        try:
            import numpy as np  # type: ignore
            mat = np.array([v for _, v in embeddings], dtype=np.float32)
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            mat /= np.maximum(norms, 1e-9)
            sim_mat = mat @ mat.T
            rows, cols = np.where(np.triu(sim_mat > threshold, k=1))
            for r, c in zip(rows.tolist(), cols.tolist()):
                semantic_edges.append({
                    "source": embeddings[r][0],
                    "target": embeddings[c][0],
                    "similarity": round(float(sim_mat[r, c]), 4),
                    "relation": "semantic_similar",
                })
        except ImportError:
            for ai in range(m):
                for bi in range(ai + 1, m):
                    s = _cosine_sim(embeddings[ai][1], embeddings[bi][1])
                    if s > threshold:
                        semantic_edges.append({
                            "source": embeddings[ai][0],
                            "target": embeddings[bi][0],
                            "similarity": round(s, 4),
                            "relation": "semantic_similar",
                        })

        WORKSPACE_STATE.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(tz=timezone.utc).isoformat()
        SEMANTIC_EDGES_FILE.write_text(json.dumps({
            "edges": semantic_edges,
            "model": model,
            "threshold": threshold,
            "created_at": ts,
        }, indent=2))

        _SEMANTIC_STATUS.update({
            "status": "complete",
            "last_run": ts,
            "edge_count": len(semantic_edges),
            "error": None,
        })

    except Exception as exc:
        ts = datetime.now(tz=timezone.utc).isoformat()
        _SEMANTIC_STATUS.update({"status": "error", "last_run": ts, "error": str(exc)})


class SemanticPassBody(BaseModel):
    model: str = "nomic-embed-text"
    threshold: float = 0.78


@app.post("/graph/semantic-pass", status_code=202)
def trigger_semantic_pass(body: SemanticPassBody) -> dict:
    """Start a background semantic similarity pass using Ollama embeddings."""
    if _SEMANTIC_STATUS.get("status") == "running":
        raise HTTPException(status_code=409, detail="Semantic pass already in progress.")
    import threading as _sem_t
    _sem_t.Thread(target=_run_semantic_pass, args=(body.model, body.threshold), daemon=True).start()
    return {"status": "running", "model": body.model, "threshold": body.threshold}


@app.get("/graph/semantic-pass/status")
def semantic_pass_status() -> dict:
    return dict(_SEMANTIC_STATUS)


@app.get("/graph/semantic-edges")
def get_semantic_edges() -> dict:
    """Return stored semantic similarity edges."""
    if not SEMANTIC_EDGES_FILE.exists():
        return {"edges": [], "model": None, "threshold": None, "created_at": None}
    try:
        return json.loads(SEMANTIC_EDGES_FILE.read_text())
    except Exception:
        return {"edges": [], "model": None, "threshold": None, "created_at": None}


@app.get("/graph/overlap-report")
def get_overlap_report() -> dict:
    """Compute cross-cluster semantic overlap groups from stored semantic edges + graph."""
    if not SEMANTIC_EDGES_FILE.exists():
        return {"groups": [], "total_cross_edges": 0, "created_at": None}
    try:
        sem_data = json.loads(SEMANTIC_EDGES_FILE.read_text())
    except Exception:
        return {"groups": [], "total_cross_edges": 0, "created_at": None}

    edges = sem_data.get("edges", [])
    if not edges:
        return {"groups": [], "total_cross_edges": 0, "created_at": sem_data.get("created_at")}

    try:
        g = _load_graph()
    except Exception:
        return {"groups": [], "total_cross_edges": 0, "created_at": sem_data.get("created_at")}

    def _cl(sf: str) -> str:
        return sf.replace("\\", "/").split("/")[0] if sf else "other"

    node_meta: dict[str, dict] = {
        n["id"]: {"label": n.get("label", n["id"]), "cluster": _cl(n.get("source_file", "")), "source_file": n.get("source_file", "")}
        for n in g.get("nodes", [])
    }

    groups: dict[str, dict] = {}
    total_cross = 0

    for edge in edges:
        sm = node_meta.get(edge["source"])
        tm = node_meta.get(edge["target"])
        if not sm or not tm:
            continue
        sc, tc = sm["cluster"], tm["cluster"]
        if sc == tc:
            continue
        total_cross += 1
        ca, cb = (sc, tc) if sc <= tc else (tc, sc)
        key = f"{ca}___{cb}"
        if key not in groups:
            groups[key] = {"cluster_a": ca, "cluster_b": cb, "edge_count": 0, "total_sim": 0.0, "pairs": []}
        groups[key]["edge_count"] += 1
        groups[key]["total_sim"] += edge["similarity"]
        groups[key]["pairs"].append({
            "source": edge["source"], "target": edge["target"],
            "label_a": sm["label"], "label_b": tm["label"],
            "file_a": sm["source_file"], "file_b": tm["source_file"],
            "similarity": round(edge["similarity"], 4),
        })

    result: list[dict] = []
    for gd in sorted(groups.values(), key=lambda x: -x["edge_count"]):
        top = sorted(gd["pairs"], key=lambda p: -p["similarity"])[:5]
        avg_sim = gd["total_sim"] / gd["edge_count"] if gd["edge_count"] else 0.0
        result.append({
            "cluster_a": gd["cluster_a"],
            "cluster_b": gd["cluster_b"],
            "edge_count": gd["edge_count"],
            "avg_similarity": round(avg_sim, 4),
            "top_pairs": top,
        })

    return {"groups": result, "total_cross_edges": total_cross, "created_at": sem_data.get("created_at")}


class CreateOverlapRecommendationRequest(BaseModel):
    cluster_a: str
    cluster_b: str
    edge_count: int
    avg_similarity: float
    top_pairs: list[dict]
    triage_verdict: Optional[str] = None   # "duplicate" | "reference" | "related"
    triage_action: Optional[str] = None
    triage_confidence: Optional[float] = None
    triage_result: Optional[dict] = None


class TriageOverlapRequest(BaseModel):
    cluster_a: str
    cluster_b: str
    edge_count: int
    avg_similarity: float
    top_pairs: list[dict]
    model: Optional[str] = None


def _truncate_text(value: object, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _bounded_text_list(value: object, *, max_items: int = 5, max_len: int = 180) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for raw in value:
        text = _truncate_text(raw, max_len)
        if text:
            items.append(text)
        if len(items) >= max_items:
            break
    return items


def _overlap_pair_name(pair: dict) -> str:
    left = pair.get("label_a") or pair.get("source") or "left side"
    right = pair.get("label_b") or pair.get("target") or "right side"
    return f"{left} ↔ {right}"


def _path_container(path: object) -> str:
    parts = [part for part in str(path or "").replace("\\", "/").split("/") if part]
    if not parts:
        return "unknown"
    return "/".join(parts[:2]) if len(parts) > 1 else parts[0]


def _side_examples(top_pairs: list[dict], side: str) -> str:
    label_key = "label_a" if side == "a" else "label_b"
    file_key = "file_a" if side == "a" else "file_b"
    examples: list[str] = []
    for pair in top_pairs[:4]:
        label = str(pair.get(label_key) or "").strip()
        path = str(pair.get(file_key) or "").strip()
        if label and path:
            examples.append(f"{label} ({path})")
        elif label:
            examples.append(label)
        elif path:
            examples.append(path)
    return "; ".join(examples) if examples else "No concrete node examples were supplied."


def _fallback_overlap_dossier(req: TriageOverlapRequest, verdict: str = "related") -> dict:
    pairs = req.top_pairs[:6]
    same_name_count = sum(1 for pair in pairs if pair.get("same_name"))
    max_pair = max(pairs, key=lambda pair: float(pair.get("similarity") or 0), default={})
    max_pct = round(float(max_pair.get("similarity") or req.avg_similarity or 0) * 100)
    avg_pct = round(req.avg_similarity * 100)

    similarities = [
        f"{_overlap_pair_name(pair)} shares {round(float(pair.get('similarity') or 0) * 100)}% semantic similarity"
        + (" and the same filename" if pair.get("same_name") else "")
        + "."
        for pair in pairs[:3]
    ]
    if not similarities:
        similarities = [f"{req.cluster_a} and {req.cluster_b} have overlapping graph terms, but no top pair details were supplied."]

    differences: list[str] = []
    for pair in pairs[:3]:
        left_container = _path_container(pair.get("file_a"))
        right_container = _path_container(pair.get("file_b"))
        if left_container != right_container:
            differences.append(f"Different containers: {left_container} versus {right_container}.")
        left_label = str(pair.get("label_a") or "").strip()
        right_label = str(pair.get("label_b") or "").strip()
        if left_label and right_label and left_label != right_label:
            differences.append(f"Different node names: {left_label} versus {right_label}.")
        if len(differences) >= 4:
            break
    if not differences:
        differences.append("No meaningful difference is visible from the overlap metadata alone.")

    canonicality_signals: list[str] = []
    if same_name_count:
        canonicality_signals.append(f"{same_name_count} top pair(s) share a filename, which is a strong duplicate/canonical-owner signal.")
    if req.avg_similarity >= 0.9:
        canonicality_signals.append(f"Average similarity is {avg_pct}%, so one side may be a redundant copy.")
    if max_pair:
        canonicality_signals.append(f"Highest-similarity pair is {_overlap_pair_name(max_pair)} at {max_pct}%.")
    if not canonicality_signals:
        canonicality_signals.append("Canonical ownership is not clear from graph data; compare recency, call sites, and owner intent before merging.")

    return {
        "verdict": verdict if verdict in ("duplicate", "reference", "related", "unknown") else "related",
        "confidence": round(min(0.85, max(0.35, req.avg_similarity)), 2),
        "reason": (
            f"{req.cluster_a} and {req.cluster_b} overlap across {req.edge_count} semantic connections, "
            f"but the graph alone does not prove whether one side should replace the other."
        ),
        "action": "Inspect the named pairs, choose a canonical owner when duplication is confirmed, and preserve explicit references when both sides serve different jobs.",
        "evidence_summary": (
            f"This matters because {req.edge_count} cross-container semantic connections link {req.cluster_a} and {req.cluster_b} "
            f"(average {avg_pct}%). The top evidence points to {_overlap_pair_name(max_pair) if max_pair else 'the listed pairs'}."
        ),
        "per_side_purpose": {
            "cluster_a": f"{req.cluster_a} appears to cover: {_side_examples(pairs, 'a')}",
            "cluster_b": f"{req.cluster_b} appears to cover: {_side_examples(pairs, 'b')}",
        },
        "similarities": similarities,
        "differences": differences[:5],
        "canonicality_signals": canonicality_signals[:5],
        "open_questions": [
            f"Which side is the intended long-term owner for this knowledge: {req.cluster_a} or {req.cluster_b}?",
            "Are these files duplicates, or is one an intentional summary/reference of the other?",
            "Would merging remove needed context for a specific workflow, repo, or operator?",
        ],
    }


def _normalize_overlap_triage(data: dict, req: TriageOverlapRequest, model: str) -> dict:
    fallback = _fallback_overlap_dossier(req, str(data.get("verdict", "related")))
    verdict = str(data.get("verdict", fallback["verdict"]))
    if verdict not in ("duplicate", "reference", "related"):
        verdict = "related"

    raw_per_side = data.get("per_side_purpose")
    per_side = fallback["per_side_purpose"]
    if isinstance(raw_per_side, dict):
        per_side = {
            "cluster_a": _truncate_text(raw_per_side.get("cluster_a") or raw_per_side.get(req.cluster_a) or per_side["cluster_a"], 320),
            "cluster_b": _truncate_text(raw_per_side.get("cluster_b") or raw_per_side.get(req.cluster_b) or per_side["cluster_b"], 320),
        }

    try:
        confidence = float(data.get("confidence", fallback["confidence"]))
    except (TypeError, ValueError):
        confidence = float(fallback["confidence"])

    return {
        "verdict": verdict,
        "confidence": round(min(1.0, max(0.0, confidence)), 2),
        "reason": _truncate_text(data.get("reason") or fallback["reason"], 420),
        "action": _truncate_text(data.get("action") or fallback["action"], 520),
        "evidence_summary": _truncate_text(data.get("evidence_summary") or fallback["evidence_summary"], 520),
        "per_side_purpose": per_side,
        "similarities": _bounded_text_list(data.get("similarities"), max_items=5) or fallback["similarities"],
        "differences": _bounded_text_list(data.get("differences"), max_items=5) or fallback["differences"],
        "canonicality_signals": _bounded_text_list(data.get("canonicality_signals"), max_items=5) or fallback["canonicality_signals"],
        "open_questions": _bounded_text_list(data.get("open_questions"), max_items=5) or fallback["open_questions"],
        "model": model,
    }


def _unique_texts(values: list[object], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _overlap_action_plan(req: CreateOverlapRecommendationRequest, verdict: str, proposed_action: str) -> dict:
    pairs = req.top_pairs[:6]
    triage = req.triage_result if isinstance(req.triage_result, dict) else {}
    side_purpose = triage.get("per_side_purpose") if isinstance(triage.get("per_side_purpose"), dict) else {}
    open_questions = _bounded_text_list(triage.get("open_questions"), max_items=5)
    risks = _bounded_text_list(triage.get("risks"), max_items=5)

    files = _unique_texts(
        [p.get("file_a") for p in pairs] + [p.get("file_b") for p in pairs],
        limit=10,
    )
    pair_names = [_overlap_pair_name(p) for p in pairs[:5]]
    same_name_count = sum(1 for p in pairs if p.get("same_name"))

    if verdict == "duplicate":
        canonical_target = (
            f"Choose one canonical owner between {req.cluster_a} and {req.cluster_b}; "
            f"start with the side that is newer, more actively maintained, or closer to operator-facing docs."
        )
        concrete_steps = [
            f"Open the top {len(pair_names)} overlap pair(s) and compare source excerpts before editing.",
            "Select the canonical file or container and list the exact source files that will be merged into it.",
            "Move only non-duplicate detail into the canonical target; preserve useful links or history notes.",
            "Update references that still point to the merged-away wording or stale source.",
            "Re-run graph and overlap checks to confirm the duplicate signal dropped.",
        ]
        default_risks = [
            "A merge could remove context that is intentionally repo-specific.",
            "Choosing the wrong canonical owner could make future maintenance less obvious.",
            "Cross-references may become stale if only text is merged.",
        ]
    elif verdict == "reference":
        canonical_target = (
            f"Keep both {req.cluster_a} and {req.cluster_b}; make the canonical source of truth explicit in the cross-reference."
        )
        concrete_steps = [
            "Identify which side is source-of-truth and which side is reference, summary, or implementation context.",
            "Add or update cross-links so the relationship is obvious from both sides.",
            "Remove only duplicated wording that creates maintenance drift.",
            "Add a short note explaining why both locations remain.",
            "Re-run overlap review and mark the pair documented if the relationship is intentional.",
        ]
        default_risks = [
            "The pair may be intentional but undocumented, so merging could damage useful context.",
            "Cross-references could create circular or noisy documentation if overdone.",
        ]
    else:
        canonical_target = (
            f"Do not merge yet; document the relationship between {req.cluster_a} and {req.cluster_b} and gather owner evidence."
        )
        concrete_steps = [
            "Review the top overlap pairs and decide whether they are same-problem, reference, or shared vocabulary.",
            "Name the different job each side performs.",
            "Add a lightweight relationship note where future operators will see it.",
            "Defer consolidation until a canonical owner is clear.",
        ]
        default_risks = [
            "Similar vocabulary could be mistaken for duplicate implementation.",
            "Deferring the decision could leave future operators with the same ambiguity.",
        ]

    if not risks:
        risks = default_risks

    acceptance_criteria = [
        "The canonical owner or intentional dual-owner relationship is written down.",
        "Every top overlap pair has been reviewed against its source path, not only its label.",
        "Any merged or retained content still preserves repo-specific context needed by an operator.",
        "A follow-up overlap check shows fewer duplicate signals or a documented reason to keep them.",
    ]

    if side_purpose:
        purpose_a = _truncate_text(side_purpose.get("cluster_a") or "", 180)
        purpose_b = _truncate_text(side_purpose.get("cluster_b") or "", 180)
        if purpose_a or purpose_b:
            concrete_steps.insert(
                1,
                f"Use the triage purpose notes as a starting hypothesis: {req.cluster_a}: {purpose_a or 'unknown'}; {req.cluster_b}: {purpose_b or 'unknown'}.",
            )

    return {
        "canonical_target": canonical_target,
        "merge_sources": files or pair_names,
        "concrete_steps": concrete_steps,
        "savings_estimate": {
            "duplicate_node_count": len(pair_names),
            "affected_files": len(files),
            "semantic_edge_reduction": min(req.edge_count, max(0, len(pair_names) * 2)),
            "rough_context_savings": (
                f"Conservative: reviewing or consolidating the top {len(pair_names)} pair(s) could remove "
                f"roughly {min(req.edge_count, max(1, len(pair_names) * 2))} repeated semantic references from future graph context."
            ),
            "caveat": "Estimate is directional only; verify by rerunning Graphify/semantic overlap after the actual edit.",
        },
        "risks": risks,
        "acceptance_criteria": acceptance_criteria,
        "rollback_note": "Keep the original files until review is accepted; rollback is to restore the pre-merge files and remove added cross-reference notes.",
        "open_questions": open_questions or [
            f"Which side should be treated as canonical: {req.cluster_a} or {req.cluster_b}?",
            "Is the overlap duplicate content, an intentional reference, or shared vocabulary?",
            "Who owns the follow-up edit after this recommendation is accepted?",
        ],
        "source_pairs": pair_names,
        "same_name_count": same_name_count,
        "proposed_action": proposed_action,
    }


OverlapWorkflowStatus = Literal["untriaged", "triaged", "task-created", "dismissed"]


class PatchOverlapStatusRequest(BaseModel):
    status: OverlapWorkflowStatus
    cluster_a: Optional[str] = None
    cluster_b: Optional[str] = None
    triage_result: Optional[dict] = None
    recommendation_id: Optional[str] = None


def _load_overlap_statuses() -> dict[str, dict]:
    if not OVERLAP_STATUS_FILE.exists():
        return {}
    try:
        data = json.loads(OVERLAP_STATUS_FILE.read_text())
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items() if isinstance(v, dict)}
    except Exception:
        pass
    return {}


def _save_overlap_statuses(statuses: dict[str, dict]) -> None:
    OVERLAP_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    OVERLAP_STATUS_FILE.write_text(json.dumps(statuses, indent=2))


@app.get("/overlap/status")
def list_overlap_statuses() -> dict:
    return {"pairs": _load_overlap_statuses()}


@app.patch("/overlap/status/{pair_key}")
def patch_overlap_status(pair_key: str, req: PatchOverlapStatusRequest) -> dict:
    statuses = _load_overlap_statuses()
    now = datetime.now(tz=timezone.utc).isoformat()
    current = statuses.get(pair_key, {})
    record = {
        **current,
        "pair_key": pair_key,
        "status": req.status,
        "updated_at": now,
    }
    if "created_at" not in record:
        record["created_at"] = now
    if req.cluster_a is not None:
        record["cluster_a"] = req.cluster_a
    if req.cluster_b is not None:
        record["cluster_b"] = req.cluster_b
    if req.triage_result is not None:
        record["triage_result"] = req.triage_result
    if req.recommendation_id is not None:
        record["recommendation_id"] = req.recommendation_id
    statuses[pair_key] = record
    _save_overlap_statuses(statuses)
    return record


@app.post("/overlap/triage")
def triage_overlap(req: TriageOverlapRequest) -> dict:
    """Ask the local LLM to classify overlap as duplicate/reference/related."""
    model = (req.model or RECOMMEND_MODEL_DEFAULT).strip()
    same_name_pairs = [p for p in req.top_pairs if p.get("same_name")]
    pairs_text = "\n".join(
        f"- '{p.get('label_a', '?')}' ↔ '{p.get('label_b', '?')}'  "
        f"[{round(p.get('similarity', 0) * 100)}% similar"
        f"{', same filename' if p.get('same_name') else ''}] "
        f"A path: {p.get('file_a') or 'unknown'}; B path: {p.get('file_b') or 'unknown'}"
        for p in req.top_pairs[:6]
    )
    same_name_note = (
        f"\nNote: {len(same_name_pairs)} pairs share the same filename — strong duplicate signal."
        if same_name_pairs else ""
    )
    prompt = (
        f"You are analysing code-repository overlap. Two repository clusters have "
        f"{req.edge_count} semantically similar content connections "
        f"(avg {round(req.avg_similarity * 100)}% cosine similarity).{same_name_note}\n\n"
        f"Cluster A: {req.cluster_a}\n"
        f"Cluster B: {req.cluster_b}\n\n"
        f"Top overlapping content pairs:\n{pairs_text}\n\n"
        f"Classify this overlap as exactly ONE of:\n"
        f'- "duplicate": content is nearly identical — should be merged into one canonical location\n'
        f'- "reference": one document intentionally references or extends the other — keep both\n'
        f'- "related": similar topic but different enough in purpose to keep separate\n\n'
        f"Do not merely restate that semantic similarity is high. Explain what each side appears to do, "
        f"why the overlap matters to a decision-maker, what looks the same, what differs, whether either "
        f"side looks canonical, and what questions remain before merge/review/document action.\n\n"
        f"Return ONLY valid JSON with no extra text:\n"
        f'{{"verdict":"duplicate"|"reference"|"related","confidence":0.0-1.0,'
        f'"reason":"one sentence decision rationale",'
        f'"action":"one sentence recommended action",'
        f'"evidence_summary":"why this matters beyond high similarity",'
        f'"per_side_purpose":{{"cluster_a":"what {req.cluster_a} appears to do","cluster_b":"what {req.cluster_b} appears to do"}},'
        f'"similarities":["concrete similarity"],'
        f'"differences":["concrete difference"],'
        f'"canonicality_signals":["signal or unclear canonicality"],'
        f'"open_questions":["question to answer before acting"]}}'
    )
    try:
        raw = _call_ollama(prompt, model, timeout=90)
        data = json.loads(raw)
        return _normalize_overlap_triage(data, req, model)
    except Exception as exc:
        fallback = _fallback_overlap_dossier(req, "unknown")
        return {
            **fallback,
            "verdict": "unknown",
            "confidence": 0.0,
            "reason": f"Triage failed: {exc}",
            "model": model,
        }


@app.post("/recommendations/from-overlap", status_code=201)
def create_overlap_recommendation(req: CreateOverlapRecommendationRequest, request: Request) -> dict:
    """Create a recommendation from overlap analysis, enriched with triage verdict when available."""
    pairs_text = "\n".join(
        f"- {p.get('label_a', '?')} ↔ {p.get('label_b', '?')} [{round(p.get('similarity', 0) * 100)}% similar]"
        for p in req.top_pairs[:5]
    )
    now = datetime.now(tz=timezone.utc).isoformat()
    effort = "medium" if req.edge_count > 50 else "low"

    verdict = req.triage_verdict or "duplicate"
    title_prefix = {
        "duplicate": "Merge",
        "reference": "Review Cross-Reference",
        "related": "Document Relationship",
    }.get(verdict, "Consolidate")
    title = f"{title_prefix}: {req.cluster_a} ↔ {req.cluster_b} ({req.edge_count} overlapping nodes)"

    triage_note = ""
    if req.triage_verdict:
        conf_pct = round((req.triage_confidence or 0) * 100)
        triage_note = f"\n\nLLM triage verdict: {req.triage_verdict.upper()} ({conf_pct}% confidence)"

    summary_tail = {
        "duplicate": "These files appear to be near-duplicates. Review and merge into one canonical location.",
        "reference": "One cluster intentionally references or extends the other. Verify cross-references are explicit and up-to-date.",
        "related": "Content is similar in topic but serves different purposes. Consider documenting the relationship to avoid future confusion.",
    }.get(verdict, "Review these files for duplication and consolidate where appropriate.")

    proposed_action = req.triage_action if req.triage_action else (
        f"Review and consolidate overlapping content between '{req.cluster_a}' and '{req.cluster_b}'. "
        f"Focus on the {len(req.top_pairs)} highest-similarity node pairs listed above."
    )

    confidence = round(req.triage_confidence or min(0.95, req.avg_similarity), 2)

    action_plan = _overlap_action_plan(req, verdict, proposed_action)

    rec: dict = {
        "id": str(uuid.uuid4()),
        "mode": "duplicates",
        "title": title,
        "summary": (
            f"Semantic analysis detected {req.edge_count} cross-repo similarity connections between "
            f"'{req.cluster_a}' and '{req.cluster_b}' (avg {round(req.avg_similarity * 100)}% similar).{triage_note}\n\n"
            f"Top overlapping content:\n{pairs_text}\n\n"
            f"{summary_tail}"
        ),
        "evidence": [
            f"{p.get('label_a', '?')} ↔ {p.get('label_b', '?')} ({round(p.get('similarity', 0) * 100)}%)"
            for p in req.top_pairs[:5]
        ],
        "confidence": confidence,
        "risk": "low",
        "effort": effort,
        "proposed_action": proposed_action,
        "action_plan": action_plan,
        "overlap": {
            "cluster_a": req.cluster_a,
            "cluster_b": req.cluster_b,
            "edge_count": req.edge_count,
            "avg_similarity": req.avg_similarity,
            "top_pairs": req.top_pairs[:5],
        },
        "overlap_dossier": req.triage_result if isinstance(req.triage_result, dict) else None,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "model": "overlap-analysis" if not req.triage_verdict else f"overlap-analysis+triage",
        "created_by": getattr(request.state, "user_id", "local"),
    }
    _save_recommendation(rec)
    return rec


# ---------------------------------------------------------------------------
# Chunk Sixteen — Knowledge Base Cluster Selector
# ---------------------------------------------------------------------------

class ClusterSelectionBody(BaseModel):
    sources: list[str]
    clusters: Optional[list[str]] = None  # None = all clusters active


@app.get("/cluster-selection")
def get_cluster_selection() -> dict:
    """Return the current cluster/source selection and available options."""
    selection = _load_cluster_selection()
    # Compute available clusters from the active graph (≥20 nodes each)
    available_clusters: list[dict] = []
    try:
        data = _load_graph()
        counts: dict[str, int] = {}
        for n in data.get("nodes", []):
            sf = n.get("source_file", "")
            cluster = sf.split("/")[0] if sf else ""
            if cluster:
                counts[cluster] = counts.get(cluster, 0) + 1
        available_clusters = [
            {"id": k, "node_count": v}
            for k, v in sorted(counts.items(), key=lambda x: -x[1])
            if v >= 20
        ]
    except Exception:
        pass
    # Available sources: local always present; cloud only when authenticated
    available_sources = ["local"]
    if _ms_auth.is_authenticated(WORKSPACE_STATE):
        available_sources.extend(["sharepoint", "onenote"])
    return {
        "selection": selection,
        "available_clusters": available_clusters,
        "available_sources": available_sources,
    }


@app.put("/cluster-selection")
def update_cluster_selection(req: ClusterSelectionBody) -> dict:
    """Atomically persist the cluster/source selection. Clears summary cache."""
    global _summary_cache
    selection = {"sources": req.sources, "clusters": req.clusters}
    _save_cluster_selection(selection)
    _summary_cache = {}
    return selection


# ---------------------------------------------------------------------------
# Chunk Fourteen — Cloud Knowledge Base Connectors
# ---------------------------------------------------------------------------

import sys as _sys  # noqa: E402

_connectors_path = Path(__file__).parent / "connectors"
if str(_connectors_path.parent) not in _sys.path:
    _sys.path.insert(0, str(_connectors_path.parent))

from connectors import microsoft_auth as _ms_auth  # noqa: E402
from connectors.ingest import merge_nodes_into_graph as _ingest  # noqa: E402
from connectors.sharepoint import SharePointConnector  # noqa: E402
from connectors.onenote import OneNoteConnector  # noqa: E402

_SYNC_STATUS: dict[str, dict] = {}
_SYNC_LOCK = _threading.Lock()

_CONNECTOR_CONFIG_PATH = Path(__file__).parent.parent / "config" / "connectors.json"


def _load_connector_config() -> dict:
    if _CONNECTOR_CONFIG_PATH.exists():
        try:
            return json.loads(_CONNECTOR_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {"sharepoint": {"site_urls": []}, "sync_interval_hours": 0}


def _connector_status_path() -> Path:
    CONNECTORS_DIR.mkdir(parents=True, exist_ok=True)
    return CONNECTORS_DIR / "sync-status.json"


def _load_sync_status() -> dict:
    p = _connector_status_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def _save_sync_status(status: dict) -> None:
    _connector_status_path().write_text(json.dumps(status, indent=2))


def _run_connector_sync(connector_id: str) -> None:
    """Background sync job — mirrors mission pattern."""
    now = datetime.now(tz=timezone.utc).isoformat()
    with _SYNC_LOCK:
        _SYNC_STATUS[connector_id] = {
            "status": "syncing",
            "started_at": now,
            "finished_at": None,
            "item_count": 0,
            "error": None,
        }

    try:
        cfg = _load_connector_config()
        graph_path = Path(_graph_path())
        item_count = 0

        if connector_id == "sharepoint":
            site_urls = cfg.get("sharepoint", {}).get("site_urls", [])
            conn = SharePointConnector(WORKSPACE_STATE, site_urls)
            items = conn.list_items()
            nodes = conn.to_graph_nodes(items)
            item_count = len(nodes)
        elif connector_id == "onenote":
            conn_one = OneNoteConnector(WORKSPACE_STATE)
            items = conn_one.list_items()
            nodes = conn_one.to_graph_nodes(items)
            item_count = len(nodes)
        else:
            raise ValueError(f"Unknown connector: {connector_id}")

        if nodes:
            new_graph = _ingest(nodes, graph_path, GRAPHS_DIR)
            # Activate merged graph
            global _graph_cache, _summary_cache
            settings: dict = {}
            if SETTINGS_FILE.exists():
                try:
                    settings = json.loads(SETTINGS_FILE.read_text())
                except Exception:
                    pass
            settings["graph_path"] = str(new_graph)
            WORKSPACE_STATE.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
            _graph_cache = None
            _summary_cache = {}

        finished = datetime.now(tz=timezone.utc).isoformat()
        result = {
            "status": "complete",
            "started_at": now,
            "finished_at": finished,
            "item_count": item_count,
            "error": None,
        }
    except Exception as exc:
        finished = datetime.now(tz=timezone.utc).isoformat()
        result = {
            "status": "error",
            "started_at": now,
            "finished_at": finished,
            "item_count": 0,
            "error": str(exc),
        }

    with _SYNC_LOCK:
        _SYNC_STATUS[connector_id] = result
    _save_sync_status({**_load_sync_status(), connector_id: result})


@app.get("/connectors")
def list_connectors() -> list[dict]:
    """List configured connectors with authentication and sync status."""
    cfg = _load_connector_config()
    persisted = _load_sync_status()

    def _status(cid: str) -> dict:
        with _SYNC_LOCK:
            mem = _SYNC_STATUS.get(cid)
        return mem or persisted.get(cid) or {}

    ms_authed = _ms_auth.is_authenticated(WORKSPACE_STATE)
    ms_configured = _ms_auth.is_configured()

    connectors = [
        {
            "id": "sharepoint",
            "display_name": "SharePoint",
            "source": "microsoft",
            "configured": ms_configured,
            "authenticated": ms_authed,
            "site_urls": cfg.get("sharepoint", {}).get("site_urls", []),
            "sync": _status("sharepoint"),
        },
        {
            "id": "onenote",
            "display_name": "OneNote",
            "source": "microsoft",
            "configured": ms_configured,
            "authenticated": ms_authed,
            "sync": _status("onenote"),
        },
    ]
    return connectors


@app.post("/connectors/microsoft/auth")
def start_microsoft_auth() -> dict:
    """Initiate Microsoft device code flow. Returns user_code + verification_uri."""
    try:
        return _ms_auth.start_device_flow(WORKSPACE_STATE)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/connectors/microsoft/auth/poll")
def poll_microsoft_auth() -> dict:
    """Poll for device code completion. Returns {status: pending|complete|error}."""
    return _ms_auth.poll_device_flow(WORKSPACE_STATE)


@app.post("/connectors/{connector_id}/sync", status_code=202)
def sync_connector(connector_id: str) -> dict:
    """Trigger a background sync for the given connector."""
    if connector_id not in ("sharepoint", "onenote"):
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    if not _ms_auth.is_authenticated(WORKSPACE_STATE):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Microsoft. Complete device code auth first."
        )
    with _SYNC_LOCK:
        current = _SYNC_STATUS.get(connector_id, {})
    if current.get("status") == "syncing":
        raise HTTPException(status_code=409, detail="Sync already in progress.")

    thread = _threading.Thread(
        target=_run_connector_sync, args=(connector_id,), daemon=True
    )
    thread.start()
    return {"connector_id": connector_id, "status": "syncing"}


@app.get("/connectors/{connector_id}/status")
def connector_sync_status(connector_id: str) -> dict:
    """Return the last sync status for a connector."""
    if connector_id not in ("sharepoint", "onenote"):
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    with _SYNC_LOCK:
        mem = _SYNC_STATUS.get(connector_id)
    if mem:
        return mem
    persisted = _load_sync_status()
    return persisted.get(connector_id) or {"status": "never_synced"}


@app.delete("/connectors/{connector_id}/auth", status_code=200)
def revoke_connector_auth(connector_id: str) -> dict:
    """Revoke Microsoft token and clear cache. Re-auth required afterward."""
    if connector_id not in ("sharepoint", "onenote", "microsoft"):
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    _ms_auth.revoke_token(WORKSPACE_STATE)
    return {"revoked": True, "connector_id": connector_id}


# ---------------------------------------------------------------------------
# Chunk Seventeen — In-Cockpit AI Assistant
# ---------------------------------------------------------------------------


class _ChatMsgModel(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[_ChatMsgModel] = []
    include_graph_context: bool = True


class ChatConfigBody(BaseModel):
    system_prompt: str
    model: Optional[str] = None


@app.get("/chat-config")
def get_chat_config() -> dict:
    """Return the current AI assistant configuration."""
    return _load_chat_config()


@app.put("/chat-config")
def update_chat_config(req: ChatConfigBody) -> dict:
    """Persist AI assistant configuration."""
    config = _load_chat_config()
    config["system_prompt"] = req.system_prompt
    if req.model is not None:
        config["model"] = req.model.strip() or RECOMMEND_MODEL_DEFAULT
    WORKSPACE_STATE.mkdir(parents=True, exist_ok=True)
    CHAT_CONFIG_FILE.write_text(json.dumps(config, indent=2))
    return config


@app.post("/chat")
def chat_stream(req: ChatRequest):
    """Stream an Ollama chat response with cluster-aware graph context via SSE."""
    config = _load_chat_config()
    system_prompt = config.get("system_prompt", _CHAT_DEFAULT_SYSTEM_PROMPT)
    model = config.get("model", RECOMMEND_MODEL_DEFAULT)

    nodes_used = 0
    graph_ctx = ""
    if req.include_graph_context:
        try:
            summary = graph_summary()
            graph_ctx = _build_graph_context(summary)
            nodes_used = len(summary.get("nodes", []))
        except Exception:
            pass

    sys_content = system_prompt
    if graph_ctx:
        sys_content = f"{system_prompt}\n\nGraph context:\n{graph_ctx}"
    messages = [{"role": "system", "content": sys_content}]
    for h in req.history[-20:]:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": req.message})

    session_id = str(uuid.uuid4())
    CHAT_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    (CHAT_SESSIONS_DIR / f"{session_id}.json").write_text(
        json.dumps({
            "session_id": session_id,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "message": req.message,
            "history_len": len(req.history),
            "nodes_used": nodes_used,
            "model": model,
        }, indent=2)
    )
    _prune_chat_sessions()

    _ollama_base = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    def _generate():
        import urllib.request as _ureq
        yield f"data: {json.dumps({'type': 'meta', 'nodes_used': nodes_used, 'session_id': session_id})}\n\n"
        payload = json.dumps({"model": model, "messages": messages, "stream": True}).encode()
        req_obj = _ureq.Request(
            f"{_ollama_base}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with _ureq.urlopen(req_obj, timeout=120) as resp:
                for raw in resp:
                    line = raw.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
                        if chunk.get("done"):
                            yield f"data: {json.dumps({'type': 'done'})}\n\n"
                            return
                    except Exception:
                        continue
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
