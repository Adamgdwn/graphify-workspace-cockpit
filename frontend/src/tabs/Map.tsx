import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiErrorMessage, apiFetch } from "../api/client";
import cytoscape from "cytoscape";
import type { Core } from "cytoscape";
// @ts-ignore
import fcose from "cytoscape-fcose";
// @ts-ignore
import layoutUtilities from "cytoscape-layout-utilities";
import { DECISION_CLASSIFICATIONS, type DecisionClassification } from "../domain/decision";
import type { ActiveCockpitContext } from "../domain/cockpitContext";
import type { ActiveCockpitContextHandler } from "../domain/cockpitContext";
import type { WorkspaceScopeProfile } from "../components/WorkspaceScopePicker";
import { WorkingStatus } from "../components/WorkingStatus";
import { useToast } from "../components/Toast";

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
  gap_type?: GapType | "";
  gap_detail?: string;
  gap_evidence?: string[];
  gap_actions?: string[];
  connections?: SummaryConnection[];
  decision_classification?: DecisionClassification | "";
  decision_count?: number;
  recommendation_count?: number;
  queued_action_count?: number;
  decision_overlay?: DecisionOverlay;
}

type GapType =
  | "truly_isolated"
  | "hidden_by_low_signal_filters"
  | "missing_semantic_extraction"
  | "root_level_docs_only";

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

interface OverlayDecision {
  id: string;
  target_id: string;
  label: string;
  classification: DecisionClassification | string;
  rationale?: string;
  status?: string;
  updated_at?: string;
}

interface OverlayRecommendation {
  id: string;
  title: string;
  mode?: string;
  status?: string;
  summary?: string;
  proposed_action?: string;
  confidence?: number;
  risk?: string;
  effort?: string;
  updated_at?: string;
}

interface OverlayAction {
  id: string;
  source_recommendation_id?: string;
  status?: string;
  action_type?: string;
  description?: string;
  proposed_action_text?: string;
  target_path?: string;
  updated_at?: string;
}

interface SemanticEdge {
  source: string;
  target: string;
  similarity: number;
}

interface SemanticEdgeMeta {
  edge_count: number;
  created_at: string | null;
  graph_matches?: boolean;
  graph_stale?: boolean;
  edge_policy_stale?: boolean;
  legacy_edge_count?: number;
  scope_node_count?: number;
  embedded_node_count?: number;
  max_neighbors_per_node?: number;
  mutual_top_neighbors?: boolean;
  max_edges?: number;
  current_graph_edge_match_count?: number;
  current_graph_node_count?: number;
}

interface SemanticPassStatus {
  status: "idle" | "running" | "complete" | "error" | string;
  progress: number;
  total: number;
  last_run: string | null;
  error: string | null;
  edge_count: number;
  model: string | null;
  threshold?: number | null;
  scope_node_count?: number;
  max_neighbors_per_node?: number;
  max_edges?: number;
}

interface DecisionOverlay {
  decision_classification?: DecisionClassification | "";
  decision_count: number;
  recommendation_count: number;
  queued_action_count: number;
  decisions: OverlayDecision[];
  recommendations: OverlayRecommendation[];
  queued_actions: OverlayAction[];
  next_actions?: string[];
}

interface GraphSummary {
  level: "top" | "project";
  project: string | null;
  total_nodes: number;
  hidden_node_count?: number;
  excluded_node_count?: number;
  signal_counts?: Record<string, number>;
  importance_counts?: Record<string, number>;
  workspace_scope?: WorkspaceScopeSummary | null;
  nodes: SummaryNode[];
  edges: SummaryEdge[];
}

interface WorkspaceScopeSummary {
  profile_name?: string;
  root?: string;
  included_paths?: string[];
  excluded_paths?: string[];
  scanned_root_count?: number;
  removed_node_count?: number;
  generated_at?: string | null;
}

interface RebuildStatus {
  status: "idle" | "running" | "complete" | "error";
  last_run: string | null;
  error?: string | null;
  code?: string | null;
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
  importance_tier?: "anchor" | "interface" | "important" | "evidence" | "hidden" | "excluded";
  importance_reason?: string;
  decision_classification?: DecisionClassification | "";
  decision_count?: number;
  recommendation_count?: number;
  queued_action_count?: number;
  decision_overlay?: DecisionOverlay;
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
  importance_counts?: Record<string, number>;
  include_low_signal?: boolean;
  knowledge_only?: boolean;
  knowledge_hidden_node_count?: number;
  nodes: FullNode[];
  edges: FullEdge[];
}

type Filter = "all" | "code" | "document";
type ViewMode = "summary" | "full";
const FULL_GRAPH_NODE_LIMIT = 15000;
const DEFAULT_SEMANTIC_MODEL = "nomic-embed-text:latest";
const DEFAULT_SEMANTIC_THRESHOLD = 0.86;
const DEFAULT_SEMANTIC_NEIGHBOR_LIMIT = 12;
const DEFAULT_SEMANTIC_STORED_EDGE_LIMIT = 50000;
type MapMode = "explore" | "trace" | "overlap" | "review";
type ScopeGateState = "checking" | "ready" | "setup";

function normalizedPathList(values: string[] | undefined): string[] {
  return [...new Set((values ?? []).map((value) => value.trim()).filter(Boolean))].sort();
}

function samePathList(left: string[] | undefined, right: string[] | undefined): boolean {
  const a = normalizedPathList(left);
  const b = normalizedPathList(right);
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

function generatedScopeMatchesProfile(
  generated: WorkspaceScopeSummary | null | undefined,
  profile: WorkspaceScopeProfile | null | undefined,
): boolean {
  if (!profile) return true;
  if (!generated) return false;
  return (
    String(generated.root || "") === profile.root
    && samePathList(generated.included_paths, profile.included_paths)
    && samePathList(generated.excluded_paths, profile.excluded_paths)
  );
}

function shouldOpenExpandedEvidence(summary: GraphSummary, project?: string): boolean {
  const includedCount = summary.workspace_scope?.included_paths?.length ?? 0;
  return (
    !project
    && includedCount >= 1
    && includedCount <= 3
    && summary.nodes.length <= includedCount
    && summary.total_nodes <= FULL_GRAPH_NODE_LIMIT
  );
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

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
    hint: "Choose a source and target to see the shortest physical or semantic path.",
    tooltip: "Path tracing: pick two nodes and show the shortest route through the evidence graph, including semantic edges when enabled.",
  },
  {
    id: "overlap",
    label: "Overlap",
    subLabel: "semantic",
    hint: "Review semantic connections, cross-folder overlap, and consolidation candidates.",
    tooltip: "Semantic overlap: show similarity edges, group cross-folder or cross-repo connections, and triage duplicate or related work.",
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

function importanceTierLabel(tier?: string): string {
  if (!tier) return "Evidence";
  if (tier === "anchor") return "Anchor";
  if (tier === "interface") return "Interface";
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
  actionabilityScore?: number;
  insightKind?: SemanticInsightKind;
  decisionSignals?: string[];
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
  actionabilityScore?: number;
  decisionSignals?: string[];
}

type SemanticInsightKind =
  | "waste_duplicate"
  | "gap_missing_bridge"
  | "cross_app_similarity"
  | "shared_pattern"
  | "drift_risk"
  | "intentional_reference"
  | "low_value"
  | "unknown";

interface ActionableSemanticEdge extends SemanticEdge {
  actionabilityScore: number;
  insightKind: SemanticInsightKind;
  decisionSignals: string[];
}

interface SelectedSemanticLink {
  edge: ActionableSemanticEdge;
  sourceNode: FullNode | null;
  targetNode: FullNode | null;
  sourceGroup: string;
  targetGroup: string;
}

interface SemanticInsightSummary {
  kind: SemanticInsightKind;
  label: string;
  score: number;
  source: "signal" | "llm";
  impact?: string;
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
  insight_kind?: SemanticInsightKind;
  actionability_score?: number;
  decision_impact?: string;
  waste_signal?: string;
  gap_signal?: string;
  cross_app_similarity?: string;
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

const SEMANTIC_INSIGHT_LABELS: Record<SemanticInsightKind, string> = {
  waste_duplicate: "Waste / Duplicate",
  gap_missing_bridge: "Gap / Missing Bridge",
  cross_app_similarity: "Cross-App Similarity",
  shared_pattern: "Shared Pattern",
  drift_risk: "Drift Risk",
  intentional_reference: "Intentional Reference",
  low_value: "Low-Value Similarity",
  unknown: "Needs Judgment",
};

function boundedPercent(value: number | undefined, fallback: number): number {
  const numeric = Number.isFinite(value) ? Number(value) : fallback;
  return Math.round(Math.min(1, Math.max(0, numeric)) * 100);
}

function semanticInsightClass(kind: SemanticInsightKind): string {
  return kind.replace(/_/g, "-");
}

function heuristicOverlapInsight(group: OverlapGroup): SemanticInsightSummary {
  const maxSimilarity = group.maxSimilarity || group.avgSimilarity || 0;
  const sameNameBoost = group.sameNameCount > 0 ? 0.18 : 0;
  const densityBoost = Math.min(0.18, group.edgeCount / 250);
  const heuristicScore = 0.34 + group.avgSimilarity * 0.34 + densityBoost + sameNameBoost;
  const score = Math.min(0.98, Math.max(heuristicScore, group.actionabilityScore ?? 0));
  let kind: SemanticInsightKind = "low_value";
  let impact = "Similarity is present, but it needs LLM triage before it should drive cleanup work.";

  if (group.sameNameCount >= 2 || (group.sameNameCount > 0 && maxSimilarity >= 0.88)) {
    kind = "waste_duplicate";
    impact = "Same-name, high-similarity pairs may indicate duplicate knowledge or implementation waste.";
  } else if (group.edgeCount >= 18 && group.avgSimilarity >= 0.86) {
    kind = "cross_app_similarity";
    impact = "Many high-similarity links connect these areas, so compare them as related application capabilities.";
  } else if (group.edgeCount >= 8 && group.avgSimilarity >= 0.8) {
    kind = "gap_missing_bridge";
    impact = "Related areas are semantically close but lack a clear duplicate signal; look for a missing bridge or owner decision.";
  } else if (maxSimilarity >= 0.92) {
    kind = "drift_risk";
    impact = "A very similar pair may drift unless the canonical source is made explicit.";
  } else if (group.edgeCount >= 4) {
    kind = "shared_pattern";
    impact = "This may be a reusable pattern or vocabulary that should be named if it matters across apps.";
  }

  return {
    kind,
    label: SEMANTIC_INSIGHT_LABELS[kind],
    score,
    source: "signal",
    impact,
  };
}

function triageInsight(triage: TriageResult | undefined, group: OverlapGroup): SemanticInsightSummary {
  const fallback = heuristicOverlapInsight(group);
  if (!triage) return fallback;
  const kind = triage.insight_kind && SEMANTIC_INSIGHT_LABELS[triage.insight_kind]
    ? triage.insight_kind
    : fallback.kind;
  return {
    kind,
    label: SEMANTIC_INSIGHT_LABELS[kind],
    score: Number.isFinite(triage.actionability_score) ? Number(triage.actionability_score) : fallback.score,
    source: "llm",
    impact: triage.decision_impact || fallback.impact,
  };
}

function semanticInsightImpact(kind: SemanticInsightKind, signals: string[] = []): string {
  if (kind === "waste_duplicate") {
    return "This link looks actionable because the endpoints may be duplicate work or duplicate knowledge that deserves one canonical home.";
  }
  if (kind === "drift_risk") {
    return "This link is strong enough that the two sides may drift unless one source of truth or an explicit relationship is named.";
  }
  if (kind === "gap_missing_bridge") {
    return "This link connects related work without a clear physical bridge, so it may point to missing documentation, ownership, or integration.";
  }
  if (kind === "cross_app_similarity") {
    return "This link crosses application boundaries and may reveal shared capability, reused workflow, or competing implementations.";
  }
  if (kind === "shared_pattern") {
    return "This link suggests a reusable pattern or vocabulary that may be worth naming if it matters across this scope.";
  }
  if (kind === "intentional_reference") {
    return "This link appears related and already has some structural support, so treat it as a reference to confirm rather than cleanup by default.";
  }
  if (signals.length > 0) {
    return "This link cleared the semantic actionability filter because several practical signals lined up.";
  }
  return "This semantic link needs human judgment before it should drive a change.";
}

function relationList(relations?: string[]): string {
  const cleaned = (relations ?? []).map((relation) => relation.trim()).filter(Boolean);
  return cleaned.length ? cleaned.slice(0, 3).join(", ") : "physical links";
}

function gapTypeLabel(type?: string): string {
  if (type === "hidden_by_low_signal_filters") return "Hidden by Filters";
  if (type === "missing_semantic_extraction") return "Needs Extraction";
  if (type === "root_level_docs_only") return "Root Docs";
  if (type === "truly_isolated") return "Isolated";
  return "Gap";
}

function gapAskPrompt(node: SummaryNode): string {
  const evidence = (node.gap_evidence ?? []).map((item) => `- ${item}`).join("\n");
  return [
    `Review the workspace map gap "${node.label}" (${node.id}).`,
    node.gap_detail || node.gap_reason || "No visible group-to-group physical links connect this area.",
    evidence ? `Evidence:\n${evidence}` : "",
    "Should this area be drilled into, monitored, archived, or re-indexed for better relationships?",
  ].filter(Boolean).join("\n\n");
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

function decisionMeta(classification?: string) {
  return classification ? DECISION_META[classification] : undefined;
}

function hasDecisionOverlay(overlay?: DecisionOverlay | null): overlay is DecisionOverlay {
  if (!overlay) return false;
  return Boolean(
    overlay.decision_count
    || overlay.recommendation_count
    || overlay.queued_action_count
    || (overlay.next_actions?.length ?? 0),
  );
}

function overlayStatusText(status?: string): string {
  return presentValue(status).replace(/-/g, " ");
}

function DecisionContextBlock({ overlay }: { overlay?: DecisionOverlay | null }) {
  if (!hasDecisionOverlay(overlay)) return null;
  return (
    <div className="map-decision-context">
      <div className="map-decision-context-head">
        <span>Decision Context</span>
        <strong>
          {overlay.decision_count}D · {overlay.recommendation_count}R · {overlay.queued_action_count}Q
        </strong>
      </div>

      {overlay.decisions.length > 0 && (
        <div className="map-decision-context-section">
          {overlay.decisions.map((decision) => {
            const meta = decisionMeta(decision.classification);
            return (
              <div className="map-decision-context-card" key={decision.id}>
                <div className="map-decision-context-card-head">
                  <span>{decision.label || decision.target_id}</span>
                  {meta && (
                    <strong style={{ color: meta.color, borderColor: meta.color }}>
                      {meta.label}
                    </strong>
                  )}
                </div>
                {decision.rationale && <p>{decision.rationale}</p>}
              </div>
            );
          })}
        </div>
      )}

      {overlay.recommendations.length > 0 && (
        <div className="map-decision-context-section">
          <div className="map-decision-context-label">Recommendations</div>
          {overlay.recommendations.map((rec) => (
            <div className="map-decision-context-card" key={rec.id}>
              <div className="map-decision-context-card-head">
                <span>{rec.title || rec.id}</span>
                <strong>{overlayStatusText(rec.status)}</strong>
              </div>
              {(rec.proposed_action || rec.summary) && (
                <p>{rec.proposed_action || rec.summary}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {overlay.queued_actions.length > 0 && (
        <div className="map-decision-context-section">
          <div className="map-decision-context-label">Queued Actions</div>
          {overlay.queued_actions.map((action) => (
            <div className="map-decision-context-card" key={action.id}>
              <div className="map-decision-context-card-head">
                <span>{action.description || action.action_type || action.id}</span>
                <strong>{overlayStatusText(action.status)}</strong>
              </div>
              {action.proposed_action_text && <p>{action.proposed_action_text}</p>}
            </div>
          ))}
        </div>
      )}

      {overlay.next_actions && overlay.next_actions.length > 0 && (
        <div className="map-decision-next-actions">
          {overlay.next_actions.slice(0, 3).map((action, index) => (
            <span key={`${action}-${index}`}>{action}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function DecisionBadge({ classification }: { classification?: string }) {
  const meta = decisionMeta(classification);
  if (!meta) return null;
  return (
    <span
      className="map-decision-badge"
      style={{ color: meta.color, borderColor: meta.color }}
    >
      {meta.label}
    </span>
  );
}

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
      "line-color": "#4f72b8",
      "target-arrow-color": "#5f82c8",
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.75,
      opacity: 0.78,
    },
  },
  {
    selector: "edge.highlighted",
    style: {
      "line-color": "#b8caff",
      "target-arrow-color": "#b8caff",
      opacity: 1,
      width: 4,
      "z-index": 20,
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
    const dec = n.decision_overlay?.decision_classification || n.decision_classification || decisions[n.id];
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
        decision_count: n.decision_overlay?.decision_count ?? n.decision_count ?? 0,
        recommendation_count: n.decision_overlay?.recommendation_count ?? n.recommendation_count ?? 0,
        queued_action_count: n.decision_overlay?.queued_action_count ?? n.queued_action_count ?? 0,
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

const FULL_FAST_LAYOUT = {
  name: "preset",
  fit: true,
  padding: 60,
  animate: false,
};

const FULL_FAST_LAYOUT_NODE_THRESHOLD = 900;
const FULL_FAST_LAYOUT_MULTI_REPO_THRESHOLD = 2;
const FULL_FAST_LAYOUT_EDGE_THRESHOLD = 1600;

const SEMANTIC_EDGE_DISPLAY_LIMIT = 2000;
const SEMANTIC_BACKBONE_NEIGHBOR_LIMIT = 4;
const SEMANTIC_BACKBONE_NODE_DEGREE_LIMIT = 6;
const SEMANTIC_ACTIONABLE_EDGE_MIN_SCORE = 0.58;
const FULL_CONTAINER_LABEL_LIMIT = 36;

const SEMANTIC_SCAFFOLD_FILENAMES = new Set([
  ".gitignore",
  "agents.md",
  "changelog.md",
  "code_of_conduct.md",
  "contributing.md",
  "deployment-guide.md",
  "docker-compose.yml",
  "dockerfile",
  "governance-check.sh",
  "governance-preflight.sh",
  "install.sh",
  "agent-inventory.md",
  "license",
  "license.md",
  "manual.md",
  "model-registry.md",
  "overview.md",
  "package-lock.json",
  "package.json",
  "pnpm-lock.yaml",
  "preflight.sh",
  "prompt-register.md",
  "pyproject.toml",
  "readme.md",
  "requirements.txt",
  "risk-register.md",
  "roadmap.md",
  "security.md",
  "setup.cfg",
  "setup.py",
  "smoke-test.sh",
  "test.sh",
  "todo.md",
  "tool-permission-matrix.md",
  "tsconfig.json",
  "vite.config.ts",
  "yarn.lock",
]);

const SEMANTIC_GENERIC_FILE_STEMS = new Set([
  "__init__",
  "agent-inventory",
  "api",
  "app",
  "bootstrap",
  "build",
  "cli",
  "client",
  "common",
  "config",
  "constants",
  "demo",
  "example",
  "governance-check",
  "governance-preflight",
  "helper",
  "helpers",
  "index",
  "main",
  "model",
  "models",
  "model-registry",
  "preflight",
  "prompt-register",
  "risk-register",
  "roadmap",
  "runner",
  "sample",
  "schema",
  "script",
  "scripts",
  "server",
  "service",
  "services",
  "settings",
  "setup",
  "test",
  "tests",
  "tool-permission-matrix",
  "types",
  "util",
  "utilities",
  "utils",
]);

const SEMANTIC_GENERIC_LABELS = new Set([
  "__init__",
  "agentinventory",
  "any",
  "app",
  "build",
  "cli",
  "config",
  "currentriskclassification",
  "do_get",
  "do_post",
  "fail",
  "get",
  "keyrisks",
  "keydecisions",
  "logger",
  "main",
  "modelregistry",
  "namespace",
  "pass",
  "path",
  "post",
  "promptregister",
  "require_file",
  "riskregister",
  "roadmap",
  "run",
  "run_once",
  "setup",
  "summary",
  "test",
  "toolpermissionmatrix",
  "warn",
]);

const SEMANTIC_SCAFFOLD_PATH_PARTS = new Set([
  ".github",
  "children",
  "demo",
  "demos",
  "doc",
  "docs",
  "documentation",
  "example",
  "examples",
  "root",
  "risk",
  "risks",
  "script",
  "scripts",
  "test",
  "tests",
  "workflow",
  "workflows",
]);

const SEMANTIC_DOMAIN_STOPWORDS = new Set([
  "about",
  "action",
  "actions",
  "agent",
  "agents",
  "build",
  "check",
  "checks",
  "code",
  "common",
  "config",
  "content",
  "demo",
  "docs",
  "document",
  "documentation",
  "example",
  "file",
  "files",
  "from",
  "graph",
  "helper",
  "helpers",
  "high",
  "import",
  "imports",
  "index",
  "json",
  "local",
  "main",
  "module",
  "node",
  "nodes",
  "nearby",
  "overview",
  "payload",
  "project",
  "readme",
  "read",
  "reads",
  "repo",
  "repos",
  "root",
  "runner",
  "sample",
  "script",
  "scripts",
  "service",
  "settings",
  "setup",
  "source",
  "text",
  "test",
  "tests",
  "types",
  "update",
  "updates",
  "utils",
  "with",
  "write",
  "writes",
  "workspace",
  "appears",
  "annotations",
  "future",
  "self",
  "starts",
  "symbol",
  "symbols",
]);

function semanticEdgeKey(source: string, target: string) {
  return source < target ? `${source}\u0000${target}` : `${target}\u0000${source}`;
}

function buildSemanticBackbone<T extends SemanticEdge>(edges: T[]): T[] {
  const uniqueByPair = new globalThis.Map<string, T>();
  for (const edge of edges) {
    const key = semanticEdgeKey(edge.source, edge.target);
    const existing = uniqueByPair.get(key);
    if (!existing || edge.similarity > existing.similarity) {
      uniqueByPair.set(key, edge);
    }
  }

  const uniqueEdges = [...uniqueByPair.values()];
  const sortedEdges = [...uniqueEdges].sort((a, b) => b.similarity - a.similarity);
  const edgesByNode = new globalThis.Map<string, T[]>();
  for (const edge of uniqueEdges) {
    edgesByNode.set(edge.source, [...(edgesByNode.get(edge.source) ?? []), edge]);
    edgesByNode.set(edge.target, [...(edgesByNode.get(edge.target) ?? []), edge]);
  }

  const rankByNode = new globalThis.Map<string, globalThis.Map<string, number>>();
  for (const [nodeId, nodeEdges] of edgesByNode) {
    const ranked = new globalThis.Map<string, number>();
    [...nodeEdges]
      .sort((a, b) => b.similarity - a.similarity)
      .forEach((edge, index) => {
        ranked.set(semanticEdgeKey(edge.source, edge.target), index + 1);
      });
    rankByNode.set(nodeId, ranked);
  }

  const selected: T[] = [];
  const degreeByNode = new globalThis.Map<string, number>();
  for (const edge of sortedEdges) {
    const key = semanticEdgeKey(edge.source, edge.target);
    const sourceRank = rankByNode.get(edge.source)?.get(key) ?? Number.POSITIVE_INFINITY;
    const targetRank = rankByNode.get(edge.target)?.get(key) ?? Number.POSITIVE_INFINITY;
    if (sourceRank > SEMANTIC_BACKBONE_NEIGHBOR_LIMIT || targetRank > SEMANTIC_BACKBONE_NEIGHBOR_LIMIT) {
      continue;
    }
    if (
      (degreeByNode.get(edge.source) ?? 0) >= SEMANTIC_BACKBONE_NODE_DEGREE_LIMIT
      || (degreeByNode.get(edge.target) ?? 0) >= SEMANTIC_BACKBONE_NODE_DEGREE_LIMIT
    ) {
      continue;
    }

    selected.push(edge);
    degreeByNode.set(edge.source, (degreeByNode.get(edge.source) ?? 0) + 1);
    degreeByNode.set(edge.target, (degreeByNode.get(edge.target) ?? 0) + 1);
    if (selected.length >= SEMANTIC_EDGE_DISPLAY_LIMIT) break;
  }

  return selected.length ? selected : sortedEdges.slice(0, SEMANTIC_EDGE_DISPLAY_LIMIT);
}

function fullNodeRepo(node: FullNode): string {
  return node.repo || node.source_root_name || node.source_root || node.cluster || "workspace";
}

function fullNodeContainer(node: FullNode): string {
  const pathHead = (node.relative_path || node.source_file || "")
    .replace(/\\/g, "/")
    .split("/")
    .filter(Boolean)[0];
  return node.container || pathHead || node.type || "root";
}

function fullNodeGroup(node: FullNode, repoCount: number): string {
  const repo = fullNodeRepo(node);
  const container = fullNodeContainer(node);
  if (repoCount > 1) return `${repo} / ${container}`;
  return container || node.cluster || repo;
}

function nodePath(node: FullNode | undefined): string {
  return (node?.source_file || node?.relative_path || "").replace(/\\/g, "/").trim();
}

function pathBasename(path: string): string {
  return path.split("/").filter(Boolean).pop()?.toLowerCase() ?? "";
}

function pathParts(path: string): string[] {
  return path
    .replace(/\\/g, "/")
    .split("/")
    .map((part) => part.trim().toLowerCase())
    .filter(Boolean);
}

function fileStemFromBasename(basename: string): string {
  const normalized = basename.trim().toLowerCase();
  if (!normalized) return "";
  return normalized
    .replace(/\.(test|spec|story|stories)(?=\.)/g, "")
    .replace(/\.[^.]+$/, "");
}

function normalizedName(value: string | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

function normalizedSemanticSymbol(value: string | undefined): string {
  return normalizedName(value)
    .replace(/[`'"]/g, "")
    .replace(/\([^)]*\)$/, "")
    .replace(/^[./#]+/, "")
    .replace(/[^\w.-]+/g, "")
    .trim();
}

function isSemanticGenericLabel(value: string | undefined): boolean {
  const symbol = normalizedSemanticSymbol(value);
  if (!symbol) return false;
  if (SEMANTIC_GENERIC_LABELS.has(symbol)) return true;
  if (SEMANTIC_GENERIC_FILE_STEMS.has(symbol)) return true;
  if (/^(get|set|is|has|run|load|save|create|update|delete|handle)[_-]?[a-z0-9]{0,4}$/.test(symbol)) return true;
  return symbol.length <= 2;
}

function isSemanticScaffoldFilename(basename: string): boolean {
  const normalized = basename.trim().toLowerCase();
  if (!normalized) return false;
  const stem = fileStemFromBasename(normalized);
  return SEMANTIC_SCAFFOLD_FILENAMES.has(normalized) || SEMANTIC_SCAFFOLD_FILENAMES.has(stem);
}

function semanticNodeScaffoldScore(node: FullNode): number {
  const sourcePath = nodePath(node);
  const basename = pathBasename(sourcePath);
  const stem = fileStemFromBasename(basename);
  const parts = [
    ...pathParts(node.relative_path || node.source_file || ""),
    normalizedName(node.container),
    normalizedName(node.cluster),
  ].filter(Boolean);
  let score = 0;

  if (isSemanticScaffoldFilename(basename)) score += 0.55;
  if (SEMANTIC_GENERIC_FILE_STEMS.has(stem)) score += 0.22;
  if (isSemanticGenericLabel(node.label) || isSemanticGenericLabel(node.symbol)) score += 0.28;

  const scaffoldPartCount = parts.filter((part) => SEMANTIC_SCAFFOLD_PATH_PARTS.has(part)).length;
  if (scaffoldPartCount > 0) score += 0.16;
  if (scaffoldPartCount > 1) score += 0.08;

  if (node.importance_tier === "anchor" || node.importance_tier === "interface") score -= 0.14;
  else if (node.importance_tier === "important" || node.signal_tier === "important") score -= 0.08;

  return Math.min(1, Math.max(0, score));
}

function semanticDomainTerms(node: FullNode): Set<string> {
  const text = [
    node.label,
    node.symbol,
    node.purpose,
    node.relative_path,
    node.source_file,
  ].filter(Boolean).join(" ");
  const terms = text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .map((term) => term.trim())
    .filter((term) => (
      term.length >= 4
      && !SEMANTIC_DOMAIN_STOPWORDS.has(term)
      && !SEMANTIC_GENERIC_FILE_STEMS.has(term)
      && !SEMANTIC_GENERIC_LABELS.has(term)
      && !SEMANTIC_SCAFFOLD_PATH_PARTS.has(term)
    ));
  return new Set(terms);
}

function semanticNodeSpecificity(node: FullNode): number {
  const basename = pathBasename(nodePath(node));
  const stem = fileStemFromBasename(basename);
  const domainTerms = semanticDomainTerms(node);
  let score = Math.min(0.18, domainTerms.size * 0.03);

  if (stem && !SEMANTIC_GENERIC_FILE_STEMS.has(stem) && !isSemanticScaffoldFilename(basename)) {
    score += 0.06;
  }
  if (node.importance_tier === "anchor" || node.importance_tier === "interface") score += 0.08;
  else if (node.importance_tier === "important" || node.signal_tier === "important") score += 0.05;
  if (node.purpose && normalizedName(node.purpose).length > 24) score += 0.03;

  return Math.min(0.3, score);
}

function sharedSemanticDomainTerms(source: FullNode, target: FullNode): string[] {
  const sourceTerms = semanticDomainTerms(source);
  const targetTerms = semanticDomainTerms(target);
  return [...sourceTerms]
    .filter((term) => targetTerms.has(term))
    .sort((a, b) => a.localeCompare(b))
    .slice(0, 3);
}

function boundaryKey(a: string, b: string): string {
  return a < b ? `${a}\u0000${b}` : `${b}\u0000${a}`;
}

function nodeSignalWeight(node: FullNode | undefined): number {
  if (!node) return 0;
  if (node.importance_tier === "anchor") return 0.08;
  if (node.importance_tier === "interface") return 0.07;
  if (node.importance_tier === "important" || node.signal_tier === "important") return 0.05;
  if (node.signal_tier === "overview") return 0.04;
  return 0;
}

function semanticSimilarityBoost(similarity: number): number {
  if (!Number.isFinite(similarity)) return 0;
  return Math.min(0.22, Math.max(0, ((similarity - 0.78) / 0.2) * 0.22));
}

function uniqueSignals(signals: string[]): string[] {
  return [...new Set(signals.map((signal) => signal.trim()).filter(Boolean))].slice(0, 4);
}

function buildActionableSemanticEdges(
  edges: SemanticEdge[],
  nodeMap: Record<string, FullNode>,
  groupMap: Record<string, string>,
  physicalEdgeKeys: Set<string>,
  physicalGroupKeys: Set<string>,
  repoCount: number,
): ActionableSemanticEdge[] {
  const groupEdgeCounts = new globalThis.Map<string, number>();
  const groupSameNameCounts = new globalThis.Map<string, number>();

  for (const edge of edges) {
    const source = nodeMap[edge.source];
    const target = nodeMap[edge.target];
    const sourceGroup = groupMap[edge.source];
    const targetGroup = groupMap[edge.target];
    if (!source || !target || !sourceGroup || !targetGroup || sourceGroup === targetGroup) continue;
    const key = boundaryKey(sourceGroup, targetGroup);
    const sourceBase = pathBasename(nodePath(source));
    const targetBase = pathBasename(nodePath(target));
    const sameName = Boolean(sourceBase && sourceBase === targetBase);
    groupEdgeCounts.set(key, (groupEdgeCounts.get(key) ?? 0) + 1);
    if (sameName) groupSameNameCounts.set(key, (groupSameNameCounts.get(key) ?? 0) + 1);
  }

  const scored = edges.map((edge): ActionableSemanticEdge | null => {
    const source = nodeMap[edge.source];
    const target = nodeMap[edge.target];
    const sourceGroup = groupMap[edge.source];
    const targetGroup = groupMap[edge.target];
    if (!source || !target || !sourceGroup || !targetGroup) return null;

    const sourcePath = nodePath(source);
    const targetPath = nodePath(target);
    const sameFile = Boolean(sourcePath && targetPath && sourcePath === targetPath);
    const sourceBase = pathBasename(sourcePath);
    const targetBase = pathBasename(targetPath);
    const sourceStem = fileStemFromBasename(sourceBase);
    const targetStem = fileStemFromBasename(targetBase);
    const sameName = Boolean(sourceBase && sourceBase === targetBase);
    const sourceLabel = normalizedName(source.label);
    const targetLabel = normalizedName(target.label);
    const sameLabel = Boolean(sourceLabel && sourceLabel === targetLabel);
    const sourceRepo = fullNodeRepo(source);
    const targetRepo = fullNodeRepo(target);
    const crossRepo = Boolean(sourceRepo && targetRepo && sourceRepo !== targetRepo);
    const crossGroup = sourceGroup !== targetGroup;
    const pairKey = boundaryKey(sourceGroup, targetGroup);
    const pairEdgeCount = groupEdgeCounts.get(pairKey) ?? 1;
    const pairSameNameCount = groupSameNameCounts.get(pairKey) ?? 0;
    const directPhysicalLink = physicalEdgeKeys.has(semanticEdgeKey(edge.source, edge.target));
    const groupPhysicalLink = physicalGroupKeys.has(pairKey);
    const sourceScaffoldScore = semanticNodeScaffoldScore(source);
    const targetScaffoldScore = semanticNodeScaffoldScore(target);
    const scaffoldPairScore = sourceScaffoldScore + targetScaffoldScore;
    const scaffoldPair = scaffoldPairScore >= 0.9;
    const sameScaffoldName = Boolean(
      sameName
        && (
          isSemanticScaffoldFilename(sourceBase)
          || isSemanticScaffoldFilename(targetBase)
          || SEMANTIC_GENERIC_FILE_STEMS.has(sourceStem)
          || SEMANTIC_GENERIC_FILE_STEMS.has(targetStem)
        ),
    );
    const sourceGenericLabel = isSemanticGenericLabel(source.label) || isSemanticGenericLabel(source.symbol);
    const targetGenericLabel = isSemanticGenericLabel(target.label) || isSemanticGenericLabel(target.symbol);
    const genericEndpoint = sourceGenericLabel || targetGenericLabel;
    const genericLabelPair = Boolean(
      sameLabel
        && (
          sourceGenericLabel
          || targetGenericLabel
        ),
    );
    const domainSameName = Boolean(sameName && !sameScaffoldName && !sameFile);
    const sharedDomainTerms = sharedSemanticDomainTerms(source, target);
    const signalWeight = nodeSignalWeight(source) + nodeSignalWeight(target);
    const importantSemanticEndpoint = Boolean(
      source.importance_tier === "anchor"
        || source.importance_tier === "interface"
        || source.importance_tier === "important"
        || source.signal_tier === "important"
        || target.importance_tier === "anchor"
        || target.importance_tier === "interface"
        || target.importance_tier === "important"
        || target.signal_tier === "important"
        || signalWeight >= 0.1
    );
    const sourceSpecificity = semanticNodeSpecificity(source);
    const targetSpecificity = semanticNodeSpecificity(target);
    const specificEndpointPair = sourceSpecificity >= 0.12 && targetSpecificity >= 0.12;
    const domainSameLabel = Boolean(sameLabel && !genericLabelPair && !sameFile);
    const usefulSharedTerms = Boolean(sharedDomainTerms.length > 0 && !genericEndpoint);
    const hasDomainSignal = Boolean(
      domainSameName
        || domainSameLabel
        || usefulSharedTerms
    );
    const strongNonScaffoldSimilarity = Boolean(
      edge.similarity >= 0.94
        && !scaffoldPair
        && !sameScaffoldName
        && !genericEndpoint
        && specificEndpointPair
    );

    const decisionSignals: string[] = [];
    let score = 0.08;

    if (crossRepo) {
      score += 0.3;
      decisionSignals.push("cross-repo");
    } else if (crossGroup) {
      score += 0.24;
      decisionSignals.push(repoCount > 1 ? "cross-project" : "cross-folder");
    } else {
      score -= 0.35;
    }

    score += semanticSimilarityBoost(edge.similarity);
    if (edge.similarity >= 0.92) decisionSignals.push("very high similarity");
    else if (edge.similarity >= 0.86) decisionSignals.push("high similarity");

    if (usefulSharedTerms && !scaffoldPair) {
      score += Math.min(0.1, sharedDomainTerms.length * 0.04);
      decisionSignals.push(`shared term: ${sharedDomainTerms.slice(0, 2).join(", ")}`);
    }

    if (domainSameName) {
      score += 0.22;
      decisionSignals.push("same filename");
    } else if (sameScaffoldName) {
      score -= 0.1;
      decisionSignals.push("shared scaffolding");
    } else if (domainSameLabel) {
      score += 0.12;
      decisionSignals.push("same label");
    } else if (genericLabelPair) {
      score -= 0.08;
      decisionSignals.push("generic label");
    }

    if (genericEndpoint && !domainSameName && !domainSameLabel) {
      score -= 0.1;
      decisionSignals.push("generic symbol");
    }

    const densityBoost = Math.min(0.16, (Math.log1p(pairEdgeCount) / Math.log1p(30)) * 0.16);
    if (hasDomainSignal && !scaffoldPair) {
      score += densityBoost;
      if (pairEdgeCount >= 4) decisionSignals.push(`${pairEdgeCount} related links`);
    } else if (pairEdgeCount >= 4) {
      score += Math.min(0.03, densityBoost * 0.25);
    }
    if (pairSameNameCount >= 2 && domainSameName && !scaffoldPair) {
      score += 0.08;
      decisionSignals.push(`${pairSameNameCount} same-name pairs`);
    }

    score += signalWeight;
    if (importantSemanticEndpoint) decisionSignals.push("important nodes");

    if (scaffoldPair) {
      score -= Math.min(0.42, 0.2 + scaffoldPairScore * 0.12);
      decisionSignals.push("shared scaffolding");
    } else if (scaffoldPairScore >= 0.45) {
      score -= Math.min(0.18, scaffoldPairScore * 0.08);
    }

    if (crossGroup && !directPhysicalLink && !groupPhysicalLink) {
      if (hasDomainSignal && !scaffoldPair) {
        score += 0.11;
        decisionSignals.push("missing physical bridge");
      } else if (strongNonScaffoldSimilarity) {
        score += 0.04;
      }
    } else if (crossGroup && !directPhysicalLink && groupPhysicalLink) {
      if (hasDomainSignal && !scaffoldPair) {
        score += 0.04;
        decisionSignals.push("boundary already linked");
      }
    } else if (directPhysicalLink) {
      score -= 0.08;
    }

    if (sameFile) {
      score -= 0.45;
      decisionSignals.push("same source file");
    }

    const boundedScore = Math.min(0.99, Math.max(0, score));
    const clearsPragmaticGate = hasDomainSignal || strongNonScaffoldSimilarity;
    let insightKind: SemanticInsightKind = "low_value";
    if (
      boundedScore >= SEMANTIC_ACTIONABLE_EDGE_MIN_SCORE
      && crossGroup
      && !sameFile
      && clearsPragmaticGate
    ) {
      if (domainSameName && edge.similarity >= 0.84) {
        insightKind = "waste_duplicate";
      } else if (edge.similarity >= 0.93 && !scaffoldPair) {
        insightKind = "drift_risk";
      } else if (!groupPhysicalLink && hasDomainSignal) {
        insightKind = "gap_missing_bridge";
      } else if (crossRepo && !scaffoldPair) {
        insightKind = "cross_app_similarity";
      } else if (pairEdgeCount >= 4 && hasDomainSignal) {
        insightKind = "shared_pattern";
      } else {
        insightKind = "intentional_reference";
      }
    }

    return {
      ...edge,
      actionabilityScore: boundedScore,
      insightKind,
      decisionSignals: uniqueSignals(decisionSignals),
    };
  });

  return scored
    .filter((edge): edge is ActionableSemanticEdge => (
      Boolean(edge)
        && edge!.insightKind !== "low_value"
        && edge!.actionabilityScore >= SEMANTIC_ACTIONABLE_EDGE_MIN_SCORE
    ))
    .sort((a, b) => {
      if (b.actionabilityScore !== a.actionabilityScore) return b.actionabilityScore - a.actionabilityScore;
      return b.similarity - a.similarity;
    });
}

function visibleFullNodes(full: FullGraph, filter: Filter, selectedClusters: Set<string> | null = null): FullNode[] {
  return full.nodes
    .filter((n) => filter === "all" || n.type === filter)
    .filter((n) => selectedClusters === null || selectedClusters.has(n.cluster));
}

function visibleFullEdgeCount(full: FullGraph, visibleIds: Set<string>): number {
  const seen = new Set<string>();
  let count = 0;
  for (const edge of full.edges) {
    if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) continue;
    const key = `${edge.source}::${edge.target}`;
    if (seen.has(key)) continue;
    seen.add(key);
    count += 1;
  }
  return count;
}

function shouldUseFastFullLayout(full: FullGraph, filter: Filter, selectedClusters: Set<string> | null = null): boolean {
  const nodes = visibleFullNodes(full, filter, selectedClusters);
  const visibleIds = new Set(nodes.map((node) => node.id));
  const repoCount = new Set(nodes.map(fullNodeRepo)).size;
  return (
    nodes.length >= FULL_FAST_LAYOUT_NODE_THRESHOLD
    || (repoCount > 1 && nodes.length >= FULL_FAST_LAYOUT_MULTI_REPO_THRESHOLD)
    || visibleFullEdgeCount(full, visibleIds) >= FULL_FAST_LAYOUT_EDGE_THRESHOLD
  );
}

function stableLayoutHash(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = Math.imul(31, hash) + value.charCodeAt(index) | 0;
  }
  return Math.abs(hash);
}

function nodeCloudRadius(count: number): number {
  if (count <= 1) return 0;
  return Math.max(34, Math.sqrt(count) * 18);
}

type FullPresetLayout = {
  positions: Record<string, { x: number; y: number }>;
  repoLabels: Array<{ id: string; label: string; position: { x: number; y: number } }>;
  containerLabels: Array<{ id: string; label: string; position: { x: number; y: number } }>;
};

function placeNodeCloud(
  nodes: FullNode[],
  centerX: number,
  centerY: number,
  seed: string,
  positions: Record<string, { x: number; y: number }>,
) {
  if (nodes.length === 1) {
    positions[nodes[0].id] = { x: centerX, y: centerY };
    return;
  }

  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  const angleOffset = (stableLayoutHash(seed) % 628) / 100;
  nodes.forEach((node, index) => {
    const radius = 18 * Math.sqrt(index + 1);
    const angle = index * goldenAngle + angleOffset;
    positions[node.id] = {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    };
  });
}

function buildFullPresetLayout(nodes: FullNode[]): FullPresetLayout {
  const repos = new globalThis.Map<string, FullNode[]>();
  for (const node of nodes) {
    const key = fullNodeRepo(node);
    const bucket = repos.get(key);
    if (bucket) bucket.push(node);
    else repos.set(key, [node]);
  }

  const repoLayouts = [...repos.entries()]
    .sort(([repoA, nodesA], [repoB, nodesB]) => nodesB.length - nodesA.length || repoA.localeCompare(repoB))
    .map(([repo, repoNodes]) => {
      const localPositions: Record<string, { x: number; y: number }> = {};
      const containers = new globalThis.Map<string, FullNode[]>();
      for (const node of repoNodes) {
        const key = fullNodeContainer(node);
        const bucket = containers.get(key);
        if (bucket) bucket.push(node);
        else containers.set(key, [node]);
      }

      const groups = [...containers.entries()]
        .sort(([containerA, nodesA], [containerB, nodesB]) => nodesB.length - nodesA.length || containerA.localeCompare(containerB))
        .map(([container, groupNodes]) => ({
          container,
          nodes: [...groupNodes].sort((a, b) => (
            (a.relative_path || a.source_file || a.id).localeCompare(b.relative_path || b.source_file || b.id)
          )),
          radius: nodeCloudRadius(groupNodes.length),
        }));

      const goldenAngle = Math.PI * (3 - Math.sqrt(5));
      const largestRadius = groups[0]?.radius ?? 0;
      const containerLabels: FullPresetLayout["containerLabels"] = [];
      const shouldLabelContainers = groups.length <= FULL_CONTAINER_LABEL_LIMIT;
      groups.forEach((group, index) => {
        const radius = index === 0
          ? 0
          : Math.sqrt(index) * Math.max(180, largestRadius * 0.75 + group.radius + 110);
        const angle = index === 0 ? 0 : index * goldenAngle + (stableLayoutHash(`${repo}:${group.container}`) % 314) / 100;
        const centerX = Math.cos(angle) * radius;
        const centerY = Math.sin(angle) * radius;
        placeNodeCloud(group.nodes, centerX, centerY, `${repo}:${group.container}`, localPositions);
        if (shouldLabelContainers) {
          containerLabels.push({
            id: `container_label_${stableLayoutHash(`${repo}:${group.container}`)}_${index}`,
            label: group.container,
            position: {
              x: centerX,
              y: centerY - group.radius - 34,
            },
          });
        }
      });

      const coords = Object.values(localPositions);
      const minX = Math.min(...coords.map((position) => position.x));
      const maxX = Math.max(...coords.map((position) => position.x));
      const minY = Math.min(...coords.map((position) => position.y));
      const maxY = Math.max(...coords.map((position) => position.y));
      const padding = 140;
      return {
        repo,
        positions: localPositions,
        containerLabels,
        bounds: {
          minX: minX - padding,
          maxX: maxX + padding,
          minY: minY - padding,
          maxY: maxY + padding,
        },
      };
    });

  const positions: Record<string, { x: number; y: number }> = {};
  const repoLabels: FullPresetLayout["repoLabels"] = [];
  const containerLabels: FullPresetLayout["containerLabels"] = [];
  const repoGap = 520;
  const repoWidths = repoLayouts.map((layout) => layout.bounds.maxX - layout.bounds.minX);
  const totalWidth = repoWidths.reduce((sum, width) => sum + width, 0) + repoGap * Math.max(0, repoLayouts.length - 1);
  let cursorX = -totalWidth / 2;

  repoLayouts.forEach((layout, index) => {
    const width = repoWidths[index] ?? 0;
    const offsetX = cursorX - layout.bounds.minX;
    const offsetY = -((layout.bounds.minY + layout.bounds.maxY) / 2);

    for (const [nodeId, position] of Object.entries(layout.positions)) {
      positions[nodeId] = {
        x: position.x + offsetX,
        y: position.y + offsetY,
      };
    }
    repoLabels.push({
      id: `repo_label_${index}_${stableLayoutHash(layout.repo)}`,
      label: layout.repo,
      position: {
        x: (layout.bounds.minX + layout.bounds.maxX) / 2 + offsetX,
        y: layout.bounds.minY + offsetY - 46,
      },
    });
    for (const containerLabel of layout.containerLabels) {
      containerLabels.push({
        id: `${containerLabel.id}_${index}`,
        label: containerLabel.label,
        position: {
          x: containerLabel.position.x + offsetX,
          y: containerLabel.position.y + offsetY,
        },
      });
    }

    cursorX += width + repoGap;
  });

  return { positions, repoLabels, containerLabels };
}

function buildFullElements(
  full: FullGraph,
  filter: Filter,
  selectedClusters: Set<string> | null = null,
  presetLayout: FullPresetLayout | null = null,
) {
  const visibleNodes = visibleFullNodes(full, filter, selectedClusters);
  const visibleIds = new Set(visibleNodes.map((n) => n.id));
  const positions = presetLayout?.positions ?? {};
  const repoCount = new Set(visibleNodes.map(fullNodeRepo)).size;

  const nodes = visibleNodes.map((n) => ({
    data: {
      id: n.id,
      label: n.label,
      type: n.type,
      cluster: n.cluster,
      source_file: n.source_file,
      color: clusterColor(fullNodeGroup(n, repoCount)),
      decision: n.decision_overlay?.decision_classification || n.decision_classification || "",
      decision_count: n.decision_overlay?.decision_count ?? n.decision_count ?? 0,
      recommendation_count: n.decision_overlay?.recommendation_count ?? n.recommendation_count ?? 0,
      queued_action_count: n.decision_overlay?.queued_action_count ?? n.queued_action_count ?? 0,
    },
    ...(positions[n.id] ? { position: positions[n.id] } : {}),
  }));
  const repoLabelNodes = (presetLayout?.repoLabels ?? []).map((repoLabel) => ({
    data: {
      id: repoLabel.id,
      label: repoLabel.label,
      color: "#6b8cff",
    },
    classes: "repo-label",
    position: repoLabel.position,
    selectable: false,
    grabbable: false,
    locked: true,
  }));
  const containerLabelNodes = (presetLayout?.containerLabels ?? []).map((containerLabel) => ({
    data: {
      id: containerLabel.id,
      label: containerLabel.label,
      color: "#6b8cff",
    },
    classes: "container-label",
    position: containerLabel.position,
    selectable: false,
    grabbable: false,
    locked: true,
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

  return [...repoLabelNodes, ...containerLabelNodes, ...nodes, ...edges];
}

function applyStructuralEdgeVisibility(cy: Core, showStructural: boolean, emphasizeSemantic = false) {
  cy.batch(() => {
    cy.edges().forEach((edge: any) => {
      if (edge.hasClass("semantic-edge")) {
        edge.removeClass("struct-hidden");
        edge.removeClass("struct-muted");
        return;
      }
      if (showStructural) {
        edge.removeClass("struct-hidden");
        if (emphasizeSemantic) edge.addClass("struct-muted");
        else edge.removeClass("struct-muted");
      } else {
        edge.addClass("struct-hidden");
        edge.removeClass("struct-muted");
      }
    });
  });
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
    selector: "node.repo-label",
    style: {
      width: 1,
      height: 1,
      "background-opacity": 0,
      "border-width": 0,
      label: "data(label)",
      color: "#c6d4f6",
      "font-family": '"JetBrains Mono", ui-monospace, monospace',
      "font-size": 24,
      "font-weight": 700,
      "min-zoomed-font-size": 0,
      "text-halign": "center",
      "text-valign": "center",
      "text-outline-color": "#070a12",
      "text-outline-opacity": 0.94,
      "text-outline-width": 4,
      "text-transform": "none",
      events: "no",
      opacity: 0.92,
    },
  },
  {
    selector: "node.repo-label:hover",
    style: {
      width: 1,
      height: 1,
      "border-width": 0,
    },
  },
  {
    selector: 'node[decision="invest"]',
    style: {
      "border-color": "#4ade80",
      "border-width": 2.5,
      "shadow-blur": 16,
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
      "border-width": 2.5,
      "shadow-blur": 16,
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
      "border-width": 2.5,
      "shadow-blur": 14,
      "shadow-color": "#6b8cff",
      "shadow-opacity": 0.6,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
    },
  },
  {
    selector: 'node[decision="archive"]',
    style: {
      "border-color": "#9ca3af",
      "border-width": 2,
      "shadow-blur": 8,
      "shadow-color": "#9ca3af",
      "shadow-opacity": 0.35,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
      opacity: 0.62,
    },
  },
  {
    selector: 'node[decision="paused"]',
    style: {
      "border-color": "#f97316",
      "border-width": 2.5,
      "shadow-blur": 14,
      "shadow-color": "#f97316",
      "shadow-opacity": 0.55,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
    },
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
    selector: "node.path-source",
    style: {
      width: 15,
      height: 15,
      "border-color": "#f5a623",
      "border-width": 3,
      "shadow-blur": 22,
      "shadow-color": "#f5a623",
      "shadow-opacity": 0.9,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
      color: "#f5d280",
    },
  },
  {
    selector: "node.path-target",
    style: {
      width: 15,
      height: 15,
      "border-color": "#4ade80",
      "border-width": 3,
      "shadow-blur": 22,
      "shadow-color": "#4ade80",
      "shadow-opacity": 0.9,
      "shadow-offset-x": 0,
      "shadow-offset-y": 0,
      color: "#90f0b8",
    },
  },
  {
    selector: "node.container-label",
    style: {
      width: 1,
      height: 1,
      "background-opacity": 0,
      "border-width": 0,
      label: "data(label)",
      color: "#c6d4f6",
      "font-family": '"JetBrains Mono", ui-monospace, monospace',
      "font-size": 14,
      "font-weight": 700,
      "min-zoomed-font-size": 0,
      "text-halign": "center",
      "text-valign": "center",
      "text-outline-color": "#070a12",
      "text-outline-width": 2,
      "text-outline-opacity": 0.94,
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
      "line-color": "#78a7ff",
      opacity: 0.84,
    },
  },
  {
    selector: "edge.highlighted",
    style: { "line-color": "#c7d7ff", opacity: 1, width: 3, "z-index": 20 },
  },
  {
    selector: "edge.path-edge",
    style: {
      "line-color": "#f5a623",
      opacity: 1,
      width: 3,
    },
  },
  {
    selector: "edge.faded",
    style: { opacity: 0.03 },
  },
  {
    selector: "edge.struct-muted",
    style: { opacity: 0.16 },
  },
  {
    selector: "edge.semantic-edge",
    style: {
      "curve-style": "bezier",
      "line-color": "#39ff88",
      "line-style": "solid",
      "z-index": 30,
      width: 3,
      opacity: 0.96,
    },
  },
  {
    selector: "edge.semantic-edge.highlighted",
    style: {
      "line-color": "#69e6b1",
      "line-style": "solid",
      opacity: 1,
      width: 4,
    },
  },
  {
    selector: "edge.semantic-edge.path-edge",
    style: {
      "line-color": "#69e6b1",
      "line-style": "solid",
      opacity: 1,
      width: 3.5,
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
  const scopeProfileRef = useRef<WorkspaceScopeProfile | null>(null);
  const renderCycleRef = useRef(0);
  const semanticPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { addToast } = useToast();

  // Refs for cy event handlers — avoids stale closures over React state
  const pathModeRef = useRef(false);
  const pathSourceRef = useRef<string | null>(null);
  const summaryRef = useRef<GraphSummary | null>(null);

  const [viewMode, setViewMode] = useState<ViewMode>("summary");
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [fullGraph, setFullGraph] = useState<FullGraph | null>(null);
  const [fullLoading, setFullLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mapRendering, setMapRendering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SummaryNode | null>(null);
  const [selectedFull, setSelectedFull] = useState<FullNode | null>(null);
  const [selectedSemanticLink, setSelectedSemanticLink] = useState<SelectedSemanticLink | null>(null);
  const [breadcrumb, setBreadcrumb] = useState<string[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [mapMode, setMapMode] = useState<MapMode>("explore");
  const [pathMode, setPathMode] = useState(false);
  const [pathSource, setPathSource] = useState<string | null>(null);
  const [pathNoRoute, setPathNoRoute] = useState(false);
  // target_id → classification for active decisions
  const [decisions, setDecisions] = useState<Record<string, string>>({});
  const [decisionRecords, setDecisionRecords] = useState<Record<string, { id: string; classification: string }>>({});
  const [savingGapDecision, setSavingGapDecision] = useState<DecisionClassification | null>(null);
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
  const [knowledgeOnly, setKnowledgeOnly] = useState(false);
  // edge layer toggles
  const [showStructural, setShowStructural] = useState(true);
  // semantic similarity overlay
  const [showSemantic, setShowSemantic] = useState(false);
  const [semanticEdges, setSemanticEdges] = useState<SemanticEdge[]>([]);
  const [semanticMeta, setSemanticMeta] = useState<SemanticEdgeMeta | null>(null);
  const [semanticStatus, setSemanticStatus] = useState<SemanticPassStatus | null>(null);
  const [runningSemantic, setRunningSemantic] = useState(false);
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
  const [canGenerateScopeMap, setCanGenerateScopeMap] = useState(false);
  const [generatingScopeMap, setGeneratingScopeMap] = useState(false);

  const showSemanticRef = useRef(false);
  const visibleSemanticEdgesRef = useRef<ActionableSemanticEdge[]>([]);
  const showStructuralRef = useRef(true);
  const overlapNodeGroupMapRef = useRef<Record<string, string>>({});

  const fullNodeMap = useMemo(
    () => Object.fromEntries(fullGraph?.nodes.map((n) => [n.id, n]) ?? []) as Record<string, FullNode>,
    [fullGraph],
  );
  const nodeRepoMap = useMemo(
    () => Object.fromEntries(fullGraph?.nodes.map((n) => [n.id, fullNodeRepo(n)]) ?? []) as Record<string, string>,
    [fullGraph],
  );
  const visibleFullNodeIds = useMemo(
    () => new Set(fullGraph ? visibleFullNodes(fullGraph, filter, selectedClusters).map((n) => n.id) : []),
    [fullGraph, filter, selectedClusters],
  );
  const visibleRepoCount = useMemo(
    () => new Set([...visibleFullNodeIds].map((nodeId) => nodeRepoMap[nodeId]).filter(Boolean)).size,
    [nodeRepoMap, visibleFullNodeIds],
  );
  const overlapNodeGroupMap = useMemo(
    () => Object.fromEntries(
      fullGraph?.nodes.map((n) => [
        n.id,
        fullNodeGroup(n, visibleRepoCount),
      ]) ?? [],
    ) as Record<string, string>,
    [fullGraph, visibleRepoCount],
  );
  const physicalEdgeKeys = useMemo(() => {
    if (!fullGraph) return new Set<string>();
    return new Set(fullGraph.edges.map((edge) => semanticEdgeKey(edge.source, edge.target)));
  }, [fullGraph]);
  const physicalGroupKeys = useMemo(() => {
    if (!fullGraph) return new Set<string>();
    const keys = new Set<string>();
    for (const edge of fullGraph.edges) {
      const sourceGroup = overlapNodeGroupMap[edge.source];
      const targetGroup = overlapNodeGroupMap[edge.target];
      if (!sourceGroup || !targetGroup || sourceGroup === targetGroup) continue;
      keys.add(boundaryKey(sourceGroup, targetGroup));
    }
    return keys;
  }, [fullGraph, overlapNodeGroupMap]);

  // Semantic edges that connect nodes currently available in Evidence view.
  const visibleSemanticEdges = useMemo(() => {
    if (!fullGraph) return [];
    return semanticEdges.filter((e) => visibleFullNodeIds.has(e.source) && visibleFullNodeIds.has(e.target));
  }, [semanticEdges, visibleFullNodeIds, fullGraph]);

  // Cross-cluster semantic edges drive Overlap; intra-cluster semantic edges still matter for Trace.
  const crossSemanticEdges = useMemo(() => (
    visibleSemanticEdges.filter((e) => {
      const sc = overlapNodeGroupMap[e.source];
      const tc = overlapNodeGroupMap[e.target];
      return sc && tc && sc !== tc;
    })
  ), [visibleSemanticEdges, overlapNodeGroupMap]);
  const crossRepoSemanticEdges = useMemo(() => (
    visibleSemanticEdges.filter((e) => {
      const sourceRepo = nodeRepoMap[e.source];
      const targetRepo = nodeRepoMap[e.target];
      return sourceRepo && targetRepo && sourceRepo !== targetRepo;
    })
  ), [visibleSemanticEdges, nodeRepoMap]);

  const semanticCandidateEdges = useMemo(
    () => (visibleRepoCount > 1 ? crossRepoSemanticEdges : crossSemanticEdges),
    [crossRepoSemanticEdges, crossSemanticEdges, visibleRepoCount],
  );
  const actionableSemanticEdges = useMemo(
    () => buildActionableSemanticEdges(
      semanticCandidateEdges,
      fullNodeMap,
      overlapNodeGroupMap,
      physicalEdgeKeys,
      physicalGroupKeys,
      visibleRepoCount,
    ),
    [
      fullNodeMap,
      overlapNodeGroupMap,
      physicalEdgeKeys,
      physicalGroupKeys,
      semanticCandidateEdges,
      visibleRepoCount,
    ],
  );
  const semanticEdgesForDisplay = useMemo(
    () => buildSemanticBackbone(actionableSemanticEdges),
    [actionableSemanticEdges],
  );
  const overlapSemanticEdges = useMemo(
    () => actionableSemanticEdges,
    [actionableSemanticEdges],
  );

  // Overlap analysis groups — ranked cross-cluster pairs by connection count
  const fullOverlapGroups = useMemo((): OverlapGroup[] => {
    if (!fullGraph || !overlapSemanticEdges.length) return [];
    const basename = (f: string) => f.split("/").pop() ?? f;
    const groups: Record<string, { clusterA: string; clusterB: string; edges: OverlapPair[] }> = {};
    for (const edge of overlapSemanticEdges) {
      const sc = overlapNodeGroupMap[edge.source];
      const tc = overlapNodeGroupMap[edge.target];
      if (!sc || !tc || sc === tc) continue;
      const ca = sc <= tc ? sc : tc;
      const cb = sc <= tc ? tc : sc;
      const key = `${ca}___${cb}`;
      if (!groups[key]) groups[key] = { clusterA: ca, clusterB: cb, edges: [] };
      const na = fullNodeMap[edge.source];
      const nb = fullNodeMap[edge.target];
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
        actionabilityScore: edge.actionabilityScore,
        insightKind: edge.insightKind,
        decisionSignals: edge.decisionSignals,
      });
    }
    return Object.values(groups)
      .map((g) => {
        const avg = g.edges.reduce((s, e) => s + e.similarity, 0) / g.edges.length;
        const maxSim = Math.max(...g.edges.map((e) => e.similarity));
        const sameNameCount = g.edges.filter((e) => e.sameName).length;
        const actionabilityScore = Math.max(...g.edges.map((e) => e.actionabilityScore ?? 0));
        const decisionSignals = uniqueSignals(g.edges.flatMap((e) => e.decisionSignals ?? []));
        // sort: same-name first, then by similarity desc
        const sorted = [...g.edges].sort((a, b) => {
          if (a.sameName !== b.sameName) return a.sameName ? -1 : 1;
          if ((b.actionabilityScore ?? 0) !== (a.actionabilityScore ?? 0)) {
            return (b.actionabilityScore ?? 0) - (a.actionabilityScore ?? 0);
          }
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
          actionabilityScore,
          decisionSignals,
        };
      })
      // sort: groups with stronger pragmatic signal first, then same-name and density
      .sort((a, b) => {
        if ((b.actionabilityScore ?? 0) !== (a.actionabilityScore ?? 0)) {
          return (b.actionabilityScore ?? 0) - (a.actionabilityScore ?? 0);
        }
        if ((a.sameNameCount > 0) !== (b.sameNameCount > 0)) return a.sameNameCount > 0 ? -1 : 1;
        if (b.edgeCount !== a.edgeCount) return b.edgeCount - a.edgeCount;
        return b.maxSimilarity - a.maxSimilarity;
      });
  }, [overlapSemanticEdges, overlapNodeGroupMap, fullGraph, fullNodeMap]);

  const summaryOverlapGroupsData = useMemo(
    () => overlapSummaryGroups(summaryOverlap),
    [summaryOverlap],
  );
  const usingSummaryOverlap = viewMode !== "full";
  const overlapGroups = usingSummaryOverlap ? summaryOverlapGroupsData : fullOverlapGroups;
  const storedSemanticEdgeCount = semanticMeta?.edge_count ?? semanticEdges.length;
  const legacySemanticEdgeCount = semanticMeta?.legacy_edge_count ?? 0;
  const semanticCacheStale = Boolean(semanticMeta?.graph_stale);
  const semanticPolicyStale = Boolean(semanticMeta?.edge_policy_stale);
  const semanticAnalysisMissing = Boolean(
    fullGraph
      && semanticMeta
      && !semanticMeta.created_at
      && !semanticCacheStale
      && storedSemanticEdgeCount === 0,
  );
  const outOfScopeSemanticEdgeCount = fullGraph
    ? Math.max(0, storedSemanticEdgeCount - visibleSemanticEdges.length)
    : 0;
  const semanticCacheMostlyOutOfScope = Boolean(
    fullGraph
      && storedSemanticEdgeCount > 0
      && outOfScopeSemanticEdgeCount > Math.max(100, visibleSemanticEdges.length * 20),
  );
  const overlapConnectionCount = usingSummaryOverlap
    ? summaryOverlap?.total_cross_edges ?? 0
    : overlapSemanticEdges.length;

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
  useEffect(() => { visibleSemanticEdgesRef.current = semanticEdgesForDisplay; }, [semanticEdgesForDisplay]);
  useEffect(() => { showStructuralRef.current = showStructural; }, [showStructural]);
  useEffect(() => { overlapNodeGroupMapRef.current = overlapNodeGroupMap; }, [overlapNodeGroupMap]); // eslint-disable-line

  function beginMapRender() {
    renderCycleRef.current += 1;
    setMapRendering(true);
    return renderCycleRef.current;
  }

  function finishMapRender(renderCycle: number) {
    const clearRendering = () => {
      if (renderCycleRef.current === renderCycle) {
        setMapRendering(false);
      }
    };
    requestAnimationFrame(() => {
      requestAnimationFrame(clearRendering);
    });
    window.setTimeout(clearRendering, 250);
  }

  function cancelMapRender(renderCycle: number) {
    if (renderCycleRef.current === renderCycle) {
      setMapRendering(false);
    }
  }

  useEffect(() => {
    if (!mapRendering || loading || fullLoading) return;
    const watchdog = window.setTimeout(() => {
      const cy = cyRef.current;
      const destroyed = Boolean((cy as any)?.destroyed?.());
      if (error || !cy || destroyed || cy.elements().length > 0) {
        setMapRendering(false);
      }
    }, 12000);
    return () => window.clearTimeout(watchdog);
  }, [error, fullGraph, fullLoading, loading, mapRendering, summary, viewMode]);

  function normalizeLookup(value: string) {
    return value.trim().toLowerCase().replace(/\s+/g, " ");
  }

  function handlePathNodeTap(cy: Core, node: any, nodeId: string): boolean {
    if (!pathModeRef.current) return false;
    const src = pathSourceRef.current;

    if (!src) {
      cy.nodes().removeClass("path-source path-target");
      cy.elements().removeClass("path-edge faded");
      node.addClass("path-source");
      setPathSource(nodeId);
      setPathNoRoute(false);
      return true;
    }

    if (src === nodeId) return true;

    const source = cy.getElementById(src);
    try {
      const traversalElements = cy.elements().filter((ele: any) => (
        ele.isNode() || !ele.hasClass("struct-hidden")
      ));
      const dijk = (traversalElements as any).dijkstra({
        root: source,
        weight: (edge: any) => {
          if (!edge.hasClass("semantic-edge")) return 1;
          const similarity = Number(edge.data("similarity") ?? 0);
          return 0.75 + Math.max(0, 1 - similarity);
        },
      });
      const path = dijk.pathTo(node);

      if (path && path.edges().length > 0) {
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
    return true;
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

  function semanticEdgeDataFromElement(edgeElement: any): ActionableSemanticEdge | null {
    const source = String(edgeElement.data("source") ?? "");
    const target = String(edgeElement.data("target") ?? "");
    if (!source || !target) return null;
    const rawKind = String(edgeElement.data("insight_kind") ?? "unknown") as SemanticInsightKind;
    const signals = edgeElement.data("decision_signals");
    return {
      source,
      target,
      similarity: Number(edgeElement.data("similarity") ?? 0),
      actionabilityScore: Number(edgeElement.data("actionability") ?? 0),
      insightKind: SEMANTIC_INSIGHT_LABELS[rawKind] ? rawKind : "unknown",
      decisionSignals: Array.isArray(signals)
        ? signals.map((signal) => String(signal).trim()).filter(Boolean)
        : String(signals ?? "").split(",").map((signal) => signal.trim()).filter(Boolean),
    };
  }

  function clearSemanticLinkSelection(clearContext = true) {
    const cy = cyRef.current;
    if (cy) {
      cy.edges(".semantic-edge").removeClass("highlighted");
      cy.nodes().removeClass("selected");
    }
    setSelectedSemanticLink(null);
    if (clearContext) onActiveContextChange?.(null);
  }

  function selectSemanticEdgeElement(edgeElement: any) {
    const edge = semanticEdgeDataFromElement(edgeElement);
    if (!edge) return;
    const sourceNode = fullNodeMap[edge.source] ?? null;
    const targetNode = fullNodeMap[edge.target] ?? null;
    const sourceGroup = overlapNodeGroupMap[edge.source] ?? sourceNode?.cluster ?? UNKNOWN_VALUE;
    const targetGroup = overlapNodeGroupMap[edge.target] ?? targetNode?.cluster ?? UNKNOWN_VALUE;
    const cy = cyRef.current;
    if (cy) {
      cy.batch(() => {
        cy.nodes().removeClass("selected");
        cy.edges().removeClass("highlighted");
        edgeElement.addClass("highlighted");
        edgeElement.connectedNodes().addClass("selected");
      });
    }
    setSelectedSemanticLink({ edge, sourceNode, targetNode, sourceGroup, targetGroup });
    setSelectedFull(null);
    setSelected(null);
    setShowOverlap(false);
    setHighlightedPair(null);
    onActiveContextChange?.({
      kind: "overlap-pair",
      source: "map",
      clusterA: sourceGroup,
      clusterB: targetGroup,
      sourceNodeId: edge.source,
      targetNodeId: edge.target,
      labelA: sourceNode?.label ?? edge.source,
      labelB: targetNode?.label ?? edge.target,
      similarity: edge.similarity,
    });
  }

  // Fetch decisions (non-critical — silently ignored if backend down)
  useEffect(() => {
    apiFetch(`/decisions`)
      .then((r) => (r.ok ? r.json() : []))
      .then((list: Array<{ id: string; target_id: string; classification: string; status: string }>) => {
        const map: Record<string, string> = {};
        const records: Record<string, { id: string; classification: string }> = {};
        list.filter((d) => d.status === "active").forEach((d) => {
          map[d.target_id] = d.classification;
          records[d.target_id] = { id: d.id, classification: d.classification };
        });
        setDecisions(map);
        setDecisionRecords(records);
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

  const loadSemanticEdges = useCallback(async () => {
    const response = await apiFetch(`/graph/semantic-edges`);
    if (!response.ok) throw new Error(await apiErrorMessage(response));
    const data = await response.json();
    setSemanticEdges(data.edges ?? []);
    setSemanticMeta({
      edge_count: data.edge_count ?? (data.edges ?? []).length,
      created_at: data.created_at ?? null,
      graph_matches: data.graph_matches,
      graph_stale: data.graph_stale,
      edge_policy_stale: data.edge_policy_stale,
      legacy_edge_count: data.legacy_edge_count,
      scope_node_count: data.scope_node_count,
      embedded_node_count: data.embedded_node_count,
      max_neighbors_per_node: data.max_neighbors_per_node,
      mutual_top_neighbors: data.mutual_top_neighbors,
      max_edges: data.max_edges,
      current_graph_edge_match_count: data.current_graph_edge_match_count,
      current_graph_node_count: data.current_graph_node_count,
    });
    return data;
  }, []);

  const loadSummaryOverlap = useCallback(async (currentSummary: GraphSummary | null = summary) => {
    if (!currentSummary) return;
    const qs = currentSummary.project ? `?project=${encodeURIComponent(currentSummary.project)}` : "";
    const response = await apiFetch(`/graph/overlap-summary${qs}`);
    if (!response.ok) throw new Error(await apiErrorMessage(response));
    const data = await response.json() as OverlapSummaryResponse;
    setSummaryOverlap(data);
  }, [summary]);

  const stopSemanticPolling = useCallback(() => {
    if (!semanticPollRef.current) return;
    clearInterval(semanticPollRef.current);
    semanticPollRef.current = null;
  }, []);

  const handleSemanticComplete = useCallback(async (status: SemanticPassStatus) => {
    stopSemanticPolling();
    setRunningSemantic(false);
    await loadSemanticEdges();
    await loadSummaryOverlap();
    setFullGraph(null);
    setShowSemantic(true);
    setFocusNotice({
      tone: "info",
      text: `Semantic Analysis complete. Found ${status.edge_count.toLocaleString()} actionable candidate edges for this map; the Evidence layer is refreshed.`,
    });
    addToast(`Semantic analysis complete - ${status.edge_count.toLocaleString()} candidate edges found`, "success");
  }, [addToast, loadSemanticEdges, loadSummaryOverlap, stopSemanticPolling]);

  const handleSemanticError = useCallback((status: SemanticPassStatus) => {
    stopSemanticPolling();
    setRunningSemantic(false);
    const message = status.error || "Semantic analysis failed";
    setFocusNotice({ tone: "warn", text: message });
    addToast(`Semantic analysis failed: ${message}`, "error");
  }, [addToast, stopSemanticPolling]);

  const pollSemanticStatus = useCallback(() => {
    stopSemanticPolling();
    semanticPollRef.current = setInterval(async () => {
      try {
        const response = await apiFetch(`/graph/semantic-pass/status`);
        if (!response.ok) throw new Error(await apiErrorMessage(response));
        const status = await response.json() as SemanticPassStatus;
        setSemanticStatus(status);
        if (status.status === "complete") {
          await handleSemanticComplete(status);
        } else if (status.status === "error") {
          handleSemanticError(status);
        }
      } catch (error) {
        stopSemanticPolling();
        setRunningSemantic(false);
        setFocusNotice({
          tone: "warn",
          text: error instanceof Error ? error.message : "Lost semantic analysis status.",
        });
      }
    }, 3000);
  }, [handleSemanticComplete, handleSemanticError, stopSemanticPolling]);

  // Load semantic edges and any in-flight semantic status on mount.
  useEffect(() => {
    void loadSemanticEdges().catch(() => {});
    apiFetch(`/graph/semantic-pass/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((status: SemanticPassStatus | null) => {
        if (!status) return;
        setSemanticStatus(status);
        if (status.status === "running") {
          setRunningSemantic(true);
          pollSemanticStatus();
        }
      })
      .catch(() => {});
    return () => stopSemanticPolling();
  }, [loadSemanticEdges, pollSemanticStatus, stopSemanticPolling]);

  // Load broad-safe overlap groups aligned to the current summary surface.
  useEffect(() => {
    void loadSummaryOverlap().catch(() => {});
  }, [loadSummaryOverlap]);

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
  // The bright overlay uses actionable semantic edges; raw local similarity stays out of the main Evidence view.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || viewMode !== "full") return;
    if (!showSemantic) {
      cy.elements('[?semantic]').remove();
      setSelectedSemanticLink(null);
      return;
    }
    const nodeIds = new Set<string>(cy.nodes().map((n) => n.id()));
    cy.batch(() => {
      cy.elements('[?semantic]').remove();
      if (!semanticEdgesForDisplay.length) return;
      const toAdd = semanticEdgesForDisplay
        .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
        .map((e) => ({
          group: "edges" as const,
          data: {
            id: `sem__${e.source}__${e.target}`,
            source: e.source,
            target: e.target,
            similarity: e.similarity,
            actionability: e.actionabilityScore,
            insight_kind: e.insightKind,
            decision_signals: e.decisionSignals,
            semantic: true,
          },
          classes: "semantic-edge",
        }));
      if (toAdd.length) cy.add(toAdd);
    });
    applyStructuralEdgeVisibility(cy, showStructuralRef.current, showSemantic);
  }, [showSemantic, semanticEdgesForDisplay, viewMode]);

  // Toggle structural edges on/off (class swap — no layout restart)
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || viewMode !== "full") return;
    applyStructuralEdgeVisibility(cy, showStructural, showSemanticRef.current);
  }, [showStructural, viewMode, semanticEdgesForDisplay.length]);

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

  const loadWorkspaceScopeProfile = useCallback(async (): Promise<WorkspaceScopeProfile | null> => {
    const response = await apiFetch(`/workspace-scope`);
    if (!response.ok) throw new Error(await apiErrorMessage(response));
    const data = await response.json() as { profile: WorkspaceScopeProfile | null };
    scopeProfileRef.current = data.profile;
    return data.profile;
  }, []);

  const fetchSummary = useCallback(async (
    project?: string,
    label?: string,
    expectedScope?: WorkspaceScopeProfile | null,
  ) => {
    setLoading(true);
    setError(null);
    setSelected(null);
    setSelectedFull(null);
    setSelectedSemanticLink(null);
    setFullGraph(null);
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
      const scopeToCheck = expectedScope ?? scopeProfileRef.current;
      if (!generatedScopeMatchesProfile(data.workspace_scope, scopeToCheck)) {
        setSummary(null);
        setFullGraph(null);
        setScopeGate("setup");
        setCanGenerateScopeMap(Boolean(scopeToCheck));
        setScopeGateReason(
          "The selected workspace scope has not been generated yet. Generate the map to show only the selected folders and exclusions.",
        );
        return;
      }
      setCanGenerateScopeMap(false);
      setMapRendering(true);
      setSummary(data);
      setBreadcrumb(project ? [label || project] : []);
      if (shouldOpenExpandedEvidence(data, project)) {
        setViewMode("full");
        setFocusNotice({
          tone: "info",
          text: `Opening the expanded evidence map for ${data.total_nodes.toLocaleString()} visible nodes in this selected workspace scope.`,
        });
      } else {
        setViewMode("summary");
      }
      if (!project && data.total_nodes > FULL_GRAPH_NODE_LIMIT) {
        setFocusNotice({
          tone: "warn",
          text: `Overview is ready. Evidence view is capped at ${FULL_GRAPH_NODE_LIMIT.toLocaleString()} visible nodes, and this scope has ${data.total_nodes.toLocaleString()}. Select a narrower scope or drill into a smaller project before opening Evidence.`,
        });
      }
      setScopeGate("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setMapRendering(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function checkWorkspaceScope() {
      setScopeGate("checking");
      try {
        const profile = await loadWorkspaceScopeProfile();
        if (cancelled) return;
        if (!profile) {
          setCanGenerateScopeMap(false);
          setScopeGate("setup");
          setScopeGateReason("No workspace scope is selected yet. Select folders in Workspace Scope, then generate the map.");
          return;
        }
        setScopeGate("ready");
        void fetchSummary(undefined, undefined, profile);
      } catch (e) {
        if (cancelled) return;
        setCanGenerateScopeMap(false);
        setScopeGate("setup");
        setScopeGateReason(e instanceof Error ? e.message : "Workspace scope is unavailable. Inspect a folder before generating the map.");
      }
    }
    void checkWorkspaceScope();
    return () => { cancelled = true; };
  }, [fetchSummary, loadWorkspaceScopeProfile]);

  const handleGenerateScopeMap = useCallback(async () => {
    if (generatingScopeMap) return;
    setGeneratingScopeMap(true);
    setCanGenerateScopeMap(false);
    setError(null);
    setScopeGate("setup");
    setScopeGateReason("Generating the selected workspace map...");
    try {
      const profile = scopeProfileRef.current ?? await loadWorkspaceScopeProfile();
      if (!profile) {
        setScopeGateReason("No workspace scope is selected yet. Select folders in Workspace Scope, then generate the map.");
        return;
      }

      const response = await apiFetch(`/graph/rebuild`, { method: "POST" });
      if (!response.ok) {
        const message = await apiErrorMessage(response);
        if (!message.toLowerCase().includes("already in progress")) {
          throw new Error(message);
        }
        setScopeGateReason("Rebuild already in progress. Watching for completion...");
      }

      while (true) {
        await sleep(2000);
        const statusResponse = await apiFetch(`/graph/rebuild/status`);
        if (!statusResponse.ok) throw new Error(await apiErrorMessage(statusResponse));
        const status = await statusResponse.json() as RebuildStatus;
        if (status.status === "complete") {
          const refreshedProfile = await loadWorkspaceScopeProfile();
          await fetchSummary(undefined, undefined, refreshedProfile ?? profile);
          return;
        }
        if (status.status === "error") {
          throw new Error(status.error || "Graph generation failed");
        }
      }
    } catch (e) {
      setCanGenerateScopeMap(Boolean(scopeProfileRef.current));
      setScopeGate("setup");
      setScopeGateReason(e instanceof Error ? e.message : "Graph generation failed");
    } finally {
      setGeneratingScopeMap(false);
    }
  }, [fetchSummary, generatingScopeMap, loadWorkspaceScopeProfile]);

  const fetchFullGraph = useCallback(async () => {
    const effectiveKnowledgeOnly = knowledgeOnly && !showLowSignal;
    if (
      fullGraph
      && Boolean(fullGraph.include_low_signal) === showLowSignal
      && Boolean(fullGraph.knowledge_only) === effectiveKnowledgeOnly
    ) return; // already loaded
    setFullLoading(true);
    try {
      const params = new URLSearchParams();
      if (showLowSignal) params.set("include_low_signal", "true");
      if (effectiveKnowledgeOnly) params.set("knowledge_only", "true");
      params.set("max_nodes", String(FULL_GRAPH_NODE_LIMIT));
      const qs = params.toString() ? `?${params.toString()}` : "";
      const res = await apiFetch(`/graph/full${qs}`);
      if (!res.ok) throw new Error(await apiErrorMessage(res));
      const data: FullGraph = await res.json();
      setMapRendering(true);
      setFullGraph(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setMapRendering(false);
    } finally {
      setFullLoading(false);
    }
  }, [fullGraph, knowledgeOnly, showLowSignal]);

  // When switching to full mode, load the full graph once
  useEffect(() => {
    if (viewMode === "full") fetchFullGraph();
  }, [viewMode, fetchFullGraph]);

  // Init / reinit Cytoscape when summary data changes (summary mode only)
  useEffect(() => {
    if (!containerRef.current || !summary || viewMode !== "summary") return;

    ensureExtensions();
    const renderCycle = beginMapRender();
    let renderFinished = false;
    const finishRender = () => {
      if (renderFinished) return;
      renderFinished = true;
      try {
        cy.fit(undefined, 70);
      } catch (err) {
        console.warn("Map render finalization failed", err);
      } finally {
        finishMapRender(renderCycle);
      }
    };

    cyRef.current?.destroy();
    cyRef.current = null;

    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(summary, decisions, godNodeIds),
      style: CY_STYLE as any,
      pixelRatio: 1,
      minZoom: 0.05,
      maxZoom: 8,
    });

    // Auto-fit after animation so the graph fills the canvas neatly
    const layout = cy.layout(getLayout(summary) as any);
    layout.one("layoutstop", finishRender);
    layout.run();
    const renderFallback = window.setTimeout(finishRender, 12000);

    cy.on("tap", "node", (e: any) => {
      const node = e.target;
      const nodeId: string = node.id();

      if (handlePathNodeTap(cy, node, nodeId)) return;

      // Normal tap — select + highlight connected edges
      cy.nodes().removeClass("selected");
      cy.edges().removeClass("highlighted");
      node.addClass("selected");
      node.connectedEdges().addClass("highlighted");

      const nodeData =
        summaryRef.current?.nodes.find((n) => n.id === nodeId) ?? null;
      setSelected(nodeData);
      setSelectedSemanticLink(null);
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
        setSelectedSemanticLink(null);
        onActiveContextChange?.(null);
      }
    });

    cyRef.current = cy;
    return () => {
      window.clearTimeout(renderFallback);
      cancelMapRender(renderCycle);
      cy.destroy();
      cyRef.current = null;
    };
  }, [summary, decisions, godNodeIds, viewMode]);

  // Full-graph Cytoscape init
  useEffect(() => {
    if (viewMode !== "full" || !containerRef.current || !fullGraph) return;

    ensureExtensions();
    const renderCycle = beginMapRender();
    let renderFinished = false;
    let fastFinishFrame = 0;
    let fastFinishTimer = 0;

    cyRef.current?.destroy();
    cyRef.current = null;

    const useFastLayout = shouldUseFastFullLayout(fullGraph, filter, selectedClusters);
    const fastPresetLayout = useFastLayout
      ? buildFullPresetLayout(visibleFullNodes(fullGraph, filter, selectedClusters))
      : null;
    const cy = cytoscape({
      container: containerRef.current,
      elements: buildFullElements(fullGraph, filter, selectedClusters, fastPresetLayout),
      style: FULL_CY_STYLE as any,
      ...(useFastLayout ? { layout: FULL_FAST_LAYOUT as any } : {}),
      pixelRatio: 1,
      minZoom: 0.02,
      maxZoom: 12,
    });
    if (fastPresetLayout) {
      cy.batch(() => {
        cy.nodes().forEach((node: any) => {
          const position = fastPresetLayout.positions[node.id()]
            ?? fastPresetLayout.repoLabels.find((repoLabel) => repoLabel.id === node.id())?.position
            ?? fastPresetLayout.containerLabels.find((containerLabel) => containerLabel.id === node.id())?.position;
          if (position) node.position(position);
        });
      });
    }
    applyStructuralEdgeVisibility(cy, showStructuralRef.current, showSemanticRef.current);

    // Keep region labels at a constant readable screen size.
    // Cytoscape font-size is in model units, so it scales with zoom by
    // default. Counter-scale it against the live zoom level so the label
    // renders at the same on-screen pixel size whether Adam is zoomed in
    // on one repo or zoomed out across the whole comparison.
    const REPO_LABEL_SCREEN_PX = 18;
    const REPO_LABEL_OUTLINE_SCREEN_PX = 3;
    const CONTAINER_LABEL_SCREEN_PX = 12;
    const CONTAINER_LABEL_OUTLINE_SCREEN_PX = 2;
    let repoLabelFrame = 0;
    const syncRepoLabelScale = () => {
      repoLabelFrame = 0;
      const zoom = cy.zoom() || 1;
      cy.nodes(".repo-label").style({
        "font-size": REPO_LABEL_SCREEN_PX / zoom,
        "text-outline-width": REPO_LABEL_OUTLINE_SCREEN_PX / zoom,
      });
      cy.nodes(".container-label").style({
        "font-size": CONTAINER_LABEL_SCREEN_PX / zoom,
        "text-outline-width": CONTAINER_LABEL_OUTLINE_SCREEN_PX / zoom,
      });
    };
    const scheduleRepoLabelScale = () => {
      if (repoLabelFrame) return;
      repoLabelFrame = window.requestAnimationFrame(syncRepoLabelScale);
    };
    cy.on("zoom", scheduleRepoLabelScale);

    let semanticEdgesRestored = false;
    const restoreSemanticEdges = () => {
      if (semanticEdgesRestored) return;
      semanticEdgesRestored = true;
      if (showSemanticRef.current && visibleSemanticEdgesRef.current.length > 0) {
        const nodeIds = new Set<string>(cy.nodes().map((n) => n.id()));
        const toAdd = visibleSemanticEdgesRef.current
          .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
          .map((e) => ({
            group: "edges" as const,
            data: {
              id: `sem__${e.source}__${e.target}`,
              source: e.source,
              target: e.target,
              similarity: e.similarity,
              actionability: (e as ActionableSemanticEdge).actionabilityScore,
              insight_kind: (e as ActionableSemanticEdge).insightKind,
              decision_signals: (e as ActionableSemanticEdge).decisionSignals,
              semantic: true,
            },
            classes: "semantic-edge",
          }));
        if (toAdd.length) cy.batch(() => cy.add(toAdd));
      }
      applyStructuralEdgeVisibility(cy, showStructuralRef.current, showSemanticRef.current);
    };
    const finishRender = () => {
      if (renderFinished) return;
      renderFinished = true;
      try {
        restoreSemanticEdges();
        cy.fit(undefined, 40);
        syncRepoLabelScale();
      } catch (err) {
        console.warn("Full map render finalization failed", err);
      } finally {
        finishMapRender(renderCycle);
      }
    };
    let renderFallback = 0;
    if (useFastLayout) {
      fastFinishFrame = window.requestAnimationFrame(finishRender);
      fastFinishTimer = window.setTimeout(finishRender, 250);
    } else {
      const layout = cy.layout(FULL_FCOSE_LAYOUT as any);
      layout.one("layoutstop", finishRender);
      layout.run();
      renderFallback = window.setTimeout(finishRender, 20000);
    }

    cy.on("tap", "node", (e: any) => {
      const node = e.target;
      const nodeId: string = node.id();
      if (handlePathNodeTap(cy, node, nodeId)) return;

      cy.nodes().removeClass("selected");
      cy.edges().removeClass("highlighted");
      node.addClass("selected");
      node.connectedEdges().addClass("highlighted");
      const n = fullGraph.nodes.find((n) => n.id === nodeId) ?? null;
      setSelectedFull(n);
      setSelected(null);
      setSelectedSemanticLink(null);
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

    cy.on("tap", "edge.semantic-edge", (e: any) => {
      e.stopPropagation?.();
      selectSemanticEdgeElement(e.target);
    });

    cy.on("tap", (e: any) => {
      if (e.target === cy) {
        cy.nodes().removeClass("selected");
        cy.edges().removeClass("highlighted");
        setSelectedFull(null);
        setSelectedSemanticLink(null);
        onActiveContextChange?.(null);
      }
    });

    cyRef.current = cy;

    return () => {
      window.clearTimeout(renderFallback);
      window.clearTimeout(fastFinishTimer);
      if (fastFinishFrame) window.cancelAnimationFrame(fastFinishFrame);
      if (repoLabelFrame) window.cancelAnimationFrame(repoLabelFrame);
      cancelMapRender(renderCycle);
      cy.destroy();
      cyRef.current = null;
    };
  }, [viewMode, fullGraph, filter, selectedClusters]);

  // Apply cross-tab evidence context once the relevant graph surface is ready.
  useEffect(() => {
    if (!activeContext || activeContext.source === "map") return;
    const key = contextKey(activeContext);
    if (appliedContextKeyRef.current === key) return;

    if (activeContext.kind === "overlap-pair") {
      if (viewMode !== "full") {
        setKnowledgeOnly(false);
        setViewMode("full");
        return;
      }

      if (knowledgeOnly) {
        setKnowledgeOnly(false);
        setFullGraph(null);
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
      setSelectedSemanticLink(null);

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
      setKnowledgeOnly(false);
      setViewMode("full");
      return;
    }

    if (knowledgeOnly) {
      setKnowledgeOnly(false);
      setFullGraph(null);
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
        setSelectedSemanticLink(null);
        setShowOverlap(false);
        setHighlightedPair(null);
        appliedContextKeyRef.current = key;
        return;
      }

      setSelectedFull(null);
      setSelectedSemanticLink(null);
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
    setSelectedSemanticLink(null);
    setShowOverlap(false);
    setHighlightedPair(null);
    appliedContextKeyRef.current = key;
  }, [activeContext, fetchFullGraph, filter, fullGraph, knowledgeOnly, selectedClusters, viewMode]);

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
    const groupMap = overlapNodeGroupMapRef.current;
    cy.batch(() => {
      cy.edges(".semantic-edge").forEach((e: any) => {
        const src = e.data("source") as string;
        const tgt = e.data("target") as string;
        const sc = groupMap[src];
        const tc = groupMap[tgt];
        const inPair = (sc === ca && tc === cb) || (sc === cb && tc === ca);
        if (inPair) {
          e.removeClass("faded").addClass("highlighted");
        } else {
          e.addClass("faded").removeClass("highlighted");
        }
      });
    });
  }, [highlightedPair, viewMode, showSemantic, overlapSemanticEdges.length]);

  // Clear highlighted pair when semantic is turned off
  useEffect(() => {
    if (!showSemantic && viewMode === "full") {
      setHighlightedPair(null);
      setSelectedSemanticLink(null);
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
            source: p.source,
            target: p.target,
            label_a: p.labelA, label_b: p.labelB,
            file_a: p.fileA, file_b: p.fileB,
            similarity: p.similarity,
            same_name: p.sameName,
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
      setShowOverlap(false);
      setHighlightedPair(null);
      onActiveContextChange?.(null);
      setSelected(null);
      setSelectedFull(null);
      setSelectedSemanticLink(null);
      setPathSource(null);
      setPathNoRoute(false);
      if (broadEvidenceDisabled) {
        setViewMode("summary");
        setShowSemantic(false);
        setFocusNotice({
          tone: "info",
          text: `Using summary trace because Evidence view is capped at ${FULL_GRAPH_NODE_LIMIT.toLocaleString()} visible nodes for this scope. Narrow the scope to trace semantic file-level paths.`,
        });
      } else {
        setViewMode("full");
        if (storedSemanticEdgeCount > 0) setShowSemantic(true);
      }
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
        setSelectedSemanticLink(null);
        setShowOverlap(true);
        setFocusNotice({
          tone: "info",
          text: `Showing summary-level overlap because Evidence view is capped at ${FULL_GRAPH_NODE_LIMIT.toLocaleString()} visible nodes for this scope.`,
        });
        return;
      }
      setViewMode("full");
      setKnowledgeOnly(false);
      setShowSemantic(true);
      setSelectedSemanticLink(null);
      setShowOverlap(true);
      return;
    }

    setShowOverlap(false);
    setHighlightedPair(null);
    setSelectedSemanticLink(null);
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
    setSelectedSemanticLink(null);
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
    setMapMode("trace");
    setShowOverlap(false);
    setHighlightedPair(null);
    setSelected(null);
    setSelectedFull(null);
    setSelectedSemanticLink(null);
    onActiveContextChange?.(null);
    setPathNoRoute(false);
    cy.nodes().removeClass("path-source path-target");
    cy.elements().removeClass("path-edge faded");
    cy.getElementById(nodeId).addClass("path-source");
    setPathSource(nodeId);
    setPathMode(true);
  }

  async function copyGapAskPrompt(node: SummaryNode) {
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable.");
      await navigator.clipboard?.writeText(gapAskPrompt(node));
      setFocusNotice({ tone: "info", text: `Copied Ask prompt for ${node.label}.` });
    } catch {
      setFocusNotice({ tone: "warn", text: "Could not copy the Ask prompt in this browser." });
    }
  }

  async function saveGapDecision(node: SummaryNode, classification: DecisionClassification) {
    setSavingGapDecision(classification);
    const rationale = node.gap_detail || node.gap_reason || "Marked from Map gap triage.";
    const existing = decisionRecords[node.id];
    try {
      const res = await apiFetch(existing ? `/decisions/${encodeURIComponent(existing.id)}` : `/decisions`, {
        method: existing ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(existing
          ? { classification, rationale, label: node.label, status: "active" }
          : { target_id: node.id, label: node.label, classification, rationale }
        ),
      });
      if (!res.ok) throw new Error(await apiErrorMessage(res));
      const saved = await res.json();
      setDecisions((current) => ({ ...current, [node.id]: saved.classification }));
      setDecisionRecords((current) => ({
        ...current,
        [node.id]: { id: saved.id, classification: saved.classification },
      }));
      const label = DECISION_META[saved.classification]?.label ?? saved.classification;
      setFocusNotice({ tone: "info", text: `${node.label} marked ${label}.` });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Could not save the decision.";
      setFocusNotice({ tone: "warn", text: message });
    } finally {
      setSavingGapDecision(null);
    }
  }

  const pctCode = selected
    ? Math.round((selected.code_count / Math.max(1, selected.node_count)) * 100)
    : 0;
  const selectedConnections = selected?.connections ?? [];

  const activeMapMode = MAP_MODES.find((mode) => mode.id === mapMode) ?? MAP_MODES[0];
  const hiddenLowSignalCount = lowSignalCount(fullGraph, summary);
  const excludedFromScopeCount = excludedNodeCount(fullGraph, summary);
  const importanceCounts = fullGraph?.importance_counts ?? summary?.importance_counts ?? {};
  const knowledgeAnchorCount = (importanceCounts.anchor ?? 0) + (importanceCounts.interface ?? 0) + (importanceCounts.important ?? 0);
  const knowledgeHiddenCount = fullGraph?.knowledge_hidden_node_count ?? 0;
  const summaryVisibleNodeCount = summary?.total_nodes ?? 0;
  const summaryExceedsEvidenceCap = summaryVisibleNodeCount > FULL_GRAPH_NODE_LIMIT;
  const broadEvidenceDisabled = !fullGraph && summaryExceedsEvidenceCap;
  const usingFastFullLayout = useMemo(
    () => Boolean(fullGraph && viewMode === "full" && shouldUseFastFullLayout(fullGraph, filter, selectedClusters)),
    [fullGraph, filter, selectedClusters, viewMode],
  );
  const mapWorkPending = loading || (fullLoading && viewMode === "full") || mapRendering;
  const mapWorkLabel = fullLoading && viewMode === "full"
    ? (knowledgeOnly ? "Loading workspace knowledge" : "Loading full graph")
    : mapRendering
      ? "Rendering map"
      : "Building graph summary";
  const mapWorkDetail = mapRendering && !loading && !(fullLoading && viewMode === "full")
    ? usingFastFullLayout
      ? "Arranging selected repos into a folder-level comparison"
      : "Laying out the workspace view"
    : "First load may take a moment";
  const traceLayerText = viewMode === "full"
    ? showSemantic && semanticEdgesForDisplay.length
      ? showStructural
        ? "physical + semantic evidence"
        : "semantic evidence"
      : "physical evidence"
    : "summary physical";
  const semanticDisplayCount = semanticEdgesForDisplay.length;
  const semanticActionableCount = actionableSemanticEdges.length;
  const semanticCandidateCount = semanticCandidateEdges.length;
  const semanticRawVisibleCount = visibleSemanticEdges.length;
  const semanticLowValueHiddenCount = Math.max(0, semanticRawVisibleCount - semanticActionableCount);
  const semanticReadabilityHiddenCount = Math.max(0, semanticActionableCount - semanticDisplayCount);
  const semanticDisplayText = semanticDisplayCount.toLocaleString();
  const semanticActionableText = semanticActionableCount.toLocaleString();
  const semanticCandidateText = semanticCandidateCount.toLocaleString();
  const semanticVisibleText = semanticRawVisibleCount.toLocaleString();
  const semanticLowValueHiddenText = semanticLowValueHiddenCount.toLocaleString();
  const semanticReadabilityHiddenText = semanticReadabilityHiddenCount.toLocaleString();
  const overlapScopeLabel = visibleRepoCount > 1 ? "cross-repo" : "cross-folder";
  const semanticButtonCountText = fullGraph
    ? semanticAnalysisMissing
      ? " (not run)"
      : semanticRawVisibleCount > semanticDisplayCount
      ? ` (${semanticDisplayText}/${semanticVisibleText})`
      : ` (${semanticDisplayText})`
    : "";
  const semanticStaleCaveat = semanticCacheStale
    ? semanticPolicyStale
      ? `${legacySemanticEdgeCount.toLocaleString()} old broad semantic edges were withheld. Click Semantic to rebuild actionable candidates for this map.`
      : `${storedSemanticEdgeCount.toLocaleString()} stored semantic edges were built for a different graph. Click Semantic to rerun analysis for the current map.`
    : "";
  const semanticScopeCaveat = semanticCacheMostlyOutOfScope
    ? `${outOfScopeSemanticEdgeCount.toLocaleString()} stored semantic edges are outside this Evidence scope; click Semantic to rerun analysis for the current map.`
    : "";
  const semanticActionabilityCaveat = semanticCacheStale
    ? ""
    : fullGraph && semanticRawVisibleCount > 0 && semanticActionableCount === 0
    ? semanticCandidateCount === 0
      ? `${semanticVisibleText} raw semantic edges match this Evidence scope, but none cross the ${overlapScopeLabel} boundary needed for bright evidence.`
      : `${semanticCandidateText} ${overlapScopeLabel} semantic candidates match this Evidence scope, but none clear the actionability filter.`
    : fullGraph && semanticLowValueHiddenCount > 0
    ? `${semanticLowValueHiddenText} raw in-scope semantic edges are hidden as low-value or shared-scaffolding similarity.`
    : "";
  const semanticBackboneCaveat = semanticReadabilityHiddenCount > 0
    ? `${semanticReadabilityHiddenText} actionable edges are held back by the readability backbone.`
    : "";
  const semanticPassRunning = runningSemantic || semanticStatus?.status === "running";
  const semanticProgressText = semanticStatus?.total
    ? ` ${semanticStatus.progress.toLocaleString()}/${semanticStatus.total.toLocaleString()}`
    : "";
  const semanticOverlayNotice = [
    semanticPassRunning
      ? `Semantic Analysis is running${semanticProgressText ? ` (${semanticProgressText.trim()} nodes)` : ""}. The Evidence layer will refresh when it completes.`
      : semanticDisplayCount
      ? `Showing ${semanticDisplayText} actionable semantic edges in this Evidence view.`
      : semanticAnalysisMissing
      ? "Semantic Analysis has not run for this map yet. Click Semantic to analyze this exact map/scope."
      : semanticCacheStale
      ? "Semantic cache is stale for this Evidence view."
      : semanticRawVisibleCount
      ? "No actionable semantic edges in this Evidence view."
      : "",
    semanticStaleCaveat,
    semanticActionabilityCaveat,
    semanticBackboneCaveat,
    semanticCacheStale ? "" : semanticScopeCaveat,
  ].filter(Boolean).join(" ");
  const semanticOverlayNoticeTone: "info" | "warn" = semanticPassRunning || semanticDisplayCount ? "info" : "warn";
  const semanticScopeText = semanticDisplayCount
    ? `${semanticDisplayText} actionable ${overlapScopeLabel} semantic edges from ${semanticCandidateText} boundary candidates and ${semanticVisibleText} raw in-scope matches`
    : semanticAnalysisMissing
    ? "semantic analysis has not run for this map"
    : semanticCacheStale
    ? "stale semantic cache for this graph"
    : semanticRawVisibleCount
    ? semanticCandidateCount
      ? `0 actionable ${overlapScopeLabel} semantic edges from ${semanticCandidateText} boundary candidates and ${semanticVisibleText} raw in-scope matches`
      : `0 ${overlapScopeLabel} semantic candidates from ${semanticVisibleText} raw in-scope matches`
    : "0 visible semantic edges";
  const semanticRunRecommended = Boolean(
    !semanticMeta
      || semanticAnalysisMissing
      || semanticCacheStale
      || semanticCacheMostlyOutOfScope
      || (!storedSemanticEdgeCount && semanticMeta)
      || (fullGraph && semanticRawVisibleCount === 0 && !semanticMeta?.created_at),
  );
  const semanticButtonLabel = semanticPassRunning
    ? `Analysing...${semanticProgressText}`
    : semanticRunRecommended
    ? storedSemanticEdgeCount || semanticCacheStale || semanticCacheMostlyOutOfScope
      ? "Rerun Semantic"
      : "Run Semantic"
    : `Semantic${semanticButtonCountText}`;

  async function handleRunSemanticAnalysisFromMap() {
    if (semanticPassRunning) {
      setFocusNotice({
        tone: "info",
        text: `Semantic Analysis is running${semanticProgressText ? ` (${semanticProgressText.trim()} nodes)` : ""}. The map will refresh when it completes.`,
      });
      return;
    }

    setRunningSemantic(true);
    setShowSemantic(true);
    setSelectedSemanticLink(null);
    setFocusNotice({
      tone: "info",
      text: "Semantic Analysis started for the active map. It will keep only strong actionable candidates and refresh the Evidence layer when complete.",
    });
    if (viewMode !== "full" && !broadEvidenceDisabled) {
      setViewMode("full");
      setPathMode(false);
      setPathNoRoute(false);
    }

    try {
      const scopedNodeIds = fullGraph ? [...visibleFullNodeIds] : [];
      const response = await apiFetch(`/graph/semantic-pass`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: DEFAULT_SEMANTIC_MODEL,
          threshold: DEFAULT_SEMANTIC_THRESHOLD,
          include_low_signal: showLowSignal,
          knowledge_only: knowledgeOnly && !showLowSignal,
          node_ids: fullGraph ? scopedNodeIds : undefined,
          max_neighbors_per_node: DEFAULT_SEMANTIC_NEIGHBOR_LIMIT,
          mutual_top_neighbors: true,
          max_edges: DEFAULT_SEMANTIC_STORED_EDGE_LIMIT,
        }),
      });
      if (!response.ok) {
        const message = await apiErrorMessage(response);
        if (response.status !== 409) throw new Error(message);
        setFocusNotice({
          tone: "info",
          text: "Semantic Analysis is already running. Watching it from the Map.",
        });
      } else {
        addToast("Semantic analysis started", "info");
      }
      setSemanticStatus({
        status: "running",
        progress: semanticStatus?.progress ?? 0,
        total: semanticStatus?.total ?? 0,
        last_run: semanticStatus?.last_run ?? null,
        error: null,
        edge_count: semanticStatus?.edge_count ?? 0,
        model: DEFAULT_SEMANTIC_MODEL,
        threshold: DEFAULT_SEMANTIC_THRESHOLD,
        scope_node_count: scopedNodeIds.length,
        max_neighbors_per_node: DEFAULT_SEMANTIC_NEIGHBOR_LIMIT,
        max_edges: DEFAULT_SEMANTIC_STORED_EDGE_LIMIT,
      });
      pollSemanticStatus();
    } catch (error) {
      setRunningSemantic(false);
      const message = error instanceof Error ? error.message : "Failed to start semantic analysis";
      setFocusNotice({ tone: "warn", text: message });
      addToast(`Failed to start semantic analysis: ${message}`, "error");
    }
  }

  useEffect(() => {
    if (viewMode !== "full" || !showSemantic || !fullGraph) return;
    if (semanticOverlayNotice && (
      semanticPassRunning
      || semanticAnalysisMissing
      || semanticCacheStale
      || semanticCacheMostlyOutOfScope
      || semanticActionabilityCaveat
      || semanticBackboneCaveat
    )) {
      setFocusNotice({
        tone: semanticOverlayNoticeTone,
        text: semanticOverlayNotice,
      });
    } else if (!semanticDisplayCount && storedSemanticEdgeCount) {
      setFocusNotice({
        tone: "warn",
        text: "Stored semantic edges do not match this Evidence scope. Click Semantic to rebuild them for this map.",
      });
    }
  }, [
    fullGraph,
    semanticActionabilityCaveat,
    semanticBackboneCaveat,
    semanticAnalysisMissing,
    semanticCacheStale,
    semanticCacheMostlyOutOfScope,
    semanticDisplayCount,
    semanticOverlayNotice,
    semanticOverlayNoticeTone,
    semanticPassRunning,
    showSemantic,
    storedSemanticEdgeCount,
    viewMode,
  ]);

  if (scopeGate === "checking") {
    return (
      <div className="map-pane">
        <div className="map-startup-shell">
          <div className="map-overlay map-startup-overlay">
            <WorkingStatus
              label="Checking workspace scope"
              detail="The map waits until scope is known."
            />
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
            {generatingScopeMap ? (
              <WorkingStatus
                label="Generating workspace map"
                detail={scopeGateReason}
              />
            ) : (
              <>
                <span className="map-empty-title">Generate a workspace map first</span>
                <span className="map-overlay-sub">{scopeGateReason}</span>
              </>
            )}
            <div className="map-empty-actions">
              {canGenerateScopeMap && (
                <button
                  type="button"
                  className="settings-upload-btn"
                  onClick={handleGenerateScopeMap}
                  disabled={generatingScopeMap}
                >
                  {generatingScopeMap ? "Generating..." : "Generate Map"}
                </button>
              )}
              <button
                type="button"
                className="settings-upload-btn settings-secondary-btn"
                onClick={onNavigateScope}
                disabled={generatingScopeMap}
              >
                Open Workspace Scope
              </button>
            </div>
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
            setSelectedSemanticLink(null);
            if (m === "full") {
              setKnowledgeOnly(false);
              setPathMode(false);
            }
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
        setSelectedSemanticLink(null);
        setFullGraph(null);
        setKnowledgeOnly(false);
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

  const knowledgeControl = (
    <button
      className={`map-path-btn${knowledgeOnly && viewMode === "full" ? " map-knowledge-active" : ""}`}
      onClick={() => {
        const activatingKnowledge = !(knowledgeOnly && viewMode === "full");
        setSelectedFull(null);
        setSelectedSemanticLink(null);
        setFullGraph(null);
        setShowLowSignal(false);
        setKnowledgeOnly(activatingKnowledge);
        if (activatingKnowledge) {
          setViewMode("full");
          setPathMode(false);
          setPathNoRoute(false);
        } else if (summaryExceedsEvidenceCap) {
          setViewMode("summary");
          setFocusNotice({
            tone: "warn",
            text: `Evidence view is capped at ${FULL_GRAPH_NODE_LIMIT.toLocaleString()} visible nodes. Returned to Overview.`,
          });
        } else {
          setFocusNotice({ tone: "info", text: "Returning to Evidence view." });
        }
      }}
      title={
        knowledgeOnly && viewMode === "full"
          ? `Showing workspace knowledge anchors and interfaces${knowledgeHiddenCount ? `; ${knowledgeHiddenCount.toLocaleString()} lower-importance visible nodes hidden` : ""}`
          : `Show workspace knowledge lens with ${knowledgeAnchorCount.toLocaleString()} anchors, interfaces, and important boundary nodes`
      }
      type="button"
    >
      Knowledge{knowledgeAnchorCount ? ` (${knowledgeAnchorCount.toLocaleString()})` : ""}
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
          if (semanticPassRunning || semanticRunRecommended) {
            void handleRunSemanticAnalysisFromMap();
            return;
          }
          if (viewMode !== "full") {
            if (broadEvidenceDisabled) {
              setFocusNotice({
                tone: "warn",
                text: `Evidence view is capped at ${FULL_GRAPH_NODE_LIMIT.toLocaleString()} visible nodes. Semantic Analysis can run from smaller scopes or drilldowns.`,
              });
              return;
            }
            setViewMode("full");
            setPathMode(false);
            setPathNoRoute(false);
            setShowSemantic(true);
            if (semanticOverlayNotice && (semanticAnalysisMissing || semanticCacheStale || semanticCacheMostlyOutOfScope || semanticActionabilityCaveat || semanticBackboneCaveat)) {
              setFocusNotice({
                tone: semanticOverlayNoticeTone,
                text: semanticOverlayNotice,
              });
            } else if (fullGraph && !semanticDisplayCount && storedSemanticEdgeCount) {
              setFocusNotice({
                tone: "warn",
                text: "Stored semantic edges do not match this Evidence scope. Click Semantic to rebuild them for this map.",
              });
            }
            return;
          }
          setShowSemantic((current) => {
            const next = !current;
            if (next) {
              if (semanticOverlayNotice && (semanticAnalysisMissing || semanticCacheStale || semanticCacheMostlyOutOfScope || semanticActionabilityCaveat || semanticBackboneCaveat)) {
                setFocusNotice({
                  tone: semanticOverlayNoticeTone,
                  text: semanticOverlayNotice,
                });
              } else if (!semanticDisplayCount && storedSemanticEdgeCount) {
                setFocusNotice({
                  tone: "warn",
                  text: "Stored semantic edges do not match this Evidence scope. Click Semantic to rebuild them for this map.",
                });
              }
            }
            return next;
          });
        }}
        title={
          semanticPassRunning
            ? `Semantic Analysis is running from the Map${semanticProgressText ? ` (${semanticProgressText.trim()} nodes)` : ""}.`
            : semanticRunRecommended
            ? semanticCacheStale
              ? `${semanticScopeText}. Click to rerun Semantic Analysis for the current map.`
              : semanticAnalysisMissing
              ? "Semantic Analysis has not run for this map yet. Click to run it here."
              : semanticCacheMostlyOutOfScope
              ? `${semanticScopeText}. Click to rebuild semantic edges for the active map.`
              : "No usable semantic edges are available for this map. Click to run Semantic Analysis."
            : viewMode !== "full"
            ? "Switch to Evidence and show actionable semantic edges for this scope"
            : semanticDisplayCount
            ? `${showSemantic ? "Hide" : "Show"} ${semanticScopeText} (${semanticActionableText} actionable before backbone, ${semanticMeta?.edge_count ?? 0} stored total). Display uses actionability first, then mutual top-${SEMANTIC_BACKBONE_NEIGHBOR_LIMIT} neighbors so dense pockets stay readable; Trace routes through this backbone.${semanticActionabilityCaveat ? ` ${semanticActionabilityCaveat}` : ""}${semanticBackboneCaveat ? ` ${semanticBackboneCaveat}` : ""}${semanticCacheStale ? "" : semanticScopeCaveat ? ` ${semanticScopeCaveat}` : ""}`
            : semanticCacheStale
            ? `${showSemantic ? "Hide" : "Show"} semantic overlay. ${semanticScopeText}. ${semanticStaleCaveat}`
            : semanticAnalysisMissing
            ? `${showSemantic ? "Hide" : "Show"} semantic overlay. Semantic Analysis has not run for this map yet. Click Semantic to run it here.`
            : semanticRawVisibleCount
            ? `${showSemantic ? "Hide" : "Show"} semantic overlay. ${semanticScopeText}. The bright layer is filtered for duplicate, drift, gap, cross-app, or shared-pattern signal and hides generic scaffolding by default.${semanticScopeCaveat ? ` ${semanticScopeCaveat}` : ""}`
            : semanticMeta?.edge_count
            ? `Semantic overlay has ${semanticMeta.edge_count} stored edges, but none match the current full-graph scope and source filters.`
            : "No semantic edges yet - click to run Semantic Analysis"
        }
        style={
          semanticPassRunning
            ? { borderColor: "#f5a623", color: "#f5a623", background: "rgba(245,166,35,0.08)" }
            : viewMode !== "full"
            ? { opacity: 0.3, cursor: "default" }
            : showSemantic
            ? { borderColor: "#22c55e", color: "#22c55e", background: "rgba(34,197,94,0.07)" }
            : {}
        }
        type="button"
      >
        {semanticButtonLabel}
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
          : !showSemantic
          ? "Click Semantic to show existing edges or run analysis for this map"
          : !overlapSemanticEdges.length
          ? semanticAnalysisMissing
            ? "Semantic Analysis has not run for this map yet. Click Semantic to run it here."
            : storedSemanticEdgeCount
            ? `Semantic overlay is on, but no actionable ${overlapScopeLabel} overlap edges match the current scope or source filters.`
            : "No semantic edges yet - click Semantic to run analysis"
          : `${showOverlap ? "Close" : "Open"} overlap analysis - ${overlapGroups.length} ${overlapScopeLabel} pairs detected`
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
        if (mapMode !== "trace") {
          switchMapMode("trace");
          return;
        }
        setPathMode((p) => !p);
      }}
      title={
        viewMode === "full"
          ? "Trace the shortest route through visible physical and semantic Evidence edges"
          : "Trace the shortest route through the summary graph"
      }
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
              <span className={`map-meta-pill${summaryExceedsEvidenceCap ? " map-meta-pill-warn" : ""}`}>
                {summary.nodes.length}&thinsp;groups&thinsp;·&thinsp;
                {summaryVisibleNodeCount.toLocaleString()}&thinsp;/&thinsp;{FULL_GRAPH_NODE_LIMIT.toLocaleString()}&thinsp;Evidence cap
                {hiddenLowSignalCount ? <>&thinsp;·&thinsp;{hiddenLowSignalCount.toLocaleString()}&thinsp;hidden</> : null}
                {fullGraph?.knowledge_only && knowledgeHiddenCount ? <>&thinsp;·&thinsp;{knowledgeHiddenCount.toLocaleString()}&thinsp;held by lens</> : null}
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
            {knowledgeControl}
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

          {!focusNotice && summaryExceedsEvidenceCap && viewMode !== "full" && (
            <div className="map-focus-notice map-focus-notice-warn">
              This generated selection has {summaryVisibleNodeCount.toLocaleString()} visible nodes. Evidence opens up to {FULL_GRAPH_NODE_LIMIT.toLocaleString()}; narrow Workspace Scope or drill into a smaller group first.
            </div>
          )}

          {mapWorkPending && (
            <div className="map-overlay">
              <WorkingStatus
                label={mapWorkLabel}
                detail={mapWorkDetail}
              />
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
                ? `● Click a target node to trace ${traceLayerText}`
                : `○ Click a source node to begin ${traceLayerText} trace`}
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
            {!usingSummaryOverlap && !showSemantic ? (
              <div className="map-overlap-empty">
                Enable the Semantic overlay first to see {overlapScopeLabel} overlap analysis.
              </div>
            ) : !usingSummaryOverlap && !overlapSemanticEdges.length ? (
              <div className="map-overlap-empty">
                {storedSemanticEdgeCount
                  ? `Semantic overlay is on, but no actionable ${overlapScopeLabel} overlap edges are visible in the current scope and source filters.`
                  : "No semantic edges are available yet. Click Semantic to run analysis from the Map."}
              </div>
            ) : overlapGroups.length === 0 ? (
              <div className="map-overlap-empty">
                {usingSummaryOverlap
                  ? "No summary-level overlap pairs detected for the current map."
                  : `No ${overlapScopeLabel} overlaps detected.`}
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
                  <span className="map-overlap-hint-inline">LLM: waste / gap / cross-app / drift</span>
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
                    const insight = triageInsight(triage, g);
                    const insightPercent = boundedPercent(insight.score, 0.5);
                    const insightClass = semanticInsightClass(insight.kind);
                    const isTriaging = triaging[triageKey] ?? false;
                    const similarities = dossierList(triage?.similarities);
                    const differences = dossierList(triage?.differences);
                    const canonicalitySignals = dossierList(triage?.canonicality_signals);
                    const openQuestions = dossierList(triage?.open_questions);
                    const triageDecisionSignals = [
                      triage?.waste_signal,
                      triage?.gap_signal,
                      triage?.cross_app_similarity,
                    ].map((item) => item?.trim()).filter(Boolean).slice(0, 3);
                    const actionabilitySignals = (g.decisionSignals ?? []).slice(0, 5);
                    const displayedDecisionSignals = triageDecisionSignals.length
                      ? triageDecisionSignals
                      : actionabilitySignals;
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
                        <div className={`map-overlap-insight map-overlap-insight-${insightClass}`}>
                          <div className="map-overlap-insight-head">
                            <span className="map-overlap-insight-source">{insight.source === "llm" ? "LLM" : "Signal"}</span>
                            <strong>{insight.label}</strong>
                            <span className="map-overlap-actionability">{insightPercent}% actionable</span>
                          </div>
                          {insight.impact && <p>{insight.impact}</p>}
                          {displayedDecisionSignals.length > 0 && (
                            <ul className="map-overlap-decision-signals">
                              {displayedDecisionSignals.map((item, i) => <li key={i}>{item}</li>)}
                            </ul>
                          )}
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

        {/* Semantic-edge inspect panel */}
        {selectedSemanticLink && viewMode === "full" && !showOverlap && (
          <aside className="map-panel map-semantic-panel">
            <div className="map-panel-head">
              <span className="map-panel-name">Semantic Link</span>
              <button className="map-panel-close" onClick={() => clearSemanticLinkSelection()} aria-label="Close">✕</button>
            </div>
            <div className="map-panel-section">
              <span className={`map-type-badge map-semantic-kind-${semanticInsightClass(selectedSemanticLink.edge.insightKind)}`}>
                {SEMANTIC_INSIGHT_LABELS[selectedSemanticLink.edge.insightKind]}
              </span>
            </div>

            <div className="map-semantic-score-grid">
              <div className="map-stat">
                <span className="map-stat-label">Actionable</span>
                <span className="map-stat-value">{boundedPercent(selectedSemanticLink.edge.actionabilityScore, 0)}%</span>
              </div>
              <div className="map-stat">
                <span className="map-stat-label">Similarity</span>
                <span className="map-stat-value">{boundedPercent(selectedSemanticLink.edge.similarity, 0)}%</span>
              </div>
            </div>

            <div className="map-inspector-block">
              <div className="map-inspector-title">Why this matters</div>
              <p className="map-inspector-purpose">
                {semanticInsightImpact(selectedSemanticLink.edge.insightKind, selectedSemanticLink.edge.decisionSignals)}
              </p>
            </div>

            {selectedSemanticLink.edge.decisionSignals.length > 0 && (
              <div className="map-inspector-block">
                <div className="map-inspector-title">Decision signals</div>
                <div className="map-semantic-signal-list">
                  {selectedSemanticLink.edge.decisionSignals.map((signal) => (
                    <span key={signal}>{signal}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="map-inspector-block">
              <div className="map-inspector-title">Endpoints</div>
              <div className="map-semantic-endpoints">
                <section className="map-semantic-endpoint">
                  <span className="map-semantic-endpoint-kicker">{selectedSemanticLink.sourceGroup}</span>
                  <strong>{selectedSemanticLink.sourceNode?.label ?? selectedSemanticLink.edge.source}</strong>
                  <small>{presentValue(selectedSemanticLink.sourceNode?.relative_path || selectedSemanticLink.sourceNode?.source_file)}</small>
                </section>
                <section className="map-semantic-endpoint">
                  <span className="map-semantic-endpoint-kicker">{selectedSemanticLink.targetGroup}</span>
                  <strong>{selectedSemanticLink.targetNode?.label ?? selectedSemanticLink.edge.target}</strong>
                  <small>{presentValue(selectedSemanticLink.targetNode?.relative_path || selectedSemanticLink.targetNode?.source_file)}</small>
                </section>
              </div>
            </div>

            <div className="map-provenance-grid">
              <div className="map-provenance-row">
                <span>Source repo</span>
                <strong>{presentValue(selectedSemanticLink.sourceNode?.repo || selectedSemanticLink.sourceNode?.source_root_name)}</strong>
              </div>
              <div className="map-provenance-row">
                <span>Target repo</span>
                <strong>{presentValue(selectedSemanticLink.targetNode?.repo || selectedSemanticLink.targetNode?.source_root_name)}</strong>
              </div>
              <div className="map-provenance-row map-provenance-wide">
                <span>Source node</span>
                <strong>{selectedSemanticLink.edge.source}</strong>
              </div>
              <div className="map-provenance-row map-provenance-wide">
                <span>Target node</span>
                <strong>{selectedSemanticLink.edge.target}</strong>
              </div>
            </div>

            <div className="map-panel-actions">
              <button
                className="map-action-btn"
                onClick={() => startPathFrom(selectedSemanticLink.edge.source)}
              >
                Trace from source
              </button>
            </div>
          </aside>
        )}

        {/* Full-graph inspect panel */}
        {selectedFull && viewMode === "full" && !showOverlap && !selectedSemanticLink && (
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
              <span
                className={`map-type-badge map-importance-badge map-importance-${selectedFull.importance_tier ?? "evidence"}`}
                title={selectedFull.importance_reason || "File importance"}
              >
                {importanceTierLabel(selectedFull.importance_tier)}
              </span>
              <DecisionBadge classification={selectedFull.decision_overlay?.decision_classification || selectedFull.decision_classification} />
            </div>

            <div className="map-inspector-block">
              <div className="map-inspector-title">What this appears to do</div>
              <p className="map-inspector-purpose">
                {selectedFull.purpose || `${selectedFull.label} is a ${selectedFull.type} node. Source detail is limited for this item.`}
              </p>
            </div>

            <DecisionContextBlock overlay={selectedFull.decision_overlay} />

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
              <div className="map-provenance-row">
                <span>Importance</span>
                <strong>{presentValue(selectedFull.importance_reason)}</strong>
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

            <div className="map-panel-actions">
              <button
                className="map-action-btn"
                onClick={() => startPathFrom(selectedFull.id)}
              >
                Trace path from here
              </button>
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
              <DecisionBadge classification={selected.decision_overlay?.decision_classification || selected.decision_classification || decisions[selected.id]} />
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

            <DecisionContextBlock overlay={selected.decision_overlay} />

            {selected.is_gap && (
              <div className="map-gap-triage">
                <div className="map-gap-triage-head">
                  <span>Gap Triage</span>
                  <strong>{gapTypeLabel(selected.gap_type)}</strong>
                </div>
                <p>{selected.gap_detail || selected.gap_reason || "No visible group-to-group physical links at the current filters."}</p>
                {(selected.gap_evidence ?? []).length > 0 && (
                  <div className="map-gap-evidence">
                    {selected.gap_evidence?.map((item) => (
                      <span key={item}>{item}</span>
                    ))}
                  </div>
                )}
                <div className="map-gap-actions">
                  {selected.is_drillable && (
                    <button
                      className="map-action-btn map-action-primary"
                      onClick={() => handleDrillDown(selected)}
                    >
                      Drill In
                    </button>
                  )}
                  {selected.gap_actions?.includes("show_low_signal") && (
                    <button
                      className="map-action-btn"
                      onClick={() => {
                        setShowLowSignal(true);
                        setViewMode("full");
                        setFocusNotice({ tone: "info", text: "Opening Evidence with low-signal nodes included." });
                      }}
                    >
                      Show Low Signal
                    </button>
                  )}
                  <button
                    className="map-action-btn"
                    onClick={() => copyGapAskPrompt(selected)}
                  >
                    Copy Ask Prompt
                  </button>
                  <button
                    className="map-action-btn"
                    disabled={savingGapDecision !== null}
                    onClick={() => saveGapDecision(selected, "monitor")}
                  >
                    {savingGapDecision === "monitor" ? "Saving..." : "Mark Monitor"}
                  </button>
                  <button
                    className="map-action-btn"
                    disabled={savingGapDecision !== null}
                    onClick={() => saveGapDecision(selected, "archive")}
                  >
                    {savingGapDecision === "archive" ? "Saving..." : "Mark Archive"}
                  </button>
                </div>
              </div>
            )}

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
