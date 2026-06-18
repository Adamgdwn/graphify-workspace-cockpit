"""Workspace scope inspection for safe, pre-scan tree summaries."""

from __future__ import annotations

import os
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    from backend import config as _config
except ModuleNotFoundError:
    import config as _config


ScopeState = Literal["included", "excluded", "partial"]
EntryKind = Literal["directory", "file", "symlink", "other"]
SignalTier = Literal["overview", "important", "evidence", "hidden", "excluded"]
ImportanceTier = Literal["anchor", "interface", "important", "evidence", "hidden", "excluded"]

DEFAULT_EXCLUDE_PATTERNS = [
    "node_modules/",
    ".venv/",
    "venv/",
    ".pnpm-store/",
    "dist/",
    "build/",
    ".next/",
    "out/",
    "coverage/",
    ".cache/",
    ".pytest_cache/",
    "__pycache__/",
    ".ruff_cache/",
    ".git/",
    "graphify-out/",
    "graphify-out/cache/",
    "workspace/state/",
    ".env*",
    "*.pem",
    "*.key",
]

DEFAULT_SIGNAL_SETTINGS = {
    "hide_low_signal": True,
    "show_generated": False,
    "min_visible_signal": "important",
}

VISIBLE_SIGNAL_TIERS = {"overview", "important"}
VISIBLE_KNOWLEDGE_TIERS = {"anchor", "interface", "important"}

GENERATED_TYPE_FILENAMES = {
    "_vercel-types.ts",
    "next-env.d.ts",
    "vite-env.d.ts",
}

LOCKFILE_NAMES = {
    "bun.lockb",
    "cargo.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}

SOURCE_OF_TRUTH_NAMES = {
    "agents.md",
    "architecture.md",
    "claude.md",
    "dockerfile",
    "package.json",
    "project-control.yaml",
    "pyproject.toml",
    "readme.md",
    "requirements.txt",
    "roadmap.md",
    "runbook.md",
    "start_here.md",
    "tsconfig.json",
    "vite.config.ts",
}

IMPORTANT_PATH_MARKERS = {
    "adr",
    "adrs",
    "api",
    "auth",
    "config",
    "contracts",
    "db",
    "docs",
    "governance",
    "main",
    "migrations",
    "models",
    "policy",
    "prompts",
    "routes",
    "schema",
    "schemas",
    "settings",
    "standards",
}

INTERFACE_PATH_MARKERS = {
    "api",
    "auth",
    "contract",
    "contracts",
    "db",
    "interface",
    "interfaces",
    "migration",
    "migrations",
    "public",
    "route",
    "routes",
    "schema",
    "schemas",
    "storage",
}

CONFIG_BOUNDARY_NAMES = {
    "caddyfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "dockerfile",
    "eslint.config.js",
    "next.config.js",
    "next.config.mjs",
    "package.json",
    "project-control.yaml",
    "pyproject.toml",
    "requirements.txt",
    "tailwind.config.js",
    "tsconfig.json",
    "vite.config.ts",
}

ENTRYPOINT_NAMES = {
    "app.py",
    "index.ts",
    "index.tsx",
    "main.go",
    "main.py",
    "main.ts",
    "main.tsx",
    "server.py",
    "server.ts",
    "server.tsx",
}

HIGH_SIGNAL_TEST_MARKERS = {
    "api",
    "auth",
    "contract",
    "contracts",
    "e2e",
    "integration",
    "schema",
    "scope",
    "service",
    "smoke",
    "workflow",
}

LOW_SIGNAL_PATH_MARKERS = {
    "__fixtures__",
    "fixtures",
    "mocks",
    "snapshots",
    "testdata",
}

EXCLUDED_DIR_REASONS = {
    ".git": "VCS internals are excluded before indexing.",
    "node_modules": "Dependency folders are excluded before indexing.",
    ".venv": "Virtual environments are excluded before indexing.",
    "venv": "Virtual environments are excluded before indexing.",
    ".pnpm-store": "Dependency stores are excluded before indexing.",
    "dist": "Build outputs are excluded before indexing.",
    "build": "Build outputs are excluded before indexing.",
    ".next": "Build outputs are excluded before indexing.",
    "out": "Build outputs are excluded before indexing.",
    "coverage": "Coverage output is excluded before indexing.",
    ".cache": "Caches are excluded before indexing.",
    ".pytest_cache": "Caches are excluded before indexing.",
    "__pycache__": "Caches are excluded before indexing.",
    ".ruff_cache": "Caches are excluded before indexing.",
    "graphify-out": "Generated Graphify output is excluded before indexing.",
}

MEDIA_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".tif",
    ".tiff",
    ".wav",
    ".webm",
    ".webp",
    ".zip",
}

PROJECT_MARKERS = {
    "package.json": "node",
    "pnpm-lock.yaml": "node",
    "yarn.lock": "node",
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "Dockerfile": "container",
    "docker-compose.yml": "container",
    "README.md": "project",
    "AGENTS.md": "project",
}


class WorkspaceScopeError(ValueError):
    """Raised when a workspace scope request cannot be safely inspected."""


@dataclass
class CountBudget:
    files_remaining: int = 10_000
    dirs_remaining: int = 2_000
    truncated: bool = False


def _entry_kind(path: Path) -> EntryKind:
    if path.is_symlink():
        return "symlink"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "other"


def _relative_path(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return ""
    return "" if str(rel) == "." else rel.as_posix()


def _path_parts(path: Path, root: Path) -> list[str]:
    rel = _relative_path(path, root)
    return [part.lower() for part in rel.split("/") if part]


def _contains_workspace_state(path: Path, root: Path) -> bool:
    parts = _path_parts(path, root)
    return any(left == "workspace" and right == "state" for left, right in zip(parts, parts[1:]))


def _is_secret_like(path: Path, root: Path) -> bool:
    rel = _relative_path(path, root).lower()
    name = path.name.lower()
    if name.startswith(".env") or name.endswith((".pem", ".key")):
        return True
    parts = _path_parts(path, root)
    markers = tuple(marker.lower() for marker in _config.SECRET_PATH_MARKERS)
    return any(marker in parts or marker in rel for marker in markers)


def _basic_exclusion_reasons(path: Path, root: Path) -> list[str]:
    name = path.name
    reasons: list[str] = []
    kind = _entry_kind(path)

    if kind == "symlink":
        reasons.append("Symlinks are excluded from inspection to avoid recursive or surprising paths.")
        return reasons

    if _is_secret_like(path, root):
        reasons.append("Secret-like path detected; presence is reported but contents are never read.")

    if _contains_workspace_state(path, root):
        reasons.append("Cockpit local state is excluded before indexing.")

    if kind == "directory" and name in EXCLUDED_DIR_REASONS:
        reasons.append(EXCLUDED_DIR_REASONS[name])

    if kind == "file" and name.lower() in LOCKFILE_NAMES:
        reasons.append("Lockfiles are low-signal dependency state and are hidden from default maps.")

    if kind == "file" and path.suffix.lower() in MEDIA_EXTENSIONS:
        reasons.append("Binary or media bulk is excluded unless explicitly included.")

    return reasons


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _path_matches_default_exclusion(
    path: Path,
    root: Path,
    patterns: list[str] | None = None,
) -> bool:
    rel = _relative_path(path, root).lower()
    parts = _path_parts(path, root)
    name = path.name.lower()

    if any(part in EXCLUDED_DIR_REASONS for part in parts):
        return True
    if any(left == "workspace" and right == "state" for left, right in zip(parts, parts[1:])):
        return True
    if _is_secret_like(path, root):
        return True
    if path.is_file() and name in LOCKFILE_NAMES:
        return True
    if path.suffix.lower() in MEDIA_EXTENSIONS:
        return True
    for pattern in patterns or DEFAULT_EXCLUDE_PATTERNS:
        normalized = pattern.lower().strip()
        if normalized.endswith("/"):
            pattern_name = normalized.strip("/")
            if pattern_name in parts:
                return True
            continue
        if normalized.startswith("*.") and name.endswith(normalized[1:]):
            return True
        if normalized.endswith("*") and name.startswith(normalized[:-1]):
            return True
        if normalized == rel or normalized == name:
            return True
    return False


def _detect_project_type(path: Path) -> str | None:
    if not path.is_dir() or path.is_symlink():
        return None
    if (path / ".git").is_dir():
        return "git-repo"
    for marker, project_type in PROJECT_MARKERS.items():
        if (path / marker).exists():
            return project_type
    return None


def _count_files(path: Path, root: Path, *, excluded: bool, budget: CountBudget) -> tuple[int, int]:
    if budget.files_remaining <= 0 or budget.dirs_remaining <= 0:
        budget.truncated = True
        return 0, 0

    kind = _entry_kind(path)
    if kind == "file":
        budget.files_remaining -= 1
        if excluded or _basic_exclusion_reasons(path, root):
            return 0, 1
        return 1, 0
    if kind != "directory":
        return 0, 0

    budget.dirs_remaining -= 1
    own_excluded = excluded or bool(_basic_exclusion_reasons(path, root))
    included_count = 0
    excluded_count = 0
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                if budget.files_remaining <= 0 or budget.dirs_remaining <= 0:
                    budget.truncated = True
                    break
                child = Path(entry.path)
                child_included, child_excluded = _count_files(
                    child,
                    root,
                    excluded=own_excluded,
                    budget=budget,
                )
                included_count += child_included
                excluded_count += child_excluded
    except OSError:
        budget.truncated = True
    return included_count, excluded_count


def _child_entries(path: Path) -> list[Path]:
    try:
        children = [Path(entry.path) for entry in os.scandir(path)]
    except OSError:
        return []
    return sorted(children, key=lambda item: (not item.is_dir(), item.name.lower()))


def _include_tree_entry(path: Path, root: Path) -> bool:
    kind = _entry_kind(path)
    if kind == "directory":
        return True
    return bool(_basic_exclusion_reasons(path, root))


def _build_node(
    path: Path,
    root: Path,
    *,
    depth: int,
    max_depth: int,
    child_limit: int,
) -> dict:
    kind = _entry_kind(path)
    reasons = _basic_exclusion_reasons(path, root)
    project_type = _detect_project_type(path)
    is_root = path == root
    should_stop_at_project = bool(project_type) and not is_root
    count_budget = CountBudget()
    included_count, excluded_count = _count_files(
        path,
        root,
        excluded=bool(reasons),
        budget=count_budget,
    )

    children: list[dict] = []
    children_truncated = False
    if (
        kind == "directory"
        and not reasons
        and depth < max_depth
        and not should_stop_at_project
    ):
        visible_children = [child for child in _child_entries(path) if _include_tree_entry(child, root)]
        if len(visible_children) > child_limit:
            children_truncated = True
            visible_children = visible_children[:child_limit]
        children = [
            _build_node(
                child,
                root,
                depth=depth + 1,
                max_depth=max_depth,
                child_limit=child_limit,
            )
            for child in visible_children
        ]

    if reasons:
        state: ScopeState = "excluded"
    elif excluded_count or any(child["state"] != "included" for child in children):
        state = "partial"
    else:
        state = "included"

    warnings: list[str] = []
    if count_budget.truncated or children_truncated:
        warnings.append("Inspection was truncated to keep the summary bounded.")
    if included_count + excluded_count > 1_000:
        warnings.append("Large folder; review scope before rebuilding.")

    return {
        "name": path.name,
        "path": str(path),
        "relative_path": _relative_path(path, root),
        "kind": kind,
        "state": state,
        "project_type": project_type,
        "is_repo": project_type == "git-repo",
        "reasons": reasons,
        "warnings": warnings,
        "estimated_file_count": included_count + excluded_count,
        "estimated_included_count": included_count,
        "estimated_excluded_count": excluded_count,
        "children": children,
    }


def inspect_workspace_scope(
    root: str | Path,
    *,
    max_depth: int = 3,
    child_limit: int = 250,
) -> dict:
    """Return a safe tree summary for a parent folder without reading file contents."""
    if max_depth < 1:
        raise WorkspaceScopeError("max_depth must be at least 1.")
    if max_depth > 6:
        max_depth = 6

    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise WorkspaceScopeError(f"Root does not exist: {root_path}")
    if not root_path.is_dir():
        raise WorkspaceScopeError(f"Root is not a directory: {root_path}")

    tree = _build_node(root_path, root_path, depth=0, max_depth=max_depth, child_limit=child_limit)
    return {
        "root": {
            "name": root_path.name,
            "path": str(root_path),
            "exists": True,
            "kind": "directory",
            "state": tree["state"],
            "project_type": tree["project_type"],
            "estimated_file_count": tree["estimated_file_count"],
            "estimated_included_count": tree["estimated_included_count"],
            "estimated_excluded_count": tree["estimated_excluded_count"],
        },
        "max_depth": max_depth,
        "exclude_patterns": DEFAULT_EXCLUDE_PATTERNS,
        "tree": tree,
    }


def _normalize_scope_path(value: str, *, root_path: Path, field_name: str) -> str:
    if not value or not value.strip():
        raise WorkspaceScopeError(f"{field_name} contains an empty path.")
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(root_path)
    except ValueError as exc:
        raise WorkspaceScopeError(f"{field_name} must stay within root: {path}") from exc
    return str(path)


def normalize_workspace_scope_profile(payload: dict) -> dict:
    """Validate and normalize a persisted workspace scope profile."""
    root = payload.get("root")
    if not isinstance(root, str) or not root.strip():
        raise WorkspaceScopeError("root is required.")
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise WorkspaceScopeError(f"Root does not exist: {root_path}")
    if not root_path.is_dir():
        raise WorkspaceScopeError(f"Root is not a directory: {root_path}")

    profile_name = payload.get("profile_name")
    if not isinstance(profile_name, str) or not profile_name.strip():
        profile_name = "Workspace Scope"

    included_paths = payload.get("included_paths", [])
    excluded_paths = payload.get("excluded_paths", [])
    if not isinstance(included_paths, list) or not all(isinstance(item, str) for item in included_paths):
        raise WorkspaceScopeError("included_paths must be a list of paths.")
    if not isinstance(excluded_paths, list) or not all(isinstance(item, str) for item in excluded_paths):
        raise WorkspaceScopeError("excluded_paths must be a list of paths.")

    normalized_included = sorted({
        _normalize_scope_path(path, root_path=root_path, field_name="included_paths")
        for path in included_paths
    })
    normalized_excluded = sorted({
        _normalize_scope_path(path, root_path=root_path, field_name="excluded_paths")
        for path in excluded_paths
    })

    exclude_patterns = payload.get("exclude_patterns", DEFAULT_EXCLUDE_PATTERNS)
    if not isinstance(exclude_patterns, list) or not all(isinstance(item, str) for item in exclude_patterns):
        raise WorkspaceScopeError("exclude_patterns must be a list of strings.")
    normalized_exclude_patterns = list(dict.fromkeys(exclude_patterns))

    if not normalized_included:
        raise WorkspaceScopeError("Select at least one included folder before generating a workspace map.")
    for path_text in normalized_included:
        path = Path(path_text)
        if not path.is_dir():
            raise WorkspaceScopeError(f"included_paths must contain directories: {path}")
        if _path_matches_default_exclusion(path, root_path, normalized_exclude_patterns):
            raise WorkspaceScopeError(f"included_paths cannot include default-ignored paths: {path}")

    signal = payload.get("signal", {})
    if not isinstance(signal, dict):
        raise WorkspaceScopeError("signal must be an object.")
    normalized_signal = {
        **DEFAULT_SIGNAL_SETTINGS,
        **{key: value for key, value in signal.items() if key in DEFAULT_SIGNAL_SETTINGS},
    }
    if normalized_signal["min_visible_signal"] not in {"overview", "important", "evidence", "hidden"}:
        normalized_signal["min_visible_signal"] = DEFAULT_SIGNAL_SETTINGS["min_visible_signal"]

    return {
        "root": str(root_path),
        "profile_name": profile_name.strip(),
        "included_paths": normalized_included,
        "excluded_paths": normalized_excluded,
        "exclude_patterns": normalized_exclude_patterns,
        "signal": normalized_signal,
    }


def load_workspace_scope_profile(path: Path | str) -> dict | None:
    """Load a saved workspace scope profile, returning None for empty state."""
    profile_path = Path(path)
    if not profile_path.exists():
        return None
    try:
        payload = json.loads(profile_path.read_text())
    except Exception as exc:
        raise WorkspaceScopeError(f"Saved workspace scope is invalid JSON: {profile_path}") from exc
    if not isinstance(payload, dict):
        raise WorkspaceScopeError("Saved workspace scope must be an object.")
    return normalize_workspace_scope_profile(payload)


def save_workspace_scope_profile(path: Path | str, payload: dict, write_json_atomic) -> dict:
    """Persist a normalized workspace scope profile through the provided writer."""
    normalized = normalize_workspace_scope_profile(payload)
    write_json_atomic(Path(path), normalized)
    return normalized


def workspace_scope_scan_roots(profile: Mapping) -> list[Path]:
    """Return de-duplicated scan roots from a saved workspace scope profile."""
    root = Path(str(profile["root"])).expanduser().resolve()
    excluded_paths = [
        Path(str(path)).expanduser().resolve()
        for path in profile.get("excluded_paths", [])
    ]
    exclude_patterns = [
        str(pattern)
        for pattern in profile.get("exclude_patterns", DEFAULT_EXCLUDE_PATTERNS)
        if isinstance(pattern, str)
    ]
    included = profile.get("included_paths") or []
    candidates: list[Path] = []
    for raw in included:
        path = Path(str(raw)).expanduser().resolve()
        if not path.is_dir():
            continue
        if not _path_is_within(path, root):
            continue
        if any(path == excluded or _path_is_within(path, excluded) for excluded in excluded_paths):
            continue
        if _path_matches_default_exclusion(path, root, exclude_patterns):
            continue
        candidates.append(path)

    deduped = sorted(set(candidates), key=lambda item: (len(item.parts), str(item)))
    scan_roots: list[Path] = []
    for candidate in deduped:
        if any(candidate != existing and _path_is_within(candidate, existing) for existing in scan_roots):
            continue
        scan_roots.append(candidate)
    return scan_roots


def _resolve_node_source_path(node: Mapping, scan_root: Path) -> Path | None:
    for key in ("source_file", "file_path", "path"):
        value = node.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        raw_path = Path(value).expanduser()
        try:
            return raw_path.resolve() if raw_path.is_absolute() else (scan_root / raw_path).resolve()
        except Exception:
            return None
    return None


def _node_source_text(node: Mapping, source_path: Path | None, scan_root: Path) -> str:
    if source_path is not None:
        try:
            return source_path.relative_to(scan_root).as_posix()
        except ValueError:
            return source_path.as_posix()
    for key in ("source_file", "file_path", "path"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.replace("\\", "/")
    return ""


def _node_type(node: Mapping) -> str:
    return str(node.get("file_type") or node.get("type") or "").strip().lower()


def _metadata_text(node: Mapping, key: str) -> str:
    metadata = node.get("metadata")
    if not isinstance(metadata, Mapping):
        return ""
    value = metadata.get(key)
    return str(value or "").strip().lower()


def _has_any_marker(parts: list[str], markers: set[str]) -> bool:
    return any(part in markers for part in parts)


def _stem_has_any_marker(stem: str, markers: set[str]) -> bool:
    tokens = {token for token in stem.replace("_", "-").split("-") if token}
    return bool(tokens & markers)


def _is_type_declaration(name: str) -> bool:
    return name.endswith(".d.ts") or name.endswith(".d.mts") or name.endswith(".d.cts")


def _source_stem(name: str) -> str:
    for suffix in (".d.ts", ".d.mts", ".d.cts"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name.rsplit(".", 1)[0] if "." in name else name


def _is_dependency_type_declaration(name: str, parts: list[str]) -> bool:
    if not _is_type_declaration(name):
        return False
    return (
        "node_modules" in parts
        or ".pnpm" in parts
        or "@types" in parts
        or any(part.startswith("@types+") for part in parts)
    )


def _is_workspace_type_contract(name: str, stem: str, parts: list[str]) -> bool:
    if not _is_type_declaration(name):
        return False
    contract_markers = {
        "api",
        "contract",
        "contracts",
        "interface",
        "interfaces",
        "public",
        "schema",
        "schemas",
        "sdk",
    }
    return _has_any_marker(parts, contract_markers) or _stem_has_any_marker(stem, contract_markers)


def _is_high_signal_test(stem: str, parts: list[str]) -> bool:
    if not _has_any_marker(parts, {"test", "tests", "__tests__"}):
        return False
    return _has_any_marker(parts, HIGH_SIGNAL_TEST_MARKERS) or _stem_has_any_marker(stem, HIGH_SIGNAL_TEST_MARKERS)


def classify_file_importance(
    node: Mapping,
    *,
    degree: int = 0,
    source_path: Path | None = None,
    scan_root: Path | None = None,
) -> tuple[ImportanceTier, str]:
    """Classify a graph node by decision/knowledge value.

    The heuristic is intentionally conservative: known source-of-truth files
    and cross-project boundaries stay visible, ordinary implementation becomes
    evidence, and common generated/dependency/fixture noise is opt-in only.
    """
    root = scan_root or (source_path.parent if source_path else Path.cwd())
    source_text = _node_source_text(node, source_path, root).lower()
    parts = [part for part in source_text.split("/") if part]
    name = parts[-1] if parts else ""
    stem = _source_stem(name)
    node_type = _node_type(node)
    kind = _metadata_text(node, "kind")
    source = str(node.get("source") or node.get("origin") or "").strip().lower()

    if name in GENERATED_TYPE_FILENAMES:
        return "hidden", "generated type shim"
    if _is_dependency_type_declaration(name, parts):
        return "hidden", "dependency type declaration"
    if name in LOCKFILE_NAMES:
        return "hidden", "lockfile"
    if name == "__init__.py":
        return "hidden", "package marker"
    if any(marker in parts for marker in LOW_SIGNAL_PATH_MARKERS):
        return "hidden", "fixture or mock evidence"
    if "generated" in parts or "generated" in kind:
        return "hidden", "generated source"
    if _is_workspace_type_contract(name, stem, parts):
        return "interface", "workspace-owned type contract"
    if _is_type_declaration(name):
        return "hidden", "ambient type declaration"

    if source and source not in {"local", "graphify"}:
        return "important", "connector workspace item"
    if name in SOURCE_OF_TRUTH_NAMES:
        return "anchor", "source-of-truth file"
    if name in CONFIG_BOUNDARY_NAMES:
        return "anchor", "configuration boundary"
    if node_type == "rationale":
        return "anchor", "decision context"
    if node_type == "document":
        if any(marker in parts for marker in {"docs", "policy", "standards", "architecture", "adr", "adrs"}):
            return "anchor", "governance or architecture document"
        return "evidence", "supporting document"
    if _has_any_marker(parts, INTERFACE_PATH_MARKERS) or _stem_has_any_marker(stem, INTERFACE_PATH_MARKERS):
        return "interface", "public API or data boundary"
    if name in ENTRYPOINT_NAMES or stem.startswith("main-"):
        return "important", "runtime entry point"
    if _is_high_signal_test(stem, parts):
        return "important", "high-signal test"
    if _has_any_marker(parts, IMPORTANT_PATH_MARKERS) or _stem_has_any_marker(stem, IMPORTANT_PATH_MARKERS):
        return "important", "important path role"
    if degree >= 20:
        return "important", "high graph degree"
    if degree >= 6:
        return "important", "connected implementation node"
    return "evidence", "supporting evidence"


def _signal_tier_from_importance(importance: ImportanceTier, *, degree: int = 0) -> SignalTier:
    if importance == "excluded":
        return "excluded"
    if importance == "hidden":
        return "hidden"
    if importance == "evidence":
        return "evidence"
    if degree >= 20:
        return "overview"
    return "important"


def classify_signal_tier(
    node: Mapping,
    *,
    degree: int = 0,
    source_path: Path | None = None,
    scan_root: Path | None = None,
) -> tuple[SignalTier, str]:
    """Classify a graph node for default map visibility."""
    importance, reason = classify_file_importance(
        node,
        degree=degree,
        source_path=source_path,
        scan_root=scan_root,
    )
    return _signal_tier_from_importance(importance, degree=degree), reason


def signal_counts(nodes: list[Mapping]) -> dict[str, int]:
    """Return stable signal tier counts for API metadata."""
    counts = {tier: 0 for tier in ("overview", "important", "evidence", "hidden", "excluded")}
    for node in nodes:
        tier = str(node.get("signal_tier") or "evidence")
        if tier not in counts:
            tier = "evidence"
        counts[tier] += 1
    return counts


def importance_counts(nodes: list[Mapping]) -> dict[str, int]:
    """Return stable file-importance counts for API metadata."""
    counts = {tier: 0 for tier in ("anchor", "interface", "important", "evidence", "hidden", "excluded")}
    for node in nodes:
        tier = str(node.get("importance_tier") or "evidence")
        if tier not in counts:
            tier = "evidence"
        counts[tier] += 1
    return counts


def is_visible_signal_node(node: Mapping, *, include_low_signal: bool = False) -> bool:
    """Return whether a node should appear on default Map surfaces."""
    tier = str(node.get("signal_tier") or "evidence")
    if include_low_signal:
        return tier != "excluded"
    return tier in VISIBLE_SIGNAL_TIERS


def is_visible_knowledge_node(node: Mapping) -> bool:
    """Return whether a node belongs on the workspace-knowledge lens."""
    tier = str(node.get("importance_tier") or "evidence")
    return tier in VISIBLE_KNOWLEDGE_TIERS


def apply_signal_tiers_to_graph(graph: Mapping, *, scan_root: Path | None = None) -> dict:
    """Return a graph whose nodes include explicit signal and importance metadata."""
    links = [link for link in graph.get("links", []) if isinstance(link, Mapping)]
    degree: Counter[str] = Counter()
    for link in links:
        source = str(link.get("source") or "")
        target = str(link.get("target") or "")
        if source:
            degree[source] += 1
        if target:
            degree[target] += 1

    nodes: list[dict] = []
    for raw_node in graph.get("nodes", []):
        if not isinstance(raw_node, Mapping):
            continue
        node = dict(raw_node)
        node_id = str(node.get("id") or "")
        source_path = _resolve_node_source_path(node, scan_root) if scan_root else None
        importance, reason = classify_file_importance(
            node,
            degree=degree[node_id],
            source_path=source_path,
            scan_root=scan_root,
        )
        node["importance_tier"] = importance
        node["importance_reason"] = reason
        node["signal_tier"] = _signal_tier_from_importance(importance, degree=degree[node_id])
        node["signal_reason"] = reason
        nodes.append(node)

    result = {
        key: value
        for key, value in dict(graph).items()
        if key not in {"nodes", "links", "edges"}
    }
    result["nodes"] = nodes
    result["links"] = [dict(link) for link in links]
    return result


def _node_scope_metadata(profile: Mapping, scan_root: Path) -> dict:
    return {
        "scope_profile": str(profile.get("profile_name") or "Workspace Scope"),
        "source_root": str(scan_root),
        "source_root_name": scan_root.name,
        "repo_project_name": scan_root.name,
    }


def filter_workspace_scope_graph(graph: Mapping, profile: Mapping, scan_root: Path) -> tuple[dict, dict]:
    """Remove nodes outside a saved scope and annotate kept nodes with scope metadata."""
    root = Path(str(profile["root"])).expanduser().resolve()
    scan_root = Path(scan_root).expanduser().resolve()
    excluded_paths = [
        Path(str(path)).expanduser().resolve()
        for path in profile.get("excluded_paths", [])
    ]
    exclude_patterns = [
        str(pattern)
        for pattern in profile.get("exclude_patterns", DEFAULT_EXCLUDE_PATTERNS)
        if isinstance(pattern, str)
    ]
    kept_nodes: list[dict] = []
    kept_ids: set[str] = set()
    removed_count = 0
    metadata = _node_scope_metadata(profile, scan_root)
    degree: Counter[str] = Counter()
    for raw_link in graph.get("links", []):
        if not isinstance(raw_link, Mapping):
            continue
        source = str(raw_link.get("source") or "")
        target = str(raw_link.get("target") or "")
        if source:
            degree[source] += 1
        if target:
            degree[target] += 1

    for raw_node in graph.get("nodes", []):
        if not isinstance(raw_node, Mapping):
            removed_count += 1
            continue
        node_id = str(raw_node.get("id") or "")
        source_path = _resolve_node_source_path(raw_node, scan_root)
        excluded = False
        if source_path is not None:
            if not _path_is_within(source_path, root) or not _path_is_within(source_path, scan_root):
                excluded = True
            if any(source_path == excluded_path or _path_is_within(source_path, excluded_path) for excluded_path in excluded_paths):
                excluded = True
            if _path_matches_default_exclusion(source_path, root, exclude_patterns):
                excluded = True
        if excluded or not node_id:
            removed_count += 1
            continue
        kept = dict(raw_node)
        for key, value in metadata.items():
            kept.setdefault(key, value)
        importance, reason = classify_file_importance(
            kept,
            degree=degree[node_id],
            source_path=source_path,
            scan_root=scan_root,
        )
        kept["importance_tier"] = importance
        kept["importance_reason"] = reason
        kept["signal_tier"] = _signal_tier_from_importance(importance, degree=degree[node_id])
        kept["signal_reason"] = reason
        kept_nodes.append(kept)
        kept_ids.add(node_id)

    kept_links = []
    for raw_link in graph.get("links", []):
        if not isinstance(raw_link, Mapping):
            continue
        if str(raw_link.get("source") or "") in kept_ids and str(raw_link.get("target") or "") in kept_ids:
            kept_links.append(dict(raw_link))

    filtered = {
        key: value
        for key, value in dict(graph).items()
        if key not in {"nodes", "links", "edges"}
    }
    filtered["nodes"] = kept_nodes
    filtered["links"] = kept_links
    stats = {
        "removed_node_count": removed_count,
        "kept_node_count": len(kept_nodes),
        "kept_link_count": len(kept_links),
        "signal_counts": signal_counts(kept_nodes),
        "importance_counts": importance_counts(kept_nodes),
    }
    return filtered, stats
