from __future__ import annotations

from backend.routes.ask import parse_query_output


def test_parse_query_output_accepts_empty_location_fields() -> None:
    answer, evidence = parse_query_output(
        "\n".join(
            [
                "Traversal: BFS depth=2 | Start: ['workspace-hygiene.md'] | 3 nodes found",
                "",
                "NODE archive-guide.md [src=knowledge-hub/guides/archive-guide.md loc= community=]",
                "NODE cleanup.py [src=automation/scripts/cleanup.py loc= community=]",
            ]
        )
    )

    assert answer.startswith("Traversal: BFS depth=2")
    assert evidence == [
        {
            "label": "archive-guide.md",
            "src": "knowledge-hub/guides/archive-guide.md",
            "loc": None,
            "community": "",
        },
        {
            "label": "cleanup.py",
            "src": "automation/scripts/cleanup.py",
            "loc": None,
            "community": "",
        },
    ]


def test_parse_query_output_falls_back_to_start_nodes() -> None:
    _, evidence = parse_query_output(
        "Traversal: BFS depth=2 | Start: ['graph_watch.py', \"graph_loader.py\"] | 22 nodes found"
    )

    assert evidence == [{"label": "graph_watch.py"}, {"label": "graph_loader.py"}]
