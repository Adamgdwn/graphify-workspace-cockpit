import { useEffect, useState } from "react";
import { API } from "./config";
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

export default function App() {
  const [active, setActive] = useState<Tab>("ask");
  const [demoMode, setDemoMode] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(
    () => sessionStorage.getItem(BANNER_KEY) === "1"
  );

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((d) => setDemoMode(!!d.demo_mode))
      .catch(() => {});
  }, []);

  function dismissBanner() {
    sessionStorage.setItem(BANNER_KEY, "1");
    setBannerDismissed(true);
  }

  const showBanner = demoMode && !bannerDismissed;

  return (
    <div className="cockpit">
      <header className="cockpit-header">
        <span className="cockpit-title">Graphify Workspace Cockpit</span>
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
        {active === "ask" && <Ask />}
        {active === "map" && <Map />}
        {active === "decisions" && <Decisions />}
        {active === "recommendations" && <Recommendations />}
        {active === "work-queue" && <WorkQueue />}
        {active === "settings" && <Settings />}
      </main>
    </div>
  );
}
