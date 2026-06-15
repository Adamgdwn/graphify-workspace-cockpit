import type { DecisionClassification } from "./decision";

export type ActiveCockpitContext =
  | {
      kind: "node";
      source: "ask" | "map" | "recommendations" | "dashboard";
      nodeId: string;
      label?: string;
      nodeType?: string;
      clusterId?: string;
      viewMode?: "summary" | "full";
    }
  | {
      kind: "cluster";
      source: "ask" | "map" | "recommendations" | "settings" | "dashboard";
      clusterId: string;
      label?: string;
    }
  | {
      kind: "overlap-pair";
      source: "map" | "dashboard";
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
