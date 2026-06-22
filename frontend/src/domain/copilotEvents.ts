import type { ActiveCockpitContext } from "./cockpitContext";

export const COPILOT_PROMPT_EVENT = "cockpit:copilot-prompt";

export interface CopilotPromptEventDetail {
  prompt: string;
  autoSend?: boolean;
  context?: ActiveCockpitContext | null;
}
