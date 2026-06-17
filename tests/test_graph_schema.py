from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.graph_schema import GraphValidationError, count_links, normalize_graph


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_normalize_graph_keeps_links_as_canonical_relationships() -> None:
    graph = normalize_graph(load_fixture("demo_graph_links.json"))

    assert "edges" not in graph
    assert graph["links"] == [
        {
            "source": "frontend:App",
            "target": "backend:main",
            "relation": "calls",
            "weight": 1,
        }
    ]
    assert count_links(graph) == 1


def test_normalize_graph_accepts_legacy_edges_and_label_relation() -> None:
    graph = normalize_graph(load_fixture("demo_graph_edges.json"))

    assert "edges" not in graph
    assert graph["links"] == [
        {
            "source": "frontend:Settings",
            "target": "backend:settings",
            "relation": "uses",
            "weight": 1,
        }
    ]
    assert count_links(graph) == 1


def test_normalize_graph_defaults_missing_relation_to_related() -> None:
    graph = normalize_graph(
        {
            "nodes": [{"id": "a"}, {"id": "b"}],
            "edges": [{"source": "a", "target": "b"}],
        }
    )

    assert graph["links"][0]["relation"] == "related"


def test_normalize_graph_deduplicates_links_and_edges() -> None:
    graph = normalize_graph(
        {
            "nodes": [{"id": "a"}, {"id": "b"}],
            "links": [{"source": "a", "target": "b", "relation": "calls"}],
            "edges": [{"source": "a", "target": "b", "label": "calls"}],
        }
    )

    assert count_links(graph) == 1


def test_normalize_graph_rejects_malformed_links() -> None:
    with pytest.raises(GraphValidationError, match="source and target"):
        normalize_graph({"nodes": [{"id": "a"}], "links": [{"source": "a"}]})


def test_normalize_graph_can_require_links_to_reference_nodes() -> None:
    graph = {"nodes": [{"id": "a"}], "links": [{"source": "a", "target": "missing"}]}

    assert count_links(graph) == 1
    with pytest.raises(GraphValidationError, match="reference existing nodes"):
        normalize_graph(graph, require_link_targets=True)


def test_normalize_graph_requires_nodes_array() -> None:
    with pytest.raises(GraphValidationError, match="nodes array"):
        normalize_graph({"links": []})
