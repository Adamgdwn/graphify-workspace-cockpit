"""Abstract base and graph contract helpers for cloud knowledge connectors."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


ConnectorGraphNode = dict[str, Any]
ConnectorGraphLink = dict[str, Any]


def _path_part(value: Any, fallback: str = "item") -> str:
    text = str(value or fallback).strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-._")
    return (text or fallback)[:100]


def connector_source_file(connector_id: str, *parts: Any) -> str:
    """Build the virtual source path that lets Graphify UI group cloud nodes."""
    cleaned = [_path_part(connector_id, "connector")]
    cleaned.extend(_path_part(part) for part in parts if str(part or "").strip())
    return "/".join(cleaned)


def connector_node(
    *,
    connector_id: str,
    item_id: Any,
    label: Any,
    node_type: str,
    file_type: str = "document",
    source_path_parts: tuple[Any, ...] = (),
    metadata: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> ConnectorGraphNode:
    """Return a cloud node that is also compatible with local Graphify nodes.

    Connector nodes use a provider-stable ``id`` of
    ``<connector_id>:<provider_item_id>``, keep ``source`` as the simple
    connector id used by source filters, and include ``source_file`` /
    ``file_type`` so Map and Settings can group, filter, and count them beside
    local Graphify graph data.
    """
    source = str(connector_id)
    source_file = connector_source_file(source, *(source_path_parts or (item_id,)))
    node: ConnectorGraphNode = {
        "id": f"{source}:{item_id}",
        "label": str(label or item_id),
        "type": str(node_type or file_type),
        "file_type": str(file_type or "document"),
        "source": source,
        "source_file": source_file,
        "_origin": source,
        "metadata": dict(metadata or {}),
    }
    for key, value in dict(extra or {}).items():
        if value is not None:
            node[key] = value
    return node


def normalize_connector_node(raw: Mapping[str, Any]) -> ConnectorGraphNode:
    """Normalize a connector-produced node before it is merged into a graph."""
    raw_id = raw.get("id")
    if not raw_id:
        raise ValueError("connector node must include id")

    node = dict(raw)
    node_id = str(raw_id)
    source = str(
        node.get("source")
        or (node_id.split(":", 1)[0] if ":" in node_id else "connector")
    )
    label = str(node.get("label") or node_id)
    node["id"] = node_id
    node["label"] = label
    node["source"] = source
    node.setdefault("_origin", source)
    node.setdefault("type", "document")
    node["file_type"] = str(node.get("file_type") or "document")
    node.setdefault("source_file", connector_source_file(source, label))
    metadata = node.get("metadata")
    node["metadata"] = dict(metadata) if isinstance(metadata, Mapping) else {}
    return node


def connector_link(
    *,
    source: Any,
    target: Any,
    relation: str = "related",
    weight: float = 1.0,
) -> ConnectorGraphLink:
    """Return the canonical link shape shared with local Graphify graphs."""
    return {
        "source": str(source),
        "target": str(target),
        "relation": str(relation or "related"),
        "weight": float(weight),
    }


class ConnectorBase(ABC):
    connector_id: str
    display_name: str

    @abstractmethod
    def is_authenticated(self) -> bool: ...

    @abstractmethod
    def list_items(self) -> list[dict]: ...

    @abstractmethod
    def fetch_content(self, item_id: str) -> str: ...

    def to_graph_nodes(self, items: list[dict]) -> list[ConnectorGraphNode]:
        return []
