import { useState, useEffect, useRef, useCallback } from "react";
import { apiErrorMessage, apiFetch } from "../api/client";
import { useToast } from "../components/Toast";

// ── Types ─────────────────────────────────────────────────────────────────

type MissionType = "archive-candidates" | "rank-builds" | "weak-coverage" | "duplicates";
type MissionStatus = "running" | "completed" | "cancelled" | "failed";

type ActionStatus = "pending" | "dry-run-ready" | "executed" | "failed";

interface DryRunPreview {
  target_path: string;
  file_exists: boolean;
  would_create: boolean;
  preview_content: string;
  summary: string;
}

interface ActionResult {
  success: boolean;
  file_created?: string;
  message: string;
}

interface QueuedAction {
  id: string;
  source_recommendation_id: string;
  action_type: string;
  description: string;
  target_path: string;
  proposed_action_text: string;
  rec_title: string;
  rec_summary: string;
  action_plan?: ActionPlan | null;
  dry_run_preview: DryRunPreview | null;
  dry_run_at: string | null;
  approved_at: string | null;
  executed_at: string | null;
  result: ActionResult | null;
  rollback_note: string;
  status: ActionStatus;
  created_at: string;
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
}

interface Mission {
  id: string;
  type: MissionType;
  status: MissionStatus;
  log: string[];
  cards_generated: number;
  started_at: string;
  finished_at: string | null;
}

// ── Constants ─────────────────────────────────────────────────────────────

const MISSION_DEFS: { type: MissionType; label: string; description: string }[] = [
  {
    type: "archive-candidates",
    label: "Archive Candidates",
    description: "Find low-activity, low-connection projects that are safe to archive or park.",
  },
  {
    type: "rank-builds",
    label: "Rank Next Builds",
    description: "Surface the highest-value next build target based on graph and your decisions.",
  },
  {
    type: "weak-coverage",
    label: "Weak Coverage",
    description: "Find active projects with no docs or test nodes — flag for quality investment.",
  },
  {
    type: "duplicates",
    label: "Find Duplicates",
    description: "Spot project areas solving the same problem — candidates for consolidation.",
  },
];

const STATUS_COLOR: Record<MissionStatus, string> = {
  running:   "#6b8cff",
  completed: "#4ade80",
  cancelled: "#f5d280",
  failed:    "#f87171",
};

const STATUS_LABEL: Record<MissionStatus, string> = {
  running:   "Running…",
  completed: "Completed",
  cancelled: "Cancelled",
  failed:    "Failed",
};

// ── Helpers ───────────────────────────────────────────────────────────────

function missionLabel(type: MissionType): string {
  return MISSION_DEFS.find((d) => d.type === type)?.label ?? type;
}

function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
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

function listItems(items?: string[], limit = 4): string[] {
  return (items ?? []).map((item) => item.trim()).filter(Boolean).slice(0, limit);
}

function ActionPlanSummary({ plan }: { plan: ActionPlan }) {
  const steps = listItems(plan.concrete_steps, 4);
  const risks = listItems(plan.risks, 3);
  const doneWhen = listItems(plan.acceptance_criteria, 3);
  const savings = plan.savings_estimate;

  return (
    <div className="wq-action-plan">
      {plan.canonical_target && (
        <div className="wq-plan-row">
          <strong>Where</strong>
          <span>{plan.canonical_target}</span>
        </div>
      )}
      {steps.length > 0 && (
        <div className="wq-plan-row">
          <strong>How</strong>
          <span>{steps.join(" ")}</span>
        </div>
      )}
      {savings && (
        <div className="wq-plan-row">
          <strong>Savings</strong>
          <span>
            {savings.duplicate_node_count ?? 0} pair(s), {savings.affected_files ?? 0} file(s), up to {savings.semantic_edge_reduction ?? 0} semantic edge(s). {savings.caveat ?? ""}
          </span>
        </div>
      )}
      {risks.length > 0 && (
        <div className="wq-plan-row">
          <strong>Risks</strong>
          <span>{risks.join(" ")}</span>
        </div>
      )}
      {doneWhen.length > 0 && (
        <div className="wq-plan-row">
          <strong>Done When</strong>
          <span>{doneWhen.join(" ")}</span>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

export function WorkQueue() {
  const [missions, setMissions]   = useState<Mission[]>([]);
  const [starting, setStarting]   = useState<MissionType | null>(null);
  const [focusId, setFocusId]     = useState<string | null>(null);
  const [error, setError]         = useState<string | null>(null);
  const pollingRef                = useRef<ReturnType<typeof setInterval> | null>(null);
  const logRef                    = useRef<HTMLDivElement>(null);
  const { addToast } = useToast();

  // Action queue state
  const [actions, setActions]           = useState<QueuedAction[]>([]);
  const [expandedAction, setExpanded]   = useState<string | null>(null);
  const [actionWorking, setActionWorking] = useState<string | null>(null);
  const [actionError, setActionError]   = useState<string | null>(null);
  const actionEtagRef                   = useRef<string>("");

  // ── Polling ──────────────────────────────────────────────────────────

  function stopPolling() {
    if (pollingRef.current !== null) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }

  const pollMission = useCallback(async (id: string) => {
    try {
      const r = await apiFetch(`/missions/${id}`);
      if (!r.ok) return;
      const m: Mission = await r.json();
      setMissions((prev) => prev.map((x) => (x.id === id ? m : x)));
      if (m.status !== "running") {
        stopPolling();
        if (m.status === "completed") {
          addToast(`Mission completed — ${m.cards_generated} card${m.cards_generated !== 1 ? "s" : ""} added`, "success");
        } else if (m.status === "failed") {
          addToast("Mission failed", "error");
        }
      }
    } catch {
      // network blip — keep polling
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function startPolling(id: string) {
    stopPolling();
    pollingRef.current = setInterval(() => pollMission(id), 2000);
  }

  useEffect(() => () => stopPolling(), []);

  // ── Auto-scroll log ──────────────────────────────────────────────────

  const focusMission = missions.find((m) => m.id === focusId);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [focusMission?.log.length]);

  // ── Initial load ─────────────────────────────────────────────────────

  const fetchActions = useCallback(async () => {
    try {
      const headers: Record<string, string> = {};
      if (actionEtagRef.current) headers["If-None-Match"] = actionEtagRef.current;
      const r = await apiFetch(`/actions`, { headers });
      if (r.status === 304) return;
      if (!r.ok) return;
      actionEtagRef.current = r.headers.get("ETag") ?? "";
      setActions(await r.json());
    } catch {
      // backend may not be up yet
    }
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const r = await apiFetch(`/missions`);
        if (!r.ok) return;
        const list: Mission[] = await r.json();
        setMissions(list);
        const running = list.find((m) => m.status === "running");
        if (running) {
          setFocusId(running.id);
          startPolling(running.id);
        } else if (list.length > 0) {
          setFocusId(list[0].id);
        }
      } catch {
        // backend may not be up yet
      }
    }
    load();
    fetchActions();
    const actionInterval = setInterval(fetchActions, 15000);
    return () => clearInterval(actionInterval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Actions ──────────────────────────────────────────────────────────

  async function startMission(type: MissionType) {
    setStarting(type);
    setError(null);
    try {
      const r = await apiFetch(`/missions`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ type }),
      });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
      }
      const m: Mission = await r.json();
      setMissions((prev) => [m, ...prev]);
      setFocusId(m.id);
      startPolling(m.id);
      addToast(`${missionLabel(type)} mission started`, "info");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      addToast(msg, "error");
    } finally {
      setStarting(null);
    }
  }

  async function cancelMission(id: string) {
    try {
      const r = await apiFetch(`/missions/${id}/cancel`, { method: "POST" });
      if (!r.ok) return;
      const m: Mission = await r.json();
      setMissions((prev) => prev.map((x) => (x.id === id ? m : x)));
      stopPolling();
      addToast("Mission cancelled", "info");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      addToast(msg, "error");
    }
  }

  // ── Action handlers ──────────────────────────────────────────────────

  async function runDryRun(id: string) {
    setActionWorking(id);
    setActionError(null);
    try {
      const r = await apiFetch(`/actions/${id}/dry-run`, { method: "POST" });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
      }
      const updated: QueuedAction = await r.json();
      setActions((prev) => prev.map((a) => (a.id === id ? updated : a)));
      setExpanded(id);
      addToast("Dry run complete — review preview below", "success");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setActionError(msg);
      addToast(msg, "error");
    } finally {
      setActionWorking(null);
    }
  }

  async function runExecute(id: string) {
    setActionWorking(id);
    setActionError(null);
    try {
      const r = await apiFetch(`/actions/${id}/execute`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ confirmed: true }),
      });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
      }
      const updated: QueuedAction = await r.json();
      setActions((prev) => prev.map((a) => (a.id === id ? updated : a)));
      addToast("Action executed successfully", "success");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setActionError(msg);
      addToast(msg, "error");
    } finally {
      setActionWorking(null);
    }
  }

  async function handleUaosExport() {
    try {
      const r = await apiFetch(`/actions?format=uaos`);
      if (!r.ok) throw new Error(await apiErrorMessage(r));
      const data = await r.json();
      downloadJson(data, "uaos-handoff.json");
      addToast("UAOS handoff exported", "info");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      addToast(msg, "error");
    }
  }

  // ── Derived ──────────────────────────────────────────────────────────

  const isRunning = missions.some((m) => m.status === "running");
  const history   = missions.filter((m) => m.id !== focusId);

  return (
    <div className="wq-pane">
      {/* Mission picker */}
      <div className="wq-section">
        <div className="wq-section-title">Launch a Mission</div>
        <div className="wq-missions-grid">
          {MISSION_DEFS.map((def) => (
            <div key={def.type} className="wq-mission-card">
              <div className="wq-mission-label">{def.label}</div>
              <div className="wq-mission-desc">{def.description}</div>
              <button
                className={`wq-start-btn${starting === def.type ? " active" : ""}`}
                disabled={isRunning || starting !== null}
                onClick={() => startMission(def.type)}
              >
                {starting === def.type ? "Starting…" : "Start"}
              </button>
            </div>
          ))}
        </div>
      </div>

      {error && <div className="wq-error">{error}</div>}

      {/* Focus panel */}
      {focusMission && (
        <div className="wq-section">
          <div className="wq-section-title">Mission Detail</div>
          <div className="wq-active-panel">
            <div className="wq-active-header">
              <span className="wq-active-name">{missionLabel(focusMission.type)}</span>
              <span
                className="wq-status-badge"
                style={{
                  color:       STATUS_COLOR[focusMission.status],
                  borderColor: STATUS_COLOR[focusMission.status],
                }}
              >
                {STATUS_LABEL[focusMission.status]}
              </span>
              {focusMission.cards_generated > 0 && (
                <span className="wq-cards-tag">
                  {focusMission.cards_generated} card{focusMission.cards_generated !== 1 ? "s" : ""} added
                </span>
              )}
            </div>

            <div className="wq-log" ref={logRef}>
              {focusMission.log.length === 0 ? (
                <span className="wq-log-empty">Waiting for output…</span>
              ) : (
                focusMission.log.map((line, i) => (
                  <div key={i} className="wq-log-line">{line}</div>
                ))
              )}
            </div>

            <div className="wq-active-footer">
              <span className="wq-time-tag">Started {relTime(focusMission.started_at)}</span>
              {focusMission.status === "running" && (
                <button
                  className="wq-cancel-btn"
                  onClick={() => cancelMission(focusMission.id)}
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Session history */}
      {history.length > 0 && (
        <div className="wq-section">
          <div className="wq-section-title">Session History</div>
          <div className="wq-history-list">
            {history.map((m) => (
              <button
                key={m.id}
                className={`wq-history-item${focusId === m.id ? " active" : ""}`}
                onClick={() => setFocusId(m.id)}
              >
                <span className="wq-history-type">{missionLabel(m.type)}</span>
                <span
                  className="wq-history-status"
                  style={{ color: STATUS_COLOR[m.status] }}
                >
                  {m.status}
                </span>
                <span className="wq-history-cards">
                  {m.cards_generated} card{m.cards_generated !== 1 ? "s" : ""}
                </span>
                <span className="wq-history-time">{relTime(m.started_at)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {missions.length === 0 && !error && (
        <div className="wq-empty">
          No missions run yet this session. Pick one above to start.
        </div>
      )}

      {/* ── Action Queue ──────────────────────────────────────────── */}
      <div className="wq-section wq-action-section">
        <div className="wq-section-title">
          Action Queue
          <button className="wq-refresh-btn" onClick={fetchActions} title="Refresh actions">↻</button>
          {actions.length > 0 && (
            <button type="button" className="export-btn" onClick={handleUaosExport}>
              Export UAOS Handoff
            </button>
          )}
        </div>

        {actionError && <div className="wq-error">{actionError}</div>}

        {actions.length === 0 ? (
          <div className="wq-empty">
            <p style={{ margin: "0 0 6px" }}>No actions queued.</p>
            <p style={{ margin: 0, opacity: 0.6, fontSize: "0.8rem" }}>
              Accept a recommendation in the Recommendations tab, then click "Queue Action".
            </p>
          </div>
        ) : (
          <div className="wq-action-list">
            {actions.map((action) => {
              const isWorking  = actionWorking === action.id;
              const isExpanded = expandedAction === action.id;
              return (
                <div key={action.id} className={`wq-action-card wq-action-${action.status}`}>
                  <div className="wq-action-head">
                    <div className="wq-action-desc">{action.description}</div>
                    <span className={`wq-action-badge wq-badge-${action.status}`}>
                      {action.status === "dry-run-ready" ? "dry-run ready" : action.status}
                    </span>
                  </div>

                  <div className="wq-action-proposed">{action.proposed_action_text}</div>

                  {action.action_plan && <ActionPlanSummary plan={action.action_plan} />}

                  <div className="wq-action-footer">
                    {action.status === "pending" && (
                      <button
                        className="wq-action-btn"
                        disabled={isWorking}
                        onClick={() => runDryRun(action.id)}
                      >
                        {isWorking ? "Running…" : "Dry Run"}
                      </button>
                    )}

                    {action.status === "dry-run-ready" && (
                      <>
                        <button
                          className="wq-action-btn secondary"
                          onClick={() => setExpanded(isExpanded ? null : action.id)}
                        >
                          {isExpanded ? "Hide Preview" : "Show Preview"}
                        </button>
                        <button
                          className="wq-action-btn primary"
                          disabled={isWorking}
                          onClick={() => runExecute(action.id)}
                        >
                          {isWorking ? "Executing…" : "Approve & Execute"}
                        </button>
                      </>
                    )}

                    {action.status === "executed" && action.result?.success && (
                      <span className="wq-action-done">
                        ✓ {action.result.message}
                        {" — "}
                        <span className="wq-rollback-note">{action.rollback_note}</span>
                      </span>
                    )}

                    {(action.status === "failed" || (action.status === "executed" && !action.result?.success)) && (
                      <span className="wq-action-failed">
                        ✗ {action.result?.message ?? "Unknown error"}
                      </span>
                    )}
                  </div>

                  {/* Dry-run preview panel */}
                  {isExpanded && action.dry_run_preview && (
                    <div className="wq-preview-panel">
                      <div className="wq-preview-summary">{action.dry_run_preview.summary}</div>
                      <pre className="wq-preview-content">{action.dry_run_preview.preview_content}</pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
