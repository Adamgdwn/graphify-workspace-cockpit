import { useEffect, useRef, useState } from "react";
import { apiFetch } from "./api/client";
import { AICopilot } from "./components/AICopilot";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { HelpModal } from "./components/HelpModal";
import { ToastProvider } from "./components/Toast";
import { Ask } from "./tabs/Ask";
import { Dashboard } from "./tabs/Dashboard";
import type { DashboardDestination } from "./tabs/Dashboard";
import { Decisions } from "./tabs/Decisions";
import { FileImportance } from "./tabs/FileImportance";
import { Map } from "./tabs/Map";
import { Recommendations } from "./tabs/Recommendations";
import { Settings } from "./tabs/Settings";
import { WorkspaceScope } from "./tabs/WorkspaceScope";
import { WorkQueue } from "./tabs/WorkQueue";
import type { ActiveCockpitContext } from "./domain/cockpitContext";

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

const BANNER_KEY = "demo_banner_dismissed";

type ConnStatus = "ok" | "degraded" | "offline";

export default function App() {
  const [active, setActive] = useState<Tab>("dashboard");
  const [demoMode, setDemoMode] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(
    () => sessionStorage.getItem(BANNER_KEY) === "1"
  );
  const [connStatus, setConnStatus] = useState<ConnStatus>("ok");
  const [focusTrigger, setFocusTrigger] = useState(0);
  const [showHelp, setShowHelp] = useState(false);
  const [activeContext, setActiveContext] = useState<ActiveCockpitContext | null>(null);
  const askRef = useRef<HTMLTextAreaElement | null>(null);

  // Connection status + demo mode poll (15s)
  useEffect(() => {
    async function checkStatus() {
      try {
        const r = await apiFetch(`/health`);
        if (!r.ok) { setConnStatus("offline"); return; }
        const d = await r.json();
        setDemoMode(!!d.demo_mode);

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

  function dismissBanner() {
    sessionStorage.setItem(BANNER_KEY, "1");
    setBannerDismissed(true);
  }

  function navigateToMapContext(context: ActiveCockpitContext) {
    setActiveContext(context);
    setActive("map");
  }

  function navigateFromDashboard(destination: DashboardDestination) {
    setActive(destination);
  }

  const showBanner = demoMode && !bannerDismissed;

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
        {showBanner && (
          <div className="demo-banner">
            <span>
              Demo graph active — upload a real graph in{" "}
              <button
                type="button"
                className="demo-banner-link"
                onClick={() => setActive("settings")}
              >
                Settings
              </button>{" "}
              to get started.
            </span>
            <button type="button" className="demo-banner-close" onClick={dismissBanner} aria-label="Dismiss">
              ✕
            </button>
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
          {active === "dashboard" && <ErrorBoundary tabName="Command Center"><Dashboard onNavigate={navigateFromDashboard} onNavigateMapContext={navigateToMapContext} /></ErrorBoundary>}
          {active === "ask" && <ErrorBoundary tabName="Ask"><Ask focusTrigger={focusTrigger} askRef={askRef} onEvidenceNavigate={navigateToMapContext} /></ErrorBoundary>}
          {active === "scope" && <ErrorBoundary tabName="Workspace Scope"><WorkspaceScope onGenerated={() => setActive("map")} /></ErrorBoundary>}
          {active === "importance" && <ErrorBoundary tabName="Importance Criteria Table"><FileImportance /></ErrorBoundary>}
          {active === "map" && <ErrorBoundary tabName="Map"><Map activeContext={activeContext} onNavigateScope={() => setActive("scope")} onActiveContextChange={setActiveContext} /></ErrorBoundary>}
          {active === "decisions" && <ErrorBoundary tabName="Decisions"><Decisions onActiveContextChange={setActiveContext} /></ErrorBoundary>}
          {active === "recommendations" && <ErrorBoundary tabName="Recommendations"><Recommendations onEvidenceNavigate={navigateToMapContext} /></ErrorBoundary>}
          {active === "work-queue" && <ErrorBoundary tabName="Work Queue"><WorkQueue /></ErrorBoundary>}
          {active === "settings" && <ErrorBoundary tabName="Settings"><Settings onNavigateScope={() => setActive("scope")} /></ErrorBoundary>}
        </main>
        <AICopilot onNavigateSettings={() => setActive("settings")} />
      </div>
    </ToastProvider>
  );
}
