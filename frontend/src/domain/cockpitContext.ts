import type { DecisionClassification } from "./decision";

export type ActiveCockpitContext =
  | {
      kind: "node";
      source: "ask" | "map" | "recommendations";
      nodeId: string;
      label?: string;
      nodeType?: string;
      clusterId?: string;
      viewMode?: "summary" | "full";
    }
  | {
      kind: "cluster";
      source: "map" | "settings";
      clusterId: string;
      label?: string;
    }
  | {
      kind: "overlap-pair";
      source: "map";
      clusterA: string;
      clusterB: string;
      sourceNodeId?: string;
      targetNodeId?: string;
      labelA?: string;
      labelB?: string;
      similarity?: number;
    }
  | {
      kind: "recommendation";
      source: "recommendations";
      recommendationId: string;
      label?: string;
    }
  | {
      kind: "decision";
      source: "decisions" | "map";
      decisionId: string;
      targetId: string;
      label?: string;
      classification?: DecisionClassification;
    };

export type ActiveCockpitContextHandler = (context: ActiveCockpitContext | null) => void;
