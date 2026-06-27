#!/usr/bin/env python3
"""
CNS store performance benchmark — Phase 2 Chunk 2.8.

Imports the real workspace graph into a fresh SQLite store and benchmarks
all 6 query patterns against the speed SLAs from the Phase 2 spec.

SLAs:
  Single relationship query:      p95 < 100ms
  Entity neighborhood traversal:  p95 < 250ms

Usage:
  python scripts/cns_benchmark.py [graph_json_path]
"""
import json
import os
import sys
import tempfile
import time

# Add project root to path so cns_store imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cns_store.db import init_db, get_connection
from cns_store.importer import import_graph
from cns_store.queries import (
    validate_connector,
    entity_neighborhood,
    authority_chain,
    entity_context,
    recent_mission_context,
    domain_mapping,
)

QUERY_SLAS_MS = {
    "validate_connector":    100,
    "entity_context":        100,
    "authority_chain":       100,
    "domain_mapping":        100,
    "entity_neighborhood":   250,
    "recent_mission_context": 100,
}

REPS = 30  # repetitions per entity per query


def percentile(times_ms: list[float], p: int) -> float:
    idx = max(0, int(len(times_ms) * p / 100) - 1)
    return sorted(times_ms)[idx]


def bench(fn, *args) -> float:
    t0 = time.perf_counter()
    fn(*args)
    return (time.perf_counter() - t0) * 1000


def main():
    graph_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "graphify-out", "merged-graph.json",
    )

    if not os.path.exists(graph_path):
        print(f"Graph not found: {graph_path}")
        sys.exit(1)

    print(f"\nBenchmarking CNS store against: {graph_path}")
    print(f"Graph size: {os.path.getsize(graph_path) / 1e6:.1f} MB\n")

    with tempfile.TemporaryDirectory(prefix="cns_bench_") as tmp_dir:
        db_path = os.path.join(tmp_dir, "bench.db")
        init_db(db_path)

        print("Importing graph...", end=" ", flush=True)
        t0 = time.perf_counter()
        summary = import_graph(graph_path, db_path)
        elapsed = time.perf_counter() - t0
        print(f"{summary['node_count']} nodes, {summary['link_count']} links in {elapsed:.2f}s")

        # Sample representative entity IDs
        conn = get_connection(db_path)
        sample_ids = [
            r[0] for r in conn.execute(
                "SELECT id FROM entities ORDER BY ROWID LIMIT 30"
            ).fetchall()
        ]
        # Pick a domain sample (entities that might have authority links)
        domain_ids = [
            r[0] for r in conn.execute(
                "SELECT id FROM entities WHERE cluster != '' LIMIT 10"
            ).fetchall()
        ]
        conn.close()

        if not sample_ids:
            print("No entities found in store — aborting.")
            sys.exit(1)

        results = {}
        all_passed = True

        def run_bench(name, fn, ids, *extra_args):
            times = []
            for eid in ids:
                for _ in range(REPS // len(ids) + 1):
                    times.append(bench(fn, eid, db_path, *extra_args))
            times = times[:REPS]
            p50 = percentile(times, 50)
            p95 = percentile(times, 95)
            p99 = percentile(times, 99)
            sla = QUERY_SLAS_MS.get(name, 100)
            passed = p95 < sla
            results[name] = {"p50": p50, "p95": p95, "p99": p99, "sla": sla, "passed": passed}
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {name:30s} p50={p50:6.1f}ms  p95={p95:6.1f}ms  p99={p99:6.1f}ms  SLA<{sla}ms")
            return passed

        print(f"\nQuery benchmarks ({REPS} reps each):")
        print("-" * 80)

        all_passed &= run_bench("entity_context",         entity_context,         sample_ids)
        all_passed &= run_bench("domain_mapping",         domain_mapping,         sample_ids)
        all_passed &= run_bench("recent_mission_context", recent_mission_context, sample_ids)
        all_passed &= run_bench("authority_chain",        authority_chain,        sample_ids)
        all_passed &= run_bench("entity_neighborhood",    entity_neighborhood,    sample_ids)

        # validate_connector has a different signature: (connector_id, domain, db_path)
        def validate_connector_wrapped(eid, db_path):
            return validate_connector(eid, "any-domain", db_path)

        all_passed &= run_bench("validate_connector",     validate_connector_wrapped, sample_ids)

        print("-" * 80)
        print(f"\nGraph: {summary['node_count']} nodes, {summary['link_count']} links")
        print(f"Status: {'ALL PASS' if all_passed else 'SOME FAILED'}")

        if not all_passed:
            sys.exit(1)

        return results


if __name__ == "__main__":
    main()
