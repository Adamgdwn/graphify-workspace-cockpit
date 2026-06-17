"""Workspace scope route group."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from backend.workspace_scope import (
        WorkspaceScopeError,
        inspect_workspace_scope,
        load_workspace_scope_profile,
        save_workspace_scope_profile,
    )
except ModuleNotFoundError:
    from workspace_scope import (
        WorkspaceScopeError,
        inspect_workspace_scope,
        load_workspace_scope_profile,
        save_workspace_scope_profile,
    )


class WorkspaceScopeInspectBody(BaseModel):
    root: str
    max_depth: int = 3


class WorkspaceScopeProfileBody(BaseModel):
    root: str
    profile_name: str = "Workspace Scope"
    included_paths: list[str] = Field(default_factory=list)
    excluded_paths: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] | None = None
    signal: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class WorkspaceScopeDeps:
    inspect_scope: Callable[..., dict]
    scope_file: Callable[[], Path]
    write_json_atomic: Callable[[Path, Any], None]


def inspect_scope(body: WorkspaceScopeInspectBody, deps: WorkspaceScopeDeps) -> dict:
    try:
        return deps.inspect_scope(body.root, max_depth=body.max_depth)
    except WorkspaceScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def get_scope_profile(deps: WorkspaceScopeDeps) -> dict:
    try:
        profile = load_workspace_scope_profile(deps.scope_file())
    except WorkspaceScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"profile": profile}


def put_scope_profile(body: WorkspaceScopeProfileBody, deps: WorkspaceScopeDeps) -> dict:
    if hasattr(body, "model_dump"):
        payload = body.model_dump(exclude_none=True)
    else:
        payload = body.dict(exclude_none=True)
    try:
        profile = save_workspace_scope_profile(
            deps.scope_file(),
            payload,
            deps.write_json_atomic,
        )
    except WorkspaceScopeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"profile": profile}


def create_workspace_scope_router(deps_factory: Callable[[], WorkspaceScopeDeps]) -> APIRouter:
    router = APIRouter()

    @router.get("/workspace-scope")
    def get_workspace_scope_endpoint() -> dict:
        return get_scope_profile(deps_factory())

    @router.put("/workspace-scope")
    def put_workspace_scope_endpoint(body: WorkspaceScopeProfileBody) -> dict:
        return put_scope_profile(body, deps_factory())

    @router.post("/workspace-scope/inspect")
    def inspect_workspace_scope_endpoint(body: WorkspaceScopeInspectBody) -> dict:
        return inspect_scope(body, deps_factory())

    return router
