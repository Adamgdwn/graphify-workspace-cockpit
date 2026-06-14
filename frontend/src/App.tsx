import { useEffect, useRef, useState } from "react";
import { API } from "./config";
import { ToastProvider } from "./components/Toast";
import { Ask } from "./tabs/Ask";
import { Decisions } from "./tabs/Decisions";
import { Map } from "./tabs/Map";
import { Recommendations } from "./tabs/Recommendations";
import { Settings } from "./tabs/Settings";
import { WorkQueue } from "./tabs/WorkQueue";

type Tab = "ask" | "map" | "decisions" | "recommendations" | "work-queue" | "settings";

const TABS: { id: Tab; label: string }[] = [
  { id: "ask", label: "Ask" },
  { id: "map", label: "Map" },
  { id: "decisions", label: "Decisions" },
  { id: "recommendations", label: "Recommendations" },
  { id: "work-queue", label: "Work Queue" },
  { id: "settings", label: "Settings" },
];

const BANNER_KEY = "demo_banner_dismissed";

type ConnStatus = "ok" | "degraded" | "offline";

export default function App() {
  const [active, setActive] = useState<Tab>("ask");
  const [demoMode, setDemoMode] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(
    () => sessionStorage.getItem(BANNER_KEY) === "1"
  );
  const [connStatus, setConnStatus] = useState<ConnStatus>("ok");
  const [focusTrigger, setFocusTrigger] = useState(0);
  const askRef = useRef<HTMLTextAreaElement | null>(null);

  // Connection status + demo mode poll (15s)
  useEffect(() => {
    async function checkStatus() {
      try {
        const r = await fetch(`${API}/health`);
        if (!r.ok) { setConnStatus("offline"); return; }
        const d = await r.json();
        setDemoMode(!!d.demo_mode);

        const ol = await fetch(`${API}/status/ollama`);
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
          <span className={connDotClass} title={connTitle} aria-label={connTitle} />
        </header>
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
          {active === "ask" && <Ask focusTrigger={focusTrigger} askRef={askRef} />}
          {active === "map" && <Map />}
          {active === "decisions" && <Decisions />}
          {active === "recommendations" && <Recommendations />}
          {active === "work-queue" && <WorkQueue />}
          {active === "settings" && <Settings />}
        </main>
      </div>
    </ToastProvider>
  );
}
