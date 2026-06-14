import { useState, useEffect, useCallback } from "react";

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
}

// ── Constants ─────────────────────────────────────────────────────────────

const API = "http://localhost:8000";

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
}: {
  rec: Recommendation;
  onSetStatus: (id: string, status: RecStatus) => void;
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
              <span key={e} className="rec-evidence-chip">{e}</span>
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

export function Recommendations() {
  const [recs, setRecs]           = useState<Recommendation[]>([]);
  const [loading, setLoading]     = useState(true);
  const [generating, setGenerating] = useState<RecMode | null>(null);
  const [error, setError]         = useState<string | null>(null);
  const [filter, setFilter]       = useState<FilterValue>("all");

  const fetchRecs = useCallback(async () => {
    try {
      const r = await fetch(`${API}/recommendations`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setRecs(await r.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRecs(); }, [fetchRecs]);

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
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
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
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
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
      </div>

      {error && <div className="rec-error">{error}</div>}

      {/* Card list */}
      <div className="rec-list">
        {loading && <div className="rec-empty">Loading…</div>}
        {!loading && filtered.length === 0 && (
          <div className="rec-empty">
            {filter === "all"
              ? "No recommendations yet. Use the buttons above to generate your first card."
              : `No ${filter} recommendations.`}
          </div>
        )}
        {filtered.map((rec) => (
          <RecCard key={rec.id} rec={rec} onSetStatus={setStatus} />
        ))}
      </div>
    </div>
  );
}
