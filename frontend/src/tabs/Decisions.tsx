import { useEffect, useRef, useState, type FormEvent } from "react";
import { apiErrorMessage, apiFetch } from "../api/client";
import { SkeletonCard } from "../components/Skeleton";
import { useToast } from "../components/Toast";
import { WorkingStatus } from "../components/WorkingStatus";
import {
  DECISION_CLASSIFICATIONS,
  decisionClassificationMeta,
  normalizeDecisionClassification,
  type DecisionClassification,
} from "../domain/decision";
import type { ActiveCockpitContextHandler } from "../domain/cockpitContext";

// ── Types ─────────────────────────────────────────────────────────────────

interface DecisionRecord {
  id: string;
  target_id: string;
  label: string;
  classification: string;
  rationale: string;
  created_at: string;
  updated_at: string;
  status: "active" | "retired";
  created_by?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-CA", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Component ─────────────────────────────────────────────────────────────

const BLANK = { target_id: "", classification: "" as DecisionClassification | "", rationale: "" };

interface DecisionsProps {
  onActiveContextChange?: ActiveCockpitContextHandler;
}

export function Decisions({ onActiveContextChange }: DecisionsProps) {
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState({ ...BLANK });
  const [areas, setAreas] = useState<string[]>([]);
  const [showRetired, setShowRetired] = useState(false);
  const etagRef = useRef<string>("");
  const { addToast } = useToast();

  async function fetchDecisions() {
    try {
      const headers: Record<string, string> = {};
      if (etagRef.current) headers["If-None-Match"] = etagRef.current;
      const r = await apiFetch(`/decisions`, { headers });
      if (r.status === 304) return;
      if (!r.ok) throw new Error(await apiErrorMessage(r));
      etagRef.current = r.headers.get("ETag") ?? "";
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
    apiFetch(`/graph/summary`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.nodes) setAreas(data.nodes.map((n: { id: string }) => n.id));
      })
      .catch(() => {});
    const interval = setInterval(fetchDecisions, 15000);
    return () => clearInterval(interval);
  }, []);

  function startEdit(d: DecisionRecord) {
    const classification = normalizeDecisionClassification(d.classification);
    setEditId(d.id);
    setForm({ target_id: d.target_id, classification, rationale: d.rationale });
    onActiveContextChange?.({
      kind: "decision",
      source: "decisions",
      decisionId: d.id,
      targetId: d.target_id,
      label: d.label,
      classification,
    });
  }

  function resetForm() {
    setEditId(null);
    setForm({ ...BLANK });
  }

  function cancelForm() {
    resetForm();
    onActiveContextChange?.(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.target_id.trim() || !form.classification) return;
    setSaving(true);
    try {
      if (editId) {
        const r = await apiFetch(`/decisions/${editId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ classification: form.classification, rationale: form.rationale }),
        });
        if (!r.ok) throw new Error(await apiErrorMessage(r));
        const updated: DecisionRecord = await r.json();
        onActiveContextChange?.({
          kind: "decision",
          source: "decisions",
          decisionId: updated.id,
          targetId: updated.target_id,
          label: updated.label,
          classification: normalizeDecisionClassification(updated.classification),
        });
        addToast("Decision updated", "success");
      } else {
        const r = await apiFetch(`/decisions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target_id: form.target_id.trim(),
            label: form.target_id.trim(),
            classification: form.classification,
            rationale: form.rationale,
          }),
        });
        if (!r.ok) throw new Error(await apiErrorMessage(r));
        const created: DecisionRecord = await r.json();
        onActiveContextChange?.({
          kind: "decision",
          source: "decisions",
          decisionId: created.id,
          targetId: created.target_id,
          label: created.label,
          classification: normalizeDecisionClassification(created.classification),
        });
        addToast("Decision saved", "success");
      }
      resetForm();
      await fetchDecisions();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      addToast(msg, "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleRetire(id: string) {
    try {
      await apiFetch(`/decisions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "retired" }),
      });
      onActiveContextChange?.(null);
      addToast("Decision retired", "info");
      await fetchDecisions();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      addToast(msg, "error");
    }
  }

  async function handleReactivate(id: string) {
    try {
      const r = await apiFetch(`/decisions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "active" }),
      });
      if (!r.ok) throw new Error(await apiErrorMessage(r));
      const decision: DecisionRecord = await r.json();
      onActiveContextChange?.({
        kind: "decision",
        source: "decisions",
        decisionId: decision.id,
        targetId: decision.target_id,
        label: decision.label,
        classification: normalizeDecisionClassification(decision.classification),
      });
      addToast("Decision reactivated", "success");
      await fetchDecisions();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      addToast(msg, "error");
    }
  }

  function handleExport() {
    downloadJson(decisions, "decisions.json");
    addToast("Decisions exported", "info");
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
              {DECISION_CLASSIFICATIONS.map((c) => (
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
          {!loading && decisions.length > 0 && (
            <button type="button" className="export-btn" onClick={handleExport}>
              Export JSON
            </button>
          )}
        </div>

        {loading && (
          <div className="dec-skeleton-list">
            <WorkingStatus label="Loading decisions" detail="Reading active classifications" />
            <SkeletonCard lines={3} />
            <SkeletonCard lines={2} />
            <SkeletonCard lines={3} />
          </div>
        )}

        {!loading && activeDecisions.length === 0 && (
          <div className="dec-empty">
            <p className="dec-empty-msg">No decisions yet.</p>
            <p className="dec-empty-hint">Use the form to classify your first project area and track what to invest in, archive, or monitor.</p>
          </div>
        )}

        {activeDecisions.map((d) => {
          const meta = decisionClassificationMeta(d.classification);
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
                <span className="dec-card-meta">
                  {formatDate(d.created_at)}
                  {d.created_by && d.created_by !== "local" && (
                    <span className="dec-card-by"> · {d.created_by}</span>
                  )}
                </span>
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
                const meta = decisionClassificationMeta(d.classification);
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
