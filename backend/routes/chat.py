"""In-cockpit AI assistant route group."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class ChatMsgModel(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMsgModel] = []
    include_graph_context: bool = True


class ChatConfigBody(BaseModel):
    system_prompt: str
    model: str | None = None


@dataclass(frozen=True)
class ChatDeps:
    load_chat_config: Callable[[], dict]
    chat_config_file: Callable[[], Path]
    chat_sessions_dir: Callable[[], Path]
    write_json_atomic: Callable[[Path, dict], None]
    prune_chat_sessions: Callable[[], None]
    recommend_model_default: Callable[[], str]
    default_system_prompt: Callable[[], str]
    graph_summary: Callable[[], dict]
    build_graph_context: Callable[[dict], str]
    ollama_url: Callable[[], str]


def get_chat_config(deps: ChatDeps) -> dict:
    return deps.load_chat_config()


def update_chat_config(req: ChatConfigBody, deps: ChatDeps) -> dict:
    config = deps.load_chat_config()
    config["system_prompt"] = req.system_prompt
    if req.model is not None:
        config["model"] = req.model.strip() or deps.recommend_model_default()
    deps.write_json_atomic(deps.chat_config_file(), config)
    return config


def chat_stream(req: ChatRequest, deps: ChatDeps):
    config = deps.load_chat_config()
    system_prompt = config.get("system_prompt", deps.default_system_prompt())
    model = config.get("model", deps.recommend_model_default())

    nodes_used = 0
    graph_ctx = ""
    if req.include_graph_context:
        try:
            summary = deps.graph_summary()
            graph_ctx = deps.build_graph_context(summary)
            nodes_used = len(summary.get("nodes", []))
        except Exception:
            pass

    sys_content = system_prompt
    if graph_ctx:
        sys_content = f"{system_prompt}\n\nGraph context:\n{graph_ctx}"
    messages = [{"role": "system", "content": sys_content}]
    for history_item in req.history[-20:]:
        messages.append({"role": history_item.role, "content": history_item.content})
    messages.append({"role": "user", "content": req.message})

    session_id = str(uuid.uuid4())
    deps.write_json_atomic(
        deps.chat_sessions_dir() / f"{session_id}.json",
        {
            "session_id": session_id,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "message": req.message,
            "history_len": len(req.history),
            "nodes_used": nodes_used,
            "model": model,
        },
    )
    deps.prune_chat_sessions()

    ollama_base = deps.ollama_url()

    def _generate():
        import urllib.request as _ureq
        yield f"data: {json.dumps({'type': 'meta', 'nodes_used': nodes_used, 'session_id': session_id})}\n\n"
        payload = json.dumps({"model": model, "messages": messages, "stream": True}).encode()
        req_obj = _ureq.Request(
            f"{ollama_base}/api/chat",
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


def create_chat_router(
    deps_factory: Callable[[], ChatDeps],
) -> tuple[
    APIRouter,
    Callable[[], dict],
    Callable[[ChatConfigBody], dict],
    Callable[[ChatRequest], object],
]:
    router = APIRouter()

    def get_chat_config_endpoint() -> dict:
        return get_chat_config(deps_factory())

    def update_chat_config_endpoint(req: ChatConfigBody) -> dict:
        return update_chat_config(req, deps_factory())

    def chat_stream_endpoint(req: ChatRequest):
        return chat_stream(req, deps_factory())

    router.add_api_route("/chat-config", get_chat_config_endpoint, methods=["GET"])
    router.add_api_route("/chat-config", update_chat_config_endpoint, methods=["PUT"])
    router.add_api_route("/chat", chat_stream_endpoint, methods=["POST"])

    return (
        router,
        get_chat_config_endpoint,
        update_chat_config_endpoint,
        chat_stream_endpoint,
    )
