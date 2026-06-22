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
      kind: "semantic-link";
      source: "map";
      sourceGroup: string;
      targetGroup: string;
      sourceNodeId: string;
      targetNodeId: string;
      labelA?: string;
      labelB?: string;
      fileA?: string;
      fileB?: string;
      sourceRepo?: string;
      targetRepo?: string;
      similarity?: number;
      actionabilityScore?: number;
      insightKind?: string;
      insightLabel?: string;
      why?: string;
      options?: string[];
      decisionSignals?: string[];
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
