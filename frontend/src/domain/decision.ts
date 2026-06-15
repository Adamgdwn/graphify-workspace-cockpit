export type DecisionClassification = "invest" | "client-ready" | "monitor" | "archive" | "paused";

export interface DecisionClassificationMeta {
  id: DecisionClassification;
  label: string;
  color: string;
  bg: string;
  description: string;
}

export const DECISION_CLASSIFICATIONS: DecisionClassificationMeta[] = [
  { id: "invest",       label: "Invest",       color: "#4ade80", bg: "#071a0f", description: "Actively build or expand" },
  { id: "client-ready", label: "Client Ready", color: "#f5d280", bg: "#1e1608", description: "Presentable to clients" },
  { id: "monitor",      label: "Monitor",      color: "#6b8cff", bg: "#08102a", description: "Watch, no action yet" },
  { id: "archive",      label: "Archive",      color: "#9ca3af", bg: "#111318", description: "Wind down or deprecate" },
  { id: "paused",       label: "Paused",       color: "#f97316", bg: "#1c0e04", description: "On hold" },
];

export function isDecisionClassification(id: string): id is DecisionClassification {
  return DECISION_CLASSIFICATIONS.some((c) => c.id === id);
}

export function normalizeDecisionClassification(id: string): DecisionClassification {
  return isDecisionClassification(id) ? id : "monitor";
}

export function decisionClassificationMeta(id: string) {
  return DECISION_CLASSIFICATIONS.find((c) => c.id === id) ?? DECISION_CLASSIFICATIONS[2];
}
