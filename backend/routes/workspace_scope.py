"""Workspace scope route group."""

from __future__ import annotations

import os
import string
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
    suggested_roots: Callable[[], dict]


def _append_existing_dir(paths: list[str], seen: set[str], path: Path) -> None:
    try:
        resolved = path.expanduser().resolve()
    except Exception:
        return
    if not resolved.is_dir():
        return
    key = os.path.normcase(str(resolved))
    if key in seen:
        return
    seen.add(key)
    paths.append(str(resolved))


def _windows_drive_roots() -> list[Path]:
    roots: list[Path] = []
    for letter in string.ascii_uppercase:
        path = Path(f"{letter}:\\")
        if path.is_dir():
            roots.append(path)
    return roots


def _home_onedrive_roots(home_path: Path) -> list[Path]:
    try:
        candidates = sorted(home_path.iterdir(), key=lambda path: path.name.lower())
    except Exception:
        return []
    return [
        path
        for path in candidates
        if path.is_dir() and path.name.lower().startswith("onedrive")
    ]


def suggested_workspace_roots(
    *,
    repo_root: Path,
    workspace_state: Path,
    graph_path: Path | None,
    home: Path | None = None,
) -> dict:
    """Return host-specific roots the UI can offer before a scope is saved."""
    home_path = home or Path.home()
    paths: list[str] = []
    seen: set[str] = set()

    preferred_paths = [
        repo_root.parent,
        repo_root,
        home_path,
        home_path / "01. Code Projects",
        home_path / "Code",
        home_path / "code",
        home_path / "source",
        home_path / "src",
        home_path / "Documents",
        home_path / "Desktop",
        home_path / "OneDrive",
        *_home_onedrive_roots(home_path),
    ]
    if os.name == "nt":
        preferred_paths.extend(_windows_drive_roots())
    else:
        preferred_paths.extend([Path("/"), home_path / "code", Path("/mnt"), Path("/media")])

    for path in preferred_paths:
        _append_existing_dir(paths, seen, path)

    return {
        "platform": "windows" if os.name == "nt" else os.name,
        "initial_root": paths[0] if paths else str(home_path.expanduser().resolve()),
        "roots": paths,
        "repo_root": str(repo_root.expanduser().resolve()),
        "state_dir": str(workspace_state.expanduser().resolve()),
        "graph_path": str(graph_path.expanduser().resolve()) if graph_path else "",
    }


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


def get_suggested_roots(deps: WorkspaceScopeDeps) -> dict:
    return deps.suggested_roots()


def create_workspace_scope_router(deps_factory: Callable[[], WorkspaceScopeDeps]) -> APIRouter:
    router = APIRouter()

    @router.get("/workspace-scope")
    def get_workspace_scope_endpoint() -> dict:
        return get_scope_profile(deps_factory())

    @router.put("/workspace-scope")
    def put_workspace_scope_endpoint(body: WorkspaceScopeProfileBody) -> dict:
        return put_scope_profile(body, deps_factory())

    @router.get("/workspace-scope/suggested-roots")
    def get_workspace_scope_suggested_roots_endpoint() -> dict:
        return get_suggested_roots(deps_factory())

    @router.post("/workspace-scope/inspect")
    def inspect_workspace_scope_endpoint(body: WorkspaceScopeInspectBody) -> dict:
        return inspect_scope(body, deps_factory())

    return router
