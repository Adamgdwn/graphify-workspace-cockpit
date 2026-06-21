import { useState, useEffect, useRef, useCallback } from "react";
import { apiErrorMessage, apiFetch } from "../api/client";
import { SkeletonCard } from "../components/Skeleton";
import { useToast } from "../components/Toast";
import { WorkingStatus } from "../components/WorkingStatus";
import type { ActiveCockpitContext } from "../domain/cockpitContext";

// ── Types ─────────────────────────────────────────────────────────────────

type RecMode = "next-build" | "archive-candidates" | "duplicates";
type RecStatus = "pending" | "accepted" | "rejected" | "deferred";

interface Recommendation {
  id: string;
  mode: RecMode;
  title: string;
  summary: string;
  evidence: string[];
  confidence: number;
  risk: string;
  effort: string;
  proposed_action: string;
  status: RecStatus;
  created_at: string;
  updated_at: string;
  model: string;
  created_by?: string;
  action_plan?: ActionPlan;
  overlap_dossier?: OverlapDossier | null;
  context?: RecommendationContext;
  scope?: RecommendationScope;
}

interface RecommendationScope {
  kind: "current_map" | "other_map" | "system";
  label: string;
  matches_current_map?: boolean;
  graph_name?: string | null;
  graph_node_count?: number | null;
}

interface RecommendationContext {
  scope_name?: string;
  map?: {
    kind?: string;
    graph_fingerprint?: string | null;
    graph_name?: string;
    graph_node_count?: number;
    summary_node_count?: number | null;
  };
  included_context?: Array<{
    id: string;
    label: string;
    group_type?: string;
    node_count?: number;
  }>;
  major_exclusions?: {
    excluded_paths?: string[];
    default_patterns?: string[];
    hidden_low_signal_nodes?: number;
    scoped_excluded_nodes?: number;
  };
  token_savings?: {
    estimated_hidden_tokens_per_query?: number;
    basis?: string;
  };
}

interface ActionPlan {
  canonical_target?: string;
  merge_sources?: string[];
  concrete_steps?: string[];
  savings_estimate?: {
    duplicate_node_count?: number;
    affected_files?: number;
    semantic_edge_reduction?: number;
    rough_context_savings?: string;
    caveat?: string;
    [key: string]: string | number | undefined;
  };
  risks?: string[];
  acceptance_criteria?: string[];
  rollback_note?: string;
  open_questions?: string[];
  source_pairs?: string[];
  same_name_count?: number;
  proposed_action?: string;
}

interface OverlapDossier {
  evidence_summary?: string;
  per_side_purpose?: Record<string, string>;
  similarities?: string[];
  differences?: string[];
  canonicality_signals?: string[];
  open_questions?: string[];
}

interface PacketEvidenceNode {
  id: string;
  label: string;
  type?: string;
  cluster?: string;
  repo?: string;
  container?: string;
  relative_path?: string;
  source_file?: string;
  source_location?: string;
  symbol?: string;
  purpose?: string;
}

interface PacketAction {
  id: string;
  status: string;
  target_path?: string;
  dry_run_at?: string | null;
  approved_at?: string | null;
  executed_at?: string | null;
}

interface PacketDecision {
  id: string;
  target_id: string;
  label: string;
  classification: string;
  rationale?: string;
  status: string;
}

interface DecisionPacket {
  schema_version: string;
  id: string;
  created_at: string;
  recommendation: Recommendation;
  evidence: {
    nodes: PacketEvidenceNode[];
    overlap?: {
      cluster_a?: string;
      cluster_b?: string;
      edge_count?: number;
      avg_similarity?: number;
    } | null;
    overlap_dossier?: OverlapDossier | null;
  };
  judgement: {
    recommendation_status: RecStatus | string;
    confidence: number;
    risk: string;
    effort: string;
    model: string;
  };
  recommendation_plan?: ActionPlan | null;
  decisions: {
    related: PacketDecision[];
    count: number;
  };
  approval: {
    queued_actions: PacketAction[];
    queued_action_count: number;
    next_gate: string;
    execution_locked_to_work_queue: boolean;
  };
  operator_choices: string[];
  markdown: string;
}

// ── Constants ─────────────────────────────────────────────────────────────

const MODE_LABELS: Record<RecMode, string> = {
  "next-build":         "Next Build",
  "archive-candidates": "Archive Candidates",
  "duplicates":         "Duplicates",
};

const STATUS_COLOR: Record<string, string> = {
  pending:  "#6b8cff",
  accepted: "#4ade80",
  rejected: "#f87171",
  deferred: "#f97316",
};

const RISK_COLOR: Record<string, string> = {
  low:    "#4ade80",
  medium: "#f5d280",
  high:   "#f87171",
};

// ── Helpers ───────────────────────────────────────────────────────────────

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadText(text: string, filename: string, type = "text/markdown") {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Sub-components ────────────────────────────────────────────────────────

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  const color = pct >= 70 ? "#4ade80" : pct >= 40 ? "#f5d280" : "#9ca3af";
  return (
    <span className="rec-confidence" title={`Confidence: ${pct}%`}>
      <span className="rec-confidence-track">
        <span className="rec-confidence-bar" style={{ width: `${pct}%`, background: color }} />
      </span>
      <span className="rec-confidence-label" style={{ color }}>{pct}%</span>
    </span>
  );
}

function MetaBadge({ label, color }: { label: string; color: string }) {
  return (
    <span className="rec-meta-badge" style={{ color, borderColor: color }}>
      {label}
    </span>
  );
}

function listItems(items?: string[], limit = 5): string[] {
  return (items ?? []).map((item) => item.trim()).filter(Boolean).slice(0, limit);
}

function savingsItems(plan: ActionPlan): string[] {
  const savings = plan.savings_estimate;
  if (!savings) return [];
  const items: string[] = [];
  if (savings.duplicate_node_count !== undefined) items.push(`${savings.duplicate_node_count} top duplicate pair(s) to review`);
  if (savings.affected_files !== undefined) items.push(`${savings.affected_files} affected file(s)`);
  if (savings.semantic_edge_reduction !== undefined) items.push(`up to ${savings.semantic_edge_reduction} repeated semantic edge(s) to reduce`);
  if (savings.rough_context_savings) items.push(String(savings.rough_context_savings));
  if (savings.caveat) items.push(String(savings.caveat));
  return items;
}

function pct(value?: number): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "unknown";
  return `${Math.round(value * 100)}%`;
}

function recommendationScopeKind(rec: Recommendation): RecommendationScope["kind"] {
  return rec.scope?.kind ?? "system";
}

function recommendationScopeLabel(rec: Recommendation): string {
  const kind = recommendationScopeKind(rec);
  if (kind === "current_map") return "Current Map";
  if (kind === "other_map") return rec.scope?.graph_name ? `Other Map: ${rec.scope.graph_name}` : "Other Map";
  return "System";
}

function ActionPlanBlock({ plan }: { plan: ActionPlan }) {
  const sources = listItems(plan.merge_sources, 6);
  const steps = listItems(plan.concrete_steps, 6);
  const savings = savingsItems(plan);
  const risks = listItems(plan.risks, 5);
  const doneWhen = listItems(plan.acceptance_criteria, 5);
  const questions = listItems(plan.open_questions, 5);

  return (
    <div className="rec-action-plan">
      <div className="rec-plan-head">Implementation Brief</div>
      {plan.canonical_target && (
        <section className="rec-plan-section rec-plan-wide">
          <h4>Where</h4>
          <p>{plan.canonical_target}</p>
        </section>
      )}
      {sources.length > 0 && (
        <section className="rec-plan-section rec-plan-wide">
          <h4>Merge / Review Sources</h4>
          <ul>{sources.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      )}
      <div className="rec-plan-grid">
        {steps.length > 0 && (
          <section className="rec-plan-section">
            <h4>How</h4>
            <ol>{steps.map((item) => <li key={item}>{item}</li>)}</ol>
          </section>
        )}
        {savings.length > 0 && (
          <section className="rec-plan-section">
            <h4>Savings</h4>
            <ul>{savings.map((item) => <li key={item}>{item}</li>)}</ul>
          </section>
        )}
        {risks.length > 0 && (
          <section className="rec-plan-section">
            <h4>Risks</h4>
            <ul>{risks.map((item) => <li key={item}>{item}</li>)}</ul>
          </section>
        )}
        {doneWhen.length > 0 && (
          <section className="rec-plan-section">
            <h4>Done When</h4>
            <ul>{doneWhen.map((item) => <li key={item}>{item}</li>)}</ul>
          </section>
        )}
      </div>
      {questions.length > 0 && (
        <section className="rec-plan-section rec-plan-wide">
          <h4>Open Questions</h4>
          <ul>{questions.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      )}
      {plan.rollback_note && (
        <section className="rec-plan-section rec-plan-wide">
          <h4>Rollback</h4>
          <p>{plan.rollback_note}</p>
        </section>
      )}
    </div>
  );
}

function PacketList({ items, empty }: { items?: string[]; empty: string }) {
  const values = listItems(items, 5);
  if (values.length === 0) return <p className="rec-packet-muted">{empty}</p>;
  return <ul>{values.map((item) => <li key={item}>{item}</li>)}</ul>;
}

function DecisionPacketBlock({
  packet,
  onEvidenceNavigate,
}: {
  packet: DecisionPacket;
  onEvidenceNavigate?: (context: ActiveCockpitContext) => void;
}) {
  const plan = packet.recommendation_plan;
  const dossier = packet.evidence.overlap_dossier;
  const queuedActions = packet.approval.queued_actions ?? [];

  function handleCopyMarkdown() {
    void navigator.clipboard?.writeText(packet.markdown);
  }

  return (
    <div className="rec-decision-packet">
      <div className="rec-packet-head">
        <div>
          <span className="rec-packet-eyebrow">Decision Packet</span>
          <strong>{packet.recommendation.title}</strong>
        </div>
        <div className="rec-packet-tools">
          <button type="button" onClick={handleCopyMarkdown}>Copy MD</button>
          <button type="button" onClick={() => downloadText(packet.markdown, "decision-packet.md")}>Markdown</button>
          <button type="button" onClick={() => downloadJson(packet, "decision-packet.json")}>JSON</button>
        </div>
      </div>

      <div className="rec-packet-grid">
        <section className="rec-packet-section">
          <h4>Evidence</h4>
          {packet.evidence.nodes.length > 0 ? (
            <div className="rec-packet-node-list">
              {packet.evidence.nodes.map((node) => (
                <button
                  key={node.id}
                  type="button"
                  className="rec-packet-node"
                  onClick={() => onEvidenceNavigate?.({
                    kind: "node",
                    source: "recommendations",
                    nodeId: node.id,
                    label: node.label || node.id,
                    clusterId: node.cluster,
                    viewMode: "full",
                  })}
                  title="Open this evidence on the Map"
                >
                  <span>{node.label || node.id}</span>
                  <small>{node.repo || "unknown repo"} / {node.relative_path || node.source_file || "unknown path"}</small>
                  {node.purpose && <em>{node.purpose}</em>}
                </button>
              ))}
            </div>
          ) : (
            <p className="rec-packet-muted">No exact graph nodes matched this recommendation's evidence.</p>
          )}
        </section>

        <section className="rec-packet-section">
          <h4>Judgement</h4>
          <dl className="rec-packet-facts">
            <div><dt>Status</dt><dd>{packet.judgement.recommendation_status}</dd></div>
            <div><dt>Confidence</dt><dd>{pct(packet.judgement.confidence)}</dd></div>
            <div><dt>Risk</dt><dd>{packet.judgement.risk}</dd></div>
            <div><dt>Effort</dt><dd>{packet.judgement.effort}</dd></div>
          </dl>
          {dossier?.evidence_summary && <p>{dossier.evidence_summary}</p>}
        </section>

        <section className="rec-packet-section">
          <h4>Recommendation</h4>
          <p>{packet.recommendation.proposed_action || packet.recommendation.summary}</p>
          {plan?.canonical_target && <p className="rec-packet-target">Where: {plan.canonical_target}</p>}
          {plan && <PacketList items={plan.concrete_steps} empty="No concrete steps recorded." />}
        </section>

        <section className="rec-packet-section">
          <h4>Approval</h4>
          <p>{packet.approval.next_gate}</p>
          {queuedActions.length > 0 ? (
            <ul>
              {queuedActions.map((action) => (
                <li key={action.id}>{action.status}{action.target_path ? ` — ${action.target_path}` : ""}</li>
              ))}
            </ul>
          ) : (
            <p className="rec-packet-muted">No queued action yet.</p>
          )}
        </section>

        <section className="rec-packet-section">
          <h4>Decision Status</h4>
          {packet.decisions.related.length > 0 ? (
            <ul>
              {packet.decisions.related.map((decision) => (
                <li key={decision.id}>
                  <strong>{decision.target_id}</strong>: {decision.classification}
                  {decision.rationale ? ` — ${decision.rationale}` : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p className="rec-packet-muted">No active decision is linked to this evidence yet.</p>
          )}
        </section>

        <section className="rec-packet-section">
          <h4>Open Questions</h4>
          <PacketList
            items={plan?.open_questions ?? dossier?.open_questions}
            empty="No open questions recorded."
          />
        </section>
      </div>
    </div>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────

function RecCard({
  rec,
  onSetStatus,
  onQueue,
  onEvidenceNavigate,
  isQueuing,
  isQueued,
}: {
  rec: Recommendation;
  onSetStatus: (id: string, status: RecStatus) => void;
  onQueue: (id: string) => void;
  onEvidenceNavigate?: (context: ActiveCockpitContext) => void;
  isQueuing: boolean;
  isQueued: boolean;
}) {
  const statusColor = STATUS_COLOR[rec.status] ?? "#9ca3af";
  const riskColor   = RISK_COLOR[rec.risk]   ?? "#9ca3af";
  const effortColor = RISK_COLOR[rec.effort] ?? "#9ca3af";
  const scopeKind = recommendationScopeKind(rec);
  const [packetOpen, setPacketOpen] = useState(false);
  const [packet, setPacket] = useState<DecisionPacket | null>(null);
  const [packetLoading, setPacketLoading] = useState(false);
  const [packetError, setPacketError] = useState<string | null>(null);

  useEffect(() => {
    if (!packetOpen || packet || packetLoading) return;
    let cancelled = false;
    async function loadPacket() {
      setPacketLoading(true);
      setPacketError(null);
      try {
        const r = await apiFetch(`/decision-packets/recommendations/${rec.id}`);
        if (!r.ok) throw new Error(await apiErrorMessage(r));
        const data: DecisionPacket = await r.json();
        if (!cancelled) setPacket(data);
      } catch (e) {
        if (!cancelled) setPacketError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setPacketLoading(false);
      }
    }
    void loadPacket();
    return () => { cancelled = true; };
  }, [packetOpen, packet, packetLoading, rec.id]);

  return (
    <div
      className="rec-card"
      style={{ "--status-color": statusColor } as React.CSSProperties}
    >
      {/* Header */}
      <div className="rec-card-head">
        <div className="rec-card-title-row">
          <span className="rec-card-title">{rec.title}</span>
          <span className="rec-mode-badge">{MODE_LABELS[rec.mode] ?? rec.mode}</span>
          <span className={`rec-scope-badge rec-scope-${scopeKind.replace("_", "-")}`}>
            {recommendationScopeLabel(rec)}
          </span>
        </div>
        <span
          className="rec-status-badge"
          style={{ color: statusColor, borderColor: statusColor }}
        >
          {rec.status}
        </span>
      </div>

      {/* Summary */}
      <p className="rec-card-summary">{rec.summary}</p>

      {rec.context && (
        <div className="rec-context-strip">
          <span>{rec.context.scope_name || "Active scope"}</span>
          {rec.context.map?.graph_name && (
            <span>{rec.context.map.graph_name}</span>
          )}
          <span>
            {(rec.context.included_context?.length ?? 0)} groups included
          </span>
          <span>
            {((rec.context.major_exclusions?.hidden_low_signal_nodes ?? 0) +
              (rec.context.major_exclusions?.scoped_excluded_nodes ?? 0)).toLocaleString()} hidden/excluded
          </span>
          {(rec.context.token_savings?.estimated_hidden_tokens_per_query ?? 0) > 0 && (
            <span>
              ~{rec.context.token_savings?.estimated_hidden_tokens_per_query?.toLocaleString()} tokens saved
            </span>
          )}
        </div>
      )}

      {/* Evidence chips */}
      {rec.evidence.length > 0 && (
        <div className="rec-evidence-row">
          <span className="rec-evidence-label">Evidence:</span>
          <div className="rec-evidence-chips">
            {rec.evidence.map((e) => (
              <button
                key={e}
                type="button"
                className="rec-evidence-chip"
                onClick={() => onEvidenceNavigate?.({
                  kind: "node",
                  source: "recommendations",
                  nodeId: e,
                  label: e,
                })}
                title="Open this evidence on the Map"
              >
                {e}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Proposed action */}
      {rec.proposed_action && (
        <div className="rec-proposed-action">
          <span className="rec-proposed-label">Next action:</span>
          {rec.proposed_action}
        </div>
      )}

      {rec.action_plan && <ActionPlanBlock plan={rec.action_plan} />}

      <div className="rec-packet-toggle-row">
        <button
          type="button"
          className="rec-packet-toggle"
          onClick={() => setPacketOpen((open) => !open)}
        >
          {packetOpen ? "Hide Decision Packet" : "Review Decision Packet"}
        </button>
        {packetOpen && (
          <button
            type="button"
            className="rec-packet-toggle rec-packet-refresh"
            onClick={() => {
              setPacket(null);
              setPacketError(null);
            }}
          >
            Refresh Packet
          </button>
        )}
      </div>

      {packetOpen && (
        packetLoading ? (
          <div className="rec-packet-loading">
            <WorkingStatus label="Loading decision packet" />
          </div>
        ) : packetError ? (
          <div className="rec-packet-error">Decision packet unavailable: {packetError}</div>
        ) : packet ? (
          <DecisionPacketBlock packet={packet} onEvidenceNavigate={onEvidenceNavigate} />
        ) : null
      )}

      {/* Meta row */}
      <div className="rec-meta-row">
        <ConfidenceMeter value={rec.confidence} />
        <MetaBadge label={`risk: ${rec.risk}`} color={riskColor} />
        <MetaBadge label={`effort: ${rec.effort}`} color={effortColor} />
        <span className="rec-model-tag">{rec.model}</span>
        {rec.created_by && rec.created_by !== "local" && (
          <span className="rec-model-tag" style={{ opacity: 0.65 }}>{rec.created_by}</span>
        )}
      </div>

      {/* Action row */}
      {rec.status === "pending" ? (
        <div className="rec-action-row">
          <button
            className="rec-action-btn accept"
            onClick={() => onSetStatus(rec.id, "accepted")}
          >
            Accept
          </button>
          <button
            className="rec-action-btn defer"
            onClick={() => onSetStatus(rec.id, "deferred")}
          >
            Defer
          </button>
          <button
            className="rec-action-btn reject"
            onClick={() => onSetStatus(rec.id, "rejected")}
          >
            Reject
          </button>
        </div>
      ) : (
        <div className="rec-action-row">
          {rec.status === "accepted" && (
            <button
              className="rec-action-btn queue"
              disabled={isQueuing || isQueued}
              onClick={() => onQueue(rec.id)}
            >
              {isQueuing ? "Queuing…" : isQueued ? "Queued ✓" : "Queue Action"}
            </button>
          )}
          <button
            className="rec-action-btn reopen"
            onClick={() => onSetStatus(rec.id, "pending")}
          >
            Reopen
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

const FILTERS = ["all", "pending", "accepted", "deferred", "rejected"] as const;
type FilterValue = (typeof FILTERS)[number];
const SCOPE_FILTERS = ["current-map", "system", "other-maps", "all"] as const;
type ScopeFilterValue = (typeof SCOPE_FILTERS)[number];

const SCOPE_FILTER_LABELS: Record<ScopeFilterValue, string> = {
  "current-map": "Current Map",
  system: "System",
  "other-maps": "Other Maps",
  all: "All",
};

export function Recommendations({ onEvidenceNavigate }: { onEvidenceNavigate?: (context: ActiveCockpitContext) => void }) {
  const [recs, setRecs]               = useState<Recommendation[]>([]);
  const [loading, setLoading]         = useState(true);
  const [generating, setGenerating]   = useState<RecMode | null>(null);
  const [error, setError]             = useState<string | null>(null);
  const [filter, setFilter]           = useState<FilterValue>("all");
  const [scopeFilter, setScopeFilter] = useState<ScopeFilterValue>("current-map");
  const [queuing, setQueuing]         = useState<string | null>(null);
  const [queuedIds, setQueuedIds]     = useState<Set<string>>(new Set());
  const etagRef = useRef<string>("");
  const { addToast } = useToast();

  const fetchRecs = useCallback(async () => {
    try {
      const headers: Record<string, string> = {};
      if (etagRef.current) headers["If-None-Match"] = etagRef.current;
      const r = await apiFetch(`/recommendations`, { headers });
      if (r.status === 304) return;
      if (!r.ok) throw new Error(await apiErrorMessage(r));
      etagRef.current = r.headers.get("ETag") ?? "";
      setRecs(await r.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecs();
    const interval = setInterval(fetchRecs, 15000);
    return () => clearInterval(interval);
  }, [fetchRecs]);

  async function generate(mode: RecMode) {
    setGenerating(mode);
    setError(null);
    try {
      const r = await apiFetch(`/recommendations/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
      }
      const newRec: Recommendation = await r.json();
      setRecs((prev) => [newRec, ...prev]);
      setScopeFilter("current-map");
      setFilter("pending");
      addToast(`${MODE_LABELS[mode]} recommendation generated`, "success");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      addToast(msg, "error");
    } finally {
      setGenerating(null);
    }
  }

  async function setStatus(id: string, status: RecStatus) {
    try {
      const r = await apiFetch(`/recommendations/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!r.ok) throw new Error(await apiErrorMessage(r));
      const updated: Recommendation = await r.json();
      setRecs((prev) => prev.map((rec) => (rec.id === id ? updated : rec)));
      addToast(`Recommendation ${status}`, "success");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      addToast(msg, "error");
    }
  }

  async function queueRec(id: string) {
    if (queuing) return;
    setQueuing(id);
    setError(null);
    try {
      const r = await apiFetch(`/recommendations/${id}/queue`, { method: "POST" });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
      }
      setQueuedIds((prev) => new Set([...prev, id]));
      addToast("Action queued — check Work Queue", "success");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      addToast(msg, "error");
    } finally {
      setQueuing(null);
    }
  }

  function handleExport() {
    const exportData = filtered;
    downloadJson(exportData, "recommendations.json");
    addToast("Recommendations exported", "info");
  }

  const scopedRecs = recs.filter((rec) => {
    const kind = recommendationScopeKind(rec);
    if (scopeFilter === "current-map") return kind === "current_map";
    if (scopeFilter === "system") return kind === "system";
    if (scopeFilter === "other-maps") return kind === "other_map";
    return true;
  });
  const filtered     = filter === "all" ? scopedRecs : scopedRecs.filter((r) => r.status === filter);
  const scopeCounts: Record<ScopeFilterValue, number> = {
    "current-map": recs.filter((rec) => recommendationScopeKind(rec) === "current_map").length,
    system: recs.filter((rec) => recommendationScopeKind(rec) === "system").length,
    "other-maps": recs.filter((rec) => recommendationScopeKind(rec) === "other_map").length,
    all: recs.length,
  };
  const pendingCount = scopedRecs.filter((r) => r.status === "pending").length;

  return (
    <div className="rec-pane">
      {/* Generate bar */}
      <div className="rec-generate-bar">
        <span className="rec-generate-label">Generate:</span>
        {(["next-build", "archive-candidates", "duplicates"] as RecMode[]).map((mode) => (
          <button
            key={mode}
            className={`rec-generate-btn${generating === mode ? " active" : ""}`}
            disabled={generating !== null}
            onClick={() => generate(mode)}
          >
            {generating === mode ? "Generating…" : MODE_LABELS[mode]}
          </button>
        ))}
      </div>

      <div className="rec-filter-bar rec-scope-filter-bar" aria-label="Recommendation scope">
        {SCOPE_FILTERS.map((scope) => (
          <button
            key={scope}
            className={`rec-filter-btn${scopeFilter === scope ? " active" : ""}`}
            onClick={() => setScopeFilter(scope)}
            type="button"
          >
            {SCOPE_FILTER_LABELS[scope]}
            {scopeCounts[scope] > 0 && (
              <span className="rec-filter-count">{scopeCounts[scope]}</span>
            )}
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <div className="rec-filter-bar">
        {FILTERS.map((f) => (
          <button
            key={f}
            className={`rec-filter-btn${filter === f ? " active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
            {f === "pending" && pendingCount > 0 && (
              <span className="rec-filter-count">{pendingCount}</span>
            )}
          </button>
        ))}
        {!loading && recs.length > 0 && (
          <button type="button" className="export-btn" onClick={handleExport}>
            Export JSON
          </button>
        )}
      </div>

      {error && <div className="rec-error">{error}</div>}

      {/* Card list */}
      <div className="rec-list">
        {loading && (
          <>
            <WorkingStatus label="Loading recommendations" detail="Reading saved decision suggestions" />
            <SkeletonCard lines={4} />
            <SkeletonCard lines={3} />
            <SkeletonCard lines={4} />
          </>
        )}
        {!loading && filtered.length === 0 && (
          <div className="rec-empty">
            {scopeFilter === "current-map" ? (
              <>
                <p className="rec-empty-msg">No recommendations for the current map.</p>
                <p className="rec-empty-hint">System and older map cards are still available in the scope filters above.</p>
              </>
            ) : filter === "all" ? (
              <>
                <p className="rec-empty-msg">No recommendations yet.</p>
                <p className="rec-empty-hint">Use the Generate buttons above to create your first recommendation from the workspace graph.</p>
              </>
            ) : (
              <p className="rec-empty-msg">No {filter} recommendations.</p>
            )}
          </div>
        )}
        {filtered.map((rec) => (
          <RecCard
            key={rec.id}
            rec={rec}
            onSetStatus={setStatus}
            onQueue={queueRec}
            onEvidenceNavigate={onEvidenceNavigate}
            isQueuing={queuing === rec.id}
            isQueued={queuedIds.has(rec.id)}
          />
        ))}
      </div>
    </div>
  );
}
