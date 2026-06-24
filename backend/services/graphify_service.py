"""Graphify CLI service boundary.

This module keeps subprocess behavior, runtime detection, and safe error
mapping out of the FastAPI route handlers.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Sequence

GRAPHIFY_EXECUTABLE = "graphify"
GRAPHIFY_MISSING = "GRAPHIFY_MISSING"
GRAPHIFY_TIMEOUT = "GRAPHIFY_TIMEOUT"
GRAPHIFY_COMMAND_FAILED = "GRAPHIFY_COMMAND_FAILED"
GRAPHIFY_VERSION_UNKNOWN = "GRAPHIFY_VERSION_UNKNOWN"

GraphifyAskMode = Literal["query", "path", "explain"]


@dataclass(frozen=True)
class GraphifyCommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return (self.stdout or "") + (self.stderr or "")


class GraphifyServiceError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 503,
        command: Sequence[str] | None = None,
        stderr: str | None = None,
        stdout: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.command = list(command or [])
        self.stderr = stderr
        self.stdout = stdout

    def to_detail(self) -> dict:
        detail = {"code": self.code, "message": self.message}
        if self.stderr:
            detail["stderr"] = self.stderr[:500]
        return detail


def is_graphify_available(executable: str = GRAPHIFY_EXECUTABLE) -> bool:
    return _resolve_graphify(executable) is not None


def get_graphify_version(
    executable: str = GRAPHIFY_EXECUTABLE,
    *,
    timeout: int = 5,
) -> str | None:
    try:
        result = _run_graphify(
            ["--version"],
            executable=executable,
            timeout=timeout,
            check=False,
        )
    except GraphifyServiceError:
        return None
    if result.returncode != 0:
        return None
    version = result.output.strip().splitlines()
    return version[0] if version else None


def get_graphify_status(
    executable: str = GRAPHIFY_EXECUTABLE,
    *,
    include_version: bool = True,
) -> dict:
    if not is_graphify_available(executable):
        return {
            "available": False,
            "version": None,
            "code": GRAPHIFY_MISSING,
            "message": "Graphify CLI is not installed or is not on PATH.",
        }

    version = get_graphify_version(executable) if include_version else None
    status = {"available": True, "version": version, "code": None, "message": None}
    if include_version and version is None:
        status["code"] = GRAPHIFY_VERSION_UNKNOWN
        status["message"] = "Graphify CLI was found, but its version could not be read."
    return status


def run_graphify_ask(
    *,
    mode: GraphifyAskMode,
    question: str,
    graph_path: str | Path,
    node_a: str | None = None,
    node_b: str | None = None,
    timeout: int = 30,
) -> GraphifyCommandResult:
    graph = str(graph_path)
    if mode == "path":
        if not node_a or not node_b:
            raise ValueError("Path mode requires node_a and node_b.")
        args = ["path", node_a, node_b, "--graph", graph]
    elif mode == "explain":
        args = ["explain", node_a or question, "--graph", graph]
    else:
        args = ["query", question, "--graph", graph]
    return _run_graphify(args, timeout=timeout)


def run_graphify_update(
    target: str | Path,
    *,
    cwd: str | Path | None = None,
    timeout: int = 300,
) -> GraphifyCommandResult:
    return _run_graphify(
        ["update", str(target), "--no-cluster"],
        cwd=cwd,
        timeout=timeout,
    )


def run_graphify_extract(
    target: str | Path,
    *,
    cwd: str | Path | None = None,
    backend: str,
    model: str | None = None,
    mode: str | None = "deep",
    timeout: int = 1800,
    api_timeout: int = 600,
    max_concurrency: int = 2,
    no_cluster: bool = True,
) -> GraphifyCommandResult:
    args = ["extract", str(target), "--backend", backend]
    if model:
        args.extend(["--model", model])
    if mode:
        args.extend(["--mode", mode])
    if max_concurrency > 0:
        args.extend(["--max-concurrency", str(max_concurrency)])
    if api_timeout > 0:
        args.extend(["--api-timeout", str(api_timeout)])
    if no_cluster:
        args.append("--no-cluster")
    return _run_graphify(args, cwd=cwd, timeout=timeout)


def run_graphify_merge(
    graph_paths: Iterable[str | Path],
    *,
    out_path: str | Path,
    timeout: int = 300,
) -> GraphifyCommandResult:
    args = ["merge-graphs", *[str(p) for p in graph_paths], "--out", str(out_path)]
    return _run_graphify(args, timeout=timeout)


def _run_graphify(
    args: Sequence[str],
    *,
    executable: str = GRAPHIFY_EXECUTABLE,
    cwd: str | Path | None = None,
    timeout: int,
    check: bool = True,
) -> GraphifyCommandResult:
    resolved = _resolve_graphify(executable)
    display_command = [executable, *[str(arg) for arg in args]]
    if resolved is None:
        raise GraphifyServiceError(
            GRAPHIFY_MISSING,
            "Graphify CLI is not installed or is not on PATH. Install it with `pip install graphifyy`.",
            status_code=503,
            command=display_command,
        )

    try:
        completed = subprocess.run(
            [resolved, *[str(arg) for arg in args]],
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise GraphifyServiceError(
            GRAPHIFY_TIMEOUT,
            f"Graphify CLI timed out after {timeout} seconds.",
            status_code=504,
            command=display_command,
            stderr=exc.stderr if isinstance(exc.stderr, str) else None,
            stdout=exc.stdout if isinstance(exc.stdout, str) else None,
        ) from exc
    except FileNotFoundError as exc:
        raise GraphifyServiceError(
            GRAPHIFY_MISSING,
            "Graphify CLI is not installed or is not on PATH. Install it with `pip install graphifyy`.",
            status_code=503,
            command=display_command,
        ) from exc

    result = GraphifyCommandResult(
        command=display_command,
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
    if check and result.returncode != 0:
        raise GraphifyServiceError(
            GRAPHIFY_COMMAND_FAILED,
            "Graphify CLI returned a non-zero exit code.",
            status_code=503,
            command=display_command,
            stderr=result.stderr,
            stdout=result.stdout,
        )
    return result


def _resolve_graphify(executable: str = GRAPHIFY_EXECUTABLE) -> str | None:
    resolved = shutil.which(executable)
    if resolved is not None:
        return resolved

    # Launchers call `.venv/bin/uvicorn` directly without activating the venv,
    # so PATH may not include the sibling `graphify` console script.
    candidates = [Path(sys.executable).with_name(executable)]
    if os.name == "nt" and not Path(executable).suffix:
        candidates.extend(
            Path(sys.executable).with_name(f"{executable}{suffix}")
            for suffix in (".exe", ".cmd", ".bat")
        )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None
