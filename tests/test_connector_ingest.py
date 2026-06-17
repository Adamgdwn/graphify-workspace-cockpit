from __future__ import annotations

import json
from pathlib import Path

from backend.connectors.ingest import merge_nodes_into_graph


def test_connector_ingest_emits_canonical_links(tmp_path: Path) -> None:
    active_graph = tmp_path / "active.json"
    active_graph.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "existing",
                        "label": "Workspace API",
                        "description": "Graph schema routing contract",
                    }
                ],
                "edges": [
                    {
                        "source": "existing",
                        "target": "legacy",
                        "label": "related",
                    }
                ],
            }
        )
    )

    merged_path = merge_nodes_into_graph(
        [
            {
                "id": "sharepoint:item-1",
                "label": "Workspace routing notes",
                "description": "Graph schema routing contract notes",
            }
        ],
        active_graph,
        tmp_path / "graphs",
    )

    merged = json.loads(merged_path.read_text())

    assert "edges" not in merged
    assert merged["links"][0]["relation"] == "related"
    assert any(link["source"] == "sharepoint:item-1" for link in merged["links"])
