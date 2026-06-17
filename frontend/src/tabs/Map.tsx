import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiErrorMessage, apiFetch } from "../api/client";
import cytoscape from "cytoscape";
import type { Core } from "cytoscape";
// @ts-ignore
import fcose from "cytoscape-fcose";
// @ts-ignore
import layoutUtilities from "cytoscape-layout-utilities";
import { DECISION_CLASSIFICATIONS } from "../domain/decision";
import type { ActiveCockpitContext } from "../domain/cockpitContext";
import type { ActiveCockpitContextHandler } from "../domain/cockpitContext";

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
  group_type?: "repo" | "module" | "group";
  node_count: number;
  code_count: number;
  doc_count: number;
  rationale_count: number;
  dominant_type: "code" | "document" | "rationale";
  is_drillable: boolean;
  connection_count?: number;
  connection_weight?: number;
  is_gap?: boolean;
  gap_reason?: string;
  connections?: SummaryConnection[];
}

interface SummaryEdge {
  source: string;
  target: string;
  weight: number;
  relations: string[];
}

interface SummaryConnection {
  id: string;
  label: string;
  weight: number;
  relations: string[];
}

interface GraphSummary {
  level: "top" | "project";
  project: string | null;
  total_nodes: number;
  hidden_node_count?: number;
  excluded_node_count?: number;
  signal_counts?: Record<string, number>;
  nodes: SummaryNode[];
  edges: SummaryEdge[];
}

// Full graph (all raw nodes/edges)
interface FullNode {
  id: string;
  label: string;
  type: "code" | "document" | "rationale";
  cluster: string;
  source_file: string;
  source_location?: string;
  source_root?: string;
  source_root_name?: string;
  repo?: string;
  container?: string;
  relative_path?: string;
  origin?: string;
  metadata?: Record<string, unknown>;
  symbol?: string;
  purpose?: string;
  signal_tier?: "overview" | "important" | "evidence" | "hidden" | "excluded";
  signal_reason?: string;
  source_excerpt?: {
    start_line: number | null;
    lines: string[];
    unavailable_reason?: string;
  };
}

interface FullEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
}

interface FullGraph {
  node_count: number;
  edge_count: number;
  total_node_count?: number;
  visible_node_count?: number;
  hidden_node_count?: number;
  excluded_node_count?: number;
  signal_counts?: Record<string, number>;
  include_low_signal?: boolean;
  nodes: FullNode[];
  edges: FullEdge[];
}

type Filter = "all" | "code" | "document";
type ViewMode = "summary" | "full";
const FULL_GRAPH_NODE_LIMIT = 5000;
type MapMode = "explore" | "trace" | "overlap" | "review";
type ScopeGateState = "checking" | "ready" | "setup";

const MAP_MODES: Array<{ id: MapMode; label: string; subLabel: string; hint: string; tooltip: string }> = [
  {
    id: "explore",
    label: "Explore",
    subLabel: "physical map",
    hint: "Browse the physical/structural graph and inspect connected context.",
    tooltip: "Physical map: browse structural workspace connections such as files, imports, dependencies, and graph neighborhoods.",
  },
  {
    id: "trace",
    label: "Trace",
    subLabel: "path",
    hint: "Choose a source and target to see the shortest summary path.",
    tooltip: "Path tracing: pick two nodes and show the shortest route through the summary graph.",
  },
  {
    id: "overlap",
    label: "Overlap",
    subLabel: "semantic",
    hint: "Review semantic connections, cross-repo overlap, and consolidation candidates.",
    tooltip: "Semantic overlap: show similarity edges, group cross-repo connections, and triage duplicate or related work.",
  },
  {
    id: "review",
    label: "Review",
    subLabel: "evidence",
    hint: "Use all filters, sources, and edge layers for evidence review.",
    tooltip: "Evidence review: combine filters, sources, physical edges, and semantic edges while inspecting nodes.",
  },
];

const UNKNOWN_VALUE = "unknown";

function presentValue(value: unknown): string {
  if (value === null || value === undefined) return UNKNOWN_VALUE;
  const text = String(value).trim();
  return text || UNKNOWN_VALUE;
}

function prettyMetadataKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function prettyMetadataValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(prettyMetadataValue).join(", ");
  if (value && typeof value === "object") return JSON.stringify(value);
  return presentValue(value);
}

function metadataEntries(node: FullNode) {
  return Object.entries(node.metadata ?? {})
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "")
    .filter(([key]) => !["kind", "language"].includes(key))
    .sort(([a], [b]) => a.localeCompare(b));
}

function lowSignalCount(graph: FullGraph | null, summary: GraphSummary | null): number {
  const counts = graph?.signal_counts ?? summary?.signal_counts ?? {};
  return (counts.evidence ?? 0) + (counts.hidden ?? 0);
}

function excludedNodeCount(graph: FullGraph | null, summary: GraphSummary | null): number {
  return graph?.excluded_node_count ?? summary?.excluded_node_count ?? 0;
}

function signalTierLabel(tier?: string): string {
  if (!tier) return "Evidence";
  return tier.replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Overlap analysis ──────────────────────────────────────────────────────

interface OverlapPair {
  source: string;
  target: string;
  labelA: string;
  labelB: string;
  fileA: string;
  fileB: string;
  similarity: number;
  sameName: boolean;
}

interface OverlapGroup {
  clusterA: string;
  clusterB: string;
  edgeCount: number;
  avgSimilarity: number;
  maxSimilarity: number;
  sameNameCount: number;
  topPairs: OverlapPair[];
  source: "full" | "summary";
}

interface OverlapSummaryResponse {
  groups?: Array<{
    cluster_a: string;
    cluster_b: string;
    edge_count: number;
    avg_similarity: number;
    max_similarity?: number;
    same_name_count?: number;
    top_pairs?: Array<{
      source?: string;
      target?: string;
      label_a?: string;
      label_b?: string;
      file_a?: string;
      file_b?: string;
      similarity?: number;
      same_name?: boolean;
    }>;
  }>;
  total_cross_edges?: number;
  created_at?: string | null;
}

interface TriageResult {
  verdict: "duplicate" | "reference" | "related" | "unknown";
  confidence: number;
  reason: string;
  action: string;
  evidence_summary?: string;
  per_side_purpose?: {
    cluster_a?: string;
    cluster_b?: string;
    [key: string]: string | undefined;
  };
  similarities?: string[];
  differences?: string[];
  canonicality_signals?: string[];
  open_questions?: string[];
  model: string;
}

type OverlapWorkflowStatus = "untriaged" | "triaged" | "task-created" | "dismissed";
type OverlapStatusFilter = "active" | OverlapWorkflowStatus;

interface OverlapStatusRecord {
  pair_key: string;
  cluster_a?: string;
  cluster_b?: string;
  status: OverlapWorkflowStatus;
  triage_result?: TriageResult;
  recommendation_id?: string;
  created_at?: string;
  updated_at?: string;
}

const OVERLAP_STATUS_LABELS: Record<OverlapWorkflowStatus, string> = {
  untriaged: "Untriaged",
  triaged: "Triaged",
  "task-created": "Task Created",
  dismissed: "Dismissed",
};

function compactPath(path: string): string {
  const normalized = path.replace(/\\/g, "/").trim();
  if (!normalized) return UNKNOWN_VALUE;
  const parts = normalized.split("/").filter(Boolean);
  if (parts.length <= 4) return normalized;
  return `${parts[0]}/…/${parts.slice(-2).join("/")}`;
}

function dossierList(items?: string[]): string[] {
  return (items ?? []).map((item) => item.trim()).filter(Boolean).slice(0, 5);
}

function relationList(relations?: string[]): string {
  const cleaned = (relations ?? []).map((relation) => relation.trim()).filter(Boolean);
  return cleaned.length ? cleaned.slice(0, 3).join(", ") : "physical links";
}

function overlapSummaryGroups(response: OverlapSummaryResponse | null): OverlapGroup[] {
  return (response?.groups ?? []).map((group) => {
    const topPairs = (group.top_pairs ?? []).map((pair) => ({
      source: pair.source ?? "",
      target: pair.target ?? "",
      labelA: pair.label_a ?? pair.source ?? UNKNOWN_VALUE,
      labelB: pair.label_b ?? pair.target ?? UNKNOWN_VALUE,
      fileA: pair.file_a ?? "",
      fileB: pair.file_b ?? "",
      similarity: Number(pair.similarity ?? 0),
      sameName: Boolean(pair.same_name),
    }));
    return {
      clusterA: group.cluster_a,
      clusterB: group.cluster_b,
      edgeCount: group.edge_count,
      avgSimilarity: Math.round(Number(group.avg_similarity ?? 0) * 100) / 100,
      maxSimilarity: Math.round(Number(group.max_similarity ?? group.avg_similarity ?? 0) * 100) / 100,
      sameNameCount: group.same_name_count ?? topPairs.filter((pair) => pair.sameName).length,
      topPairs,
      source: "summary" as const,
    };
  });
}

const DECISION_META = Object.fromEntries(
  DECISION_CLASSIFICATIONS.map((c) => [c.id, { label: c.label, color: c.color }]),
) as Record<string, { label: string; color: string }>;

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
    selector: 'node[?is_gap]',
    style: {
      "border-color": "#f97316",
      "border-width": 2.5,
      "border-style": "dashed",
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
        group_type: n.group_type ?? "group",
        is_drillable: n.is_drillable,
        connection_count: n.connection_count ?? 0,
        connection_weight: n.connection_weight ?? 0,
        is_gap: Boolean(n.is_gap),
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

// ── Full-graph helpers ────────────────────────────────────────────────────

const CLUSTER_COLORS: Record<string, string> = {
  backend:   "#3b82f6",
  frontend:  "#0ea5e9",
  docs:      "#f59e0b",
  src:       "#a78bfa",
  lib:       "#34d399",
  scripts:   "#fb923c",
  db:        "#f472b6",
  tests:     "#4ade80",
  test:      "#4ade80",
  other:     "#6b7280",
};

function clusterColor(cluster: string): string {
  if (!cluster || cluster.includes(".")) return CLUSTER_COLORS.other;
  return CLUSTER_COLORS[cluster] ?? CLUSTER_COLORS.other;
}

const FULL_FCOSE_LAYOUT = {
  name: "fcose",
  quality: "default",
  randomize: true,
  animate: true,
  animationDuration: 1200,
  animationEasing: "ease-out-cubic",
  fit: true,
  padding: 60,
  nodeSeparation: 40,
  nodeRepulsion: () => 6500,
  idealEdgeLength: () => 80,
  edgeElasticity: () => 0.45,
  numIter: 2500,
  packComponents: true,
};

function buildFullElements(full: FullGraph, filter: Filter, selectedClusters: Set<string> | null = null) {
  const visibleIds = new Set(
    full.nodes
      .filter((n) => filter === "all" || n.type === filter)
      .filter((n) => selectedClusters === null || selectedClusters.has(n.cluster))
      .map((n) => n.id)
  );

  const nodes = full.nodes
    .filter((n) => visibleIds.has(n.id))
    .map((n) => ({
      data: {
        id: n.id,
        label: n.label,
        type: n.type,
        cluster: n.cluster,
        source_file: n.source_file,
        color: clusterColor(n.cluster),
      },
    }));

  const seen = new Set<string>();
  const edges = full.edges
    .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
    .filter((e) => {
      const k = `${e.source}::${e.target}`;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .map((e) => ({
      data: {
        id: `${e.source}::${e.target}`,
        source: e.source,
        target: e.target,
        relation: e.relation,
        edgeWidth: Math.max(1.2, Math.min(3, e.weight * 1.2)),
      },
    }));

  return [...nodes, ...edges];
}

const FULL_CY_STYLE: object[] = [
  {
    selector: "node",
    style: {
      width: 10,
      height: 10,
      "background-color": "data(color)",
      "border-width": 0,
      label: "data(label)",
      color: "#8aa0c8",
      "text-outline-color": "#070a12",
      "text-outline-width": 2,
      "font-family": '"JetBrains Mono", ui-monospace, monospace',
      "font-size": 7,
      "text-valign": "bottom",
      "text-margin-y": 3,
      "min-zoomed-font-size": 9,
    },
  },
  {
    selector: "node:hover",
    style: { "border-width": 2, "border-color": "#fff", width: 13, height: 13 },
  },
  {
    selector: "node.selected",
    style: {
      width: 14, height: 14,
      "border-width": 2, "border-color": "#fff",
      "shadow-blur": 16, "shadow-color": "data(color)", "shadow-opacity": 0.9,
      "shadow-offset-x": 0, "shadow-offset-y": 0,
      color: "#e8eaf0",
    },
  },
  {
    selector: "node.faded",
    style: { opacity: 0.08 },
  },
  {
    selector: "edge",
    style: {
      "curve-style": "haystack",
      width: "data(edgeWidth)",
      "line-color": "#4a7abf",
      opacity: 0.75,
    },
  },
  {
    selector: "edge.highlighted",
    style: { "line-color": "#6b8cff", opacity: 1, width: 2 },
  },
  {
    selector: "edge.faded",
    style: { opacity: 0.03 },
  },
  {
    selector: "edge.semantic-edge",
    style: {
      "curve-style": "straight",
      "line-color": "#22c55e",
      "line-style": "dashed",
      "line-dash-pattern": [6, 4],
      width: 1.5,
      opacity: 0.7,
    },
  },
  {
    selector: "edge.semantic-edge.highlighted",
    style: {
      "line-color": "#22c55e",
      "line-style": "solid",
      opacity: 1,
      width: 2.5,
    },
  },
  {
    selector: "edge.semantic-edge.faded",
    style: { opacity: 0 },
  },
  {
    selector: "edge.struct-hidden",
    style: { opacity: 0 },
  },
];

// ── Component ─────────────────────────────────────────────────────────────

interface MapProps {
  activeContext?: ActiveCockpitContext | null;
  onNavigateScope?: () => void;
  onActiveContextChange?: ActiveCockpitContextHandler;
}

export function Map({ activeContext, onNavigateScope, onActiveContextChange }: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const appliedContextKeyRef = useRef<string | null>(null);

  // Refs for cy event handlers — avoids stale closures over React state
  const pathModeRef = useRef(false);
  const pathSourceRef = useRef<string | null>(null);
  const summaryRef = useRef<GraphSummary | null>(null);

  const [viewMode, setViewMode] = useState<ViewMode>("summary");
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [fullGraph, setFullGraph] = useState<FullGraph | null>(null);
  const [fullLoading, setFullLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SummaryNode | null>(null);
  const [selectedFull, setSelectedFull] = useState<FullNode | null>(null);
  const [breadcrumb, setBreadcrumb] = useState<string[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [mapMode, setMapMode] = useState<MapMode>("explore");
  const [pathMode, setPathMode] = useState(false);
  const [pathSource, setPathSource] = useState<string | null>(null);
  const [pathNoRoute, setPathNoRoute] = useState(false);
  // target_id → classification for active decisions
  const [decisions, setDecisions] = useState<Record<string, string>>({});
  // top-5 nodes by total edge weight
  const [godNodeIds, setGodNodeIds] = useState<Set<string>>(new Set());
  // edge count per god node for tooltip display
  const [godNodeEdgeCounts, setGodNodeEdgeCounts] = useState<Record<string, number>>({});
  // cluster/source selector panel
  const [clusterData, setClusterData] = useState<{
    selection: { sources: string[]; clusters: string[] | null };
    available_clusters: { id: string; node_count: number }[];
    available_sources: string[];
  } | null>(null);
  const [showSourcePanel, setShowSourcePanel] = useState(false);
  const [selectedClusters, setSelectedClusters] = useState<Set<string> | null>(null);
  const [showLowSignal, setShowLowSignal] = useState(false);
  // edge layer toggles
  const [showStructural, setShowStructural] = useState(true);
  // semantic similarity overlay
  const [showSemantic, setShowSemantic] = useState(false);
  const [semanticEdges, setSemanticEdges] = useState<Array<{ source: string; target: string; similarity: number }>>([]);
  const [semanticMeta, setSemanticMeta] = useState<{ edge_count: number; created_at: string | null } | null>(null);
  const [summaryOverlap, setSummaryOverlap] = useState<OverlapSummaryResponse | null>(null);
  // overlap analysis panel
  const [showOverlap, setShowOverlap] = useState(false);
  const [highlightedPair, setHighlightedPair] = useState<[string, string] | null>(null);
  const [creatingTask, setCreatingTask] = useState<string | null>(null);
  const [taskCreated, setTaskCreated] = useState<string | null>(null);
  // overlap filters
  const [minSimilarity, setMinSimilarity] = useState(0.70);
  const [sameNameOnly, setSameNameOnly] = useState(false);
  const [overlapStatusFilter, setOverlapStatusFilter] = useState<OverlapStatusFilter>("active");
  const [overlapStatuses, setOverlapStatuses] = useState<Record<string, OverlapStatusRecord>>({});
  // LLM triage
  const [triageResults, setTriageResults] = useState<Record<string, TriageResult>>({});
  const [triaging, setTriaging] = useState<Record<string, boolean>>({});
  const [focusNotice, setFocusNotice] = useState<{ tone: "info" | "warn"; text: string } | null>(null);
  const [scopeGate, setScopeGate] = useState<ScopeGateState>("checking");
  const [scopeGateReason, setScopeGateReason] = useState("Choose folders before generating a workspace map.");

  const showSemanticRef = useRef(false);
  const semanticEdgesRef = useRef<Array<{ source: string; target: string; similarity: number }>>([]);
  const showStructuralRef = useRef(true);
  const nodeClusterMapRef = useRef<Record<string, string>>({});

  // Cross-cluster node lookup — built once when fullGraph loads
  const nodeClusterMap = useMemo(
    () => Object.fromEntries(fullGraph?.nodes.map((n) => [n.id, n.cluster]) ?? []) as Record<string, string>,
    [fullGraph],
  );

  // Cross-cluster semantic edges — what semantic mode actually shows
  const crossSemanticEdges = useMemo(() => {
    const hasMap = fullGraph != null;
    if (!hasMap) return semanticEdges;
    return semanticEdges.filter((e) => {
      const sc = nodeClusterMap[e.source];
      const tc = nodeClusterMap[e.target];
      return sc && tc && sc !== tc;
    });
  }, [semanticEdges, nodeClusterMap, fullGraph]);

  // Overlap analysis groups — ranked cross-cluster pairs by connection count
  const fullOverlapGroups = useMemo((): OverlapGroup[] => {
    if (!fullGraph || !crossSemanticEdges.length) return [];
    const nodeMap = Object.fromEntries(fullGraph.nodes.map((n) => [n.id, n]));
    const basename = (f: string) => f.split("/").pop() ?? f;
    const groups: Record<string, { clusterA: string; clusterB: string; edges: OverlapPair[] }> = {};
    for (const edge of crossSemanticEdges) {
      const sc = nodeClusterMap[edge.source];
      const tc = nodeClusterMap[edge.target];
      if (!sc || !tc || sc === tc) continue;
      const ca = sc <= tc ? sc : tc;
      const cb = sc <= tc ? tc : sc;
      const key = `${ca}___${cb}`;
      if (!groups[key]) groups[key] = { clusterA: ca, clusterB: cb, edges: [] };
      const na = nodeMap[edge.source];
      const nb = nodeMap[edge.target];
      const fileA = na?.source_file ?? "";
      const fileB = nb?.source_file ?? "";
      groups[key].edges.push({
        source: edge.source, target: edge.target,
        similarity: edge.similarity,
        labelA: na?.label ?? edge.source,
        labelB: nb?.label ?? edge.target,
        fileA,
        fileB,
        sameName: !!fileA && !!fileB && basename(fileA) === basename(fileB),
      });
    }
    return Object.values(groups)
      .map((g) => {
        const avg = g.edges.reduce((s, e) => s + e.similarity, 0) / g.edges.length;
        const maxSim = Math.max(...g.edges.map((e) => e.similarity));
        const sameNameCount = g.edges.filter((e) => e.sameName).length;
        // sort: same-name first, then by similarity desc
        const sorted = [...g.edges].sort((a, b) => {
          if (a.sameName !== b.sameName) return a.sameName ? -1 : 1;
          return b.similarity - a.similarity;
        });
        return {
          clusterA: g.clusterA,
          clusterB: g.clusterB,
          edgeCount: g.edges.length,
          avgSimilarity: Math.round(avg * 100) / 100,
          maxSimilarity: Math.round(maxSim * 100) / 100,
          sameNameCount,
          topPairs: sorted.slice(0, 6),
          source: "full" as const,
        };
      })
      // sort: groups with same-name matches first, then by edge count
      .sort((a, b) => {
        if ((a.sameNameCount > 0) !== (b.sameNameCount > 0)) return a.sameNameCount > 0 ? -1 : 1;
        return b.edgeCount - a.edgeCount;
      });
  }, [crossSemanticEdges, nodeClusterMap, fullGraph]);

  const summaryOverlapGroupsData = useMemo(
    () => overlapSummaryGroups(summaryOverlap),
    [summaryOverlap],
  );
  const usingSummaryOverlap = viewMode !== "full";
  const overlapGroups = usingSummaryOverlap ? summaryOverlapGroupsData : fullOverlapGroups;
  const overlapConnectionCount = usingSummaryOverlap
    ? summaryOverlap?.total_cross_edges ?? 0
    : crossSemanticEdges.length;

  function overlapKey(group: Pick<OverlapGroup, "clusterA" | "clusterB">) {
    return `${group.clusterA}___${group.clusterB}`;
  }

  function workflowStatusFor(group: OverlapGroup): OverlapWorkflowStatus {
    const key = overlapKey(group);
    return overlapStatuses[key]?.status ?? (triageResults[key] ? "triaged" : "untriaged");
  }

  const overlapStatusCounts = useMemo(() => {
    const counts: Record<OverlapWorkflowStatus, number> = {
      untriaged: 0,
      triaged: 0,
      "task-created": 0,
      dismissed: 0,
    };
    for (const group of overlapGroups) {
      counts[workflowStatusFor(group)] += 1;
    }
    return counts;
  }, [overlapGroups, overlapStatuses, triageResults]);

  // Filtered view of groups based on user-selected thresholds
  const filteredGroups = useMemo(() =>
    overlapGroups.filter((g) => {
      if (g.maxSimilarity < minSimilarity) return false;
      if (sameNameOnly && g.sameNameCount === 0) return false;
      const status = workflowStatusFor(g);
      if (overlapStatusFilter === "active") return status !== "dismissed";
      if (status !== overlapStatusFilter) return false;
      return true;
    }),
    [overlapGroups, minSimilarity, sameNameOnly, overlapStatusFilter, overlapStatuses, triageResults],
  );

  // Keep refs current
  useEffect(() => { pathModeRef.current = pathMode; }, [pathMode]);
  useEffect(() => { pathSourceRef.current = pathSource; }, [pathSource]);
  useEffect(() => { summaryRef.current = summary; }, [summary]);
  useEffect(() => { showSemanticRef.current = showSemantic; }, [showSemantic]);
  useEffect(() => { semanticEdgesRef.current = semanticEdges; }, [semanticEdges]);
  useEffect(() => { showStructuralRef.current = showStructural; }, [showStructural]);
  useEffect(() => { nodeClusterMapRef.current = nodeClusterMap; }, [nodeClusterMap]); // eslint-disable-line

  function normalizeLookup(value: string) {
    return value.trim().toLowerCase().replace(/\s+/g, " ");
  }

  function evidenceCandidates(context: ActiveCockpitContext): string[] {
    if (context.kind !== "node") return [];
    const raw = [context.nodeId, context.label ?? ""].filter(Boolean);
    return [...new Set(raw.flatMap((value) => {
      const withoutScore = value.replace(/\s+\(\d+%?\)\s*$/, "");
      return [value, withoutScore, ...withoutScore.split(/\s*(?:↔|<--|-->|→|->)\s*/)];
    }).map((value) => value.trim()).filter(Boolean))];
  }

  function contextLabel(context: ActiveCockpitContext) {
    if (context.kind === "node") return context.label || context.nodeId;
    if (context.kind === "cluster") return context.label || context.clusterId;
    if (context.kind === "overlap-pair") return `${context.clusterA} ↔ ${context.clusterB}`;
    if (context.kind === "recommendation") return context.label || context.recommendationId;
    return context.label || context.targetId;
  }

  function contextSourceLabel(context: ActiveCockpitContext) {
    return context.source === "ask" ? "Ask evidence"
      : context.source === "recommendations" ? "Recommendation evidence"
      : context.source === "dashboard" ? "Command Center"
      : context.source === "decisions" ? "Decision"
      : "Map context";
  }

  function contextKey(context: ActiveCockpitContext) {
    return JSON.stringify(context);
  }

  function focusVisibleNode(nodeId: string, notice: string) {
    const cy = cyRef.current;
    if (!cy) return false;
    const node = cy.getElementById(nodeId);
    if (!node || node.empty()) return false;
    cy.batch(() => {
      cy.nodes().removeClass("selected");
      cy.edges().removeClass("highlighted");
      node.addClass("selected");
      node.connectedEdges().addClass("highlighted");
    });
    cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 1.8) }, { duration: 450 });
    setFocusNotice({ tone: "info", text: notice });
    return true;
  }

  function focusVisibleCluster(clusterId: string, notice: string) {
    const cy = cyRef.current;
    if (!cy) return false;
    const wanted = normalizeLookup(clusterId);
    const nodes = cy.nodes().filter((node: any) => normalizeLookup(String(node.data("cluster") ?? "")) === wanted);
    if (!nodes || nodes.empty()) return false;
    cy.batch(() => {
      cy.nodes().removeClass("selected");
      cy.edges().removeClass("highlighted");
      nodes.addClass("selected");
      nodes.connectedEdges().addClass("highlighted");
    });
    cy.fit(nodes, 80);
    setFocusNotice({ tone: "info", text: notice });
    return true;
  }

  // Fetch decisions (non-critical — silently ignored if backend down)
  useEffect(() => {
    apiFetch(`/decisions`)
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

  // Fetch cluster/source selection data
  useEffect(() => {
    apiFetch(`/cluster-selection`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        setClusterData(data);
        const sel = data.selection?.clusters;
        setSelectedClusters(sel ? new Set<string>(sel) : null);
      })
      .catch(() => {});
  }, []);

  // Load semantic edges on mount
  useEffect(() => {
    apiFetch(`/graph/semantic-edges`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setSemanticEdges(d.edges ?? []);
        setSemanticMeta({ edge_count: (d.edges ?? []).length, created_at: d.created_at ?? null });
      })
      .catch(() => {});
  }, []);

  // Load broad-safe overlap groups aligned to the current summary surface.
  useEffect(() => {
    if (!summary) return;
    const qs = summary.project ? `?project=${encodeURIComponent(summary.project)}` : "";
    apiFetch(`/graph/overlap-summary${qs}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: OverlapSummaryResponse | null) => {
        if (d) setSummaryOverlap(d);
      })
      .catch(() => {});
  }, [summary?.project]);

  // Load durable overlap review status on mount
  useEffect(() => {
    apiFetch(`/overlap/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: { pairs?: Record<string, OverlapStatusRecord> } | null) => {
        const pairs = d?.pairs ?? {};
        setOverlapStatuses(pairs);
        const restoredTriage = Object.fromEntries(
          Object.entries(pairs)
            .filter(([, record]) => record.triage_result)
            .map(([key, record]) => [key, record.triage_result as TriageResult]),
        );
        if (Object.keys(restoredTriage).length) {
          setTriageResults((current) => ({ ...restoredTriage, ...current }));
        }
      })
      .catch(() => {});
  }, []);

  // Add/remove semantic edges on the live Cytoscape instance when toggle changes.
  // Shows only cross-cluster edges (inter-repo), capped at top-2000 by similarity.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || viewMode !== "full") return;
    if (!showSemantic) {
      cy.elements('[?semantic]').remove();
      return;
    }
    if (!crossSemanticEdges.length) return;
    const nodeIds = new Set<string>(cy.nodes().map((n) => n.id()));
    const sorted = [...crossSemanticEdges].sort((a, b) => b.similarity - a.similarity).slice(0, 2000);
    cy.batch(() => {
      const existingIds = new Set(cy.edges('[?semantic]').map((e) => e.id()));
      const toAdd = sorted
        .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
        .filter((e) => !existingIds.has(`sem__${e.source}__${e.target}`))
        .map((e) => ({
          group: "edges" as const,
          data: {
            id: `sem__${e.source}__${e.target}`,
            source: e.source,
            target: e.target,
            similarity: e.similarity,
            semantic: true,
          },
          classes: "semantic-edge",
        }));
      if (toAdd.length) cy.add(toAdd);
    });
  }, [showSemantic, crossSemanticEdges, viewMode]);

  // Toggle structural edges on/off (class swap — no layout restart)
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || viewMode !== "full") return;
    const structEdges = cy.edges(":not(.semantic-edge)");
    if (showStructural) {
      structEdges.removeClass("struct-hidden");
    } else {
      structEdges.addClass("struct-hidden");
    }
  }, [showStructural, viewMode]);

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

  const fetchSummary = useCallback(async (project?: string, label?: string) => {
    setLoading(true);
    setError(null);
    setSelected(null);
    setFilter("all");
    setPathMode(false);
    setPathSource(null);
    setPathNoRoute(false);
    setFocusNotice(null);
    try {
      const qs = project ? `?project=${encodeURIComponent(project)}` : "";
      const res = await apiFetch(`/graph/summary${qs}`);
      if (!res.ok) {
        throw new Error(await apiErrorMessage(res));
      }
      const data: GraphSummary = await res.json();
      setSummary(data);
      setBreadcrumb(project ? [label || project] : []);
      if (!project && data.total_nodes > FULL_GRAPH_NODE_LIMIT) {
        setFocusNotice({
          tone: "warn",
          text: `Overview is ready. Evidence view is capped at ${FULL_GRAPH_NODE_LIMIT.toLocaleString()} visible nodes, and this scope has ${data.total_nodes.toLocaleString()}. Select a narrower scope or drill into a smaller project before opening Evidence.`,
        });
      }
      setScopeGate("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function checkWorkspaceScope() {
      setScopeGate("checking");
      try {
        const response = await apiFetch(`/workspace-scope`);
        if (!response.ok) throw new Error(await apiErrorMessage(response));
        const data = await response.json() as { profile: unknown | null };
        if (cancelled) return;
        if (!data.profile) {
          setScopeGate("setup");
          setScopeGateReason("No workspace scope is selected yet. Select folders in Workspace Scope, then generate the map.");
          return;
        }
        setScopeGate("ready");
        void fetchSummary();
      } catch (e) {
        if (cancelled) return;
        setScopeGate("setup");
        setScopeGateReason(e instanceof Error ? e.message : "Workspace scope is unavailable. Inspect a folder before generating the map.");
      }
    }
    void checkWorkspaceScope();
    return () => { cancelled = true; };
  }, [fetchSummary]);

  const fetchFullGraph = useCallback(async () => {
    if (fullGraph && Boolean(fullGraph.include_low_signal) === showLowSignal) return; // already loaded
    setFullLoading(true);
    try {
      const qs = showLowSignal ? "?include_low_signal=true" : "";
      const res = await apiFetch(`/graph/full${qs}`);
      if (!res.ok) throw new Error(await apiErrorMessage(res));
      const data: FullGraph = await res.json();
      setFullGraph(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setFullLoading(false);
    }
  }, [fullGraph, showLowSignal]);

  // When switching to full mode, load the full graph once
  useEffect(() => {
    if (viewMode === "full") fetchFullGraph();
  }, [viewMode, fetchFullGraph]);

  // Init / reinit Cytoscape when summary data changes (summary mode only)
  useEffect(() => {
    if (!containerRef.current || !summary || viewMode !== "summary") return;

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
      if (nodeData) {
        onActiveContextChange?.({
          kind: "node",
          source: "map",
          nodeId: nodeData.id,
          label: nodeData.label,
          nodeType: nodeData.dominant_type,
          viewMode: "summary",
        });
      }
    });

    cy.on("tap", (e: any) => {
      if (e.target === cy) {
        cy.nodes().removeClass("selected");
        cy.edges().removeClass("highlighted");
        setSelected(null);
        onActiveContextChange?.(null);
      }
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [summary, decisions, godNodeIds, viewMode]);

  // Full-graph Cytoscape init
  useEffect(() => {
    if (viewMode !== "full" || !containerRef.current || !fullGraph) return;

    ensureExtensions();
    cyRef.current?.destroy();
    cyRef.current = null;

    const cy = cytoscape({
      container: containerRef.current,
      elements: buildFullElements(fullGraph, filter, selectedClusters),
      style: FULL_CY_STYLE as any,
      layout: FULL_FCOSE_LAYOUT as any,
      pixelRatio: 1,
      minZoom: 0.02,
      maxZoom: 12,
    });

    cy.one("layoutstop", () => cy.fit(undefined, 40));

    cy.on("tap", "node", (e: any) => {
      const node = e.target;
      cy.nodes().removeClass("selected");
      cy.edges().removeClass("highlighted");
      node.addClass("selected");
      node.connectedEdges().addClass("highlighted");
      const n = fullGraph.nodes.find((n) => n.id === node.id()) ?? null;
      setSelectedFull(n);
      setSelected(null);
      if (n) {
        onActiveContextChange?.({
          kind: "node",
          source: "map",
          nodeId: n.id,
          label: n.label,
          nodeType: n.type,
          clusterId: n.cluster,
          viewMode: "full",
        });
      }
    });

    cy.on("tap", (e: any) => {
      if (e.target === cy) {
        cy.nodes().removeClass("selected");
        cy.edges().removeClass("highlighted");
        setSelectedFull(null);
        onActiveContextChange?.(null);
      }
    });

    cyRef.current = cy;

    // Restore semantic edges if overlay is active (use refs — no layout restart)
    cy.one("layoutstop", () => {
      if (showSemanticRef.current && semanticEdgesRef.current.length > 0) {
        const nodeIds = new Set<string>(cy.nodes().map((n) => n.id()));
        const clusterMap = nodeClusterMapRef.current;
        const hasMap = Object.keys(clusterMap).length > 0;
        const crossEdges = hasMap
          ? semanticEdgesRef.current.filter((e) => {
              const sc = clusterMap[e.source];
              const tc = clusterMap[e.target];
              return sc && tc && sc !== tc;
            })
          : semanticEdgesRef.current;
        const sorted = [...crossEdges].sort((a, b) => b.similarity - a.similarity).slice(0, 2000);
        const toAdd = sorted
          .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
          .map((e) => ({
            group: "edges" as const,
            data: { id: `sem__${e.source}__${e.target}`, source: e.source, target: e.target, similarity: e.similarity, semantic: true },
            classes: "semantic-edge",
          }));
        if (toAdd.length) cy.batch(() => cy.add(toAdd));
      }
    });

    return () => { cy.destroy(); cyRef.current = null; };
  }, [viewMode, fullGraph, filter, selectedClusters]);

  // Apply cross-tab evidence context once the relevant graph surface is ready.
  useEffect(() => {
    if (!activeContext || activeContext.source === "map") return;
    const key = contextKey(activeContext);
    if (appliedContextKeyRef.current === key) return;

    if (activeContext.kind === "overlap-pair") {
      if (viewMode !== "full") {
        setViewMode("full");
        return;
      }

      if (!fullGraph) {
        fetchFullGraph();
        return;
      }

      setMapMode("overlap");
      setShowSemantic(true);
      setShowOverlap(true);
      setOverlapStatusFilter("untriaged");
      setHighlightedPair([activeContext.clusterA, activeContext.clusterB]);
      setSelectedFull(null);
      setSelected(null);

      const cy = cyRef.current;
      if (cy && activeContext.sourceNodeId && activeContext.targetNodeId) {
        const source = cy.getElementById(activeContext.sourceNodeId);
        const target = cy.getElementById(activeContext.targetNodeId);
        const pair = source.union(target);
        if (!pair.empty()) cy.fit(pair, 90);
      }

      setFocusNotice({
        tone: "info",
        text: `${contextSourceLabel(activeContext)}: ${contextLabel(activeContext)}`,
      });
      appliedContextKeyRef.current = key;
      return;
    }

    if (activeContext.kind !== "node") {
      setFocusNotice({ tone: "warn", text: `${contextSourceLabel(activeContext)} target is not focusable on the Map yet.` });
      appliedContextKeyRef.current = key;
      return;
    }

    if (viewMode !== "full") {
      setViewMode("full");
      return;
    }

    if (!fullGraph) {
      fetchFullGraph();
      return;
    }

    const candidates = evidenceCandidates(activeContext);
    const normalized = new Set(candidates.map(normalizeLookup));
    const match = fullGraph.nodes.find((n) =>
      normalized.has(normalizeLookup(n.id)) || normalized.has(normalizeLookup(n.label))
    );
    const requested = contextLabel(activeContext);
    const sourceLabel = contextSourceLabel(activeContext);

    if (!match) {
      const clusterMatch = [...new Set(fullGraph.nodes.map((n) => n.cluster).filter(Boolean))]
        .find((cluster) => normalized.has(normalizeLookup(cluster)));
      if (clusterMatch) {
        if (filter !== "all") {
          setFilter("all");
          return;
        }

        if (selectedClusters && !selectedClusters.has(clusterMatch)) {
          setSelectedClusters(null);
          return;
        }

        if (!focusVisibleCluster(clusterMatch, `${sourceLabel}: ${requested}`)) return;
        setSelectedFull(null);
        setSelected(null);
        setShowOverlap(false);
        setHighlightedPair(null);
        appliedContextKeyRef.current = key;
        return;
      }

      setSelectedFull(null);
      setFocusNotice({ tone: "warn", text: `${sourceLabel} not found in the active graph: ${requested}` });
      appliedContextKeyRef.current = key;
      return;
    }

    if (filter !== "all") {
      setFilter("all");
      return;
    }

    if (selectedClusters && !selectedClusters.has(match.cluster)) {
      setSelectedClusters(null);
      return;
    }

    if (!focusVisibleNode(match.id, `${sourceLabel}: ${requested}`)) return;
    setSelectedFull(match);
    setSelected(null);
    setShowOverlap(false);
    setHighlightedPair(null);
    appliedContextKeyRef.current = key;
  }, [activeContext, fetchFullGraph, filter, fullGraph, selectedClusters, viewMode]);

  // Apply type filter via class toggling (no re-layout) — summary mode only.
  // Full mode re-runs its init effect to rebuild elements via buildFullElements.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || viewMode === "full") return;
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
  }, [filter, viewMode]);

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

  // Highlight a specific cluster pair's semantic edges on the map
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || viewMode !== "full") return;
    if (!highlightedPair) {
      cy.batch(() => {
        cy.edges(".semantic-edge").removeClass("faded").removeClass("highlighted");
      });
      return;
    }
    const [ca, cb] = highlightedPair;
    const clusterMap = nodeClusterMapRef.current;
    cy.batch(() => {
      cy.edges(".semantic-edge").forEach((e: any) => {
        const src = e.data("source") as string;
        const tgt = e.data("target") as string;
        const sc = clusterMap[src];
        const tc = clusterMap[tgt];
        const inPair = (sc === ca && tc === cb) || (sc === cb && tc === ca);
        if (inPair) {
          e.removeClass("faded").addClass("highlighted");
        } else {
          e.addClass("faded").removeClass("highlighted");
        }
      });
    });
  }, [highlightedPair, viewMode, showSemantic, crossSemanticEdges.length]);

  // Clear highlighted pair when semantic is turned off
  useEffect(() => {
    if (!showSemantic && viewMode === "full") {
      setHighlightedPair(null);
      onActiveContextChange?.(null);
    }
  }, [showSemantic, viewMode, onActiveContextChange]);

  async function saveOverlapStatus(
    group: OverlapGroup,
    status: OverlapWorkflowStatus,
    extras: Pick<OverlapStatusRecord, "triage_result" | "recommendation_id"> = {},
  ) {
    const key = overlapKey(group);
    const record: OverlapStatusRecord = {
      ...overlapStatuses[key],
      ...extras,
      pair_key: key,
      cluster_a: group.clusterA,
      cluster_b: group.clusterB,
      status,
    };
    setOverlapStatuses((current) => ({ ...current, [key]: record }));
    try {
      const res = await apiFetch(`/overlap/status/${encodeURIComponent(key)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          cluster_a: group.clusterA,
          cluster_b: group.clusterB,
          ...extras,
        }),
      });
      if (res.ok) {
        const saved: OverlapStatusRecord = await res.json();
        setOverlapStatuses((current) => ({ ...current, [key]: saved }));
      }
    } catch {
      // Keep the optimistic local state if the backend is temporarily unavailable.
    }
  }

  async function createOverlapTask(group: OverlapGroup) {
    const key = overlapKey(group);
    const triageKey = overlapKey(group);
    const triage = triageResults[triageKey];
    setCreatingTask(key);
    try {
      const res = await apiFetch(`/recommendations/from-overlap`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cluster_a: group.clusterA,
          cluster_b: group.clusterB,
          edge_count: group.edgeCount,
          avg_similarity: group.avgSimilarity,
          top_pairs: group.topPairs.map((p) => ({
            label_a: p.labelA, label_b: p.labelB,
            file_a: p.fileA, file_b: p.fileB,
            similarity: p.similarity,
          })),
          ...(triage ? {
            triage_verdict: triage.verdict,
            triage_action: triage.action,
            triage_confidence: triage.confidence,
            triage_result: triage,
          } : {}),
        }),
      });
      if (!res.ok) throw new Error("Failed to create overlap recommendation");
      const rec = await res.json();
      await saveOverlapStatus(group, "task-created", {
        ...(triage ? { triage_result: triage } : {}),
        ...(rec?.id ? { recommendation_id: rec.id } : {}),
      });
      setTaskCreated(key);
      setTimeout(() => setTaskCreated((k) => (k === key ? null : k)), 3500);
    } catch {
      // silent — backend may not be ready
    } finally {
      setCreatingTask(null);
    }
  }

  async function triageOverlapGroup(group: OverlapGroup) {
    const key = overlapKey(group);
    setTriaging((t) => ({ ...t, [key]: true }));
    try {
      const res = await apiFetch(`/overlap/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cluster_a: group.clusterA,
          cluster_b: group.clusterB,
          edge_count: group.edgeCount,
          avg_similarity: group.avgSimilarity,
          top_pairs: group.topPairs.map((p) => ({
            label_a: p.labelA, label_b: p.labelB,
            file_a: p.fileA, file_b: p.fileB,
            similarity: p.similarity,
            same_name: p.sameName,
          })),
        }),
      });
      if (res.ok) {
        const data: TriageResult = await res.json();
        setTriageResults((r) => ({ ...r, [key]: data }));
        const currentStatus = workflowStatusFor(group);
        const nextStatus = currentStatus === "task-created" || currentStatus === "dismissed"
          ? currentStatus
          : "triaged";
        await saveOverlapStatus(group, nextStatus, { triage_result: data });
      }
    } catch { }
    finally {
      setTriaging((t) => { const n = { ...t }; delete n[key]; return n; });
    }
  }

  async function triageAll() {
    for (const group of filteredGroups) {
      const key = overlapKey(group);
      if (!triageResults[key] && !triaging[key]) {
        await triageOverlapGroup(group);
      }
    }
  }

  function handleFit() {
    cyRef.current?.fit(undefined, 80);
  }

  function switchMapMode(mode: MapMode) {
    setMapMode(mode);
    setFocusNotice(null);

    if (mode === "trace") {
      setViewMode("summary");
      setShowOverlap(false);
      setHighlightedPair(null);
      onActiveContextChange?.(null);
      setSelectedFull(null);
      setPathNoRoute(false);
      setPathMode(true);
      return;
    }

    setPathMode(false);
    setPathNoRoute(false);

    if (mode === "overlap") {
      if (broadEvidenceDisabled) {
        setViewMode("summary");
        setShowSemantic(false);
        setHighlightedPair(null);
        setShowOverlap(true);
        setFocusNotice({
          tone: "info",
          text: `Showing summary-level overlap because Evidence view is capped at ${FULL_GRAPH_NODE_LIMIT.toLocaleString()} visible nodes for this scope.`,
        });
        return;
      }
      setViewMode("full");
      setShowSemantic(true);
      setShowOverlap(true);
      return;
    }

    setShowOverlap(false);
    setHighlightedPair(null);
    onActiveContextChange?.(null);
  }

  function handleDrillDown(node: SummaryNode) {
    if (!node.is_drillable) return;
    fetchSummary(node.id, node.label);
  }

  function focusSummaryGroup(nodeId: string) {
    const match = summaryRef.current?.nodes.find((node) => node.id === nodeId);
    if (!match) return;
    focusVisibleNode(nodeId, `Focused ${match.label}.`);
    setSelected(match);
    onActiveContextChange?.({
      kind: "node",
      source: "map",
      nodeId: match.id,
      label: match.label,
      nodeType: match.dominant_type,
      viewMode: "summary",
    });
  }

  function highlightSummaryOverlapPair(clusterA: string, clusterB: string) {
    const cy = cyRef.current;
    if (!cy) return;
    const nodeA = cy.getElementById(clusterA);
    const nodeB = cy.getElementById(clusterB);
    const pair = nodeA.union(nodeB);
    cy.batch(() => {
      cy.nodes().removeClass("selected");
      cy.edges().removeClass("highlighted");
      pair.addClass("selected");
      cy.edges().forEach((edge: any) => {
        const source = edge.data("source");
        const target = edge.data("target");
        const inPair = (source === clusterA && target === clusterB) || (source === clusterB && target === clusterA);
        if (inPair) edge.addClass("highlighted");
      });
    });
    if (!pair.empty()) cy.fit(pair, 90);
  }

  async function toggleCluster(clusterId: string) {
    if (!clusterData) return;
    let next: Set<string> | null;
    if (selectedClusters === null) {
      const all = new Set(clusterData.available_clusters.map((c) => c.id));
      all.delete(clusterId);
      next = all;
    } else {
      next = new Set(selectedClusters);
      if (next.has(clusterId)) {
        next.delete(clusterId);
      } else {
        next.add(clusterId);
        if (next.size === clusterData.available_clusters.length) next = null;
      }
    }
    setSelectedClusters(next);
    try {
      await apiFetch(`/cluster-selection`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sources: clusterData.selection.sources, clusters: next ? [...next] : null }),
      });
      fetchSummary();
    } catch {}
  }

  function startPathFrom(nodeId: string) {
    const cy = cyRef.current;
    if (!cy) return;
    setSelected(null);
    onActiveContextChange?.(null);
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
  const selectedConnections = selected?.connections ?? [];

  const activeMapMode = MAP_MODES.find((mode) => mode.id === mapMode) ?? MAP_MODES[0];
  const hiddenLowSignalCount = lowSignalCount(fullGraph, summary);
  const excludedFromScopeCount = excludedNodeCount(fullGraph, summary);
  const broadEvidenceDisabled = !fullGraph && (summary?.total_nodes ?? 0) > FULL_GRAPH_NODE_LIMIT;

  if (scopeGate === "checking") {
    return (
      <div className="map-pane">
        <div className="map-startup-shell">
          <div className="map-overlay map-startup-overlay">
            <div className="map-spinner" />
            <span>Checking workspace scope...</span>
            <span className="map-overlay-sub">The map waits until scope is known.</span>
          </div>
        </div>
      </div>
    );
  }

  if (scopeGate === "setup") {
    return (
      <div className="map-pane">
        <div className="map-startup-shell">
          <div className="map-overlay map-startup-overlay map-scope-empty">
            <span className="map-empty-title">Generate a workspace map first</span>
            <span className="map-overlay-sub">{scopeGateReason}</span>
            <button type="button" className="settings-upload-btn" onClick={onNavigateScope}>
              Open Workspace Scope
            </button>
          </div>
        </div>
      </div>
    );
  }

  const sourceSelector = clusterData && clusterData.available_clusters.length > 0 ? (
    <div className="map-source-control">
      <button
        className={`map-source-chip${selectedClusters !== null ? " map-source-chip-partial" : ""}`}
        onClick={() => setShowSourcePanel((s) => !s)}
        title="Select which repositories are shown on the map"
        type="button"
      >
        {selectedClusters === null
          ? `${clusterData.available_clusters.length} repos`
          : `${selectedClusters.size} of ${clusterData.available_clusters.length} repos`}
      </button>
      {showSourcePanel && (
        <div className="map-source-panel">
          <div className="map-source-panel-head">Repositories</div>
          {clusterData.available_clusters.map((c) => {
            const active = selectedClusters === null || selectedClusters.has(c.id);
            return (
              <label key={c.id} className="map-source-row">
                <input
                  type="checkbox"
                  checked={active}
                  onChange={() => toggleCluster(c.id)}
                />
                <span className="map-source-name">{c.id}</span>
                <span className="map-source-count">{c.node_count.toLocaleString()}</span>
              </label>
            );
          })}
          <button className="map-source-done" onClick={() => setShowSourcePanel(false)}>Done</button>
        </div>
      )}
    </div>
  ) : null;

  const typeFilterControls = (
    <div className="map-filter-group" aria-label="Node type filter">
      {(["all", "code", "document"] as Filter[]).map((f) => (
        <button
          key={f}
          className={`map-filter-btn${filter === f ? " map-filter-active" : ""}`}
          onClick={() => setFilter(f)}
          type="button"
        >
          {f === "all" ? "All" : f === "code" ? "Code" : "Docs"}
        </button>
      ))}
    </div>
  );

  const viewModeControls = (
    <div className="map-filter-group" aria-label="Graph view">
      {(["summary", "full"] as ViewMode[]).map((m) => (
        <button
          key={m}
          className={`map-filter-btn${viewMode === m ? " map-filter-active" : ""}`}
          onClick={() => {
            if (m === "full" && broadEvidenceDisabled) {
              setFocusNotice({
                tone: "warn",
                text: `Evidence view is capped at ${FULL_GRAPH_NODE_LIMIT.toLocaleString()} visible nodes. Narrow the scope or drill into a smaller project first.`,
              });
              return;
            }
            setViewMode(m);
            setSelected(null);
            setSelectedFull(null);
            if (m === "full") setPathMode(false);
          }}
          disabled={m === "full" && broadEvidenceDisabled}
          title={
            m === "full" && broadEvidenceDisabled
              ? "Narrow the workspace scope or drill into a smaller project before opening Evidence view."
              : undefined
          }
          type="button"
        >
          {m === "summary" ? "Overview" : fullLoading ? "Loading..." : "Evidence"}
        </button>
      ))}
    </div>
  );

  const signalControls = (
    <button
      className={`map-path-btn${showLowSignal ? " map-signal-active" : ""}`}
      onClick={() => {
        if (broadEvidenceDisabled) {
          setFocusNotice({
            tone: "warn",
            text: `Low Signal view would load more than ${FULL_GRAPH_NODE_LIMIT.toLocaleString()} visible nodes. Narrow the scope first.`,
          });
          return;
        }
        setSelectedFull(null);
        setFullGraph(null);
        setShowLowSignal((value) => !value);
        if (viewMode !== "full") {
          setViewMode("full");
          setPathMode(false);
          setPathNoRoute(false);
        }
      }}
      title={
        showLowSignal
          ? "Hide evidence and hidden signal tiers from the default Map"
          : `Temporarily show ${hiddenLowSignalCount.toLocaleString()} evidence and hidden low-signal nodes`
      }
      type="button"
    >
      Low Signal{hiddenLowSignalCount ? ` (${hiddenLowSignalCount.toLocaleString()})` : ""}
    </button>
  );

  const edgeLayerControls = (
    <>
      <button
        className="map-path-btn"
        onClick={() => {
          if (viewMode !== "full") {
            setViewMode("full");
            setPathMode(false);
            setPathNoRoute(false);
            setShowStructural(true);
            return;
          }
          setShowStructural((s) => !s);
        }}
        title={viewMode === "full" ? "Toggle physical/structural edges" : "Switch to Full graph and show physical/structural edges"}
        style={
          viewMode !== "full"
            ? { opacity: 0.75 }
            : !showStructural
            ? { borderColor: "#2a2a3a", color: "#3a4060", background: "transparent" }
            : { borderColor: "#4a7abf", color: "#4a7abf" }
        }
        type="button"
      >
        Physical
      </button>
      <button
        className="map-path-btn"
        onClick={() => {
          if (viewMode !== "full") {
            setViewMode("full");
            setPathMode(false);
            setPathNoRoute(false);
            setShowSemantic(true);
            return;
          }
          setShowSemantic((s) => !s);
        }}
        title={
          viewMode !== "full"
            ? "Switch to Full graph and show semantic similarity edges"
            : crossSemanticEdges.length
            ? `${showSemantic ? "Hide" : "Show"} ${crossSemanticEdges.length} cross-repo similarity edges (${semanticMeta?.edge_count ?? 0} total)`
            : semanticMeta?.edge_count
            ? "Loading cross-repo edges..."
            : "No semantic edges yet - run Semantic Analysis in Settings"
        }
        style={
          viewMode !== "full"
            ? { opacity: 0.3, cursor: "default" }
            : showSemantic
            ? { borderColor: "#22c55e", color: "#22c55e", background: "rgba(34,197,94,0.07)" }
            : {}
        }
        type="button"
      >
        Semantic{crossSemanticEdges.length ? ` (${crossSemanticEdges.length})` : semanticMeta?.edge_count ? ` (${semanticMeta.edge_count})` : ""}
      </button>
    </>
  );

  const overlapControl = (
    <button
      className="map-path-btn"
      onClick={() => {
        if (mapMode !== "overlap") {
          switchMapMode("overlap");
          return;
        }
        setShowOverlap((s) => !s);
        if (showOverlap) {
          setHighlightedPair(null);
          onActiveContextChange?.(null);
        }
      }}
      title={
        usingSummaryOverlap
          ? `${showOverlap ? "Close" : "Open"} summary overlap analysis - ${overlapGroups.length} group pairs detected`
          : !crossSemanticEdges.length
          ? "Enable Semantic overlay to run overlap analysis"
          : `${showOverlap ? "Close" : "Open"} overlap analysis - ${overlapGroups.length} cluster pairs detected`
      }
      style={
        showOverlap
          ? { borderColor: "#f59e0b", color: "#f59e0b", background: "rgba(245,158,11,0.07)" }
          : overlapGroups.length
          ? { borderColor: "#7a6020", color: "#a08030" }
          : { opacity: 0.4, cursor: "default" }
      }
      type="button"
    >
      Overlap{overlapGroups.length ? ` (${overlapGroups.length})` : ""}
    </button>
  );

  const pathControl = (
    <button
      className={`map-path-btn${pathMode ? " map-path-active" : ""}`}
      onClick={() => {
        if (viewMode !== "summary" || mapMode !== "trace") {
          switchMapMode("trace");
          return;
        }
        setPathMode((p) => !p);
      }}
      title={viewMode === "summary" ? "Trace shortest path between two nodes" : "Switch to Summary view to trace paths"}
      style={viewMode !== "summary" ? { opacity: 0.75 } : {}}
      type="button"
    >
      {pathMode
        ? pathSource
          ? "Pick Target"
          : "Pick Source"
        : "Start Trace"}
    </button>
  );

  return (
    <div className="map-pane">
      {/* ── Toolbar ── */}
      <div className="map-toolbar">
        <div className="map-toolbar-main">
          <div className="map-breadcrumb">
            <button
              className={`map-crumb-btn${breadcrumb.length === 0 ? " map-crumb-active" : ""}`}
              onClick={() => fetchSummary()}
              type="button"
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
                {summary.total_nodes.toLocaleString()}&thinsp;visible
                {hiddenLowSignalCount ? <>&thinsp;·&thinsp;{hiddenLowSignalCount.toLocaleString()}&thinsp;hidden</> : null}
                {excludedFromScopeCount ? <>&thinsp;·&thinsp;{excludedFromScopeCount.toLocaleString()}&thinsp;excluded</> : null}
              </span>
            )}
          </div>

          <div className="map-mode-switch" aria-label="Map mode">
            {MAP_MODES.map((mode) => (
              <button
                key={mode.id}
                className={`map-mode-tab${mapMode === mode.id ? " map-mode-tab-active" : ""}`}
                onClick={() => switchMapMode(mode.id)}
                data-tooltip={mode.tooltip}
                aria-label={`${mode.label}: ${mode.tooltip}`}
                title={mode.tooltip}
                type="button"
              >
                <span className="map-mode-tab-label">{mode.label}</span>
                <span className="map-mode-tab-sub">{mode.subLabel}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="map-mode-controls">
          <div className="map-mode-copy">
            <span className="map-mode-label">{activeMapMode.label}</span>
            <span className="map-mode-hint">{activeMapMode.hint}</span>
          </div>

          <div className="map-toolbar-right map-toolbar-all" aria-label="Map controls">
            {viewModeControls}
            {typeFilterControls}
            {sourceSelector}
            {signalControls}
            {edgeLayerControls}
            {pathControl}
            {overlapControl}
          </div>

          <button
            className="map-fit-btn"
            onClick={handleFit}
            title="Fit to viewport"
            type="button"
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

          {focusNotice && (
            <div className={`map-focus-notice${focusNotice.tone === "warn" ? " map-focus-notice-warn" : ""}`}>
              {focusNotice.text}
            </div>
          )}

          {(loading || (fullLoading && viewMode === "full")) && (
            <div className="map-overlay">
              <div className="map-spinner" />
              <span>{fullLoading && viewMode === "full" ? "Loading full graph…" : "Building graph summary…"}</span>
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

        {/* Overlap analysis panel */}
        {showOverlap && (viewMode === "full" || usingSummaryOverlap) && (
          <aside className="map-panel map-overlap-panel">
            <div className="map-panel-head">
              <span className="map-panel-name">
                {usingSummaryOverlap ? "Summary Overlap" : "Overlap Analysis"}
              </span>
              <button
                className="map-panel-close"
                onClick={() => { setShowOverlap(false); setHighlightedPair(null); onActiveContextChange?.(null); }}
                aria-label="Close"
              >✕</button>
            </div>
            {!usingSummaryOverlap && !crossSemanticEdges.length ? (
              <div className="map-overlap-empty">
                Enable the Semantic overlay first to see cross-repo overlap analysis.
              </div>
            ) : overlapGroups.length === 0 ? (
              <div className="map-overlap-empty">
                {usingSummaryOverlap
                  ? "No summary-level overlap pairs detected for the current map."
                  : "No cross-repo overlaps detected."}
              </div>
            ) : (
              <>
                <div className="map-overlap-summary">
                  {usingSummaryOverlap && (
                    <>
                      <span className="map-overlap-source-badge">Summary</span>
                      <span className="map-overlap-dot">·</span>
                    </>
                  )}
                  <span>
                    {filteredGroups.length}
                    {filteredGroups.length !== overlapGroups.length ? `/${overlapGroups.length}` : ""} pairs
                  </span>
                  <span className="map-overlap-dot">·</span>
                  <span>{overlapConnectionCount} connections</span>
                  {overlapStatusCounts.dismissed > 0 && (
                    <>
                      <span className="map-overlap-dot">·</span>
                      <span>{overlapStatusCounts.dismissed} dismissed</span>
                    </>
                  )}
                  {overlapGroups.some((g) => g.sameNameCount > 0) && (
                    <>
                      <span className="map-overlap-dot">·</span>
                      <span className="map-overlap-samename-summary">
                        {overlapGroups.filter((g) => g.sameNameCount > 0).length} same-name
                      </span>
                    </>
                  )}
                </div>
                {/* Similarity filter chips */}
                <div className="map-overlap-filters">
                  <span className="map-overlap-filter-label">≥</span>
                  {[0.70, 0.80, 0.85, 0.90].map((v) => (
                    <button
                      key={v}
                      className={`map-overlap-filter-chip${minSimilarity === v ? " map-overlap-filter-chip-on" : ""}`}
                      onClick={() => setMinSimilarity(v)}
                    >
                      {Math.round(v * 100)}%
                    </button>
                  ))}
                  <button
                    className={`map-overlap-filter-chip${sameNameOnly ? " map-overlap-filter-chip-warn" : ""}`}
                    onClick={() => setSameNameOnly((s) => !s)}
                    title="Show only pairs with matching filenames across repos"
                  >
                    Same-name
                  </button>
                </div>
                <div className="map-overlap-status-filters">
                  {(["active", "untriaged", "triaged", "task-created", "dismissed"] as OverlapStatusFilter[]).map((status) => {
                    const count = status === "active"
                      ? overlapGroups.length - overlapStatusCounts.dismissed
                      : overlapStatusCounts[status];
                    const label = status === "active" ? "Active" : OVERLAP_STATUS_LABELS[status];
                    return (
                      <button
                        key={status}
                        className={`map-overlap-filter-chip map-overlap-status-chip${overlapStatusFilter === status ? " map-overlap-filter-chip-on" : ""}`}
                        onClick={() => setOverlapStatusFilter(status)}
                        type="button"
                      >
                        {label} {count}
                      </button>
                    );
                  })}
                </div>
                {/* Triage bar */}
                <div className="map-overlap-triage-bar">
                  <span className="map-overlap-hint-inline">LLM: duplicate / reference / related</span>
                  <button
                    className="map-overlap-btn map-overlap-btn-triage"
                    onClick={triageAll}
                    disabled={Object.keys(triaging).length > 0}
                  >
                    {Object.keys(triaging).length > 0 ? "Triaging…" : "Triage All"}
                  </button>
                </div>
                <div className="map-overlap-list">
                  {filteredGroups.length === 0 && (
                    <div className="map-overlap-empty">No overlap pairs match the current filters.</div>
                  )}
                  {filteredGroups.map((g) => {
                    const taskKey = overlapKey(g);
                    const triageKey = overlapKey(g);
                    const isActive = highlightedPair?.[0] === g.clusterA && highlightedPair?.[1] === g.clusterB;
                    const workflowStatus = workflowStatusFor(g);
                    const workflowRecord = overlapStatuses[triageKey];
                    const created = workflowStatus === "task-created" || taskCreated === taskKey;
                    const creating = creatingTask === taskKey;
                    const triage = triageResults[triageKey];
                    const isTriaging = triaging[triageKey] ?? false;
                    const similarities = dossierList(triage?.similarities);
                    const differences = dossierList(triage?.differences);
                    const canonicalitySignals = dossierList(triage?.canonicality_signals);
                    const openQuestions = dossierList(triage?.open_questions);
                    return (
                      <div
                        key={taskKey}
                        className={[
                          "map-overlap-group",
                          isActive ? "map-overlap-group-active" : "",
                          g.sameNameCount > 0 ? "map-overlap-group-flagged" : "",
                        ].filter(Boolean).join(" ")}
                      >
                        <div className="map-overlap-group-head">
                          <div className="map-overlap-pair-title">
                            <span className="map-overlap-cluster" style={{ color: clusterColor(g.clusterA) }}>{g.clusterA}</span>
                            <span className="map-overlap-arr">↔</span>
                            <span className="map-overlap-cluster" style={{ color: clusterColor(g.clusterB) }}>{g.clusterB}</span>
                          </div>
                          <div className="map-overlap-counts">
                            <span className={`map-overlap-status-badge map-overlap-status-${workflowStatus}`}>
                              {OVERLAP_STATUS_LABELS[workflowStatus]}
                            </span>
                            {g.sameNameCount > 0 && (
                              <span
                                className="map-overlap-samename-badge"
                                title={`${g.sameNameCount} pair${g.sameNameCount > 1 ? "s" : ""} share the same filename`}
                              >
                                ≡ {g.sameNameCount}
                              </span>
                            )}
                            <span className="map-overlap-edge-count">{g.edgeCount}</span>
                            <span className="map-overlap-sim-pct">{Math.round(g.avgSimilarity * 100)}%</span>
                          </div>
                        </div>
                        {triage && (
                          <div className={`map-overlap-verdict map-overlap-verdict-${triage.verdict}`}>
                            <div className="map-overlap-verdict-head">
                              <span className="map-overlap-verdict-label">
                                {triage.verdict === "duplicate" ? "⚡ Duplicate" :
                                 triage.verdict === "reference" ? "→ Reference" :
                                 triage.verdict === "related" ? "~ Related" : "? Unknown"}
                              </span>
                              <span className="map-overlap-verdict-conf">{Math.round(triage.confidence * 100)}%</span>
                            </div>
                            {triage.reason && <p className="map-overlap-verdict-reason">{triage.reason}</p>}
                            {triage.action && (
                              <p className="map-overlap-verdict-action">
                                <span className="map-overlap-verdict-action-label">Next step: </span>
                                {triage.action}
                              </p>
                            )}
                            {(triage.evidence_summary || triage.per_side_purpose || similarities.length > 0 || differences.length > 0 || canonicalitySignals.length > 0 || openQuestions.length > 0) && (
                              <div className="map-overlap-dossier">
                                {triage.evidence_summary && (
                                  <section className="map-overlap-dossier-section">
                                    <h4>Why it matters</h4>
                                    <p>{triage.evidence_summary}</p>
                                  </section>
                                )}
                                {triage.per_side_purpose && (
                                  <section className="map-overlap-dossier-section">
                                    <h4>What each side does</h4>
                                    <div className="map-overlap-side-purpose">
                                      <strong>{g.clusterA}</strong>
                                      <span>{triage.per_side_purpose.cluster_a || UNKNOWN_VALUE}</span>
                                    </div>
                                    <div className="map-overlap-side-purpose">
                                      <strong>{g.clusterB}</strong>
                                      <span>{triage.per_side_purpose.cluster_b || UNKNOWN_VALUE}</span>
                                    </div>
                                  </section>
                                )}
                                {(similarities.length > 0 || differences.length > 0) && (
                                  <div className="map-overlap-dossier-grid">
                                    {similarities.length > 0 && (
                                      <section className="map-overlap-dossier-section">
                                        <h4>Similar</h4>
                                        <ul>{similarities.map((item, i) => <li key={i}>{item}</li>)}</ul>
                                      </section>
                                    )}
                                    {differences.length > 0 && (
                                      <section className="map-overlap-dossier-section">
                                        <h4>Different</h4>
                                        <ul>{differences.map((item, i) => <li key={i}>{item}</li>)}</ul>
                                      </section>
                                    )}
                                  </div>
                                )}
                                {(canonicalitySignals.length > 0 || openQuestions.length > 0) && (
                                  <div className="map-overlap-dossier-grid">
                                    {canonicalitySignals.length > 0 && (
                                      <section className="map-overlap-dossier-section">
                                        <h4>Canonicality</h4>
                                        <ul>{canonicalitySignals.map((item, i) => <li key={i}>{item}</li>)}</ul>
                                      </section>
                                    )}
                                    {openQuestions.length > 0 && (
                                      <section className="map-overlap-dossier-section">
                                        <h4>Open Questions</h4>
                                        <ul>{openQuestions.map((item, i) => <li key={i}>{item}</li>)}</ul>
                                      </section>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                        <div className="map-overlap-pairs-list">
                          {g.topPairs.map((p, i) => (
                            <div
                              key={i}
                              className={`map-overlap-pair-row${p.sameName ? " map-overlap-pair-row-samename" : ""}`}
                            >
                              <span className="map-overlap-pair-side" title={p.fileA}>
                                <span className="map-overlap-pair-label">{p.labelA}</span>
                                <span className="map-overlap-pair-path">{compactPath(p.fileA)}</span>
                              </span>
                              <span className="map-overlap-pair-sep">↔</span>
                              <span className="map-overlap-pair-side" title={p.fileB}>
                                <span className="map-overlap-pair-label">{p.labelB}</span>
                                <span className="map-overlap-pair-path">{compactPath(p.fileB)}</span>
                              </span>
                              {p.sameName && (
                                <span className="map-overlap-pair-samename" title="Same filename in different repos">≡</span>
                              )}
                              <span className="map-overlap-pair-sim">{Math.round(p.similarity * 100)}%</span>
                            </div>
                          ))}
                        </div>
                        <div className="map-overlap-actions">
                          <button
                            className={`map-overlap-btn${isActive ? " map-overlap-btn-lit" : ""}`}
                            onClick={() => {
                              if (isActive) {
                                setHighlightedPair(null);
                                if (!usingSummaryOverlap) setShowSemantic(false);
                                if (usingSummaryOverlap) {
                                  cyRef.current?.nodes().removeClass("selected");
                                  cyRef.current?.edges().removeClass("highlighted");
                                }
                                onActiveContextChange?.(null);
                              } else {
                                if (usingSummaryOverlap) {
                                  highlightSummaryOverlapPair(g.clusterA, g.clusterB);
                                } else if (!showSemantic) {
                                  setShowSemantic(true);
                                }
                                setHighlightedPair([g.clusterA, g.clusterB]);
                                onActiveContextChange?.({
                                  kind: "overlap-pair",
                                  source: "map",
                                  clusterA: g.clusterA,
                                  clusterB: g.clusterB,
                                  sourceNodeId: g.topPairs[0]?.source,
                                  targetNodeId: g.topPairs[0]?.target,
                                  labelA: g.topPairs[0]?.labelA,
                                  labelB: g.topPairs[0]?.labelB,
                                  similarity: g.maxSimilarity,
                                });
                              }
                            }}
                          >
                            {isActive ? "Clear" : "Highlight"}
                          </button>
                          <button
                            className={`map-overlap-btn map-overlap-btn-triage${triage ? ` map-overlap-verdict-${triage.verdict}-btn` : ""}`}
                            onClick={() => triageOverlapGroup(g)}
                            disabled={isTriaging}
                            title="Ask local LLM to classify this overlap"
                          >
                            {isTriaging ? "…" : triage ? "Re-triage" : "Triage"}
                          </button>
                          <button
                            className={`map-overlap-btn map-overlap-btn-primary${created ? " map-overlap-btn-done" : ""}`}
                            onClick={() => createOverlapTask(g)}
                            disabled={creating || created}
                            title={
                              workflowRecord?.recommendation_id
                                ? `Recommendation created: ${workflowRecord.recommendation_id}`
                                : triage
                                ? `Create task: ${triage.action || triage.verdict}`
                                : "Create consolidation task"
                            }
                          >
                            {created ? "✓" : creating ? "…" : triage
                              ? (triage.verdict === "duplicate" ? "Task: Merge →" :
                                 triage.verdict === "reference" ? "Task: Review →" :
                                 triage.verdict === "related" ? "Task: Document →" : "Task →")
                              : "Task →"}
                          </button>
                          <button
                            className="map-overlap-btn map-overlap-btn-dismiss"
                            onClick={() => {
                              const nextStatus = workflowStatus === "dismissed"
                                ? (triage ? "triaged" : "untriaged")
                                : "dismissed";
                              if (nextStatus === "dismissed" && isActive) {
                                setHighlightedPair(null);
                                onActiveContextChange?.(null);
                              }
                              saveOverlapStatus(g, nextStatus, triage ? { triage_result: triage } : {});
                            }}
                            disabled={workflowStatus === "task-created"}
                            title={workflowStatus === "dismissed" ? "Restore this pair to the active review queue" : "Dismiss this pair as non-actionable"}
                            type="button"
                          >
                            {workflowStatus === "dismissed" ? "Restore" : "Dismiss"}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </aside>
        )}

        {/* Full-graph inspect panel */}
        {selectedFull && viewMode === "full" && !showOverlap && (
          <aside className="map-panel">
            <div className="map-panel-head">
              <span className="map-panel-name">{selectedFull.label}</span>
              <button className="map-panel-close" onClick={() => { setSelectedFull(null); onActiveContextChange?.(null); }} aria-label="Close">✕</button>
            </div>
            <div className="map-panel-section">
              <span className={`map-type-badge map-type-${selectedFull.type}`}>{selectedFull.type}</span>
              <span
                className="map-type-badge"
                style={{ color: clusterColor(selectedFull.cluster), borderColor: clusterColor(selectedFull.cluster) }}
              >
                {selectedFull.cluster}
              </span>
              <span
                className={`map-type-badge map-signal-badge map-signal-${selectedFull.signal_tier ?? "evidence"}`}
                title={selectedFull.signal_reason || "Signal tier"}
              >
                {signalTierLabel(selectedFull.signal_tier)}
              </span>
            </div>

            <div className="map-inspector-block">
              <div className="map-inspector-title">What this appears to do</div>
              <p className="map-inspector-purpose">
                {selectedFull.purpose || `${selectedFull.label} is a ${selectedFull.type} node. Source detail is limited for this item.`}
              </p>
            </div>

            <div className="map-provenance-grid">
              <div className="map-provenance-row">
                <span>Repo</span>
                <strong>{presentValue(selectedFull.repo || selectedFull.source_root_name)}</strong>
              </div>
              <div className="map-provenance-row">
                <span>Container</span>
                <strong>{presentValue(selectedFull.container || selectedFull.cluster)}</strong>
              </div>
              <div className="map-provenance-row map-provenance-wide">
                <span>Path</span>
                <strong>{presentValue(selectedFull.relative_path || selectedFull.source_file)}</strong>
              </div>
              <div className="map-provenance-row">
                <span>Location</span>
                <strong>{presentValue(selectedFull.source_location)}</strong>
              </div>
              <div className="map-provenance-row">
                <span>Symbol</span>
                <strong>{presentValue(selectedFull.symbol || selectedFull.label)}</strong>
              </div>
              <div className="map-provenance-row">
                <span>Kind</span>
                <strong>{presentValue(selectedFull.metadata?.kind || selectedFull.type)}</strong>
              </div>
              <div className="map-provenance-row">
                <span>Language</span>
                <strong>{presentValue(selectedFull.metadata?.language)}</strong>
              </div>
              <div className="map-provenance-row">
                <span>Origin</span>
                <strong>{presentValue(selectedFull.origin)}</strong>
              </div>
              <div className="map-provenance-row">
                <span>Signal</span>
                <strong>{presentValue(selectedFull.signal_reason)}</strong>
              </div>
              <div className="map-provenance-row map-provenance-wide">
                <span>Source root</span>
                <strong>{presentValue(selectedFull.source_root)}</strong>
              </div>
              <div className="map-provenance-row map-provenance-wide">
                <span>Node id</span>
                <strong>{selectedFull.id}</strong>
              </div>
            </div>

            {metadataEntries(selectedFull).length > 0 && (
              <div className="map-inspector-block">
                <div className="map-inspector-title">Extra metadata</div>
                <div className="map-metadata-list">
                  {metadataEntries(selectedFull).map(([key, value]) => (
                    <div className="map-metadata-row" key={key}>
                      <span>{prettyMetadataKey(key)}</span>
                      <strong>{prettyMetadataValue(value)}</strong>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="map-inspector-block">
              <div className="map-inspector-title">Source excerpt</div>
              {selectedFull.source_excerpt?.lines?.length ? (
                <pre className="map-source-excerpt">
                  {selectedFull.source_excerpt.lines.map((line, idx) => {
                    const lineNumber = (selectedFull.source_excerpt?.start_line ?? 1) + idx;
                    return `${String(lineNumber).padStart(4, " ")}  ${line}`;
                  }).join("\n")}
                </pre>
              ) : (
                <div className="map-provenance-empty">
                  {selectedFull.source_excerpt?.unavailable_reason || "No source excerpt available for this node."}
                </div>
              )}
            </div>

            {selectedFull.source_file && (
              <div className="map-inspector-footnote">
                Graph source: {selectedFull.source_file}
              </div>
            )}
          </aside>
        )}

        {selected && viewMode === "summary" && (
          <aside className="map-panel">
            <div className="map-panel-head">
              <span className="map-panel-name">{selected.label}</span>
              <button
                className="map-panel-close"
                onClick={() => { setSelected(null); onActiveContextChange?.(null); }}
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
              <span className="map-type-badge map-group-badge">
                {selected.group_type === "repo" ? "Repo / Project" : selected.group_type === "module" ? "Module" : "Group"}
              </span>
              {godNodeIds.has(selected.id) && (
                <span className="map-god-badge" title={`High-traffic node (${godNodeEdgeCounts[selected.id] ?? 0} edge weight)`}>
                  ⚡ High-traffic node ({godNodeEdgeCounts[selected.id] ?? 0} edges)
                </span>
              )}
              {selected.is_gap && (
                <span className="map-gap-badge" title="No visible physical links connect this group to the current map.">
                  Gap
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
              <div className="map-stat">
                <span className="map-stat-label">Links</span>
                <span className="map-stat-value">{selected.connection_count ?? 0}</span>
              </div>
              <div className="map-stat">
                <span className="map-stat-label">Weight</span>
                <span className="map-stat-value">{selected.connection_weight ?? 0}</span>
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

            <div className="map-relationships">
              <div className="map-relationships-head">
                <span>Connected Groups</span>
                <strong>{selectedConnections.length}</strong>
              </div>
              {selectedConnections.length > 0 ? (
                <div className="map-relationship-list">
                  {selectedConnections.map((connection) => (
                    <button
                      className="map-relationship-row"
                      key={connection.id}
                      onClick={() => focusSummaryGroup(connection.id)}
                    >
                      <span className="map-relationship-main">
                        <span className="map-relationship-label">{connection.label}</span>
                        <span className="map-relationship-relations">{relationList(connection.relations)}</span>
                      </span>
                      <span className="map-relationship-weight">{connection.weight}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="map-relationship-empty">
                  {selected.gap_reason || "No visible group-to-group physical links at the current filters."}
                </div>
              )}
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
