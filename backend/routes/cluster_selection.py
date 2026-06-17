"""Cluster/source selection route group."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel


class ClusterSelectionBody(BaseModel):
    sources: list[str]
    clusters: list[str] | None = None


@dataclass(frozen=True)
class ClusterSelectionDeps:
    load_cluster_selection: Callable[[], dict]
    save_cluster_selection: Callable[[dict], None]
    load_graph: Callable[[], dict]
    workspace_state: Callable[[], Path]
    is_microsoft_authenticated: Callable[[Path], bool]
    clear_summary_cache: Callable[[], None]


def get_cluster_selection(deps: ClusterSelectionDeps) -> dict:
    selection = deps.load_cluster_selection()
    available_clusters: list[dict] = []
    try:
        data = deps.load_graph()
        counts: dict[str, int] = {}
        for node in data.get("nodes", []):
            source_file = node.get("source_file", "")
            cluster = source_file.split("/")[0] if source_file else ""
            if cluster:
                counts[cluster] = counts.get(cluster, 0) + 1
        available_clusters = [
            {"id": key, "node_count": value}
            for key, value in sorted(counts.items(), key=lambda item: -item[1])
            if value >= 20
        ]
    except Exception:
        pass

    available_sources = ["local"]
    if deps.is_microsoft_authenticated(deps.workspace_state()):
        available_sources.extend(["sharepoint", "onenote"])
    return {
        "selection": selection,
        "available_clusters": available_clusters,
        "available_sources": available_sources,
    }


def update_cluster_selection(req: ClusterSelectionBody, deps: ClusterSelectionDeps) -> dict:
    selection = {"sources": req.sources, "clusters": req.clusters}
    deps.save_cluster_selection(selection)
    deps.clear_summary_cache()
    return selection


def create_cluster_selection_router(
    deps_factory: Callable[[], ClusterSelectionDeps],
) -> tuple[
    APIRouter,
    Callable[[], dict],
    Callable[[ClusterSelectionBody], dict],
]:
    router = APIRouter()

    def get_cluster_selection_endpoint() -> dict:
        return get_cluster_selection(deps_factory())

    def update_cluster_selection_endpoint(req: ClusterSelectionBody) -> dict:
        return update_cluster_selection(req, deps_factory())

    router.add_api_route(
        "/cluster-selection",
        get_cluster_selection_endpoint,
        methods=["GET"],
    )
    router.add_api_route(
        "/cluster-selection",
        update_cluster_selection_endpoint,
        methods=["PUT"],
    )
    return router, get_cluster_selection_endpoint, update_cluster_selection_endpoint
