import { useState } from "react";
import { Ask } from "./tabs/Ask";
import { Decisions } from "./tabs/Decisions";
import { Map } from "./tabs/Map";
import { Recommendations } from "./tabs/Recommendations";
import { WorkQueue } from "./tabs/WorkQueue";

type Tab = "ask" | "map" | "decisions" | "recommendations" | "work-queue";

const TABS: { id: Tab; label: string }[] = [
  { id: "ask", label: "Ask" },
  { id: "map", label: "Map" },
  { id: "decisions", label: "Decisions" },
  { id: "recommendations", label: "Recommendations" },
  { id: "work-queue", label: "Work Queue" },
];

export default function App() {
  const [active, setActive] = useState<Tab>("ask");

  return (
    <div className="cockpit">
      <header className="cockpit-header">
        <span className="cockpit-title">Graphify Workspace Cockpit</span>
      </header>
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
      </main>
    </div>
  );
}
