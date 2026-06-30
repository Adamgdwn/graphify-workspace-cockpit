"""
Extraction write path for the CNS store.

Runs graphify extraction on a source path and imports the resulting graph
into the SQLite store. This was the only write path in Phase 2 and remains the
admin extraction lane after later approved relationship-memory write lanes.

Caller is responsible for not running concurrent extractions on the same
db_path — SQLite WAL mode is safe for concurrent reads but extraction is
designed as a sequential batch operation.
"""
import os
import subprocess
import sys
import tempfile
from cns_store.importer import import_graph


class ExtractionError(RuntimeError):
    """Raised when graphify extraction fails."""


def run_extraction(
    source_path: str,
    db_path: str,
    *,
    graphify_cmd: str = "graphify",
    timeout: int = 300,
) -> dict:
    """
    Run graphify extraction on source_path and import the result into db_path.

    1. Creates a temp output directory
    2. Runs `graphify update <source_path> --no-cluster` into it
    3. Imports the resulting graph.json into the SQLite store
    4. Returns import summary {node_count, link_count, source_path}

    Raises ExtractionError if graphify exits non-zero.
    """
    if not os.path.isdir(source_path):
        raise ValueError(f"source_path must be an existing directory: {source_path}")

    with tempfile.TemporaryDirectory(prefix="cns_extract_") as tmp_dir:
        out_graph = os.path.join(tmp_dir, "graph.json")

        cmd = [
            graphify_cmd,
            "update",
            source_path,
            "--no-cluster",
            "--output",
            out_graph,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise ExtractionError(
                f"graphify extraction timed out after {timeout}s for {source_path}"
            )
        except FileNotFoundError:
            raise ExtractionError(
                f"graphify command not found: {graphify_cmd!r}. "
                "Ensure graphify is installed and on PATH."
            )
        except OSError as exc:
            raise ExtractionError(
                f"graphify command could not be executed: {graphify_cmd!r}. "
                f"{exc}"
            )

        if result.returncode != 0:
            raise ExtractionError(
                f"graphify extraction failed (exit {result.returncode}):\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

        # graphify may write to a different location — look for graph.json
        if not os.path.exists(out_graph):
            # Try the default graphify-out location within source_path
            default_out = os.path.join(source_path, "graphify-out", "graph.json")
            merged_out = os.path.join(source_path, "graphify-out", "merged-graph.json")
            if os.path.exists(merged_out):
                out_graph = merged_out
            elif os.path.exists(default_out):
                out_graph = default_out
            else:
                raise ExtractionError(
                    f"graphify ran successfully but graph.json not found. "
                    f"Checked: {out_graph}, {default_out}, {merged_out}"
                )

        summary = import_graph(out_graph, db_path)
        summary["source_path"] = source_path
        return summary
