from __future__ import annotations

from backend import main


def _kind(edge_count, avg, max_sim, same_name):
    kind, _signals = main._summary_overlap_insight(edge_count, avg, max_sim, same_name)
    return kind


# Same-name pairs across clusters are the canonical-duplication signal.

def test_same_name_near_duplicate_is_waste():
    assert _kind(1, 0.93, 0.95, same_name=1) == "waste_duplicate"


def test_same_name_but_diverged_is_drift():
    # Same artifact name on both sides, similar but not near-identical => drifted.
    assert _kind(1, 0.87, 0.87, same_name=1) == "drift_risk"


# The core regression: drift is no longer a catch-all for sparse high-similarity
# groups that merely happen to clear the threshold.

def test_sparse_high_similarity_without_same_name_is_not_drift():
    kind = _kind(1, 0.97, 0.99, same_name=0)
    assert kind != "drift_risk"
    assert kind == "low_value"


def test_repeated_pattern_without_same_name_is_shared_pattern():
    assert _kind(4, 0.9, 0.96, same_name=0) == "shared_pattern"


def test_dense_cross_area_is_cross_app_similarity():
    assert _kind(20, 0.9, 0.97, same_name=0) == "cross_app_similarity"


def test_moderately_dense_is_gap_missing_bridge():
    assert _kind(10, 0.82, 0.9, same_name=0) == "gap_missing_bridge"


def test_drift_only_comes_from_same_name():
    # Across a spread of non-same-name groups, none should classify as drift.
    grid = [
        _kind(edges, avg, mx, same_name=0)
        for edges in (1, 2, 3, 5, 9, 20)
        for avg in (0.82, 0.9, 0.95)
        for mx in (0.9, 0.96, 0.99)
    ]
    assert "drift_risk" not in grid
