"""Tests for cns_store ingest (extraction write path) — Chunk 2.7."""
import json
import os
import subprocess
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cns_store.db import init_db, get_connection
from cns_store.ingest import run_extraction, ExtractionError

FIXTURES = Path(__file__).parent / "fixtures"
MINI_GRAPH = str(FIXTURES / "mini_graph.json")


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "ingest_test.db")
    init_db(db_path)
    return db_path


def _make_graphify_stub(graph_json_path: str, output_graph_path: str) -> str:
    """
    Write a small shell script that acts as a graphify stub:
    copies mini_graph.json to the expected output location.
    """
    script = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False
    )
    script.write("#!/bin/bash\n")
    # graphify update <src> --no-cluster --output <out>
    # The --output arg is at position $5 (0-indexed: graphify update src --no-cluster --output out)
    script.write(f'cp "{graph_json_path}" "${{@: -1}}"\n')
    script.write("exit 0\n")
    script.flush()
    os.chmod(script.name, 0o755)
    script.close()
    return script.name


class TestRunExtractionUnit:
    def test_raises_for_nonexistent_source(self, tmp_db, tmp_path):
        with pytest.raises(ValueError, match="source_path must be"):
            run_extraction("/does/not/exist", tmp_db)

    def test_raises_extraction_error_on_nonzero_exit(self, tmp_db, tmp_path):
        stub = tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        )
        stub.write("#!/bin/bash\nexit 1\n")
        stub.flush()
        os.chmod(stub.name, 0o755)
        stub.close()

        try:
            with pytest.raises(ExtractionError, match="extraction failed"):
                run_extraction(
                    str(tmp_path), tmp_db,
                    graphify_cmd=stub.name,
                )
        finally:
            os.unlink(stub.name)

    def test_raises_extraction_error_when_cmd_not_found(self, tmp_db, tmp_path):
        with pytest.raises(ExtractionError, match="not found"):
            run_extraction(
                str(tmp_path), tmp_db,
                graphify_cmd="/nonexistent/graphify",
            )

    def test_successful_extraction_via_stub(self, tmp_db, tmp_path):
        stub = _make_graphify_stub(MINI_GRAPH, "")
        try:
            summary = run_extraction(
                str(tmp_path), tmp_db,
                graphify_cmd=stub,
            )
            assert summary["node_count"] == 10
            assert summary["link_count"] == 8
            assert summary["source_path"] == str(tmp_path)
        finally:
            os.unlink(stub)

    def test_store_updated_after_extraction(self, tmp_db, tmp_path):
        stub = _make_graphify_stub(MINI_GRAPH, "")
        try:
            run_extraction(str(tmp_path), tmp_db, graphify_cmd=stub)
            conn = get_connection(tmp_db)
            count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            conn.close()
            assert count == 10
        finally:
            os.unlink(stub)
