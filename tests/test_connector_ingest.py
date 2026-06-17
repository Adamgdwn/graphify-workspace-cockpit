from __future__ import annotations

import json
from pathlib import Path

from backend import main
from backend.connectors.ingest import merge_nodes_into_graph
from backend.connectors.onenote import OneNoteConnector
from backend.connectors.sharepoint import SharePointConnector
from backend.graph_schema import count_links


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
    new_link = next(
        link for link in merged["links"] if link["source"] == "sharepoint:item-1"
    )
    new_node = next(
        node for node in merged["nodes"] if node["id"] == "sharepoint:item-1"
    )

    assert merged_path.parent == tmp_path / "graphs"
    assert "edges" not in merged
    assert count_links(merged) == 2
    assert set(new_link) == {"source", "target", "relation", "weight"}
    assert new_link["target"] == "existing"
    assert new_link["relation"] == "related"
    assert new_link["weight"] > 0
    assert new_node["source"] == "sharepoint"
    assert new_node["file_type"] == "document"
    assert new_node["source_file"].startswith("sharepoint/")
    assert new_node["_origin"] == "sharepoint"


def test_sharepoint_nodes_preserve_source_metadata_and_grouping(tmp_path: Path) -> None:
    connector = SharePointConnector(tmp_path, ["https://example.sharepoint.com/sites/Team"])

    nodes = connector.to_graph_nodes([
        {
            "id": "doc-1",
            "name": "Launch Readiness Checklist.md",
            "site_url": "https://example.sharepoint.com/sites/Team",
            "drive_id": "drive-1",
            "web_url": "https://example.sharepoint.com/doc-1",
            "modified_at": "2026-06-16T12:00:00Z",
            "size": 1234,
            "mime_type": "text/markdown",
        }
    ])

    assert nodes == [
        {
            "id": "sharepoint:doc-1",
            "label": "Launch Readiness Checklist.md",
            "type": "document",
            "file_type": "document",
            "source": "sharepoint",
            "source_file": "sharepoint/https-example.sharepoint.com-sites-Team/Launch-Readiness-Checklist.md",
            "_origin": "sharepoint",
            "metadata": {
                "drive_id": "drive-1",
                "item_id": "doc-1",
                "mime_type": "text/markdown",
                "size": 1234,
                "site_url": "https://example.sharepoint.com/sites/Team",
                "web_url": "https://example.sharepoint.com/doc-1",
                "modified_at": "2026-06-16T12:00:00Z",
            },
            "site_url": "https://example.sharepoint.com/sites/Team",
            "file_path": "https://example.sharepoint.com/doc-1",
            "source_location": "https://example.sharepoint.com/doc-1",
            "modified_at": "2026-06-16T12:00:00Z",
        }
    ]


def test_onenote_nodes_preserve_source_metadata_and_grouping(tmp_path: Path) -> None:
    connector = OneNoteConnector(tmp_path)

    nodes = connector.to_graph_nodes([
        {
            "id": "page-1",
            "title": "Launch Plan",
            "notebook": "Operations",
            "section": "Weekly Review",
            "created_at": "2026-06-15T12:00:00Z",
            "modified_at": "2026-06-16T12:00:00Z",
            "web_url": "https://onenote.example/page-1",
        }
    ])

    assert nodes == [
        {
            "id": "onenote:page-1",
            "label": "Launch Plan",
            "type": "note",
            "file_type": "document",
            "source": "onenote",
            "source_file": "onenote/Operations/Weekly-Review/Launch-Plan",
            "_origin": "onenote",
            "metadata": {
                "page_id": "page-1",
                "web_url": "https://onenote.example/page-1",
                "notebook": "Operations",
                "section": "Weekly Review",
                "created_at": "2026-06-15T12:00:00Z",
                "modified_at": "2026-06-16T12:00:00Z",
            },
            "notebook": "Operations",
            "section": "Weekly Review",
            "source_location": "https://onenote.example/page-1",
            "modified_at": "2026-06-16T12:00:00Z",
        }
    ]


def test_connector_merge_counts_links_and_map_grouping(
    monkeypatch, tmp_path: Path
) -> None:
    active_graph = tmp_path / "active.json"
    active_graph.write_text(json.dumps({
        "nodes": [
            {
                "id": "local:runbook",
                "label": "Operations launch plan",
                "description": "SharePoint launch readiness checklist",
                "source_file": "docs/runbook.md",
                "file_type": "document",
                "source": "local",
            }
        ],
        "links": [],
    }))

    connector = SharePointConnector(tmp_path, [])
    connector_nodes = connector.to_graph_nodes([
        {
            "id": "doc-1",
            "name": "Launch readiness checklist",
            "site_url": "https://example.sharepoint.com/sites/Team",
            "drive_id": "drive-1",
            "web_url": "https://example.sharepoint.com/doc-1",
            "modified_at": "2026-06-16T12:00:00Z",
            "size": 1234,
            "mime_type": "text/plain",
        }
    ])

    merged_path = merge_nodes_into_graph(connector_nodes, active_graph, tmp_path / "graphs")
    merged = json.loads(merged_path.read_text())

    assert count_links(merged) == 1
    assert merged["links"][0]["source"] == "sharepoint:doc-1"
    assert merged["links"][0]["target"] == "local:runbook"
    assert merged["links"][0]["relation"] == "related"
    assert merged["links"][0]["weight"] > 0

    monkeypatch.setattr(main, "DEFAULT_GRAPH", str(merged_path))
    monkeypatch.setattr(main, "SETTINGS_FILE", tmp_path / "missing-settings.json")
    monkeypatch.setattr(main, "_graph_cache", None)
    full = main.graph_full()
    sharepoint_node = next(
        node for node in full["nodes"] if node["id"] == "sharepoint:doc-1"
    )

    assert full["edge_count"] == 1
    assert sharepoint_node["label"] == "Launch readiness checklist"
    assert sharepoint_node["type"] == "document"
    assert sharepoint_node["cluster"] == "sharepoint"
    assert sharepoint_node["origin"] == "sharepoint"
