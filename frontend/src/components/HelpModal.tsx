import { useEffect } from "react";

interface HelpModalProps {
  open: boolean;
  onClose: () => void;
}

const SECTIONS = [
  {
    title: "Ask",
    body: "Ask natural-language questions about your workspace. Three modes: Query (broad questions answered from the graph), Path (how are X and Y related?), Explain (deep dive on a concept or file). Shortcut: Ctrl+K / Cmd+K from anywhere.",
  },
  {
    title: "Map",
    body: "Interactive node graph of your workspace clustered by project. Click a node to inspect it. Double-click a drillable node to expand the cluster. Use Path mode to trace shortest connections. Top-traffic nodes are highlighted with a gold ring.",
  },
  {
    title: "Decisions",
    body: "Record architectural decisions — Invest, Monitor, Archive, Client Ready, Paused. Each decision targets a workspace area and appears as a coloured highlight on the Map. Export to JSON for sharing or archiving.",
  },
  {
    title: "Recommendations",
    body: "AI-generated cards backed by Ollama + your graph. Generate 'next best build' or 'archive candidates' suggestions. Each card shows evidence nodes, confidence, and risk. Accept, reject, or defer. Accepted cards can be queued as approved actions.",
  },
  {
    title: "Work Queue",
    body: "Background analysis missions that generate recommendation cards while you work. Missions run in a thread and write cards to state only — no workspace mutations. Accepted recommendations can become actions with dry-run previews before execution. Export a UAOS handoff envelope from here.",
  },
  {
    title: "Settings",
    body: "Upload or switch the active graph. Rebuild the graph from the current repo (runs graphify update). Connect SharePoint and OneNote cloud sources via Microsoft device-code auth. View Ollama status, available models, and estimated token savings. Manage org-level settings and last-seen devices.",
  },
  {
    title: "Coming soon: AI Assistant",
    body: "A Chat tab backed by Ollama with streaming token output and graph-aware context. The assistant reads your active knowledge sources — it cannot trigger actions, decisions, or mutations.",
  },
];

export function HelpModal({ open, onClose }: HelpModalProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="help-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label="Help">
      <div className="help-modal" onClick={(e) => e.stopPropagation()}>
        <div className="help-modal-header">
          <span className="help-modal-title">Graphify Workspace Cockpit — Help</span>
          <button className="help-modal-close" onClick={onClose} aria-label="Close help">✕</button>
        </div>
        <div className="help-modal-body">
          {SECTIONS.map((s) => (
            <div key={s.title} className="help-section">
              <div className="help-section-title">{s.title}</div>
              <p className="help-section-body">{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
