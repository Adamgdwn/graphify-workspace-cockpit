import { useState, useEffect, useRef, useCallback } from "react";
import { API } from "../config";
import { SkeletonCard } from "../components/Skeleton";
import { useToast } from "../components/Toast";
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

export function Recommendations({ onEvidenceNavigate }: { onEvidenceNavigate?: (context: ActiveCockpitContext) => void }) {
  const [recs, setRecs]               = useState<Recommendation[]>([]);
  const [loading, setLoading]         = useState(true);
  const [generating, setGenerating]   = useState<RecMode | null>(null);
  const [error, setError]             = useState<string | null>(null);
  const [filter, setFilter]           = useState<FilterValue>("all");
  const [queuing, setQueuing]         = useState<string | null>(null);
  const [queuedIds, setQueuedIds]     = useState<Set<string>>(new Set());
  const etagRef = useRef<string>("");
  const { addToast } = useToast();

  const fetchRecs = useCallback(async () => {
    try {
      const headers: Record<string, string> = {};
      if (etagRef.current) headers["If-None-Match"] = etagRef.current;
      const r = await fetch(`${API}/recommendations`, { headers });
      if (r.status === 304) return;
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
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
      const r = await fetch(`${API}/recommendations/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      if (!r.ok) {
        const detail = await r.json().catch(() => ({})) as { detail?: string };
        throw new Error(detail?.detail ?? `HTTP ${r.status}`);
      }
      const newRec: Recommendation = await r.json();
      setRecs((prev) => [newRec, ...prev]);
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
      const r = await fetch(`${API}/recommendations/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
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
      const r = await fetch(`${API}/recommendations/${id}/queue`, { method: "POST" });
      if (!r.ok) {
        const detail = await r.json().catch(() => ({})) as { detail?: string };
        throw new Error(detail?.detail ?? `HTTP ${r.status}`);
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
    const exportData = filter === "all" ? recs : recs.filter((r) => r.status === filter);
    downloadJson(exportData, "recommendations.json");
    addToast("Recommendations exported", "info");
  }

  const filtered     = filter === "all" ? recs : recs.filter((r) => r.status === filter);
  const pendingCount = recs.filter((r) => r.status === "pending").length;

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
            <SkeletonCard lines={4} />
            <SkeletonCard lines={3} />
            <SkeletonCard lines={4} />
          </>
        )}
        {!loading && filtered.length === 0 && (
          <div className="rec-empty">
            {filter === "all" ? (
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
