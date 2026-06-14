import { useEffect, useState, type FormEvent } from "react";

// ── Types ─────────────────────────────────────────────────────────────────

type Classification = "invest" | "client-ready" | "monitor" | "archive" | "paused";

interface DecisionRecord {
  id: string;
  target_id: string;
  label: string;
  classification: Classification;
  rationale: string;
  created_at: string;
  updated_at: string;
  status: "active" | "retired";
}

// ── Classification metadata ───────────────────────────────────────────────

const CLASSIFICATIONS: {
  id: Classification;
  label: string;
  color: string;
  bg: string;
  description: string;
}[] = [
  { id: "invest",       label: "Invest",       color: "#4ade80", bg: "#071a0f", description: "Actively build or expand" },
  { id: "client-ready", label: "Client Ready", color: "#f5d280", bg: "#1e1608", description: "Presentable to clients" },
  { id: "monitor",      label: "Monitor",      color: "#6b8cff", bg: "#08102a", description: "Watch, no action yet" },
  { id: "archive",      label: "Archive",      color: "#9ca3af", bg: "#111318", description: "Wind down or deprecate" },
  { id: "paused",       label: "Paused",       color: "#f97316", bg: "#1c0e04", description: "On hold" },
];

function classificationMeta(id: string) {
  return CLASSIFICATIONS.find((c) => c.id === id) ?? CLASSIFICATIONS[2];
}

// ── Helpers ───────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-CA", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const API = "http://localhost:8000";

// ── Component ─────────────────────────────────────────────────────────────

const BLANK = { target_id: "", classification: "" as Classification | "", rationale: "" };

export function Decisions() {
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ ...BLANK });
  const [areas, setAreas] = useState<string[]>([]);
  const [showRetired, setShowRetired] = useState(false);

  async function fetchDecisions() {
    try {
      const r = await fetch(`${API}/decisions`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setDecisions(await r.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchDecisions();
    // Fetch known graph areas for autocomplete datalist
    fetch(`${API}/graph/summary`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.nodes) setAreas(data.nodes.map((n: { id: string }) => n.id));
      })
      .catch(() => {});
  }, []);

  function startEdit(d: DecisionRecord) {
    setEditId(d.id);
    setForm({ target_id: d.target_id, classification: d.classification, rationale: d.rationale });
  }

  function cancelForm() {
    setEditId(null);
    setForm({ ...BLANK });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.target_id.trim() || !form.classification) return;
    setSaving(true);
    try {
      if (editId) {
        const r = await fetch(`${API}/decisions/${editId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ classification: form.classification, rationale: form.rationale }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
      } else {
        const r = await fetch(`${API}/decisions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target_id: form.target_id.trim(),
            label: form.target_id.trim(),
            classification: form.classification,
            rationale: form.rationale,
          }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
      }
      cancelForm();
      await fetchDecisions();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function handleRetire(id: string) {
    try {
      await fetch(`${API}/decisions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "retired" }),
      });
      await fetchDecisions();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleReactivate(id: string) {
    try {
      await fetch(`${API}/decisions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "active" }),
      });
      await fetchDecisions();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const activeDecisions = decisions.filter((d) => d.status === "active");
  const retiredDecisions = decisions.filter((d) => d.status === "retired");

  return (
    <div className="decisions-pane">
      {/* ── Form column ── */}
      <div className="decisions-form-col">
        <div className="decisions-col-header">
          {editId ? "Edit Decision" : "New Decision"}
        </div>

        <form className="dec-form" onSubmit={handleSubmit}>
          {/* Project area */}
          <div className="dec-field">
            <label htmlFor="dec-target">Project Area</label>
            <input
              id="dec-target"
              className="dec-input"
              list="dec-areas"
              placeholder="e.g. agents, Applications"
              value={form.target_id}
              disabled={!!editId}
              onChange={(e) => setForm((f) => ({ ...f, target_id: e.target.value }))}
              autoComplete="off"
              required
            />
            <datalist id="dec-areas">
              {areas.map((a) => (
                <option key={a} value={a} />
              ))}
            </datalist>
          </div>

          {/* Classification chips */}
          <div className="dec-field">
            <label>Classification</label>
            <div className="dec-chips">
              {CLASSIFICATIONS.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`dec-chip${form.classification === c.id ? " selected" : ""}`}
                  style={
                    {
                      "--chip-color": c.color,
                      "--chip-bg": c.bg,
                    } as React.CSSProperties
                  }
                  onClick={() => setForm((f) => ({ ...f, classification: c.id }))}
                >
                  <span className="dec-chip-dot" style={{ background: c.color }} />
                  <span className="dec-chip-label">{c.label}</span>
                  <span className="dec-chip-desc">{c.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Rationale */}
          <div className="dec-field">
            <label htmlFor="dec-rationale">Rationale</label>
            <textarea
              id="dec-rationale"
              className="dec-input dec-textarea"
              placeholder="Why this classification?"
              value={form.rationale}
              onChange={(e) => setForm((f) => ({ ...f, rationale: e.target.value }))}
            />
          </div>

          {error && <div className="dec-error">{error}</div>}

          <button
            type="submit"
            className="dec-save-btn"
            disabled={saving || !form.target_id.trim() || !form.classification}
          >
            {saving ? "Saving…" : editId ? "Update Decision" : "Save Decision"}
          </button>

          {editId && (
            <button type="button" className="dec-cancel-btn" onClick={cancelForm}>
              Cancel
            </button>
          )}
        </form>
      </div>

      {/* ── List column ── */}
      <div className="decisions-list-col">
        <div className="decisions-col-header">
          Decision History
          {activeDecisions.length > 0 && (
            <span className="dec-count">{activeDecisions.length}</span>
          )}
        </div>

        {loading && <div className="dec-empty">Loading…</div>}

        {!loading && activeDecisions.length === 0 && (
          <div className="dec-empty">
            No decisions yet. Use the form to classify your first project area.
          </div>
        )}

        {activeDecisions.map((d) => {
          const meta = classificationMeta(d.classification);
          return (
            <div
              key={d.id}
              className="dec-card"
              style={
                {
                  "--card-color": meta.color,
                  "--card-bg": meta.bg,
                } as React.CSSProperties
              }
            >
              <div className="dec-card-head">
                <span className="dec-card-name">{d.label}</span>
                <span className="dec-badge">{meta.label}</span>
              </div>

              {d.rationale && (
                <div className="dec-card-rationale">{d.rationale}</div>
              )}

              <div className="dec-card-footer">
                <span className="dec-card-meta">{formatDate(d.created_at)}</span>
                <div className="dec-card-actions">
                  <button
                    className="dec-action-btn primary"
                    onClick={() => startEdit(d)}
                  >
                    Edit
                  </button>
                  <button
                    className="dec-action-btn"
                    onClick={() => handleRetire(d.id)}
                  >
                    Retire
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {retiredDecisions.length > 0 && (
          <>
            <hr className="dec-section-divider" />
            <button
              className="dec-retired-toggle"
              onClick={() => setShowRetired((v) => !v)}
            >
              <span>{showRetired ? "▾" : "▸"}</span>
              Retired ({retiredDecisions.length})
            </button>

            {showRetired &&
              retiredDecisions.map((d) => {
                const meta = classificationMeta(d.classification);
                return (
                  <div
                    key={d.id}
                    className="dec-card retired"
                    style={
                      {
                        "--card-color": meta.color,
                        "--card-bg": meta.bg,
                      } as React.CSSProperties
                    }
                  >
                    <div className="dec-card-head">
                      <span className="dec-card-name">{d.label}</span>
                      <span className="dec-badge">{meta.label}</span>
                    </div>
                    {d.rationale && (
                      <div className="dec-card-rationale">{d.rationale}</div>
                    )}
                    <div className="dec-card-footer">
                      <span className="dec-card-meta">{formatDate(d.created_at)}</span>
                      <div className="dec-card-actions">
                        <button
                          className="dec-action-btn primary"
                          onClick={() => handleReactivate(d.id)}
                        >
                          Reactivate
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
          </>
        )}
      </div>
    </div>
  );
}
