"""Atomic local state writes for the file-backed backend."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _atomic_replace(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        tmp_path.replace(path)
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass


def write_text_atomic(path: Path | str, content: str, *, encoding: str = "utf-8") -> None:
    """Write text by replacing the destination from a temp file in the same directory."""
    _atomic_replace(Path(path), content.encode(encoding))


def write_json_atomic(path: Path | str, payload: Any) -> None:
    """Write JSON with parent creation and same-directory atomic replacement."""
    write_text_atomic(path, json.dumps(payload, indent=2) + "\n")
