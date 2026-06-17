import { useCallback, useEffect, useMemo, useState } from "react";
import { API_AUTH_ERROR_MESSAGE, apiErrorMessage, apiFetch } from "../api/client";
import type { ActiveCockpitContext } from "../domain/cockpitContext";

export type DashboardDestination = "map" | "recommendations" | "work-queue" | "settings";

type RecStatus = "pending" | "accepted" | "rejected" | "deferred";
type ActionStatus = "pending" | "dry-run-ready" | "executed" | "failed";
type JobStatus = "idle" | "running" | "complete" | "error";
type OverlapWorkflowStatus = "untriaged" | "triaged" | "task-created" | "dismissed";

interface Recommendation {
  id: string;
  title: string;
  status: RecStatus;
}

interface QueuedAction {
  id: string;
  source_recommendation_id: string;
  description: string;
  status: ActionStatus;
}

interface OverlapPair {
  source: string;
  target: string;
  label_a?: string;
  label_b?: string;
  labelA?: string;
  labelB?: string;
  similarity?: number;
}

interface OverlapGroup {
  cluster_a: string;
  cluster_b: string;
  edge_count: number;
  avg_similarity: number;
  top_pairs: OverlapPair[];
}

interface OverlapReport {
  groups: OverlapGroup[];
  created_at: string | null;
}

interface OverlapStatusRecord {
  status: OverlapWorkflowStatus;
}

interface JobFreshness {
  status: JobStatus;
  last_run?: string | null;
  error?: string | null;
}

interface SemanticEdges {
  edges: unknown[];
  created_at?: string | null;
}

interface OrgSettings {
  active_graph?: { name: string; path: string };
  graph_stats?: { raw_node_count: number; estimated_tokens_saved_per_query: number };
}

type ReadinessState = "ready" | "partial" | "not_ready";

interface RuntimeAction {
  label: string;
  destination?: DashboardDestination;
}

interface RuntimeWarning {
  code: string;
  severity: "warning" | "error";
  message: string;
  action?: RuntimeAction;
}

interface RuntimeStatus {
  state: ReadinessState;
  summary: string;
  backend: { online: boolean; version: string };
  graph: {
    valid: boolean;
    exists: boolean;
    name: string;
    node_count: number;
    link_count: number;
    error?: string | null;
  };
  graphify: { available: boolean; code?: string | null; message?: string | null };
  ollama: { connected: boolean; models: string[]; url: string };
  auth: { api_key_required: boolean };
  connectors: {
    configured_count: number;
    authenticated_count: number;
    syncing_count: number;
    error_count: number;
    error?: string | null;
  };
  warnings: RuntimeWarning[];
  next_best_action: RuntimeAction;
}

interface DashboardProps {
  onNavigate: (destination: DashboardDestination) => void;
  onNavigateMapContext: (context: ActiveCockpitContext) => void;
}

const FRESH_HOURS = 24;

async function fetchJson<T>(path: string): Promise<T> {
  const response = await apiFetch(`${path}`);
  if (!response.ok) throw new Error(`${path}: ${await apiErrorMessage(response)}`);
  return response.json() as Promise<T>;
}

function overlapKey(group: Pick<OverlapGroup, "cluster_a" | "cluster_b">) {
  return `${group.cluster_a}___${group.cluster_b}`;
}

function hoursSince(iso?: string | null): number | null {
  if (!iso) return null;
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return null;
  return (Date.now() - time) / 36e5;
}

function freshnessLabel(iso?: string | null): string {
  const hours = hoursSince(iso);
  if (hours === null) return "No completed run recorded";
  if (hours < 1) return "Updated within the hour";
  if (hours < 24) return `Updated ${Math.floor(hours)}h ago`;
  return `Updated ${Math.floor(hours / 24)}d ago`;
}

function needsFreshnessAttention(status: JobStatus, lastRun?: string | null) {
  if (status === "running" || status === "error") return true;
  const hours = hoursSince(lastRun);
  return hours === null || hours > FRESH_HOURS;
}

function AttentionCard({
  count,
  label,
  detail,
  action,
  tone,
  onClick,
}: {
  count: number | string;
  label: string;
  detail: string;
  action: string;
  tone: "blue" | "green" | "amber" | "red" | "slate";
  onClick: () => void;
}) {
  return (
    <button type="button" className={`dash-card dash-card-${tone}`} onClick={onClick}>
      <span className="dash-card-count">{count}</span>
      <span className="dash-card-label">{label}</span>
      <span className="dash-card-detail">{detail}</span>
      <span className="dash-card-action">{action}</span>
    </button>
  );
}

function ReadinessPanel({
  status,
  error,
  onNavigate,
}: {
  status: RuntimeStatus | null;
  error: string | null;
  onNavigate: (destination: DashboardDestination) => void;
}) {
  const authError = Boolean(error?.includes(API_AUTH_ERROR_MESSAGE));
  const state = status?.state ?? (error ? "not_ready" : "partial");
  const label = state === "ready" ? "Ready" : state === "partial" ? "Partial" : "Not Ready";
  const summary = status?.summary ?? (
    authError
      ? "API key required before runtime readiness can be checked."
      : error
        ? "Runtime readiness could not be checked."
        : "Checking runtime readiness..."
  );
  const warnings = status?.warnings ?? (
    error
      ? [{
          code: authError ? "AUTH_REQUIRED" : "RUNTIME_STATUS_UNAVAILABLE",
          severity: "error" as const,
          message: authError ? API_AUTH_ERROR_MESSAGE : error,
          action: { label: "Open Settings", destination: "settings" as const },
        }]
      : []
  );
  const action = status?.next_best_action ?? (
    error ? { label: "Open Settings", destination: "settings" as const } : null
  );
  const chips = status
    ? [
        { label: "Backend", ok: status.backend.online, detail: status.backend.version },
        {
          label: "Graph",
          ok: status.graph.valid,
          detail: status.graph.valid
            ? `${status.graph.node_count.toLocaleString()} nodes / ${status.graph.link_count.toLocaleString()} links`
            : status.graph.exists ? "Invalid" : "Missing",
        },
        { label: "Graphify", ok: status.graphify.available, detail: status.graphify.available ? "Available" : "Missing" },
        {
          label: "Ollama",
          ok: status.ollama.connected,
          detail: status.ollama.connected ? `${status.ollama.models.length} model${status.ollama.models.length === 1 ? "" : "s"}` : "Offline",
        },
        { label: "Auth", ok: true, detail: status.auth.api_key_required ? "Required" : "Local" },
        {
          label: "Connectors",
          ok: !status.connectors.error && status.connectors.error_count === 0
            && status.connectors.authenticated_count >= status.connectors.configured_count,
          detail: status.connectors.configured_count
            ? `${status.connectors.authenticated_count}/${status.connectors.configured_count} connected`
            : "Optional",
        },
      ]
    : [{ label: "Runtime", ok: false, detail: error ? "Unavailable" : "Checking" }];

  return (
    <section className={`dash-readiness dash-readiness-${state}`}>
      <div className="dash-readiness-main">
        <div className="dash-readiness-heading">
          <span className="dash-readiness-label">{label}</span>
          <span>{summary}</span>
        </div>
        <div className="dash-readiness-chips">
          {chips.map((chip) => (
            <span key={chip.label} className={`dash-readiness-chip${chip.ok ? "" : " dash-readiness-chip-warn"}`}>
              <span className="dash-readiness-chip-label">{chip.label}</span>
              <span>{chip.detail}</span>
            </span>
          ))}
        </div>
        <div className="dash-readiness-warnings">
          {warnings.length
            ? warnings.slice(0, 2).map((warning) => <span key={warning.code}>{warning.message}</span>)
            : <span>No runtime warnings detected.</span>}
        </div>
      </div>
      {action?.destination && (
        <button type="button" className="dash-readiness-action" onClick={() => onNavigate(action.destination!)}>
          {action.label}
        </button>
      )}
    </section>
  );
}

export function Dashboard({ onNavigate, onNavigateMapContext }: DashboardProps) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [actions, setActions] = useState<QueuedAction[]>([]);
  const [overlapReport, setOverlapReport] = useState<OverlapReport>({ groups: [], created_at: null });
  const [overlapStatuses, setOverlapStatuses] = useState<Record<string, OverlapStatusRecord>>({});
  const [rebuild, setRebuild] = useState<JobFreshness>({ status: "idle", last_run: null });
  const [semantic, setSemantic] = useState<JobFreshness>({ status: "idle", last_run: null });
  const [semanticEdges, setSemanticEdges] = useState<SemanticEdges>({ edges: [], created_at: null });
  const [org, setOrg] = useState<OrgSettings>({});
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [runtimeStatusError, setRuntimeStatusError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    const results = await Promise.allSettled([
      fetchJson<Recommendation[]>("/recommendations"),
      fetchJson<QueuedAction[]>("/actions"),
      fetchJson<OverlapReport>("/graph/overlap-report"),
      fetchJson<{ pairs?: Record<string, OverlapStatusRecord> }>("/overlap/status"),
      fetchJson<JobFreshness>("/graph/rebuild/status"),
      fetchJson<JobFreshness>("/graph/semantic-pass/status"),
      fetchJson<SemanticEdges>("/graph/semantic-edges"),
      fetchJson<OrgSettings>("/settings/org"),
      fetchJson<RuntimeStatus>("/runtime/status"),
    ]);

    const failures = results.filter((result) => result.status === "rejected");
    if (results[0].status === "fulfilled") setRecommendations(results[0].value);
    if (results[1].status === "fulfilled") setActions(results[1].value);
    if (results[2].status === "fulfilled") setOverlapReport(results[2].value);
    if (results[3].status === "fulfilled") setOverlapStatuses(results[3].value.pairs ?? {});
    if (results[4].status === "fulfilled") setRebuild(results[4].value);
    if (results[5].status === "fulfilled") setSemantic(results[5].value);
    if (results[6].status === "fulfilled") setSemanticEdges(results[6].value);
    if (results[7].status === "fulfilled") setOrg(results[7].value);
    if (results[8].status === "fulfilled") {
      setRuntimeStatus(results[8].value);
      setRuntimeStatusError(null);
    } else {
      setRuntimeStatus(null);
      setRuntimeStatusError(results[8].reason instanceof Error ? results[8].reason.message : "Runtime status unavailable");
    }
    if (failures.length) setError(`${failures.length} dashboard source${failures.length === 1 ? "" : "s"} could not be refreshed.`);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 20000);
    return () => clearInterval(interval);
  }, [refresh]);

  const queuedRecommendationIds = useMemo(
    () => new Set(actions.map((action) => action.source_recommendation_id).filter(Boolean)),
    [actions],
  );

  const pendingRecommendations = recommendations.filter((rec) => rec.status === "pending");
  const acceptedNotQueued = recommendations.filter((rec) => rec.status === "accepted" && !queuedRecommendationIds.has(rec.id));
  const dryRunReadyActions = actions.filter((action) => action.status === "dry-run-ready");
  const untriagedOverlaps = overlapReport.groups.filter((group) => {
    const record = overlapStatuses[overlapKey(group)];
    return (record?.status ?? "untriaged") === "untriaged";
  });

  const semanticLastRun = semantic.last_run ?? semanticEdges.created_at ?? null;
  const graphNeedsAttention = needsFreshnessAttention(rebuild.status, rebuild.last_run);
  const semanticNeedsAttention = needsFreshnessAttention(semantic.status, semanticLastRun);
  const runtimeNeedsAttention = Boolean(runtimeStatusError || (runtimeStatus && runtimeStatus.state !== "ready"));
  const attentionTotal =
    pendingRecommendations.length +
    acceptedNotQueued.length +
    dryRunReadyActions.length +
    untriagedOverlaps.length +
    (graphNeedsAttention ? 1 : 0) +
    (semanticNeedsAttention ? 1 : 0) +
    (runtimeNeedsAttention ? 1 : 0);

  function openTopUntriagedOverlap() {
    const group = untriagedOverlaps[0];
    if (!group) {
      onNavigate("map");
      return;
    }
    const pair = group.top_pairs?.[0];
    onNavigateMapContext({
      kind: "overlap-pair",
      source: "dashboard",
      clusterA: group.cluster_a,
      clusterB: group.cluster_b,
      sourceNodeId: pair?.source,
      targetNodeId: pair?.target,
      labelA: pair?.label_a ?? pair?.labelA,
      labelB: pair?.label_b ?? pair?.labelB,
      similarity: pair?.similarity,
    });
  }

  return (
    <div className="dash-pane">
      <div className="dash-header">
        <div>
          <h1 className="dash-title">Command Center</h1>
          <p className="dash-subtitle">
            {loading ? "Refreshing decision signals..." : `${attentionTotal} item${attentionTotal === 1 ? "" : "s"} need operator attention`}
          </p>
        </div>
        <button type="button" className="dash-refresh" onClick={refresh} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <ReadinessPanel status={runtimeStatus} error={runtimeStatusError} onNavigate={onNavigate} />

      {error && <div className="dash-error">{error}</div>}

      <div className="dash-grid">
        <AttentionCard
          count={pendingRecommendations.length}
          label="Pending Recommendations"
          detail={pendingRecommendations[0]?.title ?? "No recommendation reviews waiting"}
          action="Review"
          tone={pendingRecommendations.length ? "blue" : "slate"}
          onClick={() => onNavigate("recommendations")}
        />
        <AttentionCard
          count={acceptedNotQueued.length}
          label="Accepted, Not Queued"
          detail={acceptedNotQueued[0]?.title ?? "Accepted work is already queued or clear"}
          action="Queue"
          tone={acceptedNotQueued.length ? "green" : "slate"}
          onClick={() => onNavigate("recommendations")}
        />
        <AttentionCard
          count={dryRunReadyActions.length}
          label="Dry-Run Ready Actions"
          detail={dryRunReadyActions[0]?.description ?? "No action previews awaiting approval"}
          action="Approve"
          tone={dryRunReadyActions.length ? "amber" : "slate"}
          onClick={() => onNavigate("work-queue")}
        />
        <AttentionCard
          count={untriagedOverlaps.length}
          label="Untriaged Overlaps"
          detail={
            untriagedOverlaps[0]
              ? `${untriagedOverlaps[0].cluster_a} ↔ ${untriagedOverlaps[0].cluster_b}`
              : "Overlap review queue is clear"
          }
          action="Open Map"
          tone={untriagedOverlaps.length ? "red" : "slate"}
          onClick={openTopUntriagedOverlap}
        />
      </div>

      <div className="dash-lower">
        <section className="dash-section">
          <div className="dash-section-title">Freshness</div>
          <button
            type="button"
            className={`dash-freshness-row${graphNeedsAttention ? " dash-freshness-warn" : ""}`}
            onClick={() => onNavigate("settings")}
          >
            <span className="dash-freshness-name">Graph rebuild</span>
            <span>{rebuild.status === "error" ? rebuild.error ?? "Rebuild error" : freshnessLabel(rebuild.last_run)}</span>
          </button>
          <button
            type="button"
            className={`dash-freshness-row${semanticNeedsAttention ? " dash-freshness-warn" : ""}`}
            onClick={() => onNavigate("settings")}
          >
            <span className="dash-freshness-name">Semantic pass</span>
            <span>{semantic.status === "error" ? semantic.error ?? "Semantic pass error" : freshnessLabel(semanticLastRun)}</span>
          </button>
        </section>

        <section className="dash-section">
          <div className="dash-section-title">Active Graph</div>
          <div className="dash-graph-name">{org.active_graph?.name ?? "No graph selected"}</div>
          <div className="dash-graph-meta">
            {(org.graph_stats?.raw_node_count ?? 0).toLocaleString()} nodes
            {" · "}
            {semanticEdges.edges.length.toLocaleString()} semantic edges
          </div>
          <div className="dash-graph-meta">
            ~{(org.graph_stats?.estimated_tokens_saved_per_query ?? 0).toLocaleString()} tokens saved per query
          </div>
        </section>
      </div>

      {!loading && attentionTotal === 0 && (
        <div className="dash-calm">
          No decision bottlenecks are visible right now. The core queues are clear and the graph signals are fresh.
        </div>
      )}
    </div>
  );
}
