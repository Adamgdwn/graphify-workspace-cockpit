import { useCallback, useEffect, useRef, useState } from "react";
import { API } from "../config";
import cytoscape from "cytoscape";
import type { Core } from "cytoscape";
// @ts-ignore
import fcose from "cytoscape-fcose";
// @ts-ignore
import layoutUtilities from "cytoscape-layout-utilities";

// ── Extension registration (once per page lifetime) ───────────────────────

let _registered = false;
function ensureExtensions() {
  if (!_registered) {
    cytoscape.use(layoutUtilities);
    cytoscape.use(fcose);
    _registered = true;
  }
}

// ── Types ─────────────────────────────────────────────────────────────────

interface SummaryNode {
  id: string;
  label: string;
  node_count: number;
  code_count: number;
  doc_count: number;
  rationale_count: number;
  dominant_type: "code" | "document" | "rationale";
  is_drillable: boolean;
}

interface SummaryEdge {
  source: string;
  target: string;
  weight: number;
  relations: string[];
}

interface GraphSummary {
  level: "top" | "project";
  project: string | null;
  total_nodes: number;
  nodes: SummaryNode[];
  edges: SummaryEdge[];
}

type Filter = "all" | "code" | "document";

// ── Decision metadata (mirror of Decisions.tsx) ───────────────────────────

const DECISION_META: Record<string, { label: string; color: string }> = {
  "invest":       { label: "Invest",       color: "#4ade80" },
  "client-ready": { label: "Client Ready", color: "#f5d280" },
  "monitor":      { label: "Monitor",      color: "#6b8cff" },
  "archive":      { label: "Archive",      color: "#9ca3af" },
  "paused":       { label: "Paused",       color: "#f97316" },
};

// ── Cytoscape stylesheet ──────────────────────────────────────────────────

const CY_STYLE: object[] = [
  {
    selector: "node",
    style: {
      width: "data(size)",
      height: "data(size)",
      "background-color": "#182038",
      "border-width": 1.5,
      "border-color": "#283a62",
      label: "data(label)",
      color: "#8aa0c8",
      "text-outline-color": "#070a12",
      "text-outline-width": 2.5,
      "font-family":
        '"JetBrains Mono", "Fira Mono", ui-monospace, "Cascadia Code", monospace',
      "font-size": 11,
      "font-weight": 500,
      "text-valign": "bottom",
      "text-margin-y": 7,
      "min-zoomed-font-size": 7,
    },
  },
  {
    selector: 'node[dominant_type="document"]',
    style: {
      "background-color": "#142830",
      "border-color": "#2a4848",
    },
  },
  {
    selector: 'node[dominant_type="rationale"]',
    style: {
      "background-color": "#2a1e10",
      "border-color": "#5a4020",
    },
  },
  {
    selector: 'node[?god_node]',
    style: {
      "border-color": "#fbbf24",
      "border-width": 5,
      "shadow-blur": 36,
      "shadow-color": "#fbbf24",
      "shadow-opacity": 0.75,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
    },
  },
  {
    selector: "node:hover",
    style: {
      "border-color": "#6b8cff",
      "border-width": 2.5,
      color: "#c8d8f0",
    },
  },
  {
    selector: "node.selected",
    style: {
      "border-color": "#6b8cff",
      "border-width": 3,
      "shadow-blur": 28,
      "shadow-color": "#6b8cff",
      "shadow-opacity": 0.9,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
      color: "#e8eaf0",
      "background-color": "#1e2e55",
    },
  },
  {
    selector: "node.path-source",
    style: {
      "background-color": "#2e1e00",
      "border-color": "#f5a623",
      "border-width": 3,
      "shadow-blur": 26,
      "shadow-color": "#f5a623",
      "shadow-opacity": 0.95,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
      color: "#f5d280",
    },
  },
  {
    selector: "node.path-target",
    style: {
      "background-color": "#082a18",
      "border-color": "#4ade80",
      "border-width": 3,
      "shadow-blur": 26,
      "shadow-color": "#4ade80",
      "shadow-opacity": 0.95,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
      color: "#90f0b8",
    },
  },
  {
    selector: "node.faded",
    style: { opacity: 0.1 },
  },
  {
    selector: "edge",
    style: {
      "curve-style": "bezier",
      width: "data(edgeWidth)",
      "line-color": "#1e2d4a",
      "target-arrow-color": "#2a3d60",
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.75,
      opacity: 0.6,
    },
  },
  {
    selector: "edge.highlighted",
    style: {
      "line-color": "#6b8cff",
      "target-arrow-color": "#6b8cff",
      opacity: 1,
      width: 3,
    },
  },
  {
    selector: "edge.path-edge",
    style: {
      "line-color": "#f5a623",
      "target-arrow-color": "#f5a623",
      opacity: 1,
      width: 3,
    },
  },
  {
    selector: "edge.faded",
    style: { opacity: 0.04 },
  },
  // Decision classification glows
  {
    selector: 'node[decision="invest"]',
    style: {
      "border-color": "#4ade80",
      "border-width": 3.5,
      "shadow-blur": 22,
      "shadow-color": "#4ade80",
      "shadow-opacity": 0.65,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
    },
  },
  {
    selector: 'node[decision="client-ready"]',
    style: {
      "border-color": "#f5d280",
      "border-width": 3.5,
      "shadow-blur": 22,
      "shadow-color": "#f5d280",
      "shadow-opacity": 0.65,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
    },
  },
  {
    selector: 'node[decision="monitor"]',
    style: {
      "border-color": "#6b8cff",
      "border-width": 3.5,
      "shadow-blur": 22,
      "shadow-color": "#6b8cff",
      "shadow-opacity": 0.65,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
    },
  },
  {
    selector: 'node[decision="archive"]',
    style: {
      "border-color": "#9ca3af",
      "border-width": 3,
      "shadow-blur": 10,
      "shadow-color": "#9ca3af",
      "shadow-opacity": 0.35,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
      opacity: 0.6,
    },
  },
  {
    selector: 'node[decision="paused"]',
    style: {
      "border-color": "#f97316",
      "border-width": 3.5,
      "shadow-blur": 18,
      "shadow-color": "#f97316",
      "shadow-opacity": 0.55,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
    },
  },
];

// fcose for project drill-down (multiple connected nodes, real force-directed value)
const FCOSE_LAYOUT = {
  name: "fcose",
  quality: "default",
  randomize: false,
  animate: true,
  animationDuration: 750,
  animationEasing: "ease-out-cubic",
  fit: true,
  padding: 100,
  nodeSeparation: 90,
  nodeRepulsion: () => 130000,
  idealEdgeLength: () => 220,
  edgeElasticity: () => 0.35,
  numIter: 3000,
  packComponents: true,
};

// Compute ring positions: largest node at center, groups of 4 in successive rings.
// Produces a clean hub diagram regardless of edge structure or level.
function buildRingPositions(
  nodes: SummaryNode[]
): Record<string, { x: number; y: number }> {
  const sorted = [...nodes].sort((a, b) => b.node_count - a.node_count);
  const positions: Record<string, { x: number; y: number }> = {};
  // Ring radii: ring1=190, ring2=320, ring3=430
  const RADII = [0, 190, 320, 430];

  sorted.forEach((n, i) => {
    if (i === 0) {
      positions[n.id] = { x: 0, y: 0 };
    } else {
      const ring = Math.ceil(i / 4);
      const ringStart = (ring - 1) * 4 + 1;
      const countInRing = Math.min(4, sorted.length - ringStart);
      const posInRing = i - ringStart;
      const radius = RADII[ring] ?? ring * 150;
      // Stagger rings by 45° so outer nodes sit between inner nodes
      const angleOffset = ring % 2 === 1 ? Math.PI / 4 : 0;
      const angle =
        (posInRing / countInRing) * 2 * Math.PI - Math.PI / 2 + angleOffset;
      positions[n.id] = {
        x: radius * Math.cos(angle),
        y: radius * Math.sin(angle),
      };
    }
  });

  return positions;
}

const PRESET_LAYOUT = {
  name: "preset",
  fit: true,
  padding: 80,
  animate: true,
  animationDuration: 750,
  animationEasing: "ease-out-cubic",
};

function getLayout(_summary: GraphSummary): object {
  // Always use preset layout — ring positions computed in buildElements.
  // This is deterministic and visually clean for any node count.
  return PRESET_LAYOUT;
}

// ── Compute god nodes (top-5 by total edge weight) ───────────────────────

function computeGodNodeIds(edges: SummaryEdge[]): Set<string> {
  const scores: Record<string, number> = {};
  edges.forEach((e) => {
    scores[e.source] = (scores[e.source] ?? 0) + e.weight;
    scores[e.target] = (scores[e.target] ?? 0) + e.weight;
  });
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  return new Set(sorted.slice(0, 5).map(([id]) => id));
}

// ── Element builder ───────────────────────────────────────────────────────

function buildElements(
  summary: GraphSummary,
  decisions: Record<string, string> = {},
  godNodeIds: Set<string> = new Set()
) {
  const ringPositions = buildRingPositions(summary.nodes);

  const nodes = summary.nodes.map((n) => {
    const dec = decisions[n.id];
    return {
      data: {
        id: n.id,
        label: n.label,
        node_count: n.node_count,
        code_count: n.code_count,
        doc_count: n.doc_count,
        dominant_type: n.dominant_type,
        is_drillable: n.is_drillable,
        // log₂ scaling: 1→36px, 100→66px, 10k→108px, 23k→126px
        size: Math.max(36, Math.min(126, Math.log2(n.node_count + 2) * 15)),
        god_node: godNodeIds.has(n.id),
        ...(dec ? { decision: dec } : {}),
      },
      position: ringPositions[n.id] ?? { x: 0, y: 0 },
    };
  });

  const seen = new Set<string>();
  const edges = summary.edges
    .filter((e) => {
      const key = `${e.source}::${e.target}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((e) => ({
      data: {
        id: `${e.source}::${e.target}`,
        source: e.source,
        target: e.target,
        weight: e.weight,
        edgeWidth: Math.max(1.5, Math.min(9, Math.log(e.weight + 1) * 1.8)),
        relations: e.relations.join(", "),
      },
    }));

  return [...nodes, ...edges];
}

// ── Component ─────────────────────────────────────────────────────────────

interface MapProps {
  onNavigateSettings?: () => void;
}

export function Map({ onNavigateSettings }: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Refs for cy event handlers — avoids stale closures over React state
  const pathModeRef = useRef(false);
  const pathSourceRef = useRef<string | null>(null);
  const summaryRef = useRef<GraphSummary | null>(null);

  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SummaryNode | null>(null);
  const [breadcrumb, setBreadcrumb] = useState<string[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [pathMode, setPathMode] = useState(false);
  const [pathSource, setPathSource] = useState<string | null>(null);
  const [pathNoRoute, setPathNoRoute] = useState(false);
  // target_id → classification for active decisions
  const [decisions, setDecisions] = useState<Record<string, string>>({});
  // top-5 nodes by total edge weight
  const [godNodeIds, setGodNodeIds] = useState<Set<string>>(new Set());
  // edge count per god node for tooltip display
  const [godNodeEdgeCounts, setGodNodeEdgeCounts] = useState<Record<string, number>>({});
  // active vs total sources chip (from cluster selection)
  const [sourceChip, setSourceChip] = useState<{ active: number; total: number } | null>(null);

  // Keep refs current
  useEffect(() => { pathModeRef.current = pathMode; }, [pathMode]);
  useEffect(() => { pathSourceRef.current = pathSource; }, [pathSource]);
  useEffect(() => { summaryRef.current = summary; }, [summary]);

  // Fetch decisions (non-critical — silently ignored if backend down)
  useEffect(() => {
    fetch(`${API}/decisions`)
      .then((r) => (r.ok ? r.json() : []))
      .then((list: Array<{ target_id: string; classification: string; status: string }>) => {
        const map: Record<string, string> = {};
        list.filter((d) => d.status === "active").forEach((d) => {
          map[d.target_id] = d.classification;
        });
        setDecisions(map);
      })
      .catch(() => {});
  }, []);

  // Fetch cluster selection for source chip
  useEffect(() => {
    fetch(`${API}/cluster-selection`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        const total: number = data.available_sources.length;
        const active: number = (data.selection.sources as string[]).filter((s: string) =>
          (data.available_sources as string[]).includes(s)
        ).length;
        setSourceChip({ active, total });
      })
      .catch(() => {});
  }, []);

  // Recompute god nodes whenever summary changes
  useEffect(() => {
    if (!summary) return;
    const scores: Record<string, number> = {};
    summary.edges.forEach((e) => {
      scores[e.source] = (scores[e.source] ?? 0) + e.weight;
      scores[e.target] = (scores[e.target] ?? 0) + e.weight;
    });
    const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
    setGodNodeIds(new Set(sorted.slice(0, 5).map(([id]) => id)));
    setGodNodeEdgeCounts(Object.fromEntries(sorted.slice(0, 5)));
  }, [summary]);

  const fetchSummary = useCallback(async (project?: string) => {
    setLoading(true);
    setError(null);
    setSelected(null);
    setFilter("all");
    setPathMode(false);
    setPathSource(null);
    setPathNoRoute(false);
    try {
      const qs = project ? `?project=${encodeURIComponent(project)}` : "";
      const res = await fetch(`${API}/graph/summary${qs}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as any).detail ?? `HTTP ${res.status}`);
      }
      const data: GraphSummary = await res.json();
      setSummary(data);
      setBreadcrumb(project ? [project] : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSummary(); }, [fetchSummary]);

  // Init / reinit Cytoscape when summary data changes
  useEffect(() => {
    if (!containerRef.current || !summary) return;

    ensureExtensions();

    cyRef.current?.destroy();
    cyRef.current = null;

    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(summary, decisions, godNodeIds),
      style: CY_STYLE as any,
      layout: getLayout(summary) as any,
      pixelRatio: 1,
      minZoom: 0.05,
      maxZoom: 8,
    });

    // Auto-fit after animation so the graph fills the canvas neatly
    cy.one("layoutstop", () => {
      cy.fit(undefined, 70);
    });

    cy.on("tap", "node", (e: any) => {
      const node = e.target;
      const nodeId: string = node.id();

      if (pathModeRef.current) {
        const src = pathSourceRef.current;

        if (!src) {
          cy.nodes().removeClass("path-source path-target");
          cy.elements().removeClass("path-edge faded");
          node.addClass("path-source");
          setPathSource(nodeId);
          setPathNoRoute(false);
          return;
        }

        if (src === nodeId) return;

        // Compute shortest path
        const source = cy.getElementById(src);
        try {
          const dijk = (cy.elements() as any).dijkstra({
            root: source,
            weight: () => 1,
          });
          const path = dijk.pathTo(node);

          if (path && path.length > 0) {
            cy.elements().addClass("faded").removeClass("path-source path-target path-edge");
            path.removeClass("faded");
            path.nodes().first().addClass("path-source");
            path.nodes().last().addClass("path-target");
            path.edges().addClass("path-edge");
            setPathNoRoute(false);
          } else {
            cy.elements().removeClass("faded path-source path-target path-edge");
            setPathNoRoute(true);
          }
        } catch {
          cy.elements().removeClass("faded path-source path-target path-edge");
          setPathNoRoute(true);
        }

        setPathSource(null);
        setPathMode(false);
        return;
      }

      // Normal tap — select + highlight connected edges
      cy.nodes().removeClass("selected");
      cy.edges().removeClass("highlighted");
      node.addClass("selected");
      node.connectedEdges().addClass("highlighted");

      const nodeData =
        summaryRef.current?.nodes.find((n) => n.id === nodeId) ?? null;
      setSelected(nodeData);
    });

    cy.on("tap", (e: any) => {
      if (e.target === cy) {
        cy.nodes().removeClass("selected");
        cy.edges().removeClass("highlighted");
        setSelected(null);
      }
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [summary, decisions, godNodeIds]);

  // Apply type filter via class toggling (no re-layout)
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      if (filter === "all") {
        cy.elements().removeClass("faded");
      } else {
        cy.elements().addClass("faded");
        const matching = cy.nodes(`[dominant_type = "${filter}"]`);
        matching.removeClass("faded");
        matching.connectedEdges().removeClass("faded");
      }
    });
  }, [filter]);

  // Path mode exit — clear all highlights
  useEffect(() => {
    if (!pathMode) {
      const cy = cyRef.current;
      if (cy) {
        cy.elements().removeClass("faded path-source path-target path-edge");
        cy.nodes().removeClass("selected");
        cy.edges().removeClass("highlighted");
      }
      setPathSource(null);
    }
  }, [pathMode]);

  function handleFit() {
    cyRef.current?.fit(undefined, 80);
  }

  function handleDrillDown(node: SummaryNode) {
    if (!node.is_drillable) return;
    fetchSummary(node.id);
  }

  function startPathFrom(nodeId: string) {
    const cy = cyRef.current;
    if (!cy) return;
    setSelected(null);
    setPathNoRoute(false);
    cy.nodes().removeClass("path-source path-target");
    cy.elements().removeClass("path-edge faded");
    cy.getElementById(nodeId).addClass("path-source");
    setPathSource(nodeId);
    setPathMode(true);
  }

  const pctCode = selected
    ? Math.round((selected.code_count / Math.max(1, selected.node_count)) * 100)
    : 0;

  return (
    <div className="map-pane">
      {/* ── Toolbar ── */}
      <div className="map-toolbar">
        <div className="map-breadcrumb">
          <button
            className={`map-crumb-btn${breadcrumb.length === 0 ? " map-crumb-active" : ""}`}
            onClick={() => fetchSummary()}
          >
            Workspace
          </button>
          {breadcrumb.map((crumb, i) => (
            <span key={i} className="map-crumb-segment">
              <span className="map-crumb-sep">›</span>
              <span className="map-crumb-label">{crumb}</span>
            </span>
          ))}
          {summary && !loading && (
            <span className="map-meta-pill">
              {summary.nodes.length}&thinsp;groups&thinsp;·&thinsp;
              {summary.total_nodes.toLocaleString()}&thinsp;nodes
            </span>
          )}
          {sourceChip && sourceChip.total > 1 && (
            <button
              className={`map-source-chip${sourceChip.active < sourceChip.total ? " map-source-chip-partial" : ""}`}
              onClick={onNavigateSettings}
              title="Manage knowledge sources in Settings"
              type="button"
            >
              {sourceChip.active}&thinsp;of&thinsp;{sourceChip.total}&thinsp;sources active
            </button>
          )}
        </div>

        <div className="map-toolbar-right">
          <div className="map-filter-group">
            {(["all", "code", "document"] as Filter[]).map((f) => (
              <button
                key={f}
                className={`map-filter-btn${filter === f ? " map-filter-active" : ""}`}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All" : f === "code" ? "Code" : "Docs"}
              </button>
            ))}
          </div>

          <button
            className={`map-path-btn${pathMode ? " map-path-active" : ""}`}
            onClick={() => setPathMode((p) => !p)}
            title="Trace shortest path between two nodes"
          >
            {pathMode
              ? pathSource
                ? "Click target…"
                : "Click source…"
              : "Path"}
          </button>

          <button
            className="map-fit-btn"
            onClick={handleFit}
            title="Fit to viewport"
          >
            ⊡
          </button>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="map-body">
        {/* Canvas */}
        <div className="map-canvas-wrap">
          <div className="map-canvas" ref={containerRef} />

          {loading && (
            <div className="map-overlay">
              <div className="map-spinner" />
              <span>Building graph summary…</span>
              <span className="map-overlay-sub">First load may take a moment</span>
            </div>
          )}

          {error && !loading && (
            <div className="map-overlay map-overlay-error">
              <span className="map-overlay-icon">⚠</span>
              <span>{error}</span>
              <button className="map-retry-btn" onClick={() => fetchSummary()}>
                Retry
              </button>
            </div>
          )}

          {pathMode && !pathNoRoute && (
            <div className="map-path-hint">
              {pathSource
                ? "● Click a target node to trace path"
                : "○ Click a source node to begin"}
            </div>
          )}

          {pathNoRoute && (
            <div className="map-path-hint map-path-hint-warn">
              No direct path found between those nodes
            </div>
          )}
        </div>

        {/* Inspect panel */}
        {selected && (
          <aside className="map-panel">
            <div className="map-panel-head">
              <span className="map-panel-name">{selected.label}</span>
              <button
                className="map-panel-close"
                onClick={() => setSelected(null)}
                aria-label="Close panel"
              >
                ✕
              </button>
            </div>

            <div className="map-panel-section">
              <span
                className={`map-type-badge map-type-${selected.dominant_type}`}
              >
                {selected.dominant_type}
              </span>
              {godNodeIds.has(selected.id) && (
                <span className="map-god-badge" title={`High-traffic node (${godNodeEdgeCounts[selected.id] ?? 0} edge weight)`}>
                  ⚡ High-traffic node ({godNodeEdgeCounts[selected.id] ?? 0} edges)
                </span>
              )}
              {decisions[selected.id] && (() => {
                const meta = DECISION_META[decisions[selected.id]];
                return meta ? (
                  <span
                    className="map-decision-badge"
                    style={{ color: meta.color, borderColor: meta.color }}
                  >
                    {meta.label}
                  </span>
                ) : null;
              })()}
            </div>

            <div className="map-panel-stats">
              <div className="map-stat">
                <span className="map-stat-label">Total</span>
                <span className="map-stat-value">
                  {selected.node_count.toLocaleString()}
                </span>
              </div>
              <div className="map-stat">
                <span className="map-stat-label">Code</span>
                <span className="map-stat-value">
                  {selected.code_count.toLocaleString()}
                </span>
              </div>
              <div className="map-stat">
                <span className="map-stat-label">Docs</span>
                <span className="map-stat-value">
                  {selected.doc_count.toLocaleString()}
                </span>
              </div>
              <div className="map-stat">
                <span className="map-stat-label">Code %</span>
                <span className="map-stat-value">{pctCode}%</span>
              </div>
            </div>

            <div className="map-panel-bar-wrap">
              <div className="map-panel-bar">
                <div
                  className="map-panel-bar-fill"
                  style={{ width: `${pctCode}%` }}
                />
              </div>
              <div className="map-panel-bar-labels">
                <span>Code</span>
                <span>Docs</span>
              </div>
            </div>

            <div className="map-panel-actions">
              {selected.is_drillable && (
                <button
                  className="map-action-btn map-action-primary"
                  onClick={() => handleDrillDown(selected)}
                >
                  Explore {selected.label}&thinsp;→
                </button>
              )}
              <button
                className="map-action-btn"
                onClick={() => startPathFrom(selected.id)}
              >
                Trace path from here
              </button>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
