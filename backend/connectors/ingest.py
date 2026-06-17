"""Merge connector graph nodes into the active graph.

Deduplicates by node id (source:item_id).
Computes lightweight term-overlap links between new and existing nodes.
Writes a timestamped merged graph to graphs_dir and returns the new path.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from backend.graph_schema import normalize_graph
except ModuleNotFoundError:
    from graph_schema import normalize_graph

_STOP = frozenset({
    "the", "and", "for", "this", "that", "with", "from", "are", "was",
    "not", "has", "have", "been", "its", "can", "will", "all", "one",
    "but", "more", "also", "than", "which", "some", "their",
})


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z][a-z0-9_-]{2,}", text.lower())
    return {t for t in tokens if t not in _STOP}


def _node_text(n: dict) -> str:
    return " ".join([
        n.get("label", ""),
        n.get("description", ""),
        n.get("summary", ""),
        n.get("notebook", ""),
        n.get("section", ""),
        str(n.get("metadata", "")),
    ])


def merge_nodes_into_graph(
    new_nodes: list[dict],
    active_graph_path: Path,
    graphs_dir: Path,
) -> Path:
    """
    Merge new_nodes into active_graph_path.
    Returns path to the newly written merged graph file.
    """
    if active_graph_path.exists():
        data = normalize_graph(json.loads(active_graph_path.read_text()))
    else:
        data = {"nodes": [], "links": []}

    existing_nodes: list[dict] = data.get("nodes", [])
    existing_links: list[dict] = data.get("links", [])
    existing_ids = {n["id"] for n in existing_nodes}

    to_add = [n for n in new_nodes if n["id"] not in existing_ids]

    # Build term → [node_id] index over existing nodes
    term_index: dict[str, list[str]] = {}
    for n in existing_nodes:
        for term in _tokenize(_node_text(n)):
            term_index.setdefault(term, []).append(n["id"])

    seen_pairs: set[frozenset] = {
        frozenset([e.get("source", ""), e.get("target", "")]) for e in existing_links
    }
    new_links: list[dict] = []

    for n in to_add:
        terms = _tokenize(_node_text(n))
        hits: Counter[str] = Counter()
        for term in terms:
            for eid in term_index.get(term, []):
                hits[eid] += 1
        for target_id, count in hits.most_common(3):
            if count < 2:
                break
            pair = frozenset([n["id"], target_id])
            if pair not in seen_pairs:
                new_links.append({
                    "source": n["id"],
                    "target": target_id,
                    "relation": "related",
                    "weight": round(min(count / 10.0, 1.0), 3),
                })
                seen_pairs.add(pair)

    merged = {
        "nodes": existing_nodes + to_add,
        "links": existing_links + new_links,
        "meta": data.get("meta", {}),
    }

    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = graphs_dir / f"cloud-merged-{ts}.json"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, indent=2))
    return out_path
