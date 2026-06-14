import { useState, useEffect, useRef, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────────────

type MissionType = "archive-candidates" | "rank-builds" | "weak-coverage" | "duplicates";
type MissionStatus = "running" | "completed" | "cancelled" | "failed";

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

const API = "http://localhost:8000";

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

// ── Main component ────────────────────────────────────────────────────────

export function WorkQueue() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [starting, setStarting] = useState<MissionType | null>(null);
  const [focusId, setFocusId]   = useState<string | null>(null);
  const [error, setError]       = useState<string | null>(null);
  const pollingRef              = useRef<ReturnType<typeof setInterval> | null>(null);
  const logRef                  = useRef<HTMLDivElement>(null);

  // ── Polling ──────────────────────────────────────────────────────────

  function stopPolling() {
    if (pollingRef.current !== null) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }

  const pollMission = useCallback(async (id: string) => {
    try {
      const r = await fetch(`${API}/missions/${id}`);
      if (!r.ok) return;
      const m: Mission = await r.json();
      setMissions((prev) => prev.map((x) => (x.id === id ? m : x)));
      if (m.status !== "running") stopPolling();
    } catch {
      // network blip — keep polling
    }
  }, []);

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

  useEffect(() => {
    async function load() {
      try {
        const r = await fetch(`${API}/missions`);
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
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Actions ──────────────────────────────────────────────────────────

  async function startMission(type: MissionType) {
    setStarting(type);
    setError(null);
    try {
      const r = await fetch(`${API}/missions`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ type }),
      });
      if (!r.ok) {
        const detail = await r.json().catch(() => ({})) as { detail?: string };
        throw new Error(detail?.detail ?? `HTTP ${r.status}`);
      }
      const m: Mission = await r.json();
      setMissions((prev) => [m, ...prev]);
      setFocusId(m.id);
      startPolling(m.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStarting(null);
    }
  }

  async function cancelMission(id: string) {
    try {
      const r = await fetch(`${API}/missions/${id}/cancel`, { method: "POST" });
      if (!r.ok) return;
      const m: Mission = await r.json();
      setMissions((prev) => prev.map((x) => (x.id === id ? m : x)));
      stopPolling();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
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
    </div>
  );
}
