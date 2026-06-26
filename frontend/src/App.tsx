import { Suspense, lazy, useEffect, useRef, useState } from "react";
import { apiFetch } from "./api/client";
import { AICopilot } from "./components/AICopilot";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { HelpModal } from "./components/HelpModal";
import { ToastProvider } from "./components/Toast";
import { Dashboard } from "./tabs/Dashboard";
import type { DashboardDestination } from "./tabs/Dashboard";
import type { ActiveCockpitContext } from "./domain/cockpitContext";

// Heavy tabs are code-split so the initial load (Dashboard) does not pull in
// cytoscape or the large Map module until those tabs are actually opened.
const Ask = lazy(() => import("./tabs/Ask").then((m) => ({ default: m.Ask })));
const Decisions = lazy(() => import("./tabs/Decisions").then((m) => ({ default: m.Decisions })));
const FileImportance = lazy(() => import("./tabs/FileImportance").then((m) => ({ default: m.FileImportance })));
const Map = lazy(() => import("./tabs/Map").then((m) => ({ default: m.Map })));
const Recommendations = lazy(() => import("./tabs/Recommendations").then((m) => ({ default: m.Recommendations })));
const Settings = lazy(() => import("./tabs/Settings").then((m) => ({ default: m.Settings })));
const WorkspaceScope = lazy(() => import("./tabs/WorkspaceScope").then((m) => ({ default: m.WorkspaceScope })));
const WorkQueue = lazy(() => import("./tabs/WorkQueue").then((m) => ({ default: m.WorkQueue })));

type Tab = "dashboard" | "ask" | "scope" | "importance" | "map" | "decisions" | "recommendations" | "work-queue" | "settings";

const TABS: { id: Tab; label: string }[] = [
  { id: "dashboard", label: "Command" },
  { id: "ask", label: "Ask" },
  { id: "scope", label: "Scope" },
  { id: "importance", label: "Importance Criteria Table" },
  { id: "map", label: "Map" },
  { id: "decisions", label: "Decisions" },
  { id: "recommendations", label: "Recommendations" },
  { id: "work-queue", label: "Work Queue" },
  { id: "settings", label: "Settings" },
];

type ConnStatus = "ok" | "degraded" | "offline";

export default function App() {
  const [active, setActive] = useState<Tab>("dashboard");
  const [graphConfigured, setGraphConfigured] = useState(true);
  const [graphLoaded, setGraphLoaded] = useState(true);
  const [connStatus, setConnStatus] = useState<ConnStatus>("ok");
  const [focusTrigger, setFocusTrigger] = useState(0);
  const [showHelp, setShowHelp] = useState(false);
  const [activeContext, setActiveContext] = useState<ActiveCockpitContext | null>(null);
  const askRef = useRef<HTMLTextAreaElement | null>(null);

  // Connection status + graph setup poll (15s)
  useEffect(() => {
    async function checkStatus() {
      try {
        const r = await apiFetch(`/health`);
        if (!r.ok) { setConnStatus("offline"); return; }
        const d = await r.json();
        setGraphConfigured(!!d.graph_configured);
        setGraphLoaded(!!d.graph_loaded);

        const ol = await apiFetch(`/status/ollama`);
        const olData = await ol.json();
        setConnStatus(olData.connected ? "ok" : "degraded");
      } catch {
        setConnStatus("offline");
      }
    }
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  // Ctrl+K / Cmd+K → focus Ask
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setActive("ask");
        setFocusTrigger((t) => t + 1);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function navigateToMapContext(context: ActiveCockpitContext) {
    setActiveContext(context);
    setActive("map");
  }

  function navigateFromDashboard(destination: DashboardDestination) {
    setActive(destination);
  }

  const showSetupBanner = !graphConfigured || !graphLoaded;

  const connDotClass =
    connStatus === "ok" ? "conn-dot conn-ok" :
    connStatus === "degraded" ? "conn-dot conn-degraded" :
    "conn-dot conn-offline";

  const connTitle =
    connStatus === "ok" ? "Backend + Ollama connected" :
    connStatus === "degraded" ? "Backend up — Ollama unreachable" :
    "Backend unreachable";

  return (
    <ToastProvider>
      <div className="cockpit">
        <header className="cockpit-header">
          <span className="cockpit-title">Graphify Workspace Cockpit</span>
          <div className="cockpit-header-right">
            <button
              className="help-btn"
              type="button"
              onClick={() => setShowHelp(true)}
              title="Help"
              aria-label="Open help"
            >
              ?
            </button>
            <span className={connDotClass} title={connTitle} aria-label={connTitle} />
          </div>
        </header>
        <HelpModal open={showHelp} onClose={() => setShowHelp(false)} />
        {showSetupBanner && (
          <div className="setup-banner">
            <span>
              {!graphConfigured
                ? "No workspace graph yet."
                : "Workspace graph is not loaded."}
            </span>
            <div className="setup-banner-actions">
              <button
                type="button"
                className="setup-banner-link"
                onClick={() => setActive("scope")}
              >
                Open Scope
              </button>
              <button
                type="button"
                className="setup-banner-link"
                onClick={() => setActive("settings")}
              >
                Settings
              </button>
            </div>
          </div>
        )}
        <nav className="cockpit-tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`tab-btn${active === t.id ? " active" : ""}`}
              onClick={() => setActive(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <main className="cockpit-content">
          <Suspense fallback={<div className="tab-loading">Loading…</div>}>
            {active === "dashboard" && <ErrorBoundary tabName="Command Center"><Dashboard onNavigate={navigateFromDashboard} onNavigateMapContext={navigateToMapContext} /></ErrorBoundary>}
            {active === "ask" && <ErrorBoundary tabName="Ask"><Ask focusTrigger={focusTrigger} askRef={askRef} onEvidenceNavigate={navigateToMapContext} /></ErrorBoundary>}
            {active === "scope" && <ErrorBoundary tabName="Workspace Scope"><WorkspaceScope onGenerated={() => setActive("map")} /></ErrorBoundary>}
            {active === "importance" && <ErrorBoundary tabName="Importance Criteria Table"><FileImportance /></ErrorBoundary>}
            {active === "map" && <ErrorBoundary tabName="Map"><Map activeContext={activeContext} onNavigateScope={() => setActive("scope")} onActiveContextChange={setActiveContext} /></ErrorBoundary>}
            {active === "decisions" && <ErrorBoundary tabName="Decisions"><Decisions onActiveContextChange={setActiveContext} /></ErrorBoundary>}
            {active === "recommendations" && <ErrorBoundary tabName="Recommendations"><Recommendations onEvidenceNavigate={navigateToMapContext} /></ErrorBoundary>}
            {active === "work-queue" && <ErrorBoundary tabName="Work Queue"><WorkQueue /></ErrorBoundary>}
            {active === "settings" && <ErrorBoundary tabName="Settings"><Settings onNavigateScope={() => setActive("scope")} /></ErrorBoundary>}
          </Suspense>
        </main>
        <AICopilot activeContext={activeContext} onNavigateSettings={() => setActive("settings")} />
      </div>
    </ToastProvider>
  );
}
