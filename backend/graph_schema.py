"""Graph schema normalization for backend graph contracts."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


class GraphValidationError(ValueError):
    """Raised when graph JSON cannot be normalized safely."""


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GraphValidationError(f"{label} must be an object")
    return value


def _normalize_link(raw: Any, index: int) -> dict[str, Any]:
    link = _as_mapping(raw, f"link[{index}]")
    source = link.get("source")
    target = link.get("target")
    if not source or not target:
        raise GraphValidationError(f"link[{index}] must include source and target")

    normalized = dict(link)
    normalized["source"] = str(source)
    normalized["target"] = str(target)
    normalized["relation"] = str(
        link.get("relation") or link.get("label") or "related"
    )
    normalized.pop("label", None)
    return normalized


def normalize_graph(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Return a graph using canonical ``links`` relationships.

    The backend accepts historical/internal ``edges`` records for compatibility,
    but all callers should receive a graph with ``links`` only.
    """
    graph = _as_mapping(graph, "graph")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        raise GraphValidationError("graph must include a nodes array")

    raw_links: list[Any] = []
    links = graph.get("links")
    edges = graph.get("edges")
    if links is not None:
        if not isinstance(links, list):
            raise GraphValidationError("links must be an array")
        raw_links.extend(links)
    if edges is not None:
        if not isinstance(edges, list):
            raise GraphValidationError("edges must be an array")
        raw_links.extend(edges)

    normalized = {
        key: deepcopy(value)
        for key, value in graph.items()
        if key not in {"links", "edges"}
    }
    normalized["nodes"] = deepcopy(nodes)
    normalized_links: list[dict[str, Any]] = []
    seen_links: set[tuple[str, str, str]] = set()
    for index, raw_link in enumerate(raw_links):
        link = _normalize_link(raw_link, index)
        key = (link["source"], link["target"], link["relation"])
        if key in seen_links:
            continue
        normalized_links.append(link)
        seen_links.add(key)
    normalized["links"] = normalized_links
    return normalized


def validate_graph(graph: Mapping[str, Any]) -> None:
    """Validate that graph JSON can be normalized."""
    normalize_graph(graph)


def count_links(graph: Mapping[str, Any]) -> int:
    """Count canonical links after accepting legacy edge-shaped input."""
    return len(normalize_graph(graph).get("links", []))
