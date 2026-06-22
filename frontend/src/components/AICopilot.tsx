import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { apiErrorMessage, apiFetch } from "../api/client";
import type { ActiveCockpitContext } from "../domain/cockpitContext";
import { COPILOT_PROMPT_EVENT, type CopilotPromptEventDetail } from "../domain/copilotEvents";

interface Vec2 { x: number; y: number; }
interface Size { w: number; h: number; }
interface Msg { role: "user" | "assistant"; content: string; nodesUsed?: number; }

interface AICopilotProps {
  onNavigateSettings?: () => void;
  activeContext?: ActiveCockpitContext | null;
}

const LS_POS  = "copilot_pos";
const LS_SIZE = "copilot_size";
const LS_EXP  = "copilot_expanded";
const MIN_W   = 280;
const MIN_H   = 320;
const MARGIN  = 16;
const DEF_SIZE: Size = { w: 380, h: 480 };

function lsGet<T>(key: string, fallback: T): T {
  try { const v = localStorage.getItem(key); return v ? (JSON.parse(v) as T) : fallback; }
  catch { return fallback; }
}

function defaultPos(sz: Size): Vec2 {
  return {
    x: window.innerWidth  - sz.w - MARGIN,
    y: window.innerHeight - sz.h - MARGIN,
  };
}

function clampedPos(p: Vec2, sz: Size): Vec2 {
  return {
    x: Math.max(MARGIN, Math.min(p.x, window.innerWidth  - sz.w - MARGIN)),
    y: Math.max(MARGIN, Math.min(p.y, window.innerHeight - sz.h - MARGIN)),
  };
}

function percent(value: number | undefined): string {
  return Number.isFinite(value) ? `${Math.round(Number(value) * 100)}%` : "unknown";
}

function contextSummary(context: ActiveCockpitContext | null | undefined): string {
  if (!context) return "";
  if (context.kind === "semantic-link") {
    return [
      "Active cockpit context: semantic Evidence link selected on the Map.",
      `Insight: ${context.insightLabel ?? context.insightKind ?? "unknown"}`,
      `Actionability: ${percent(context.actionabilityScore)}; similarity: ${percent(context.similarity)}`,
      `Source: ${context.labelA ?? context.sourceNodeId} (${context.sourceGroup}${context.sourceRepo ? `, ${context.sourceRepo}` : ""})`,
      context.fileA ? `Source path: ${context.fileA}` : "",
      `Target: ${context.labelB ?? context.targetNodeId} (${context.targetGroup}${context.targetRepo ? `, ${context.targetRepo}` : ""})`,
      context.fileB ? `Target path: ${context.fileB}` : "",
      context.why ? `Why the UI flagged it: ${context.why}` : "",
      context.decisionSignals?.length ? `Decision signals: ${context.decisionSignals.join("; ")}` : "",
      context.options?.length ? `Current UI options: ${context.options.join(" | ")}` : "",
    ].filter(Boolean).join("\n");
  }
  if (context.kind === "overlap-pair") {
    return [
      "Active cockpit context: semantic overlap pair selected on the Map.",
      `Clusters: ${context.clusterA} and ${context.clusterB}`,
      `Top pair: ${context.labelA ?? context.sourceNodeId ?? "unknown"} to ${context.labelB ?? context.targetNodeId ?? "unknown"}`,
      `Similarity: ${percent(context.similarity)}`,
    ].join("\n");
  }
  if (context.kind === "node") {
    return [
      "Active cockpit context: map node.",
      `Node: ${context.label ?? context.nodeId}`,
      context.clusterId ? `Cluster: ${context.clusterId}` : "",
      context.nodeType ? `Type: ${context.nodeType}` : "",
    ].filter(Boolean).join("\n");
  }
  if (context.kind === "cluster") {
    return `Active cockpit context: cluster ${context.label ?? context.clusterId}.`;
  }
  if (context.kind === "recommendation") {
    return `Active cockpit context: recommendation ${context.label ?? context.recommendationId}.`;
  }
  return `Active cockpit context: decision ${context.label ?? context.targetId}.`;
}

export function AICopilot({ onNavigateSettings, activeContext = null }: AICopilotProps) {
  const [expanded, setExpanded] = useState<boolean>(() => lsGet(LS_EXP, false));
  const [size,     setSize]     = useState<Size>(() => lsGet(LS_SIZE, DEF_SIZE));
  const [pos,      setPos]      = useState<Vec2>(() => {
    const sz    = lsGet<Size>(LS_SIZE, DEF_SIZE);
    const saved = lsGet<Vec2 | null>(LS_POS, null);
    return saved ?? defaultPos(sz);
  });

  const [msgs,      setMsgs]      = useState<Msg[]>([]);
  const [input,     setInput]     = useState("");
  const [streaming, setStreaming] = useState(false);

  const dragging    = useRef(false);
  const dragMoved   = useRef(false);
  const dragOff     = useRef<Vec2>({ x: 0, y: 0 });
  const resizing    = useRef(false);
  const resizeStart = useRef({ x: 0, y: 0, w: 0, h: 0 });
  const bodyRef     = useRef<HTMLDivElement>(null);
  const inputRef    = useRef<HTMLTextAreaElement>(null);
  // snapshot of pos/size used inside closures set at mousedown time
  const posSnap  = useRef(pos);
  const sizeSnap = useRef(size);

  useEffect(() => { posSnap.current  = pos;  }, [pos]);
  useEffect(() => { sizeSnap.current = size; }, [size]);

  // Auto-scroll messages
  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [msgs]);

  // Global drag / resize mouse handlers
  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (dragging.current) {
        dragMoved.current = true;
        setPos({ x: e.clientX - dragOff.current.x, y: e.clientY - dragOff.current.y });
      }
      if (resizing.current) {
        const s = resizeStart.current;
        setSize({ w: Math.max(MIN_W, s.w + e.clientX - s.x), h: Math.max(MIN_H, s.h + e.clientY - s.y) });
      }
    }
    function onUp(e: MouseEvent) {
      if (dragging.current) {
        const np = { x: e.clientX - dragOff.current.x, y: e.clientY - dragOff.current.y };
        dragging.current = false;
        localStorage.setItem(LS_POS, JSON.stringify(np));
      }
      if (resizing.current) {
        resizing.current = false;
        localStorage.setItem(LS_SIZE, JSON.stringify(sizeSnap.current));
      }
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup",   onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup",   onUp);
    };
  }, []);

  function openPanel() {
    setPos(p => {
      const clamped = clampedPos(p, sizeSnap.current);
      localStorage.setItem(LS_POS, JSON.stringify(clamped));
      return clamped;
    });
    setExpanded(true);
    localStorage.setItem(LS_EXP, JSON.stringify(true));
    setTimeout(() => inputRef.current?.focus(), 30);
  }

  function toggle() {
    if (!expanded) {
      openPanel();
      return;
    }
    setExpanded(false);
    localStorage.setItem(LS_EXP, JSON.stringify(false));
  }

  async function sendText(rawText: string, contextOverride: ActiveCockpitContext | null = activeContext) {
    const text = rawText.trim();
    if (!text || streaming) return;
    setInput("");
    const history = msgs.slice(-20).map(m => ({ role: m.role, content: m.content }));
    setMsgs(prev => [...prev, { role: "user", content: text }, { role: "assistant", content: "" }]);
    setStreaming(true);
    const activeContextSummary = contextSummary(contextOverride);
    const message = activeContextSummary
      ? `${text}\n\n${activeContextSummary}`
      : text;

    try {
      const r = await apiFetch(`/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history, include_graph_context: true }),
      });
      if (!r.ok || !r.body) throw new Error(await apiErrorMessage(r));

      const reader = r.body.getReader();
      const dec    = new TextDecoder();
      let buf      = "";
      let nodesUsed: number | undefined;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const pl = JSON.parse(line.slice(6)) as { type: string; token?: string; nodes_used?: number; message?: string };
            if (pl.type === "meta") {
              nodesUsed = pl.nodes_used;
            } else if (pl.type === "token") {
              setMsgs(prev => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant") next[next.length - 1] = { ...last, content: last.content + (pl.token ?? "") };
                return next;
              });
            } else if (pl.type === "error") {
              setMsgs(prev => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant") next[next.length - 1] = { ...last, content: `Error: ${pl.message ?? "Ollama unreachable"}` };
                return next;
              });
            }
          } catch { /* skip malformed */ }
        }
      }
      setMsgs(prev => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant") next[next.length - 1] = { ...last, nodesUsed };
        return next;
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Connection error — is Ollama running?";
      setMsgs(prev => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === "assistant") next[next.length - 1] = { ...last, content: message };
        return next;
      });
    } finally {
      setStreaming(false);
    }
  }

  function send() {
    void sendText(input);
  }

  useEffect(() => {
    function onPrompt(event: Event) {
      const detail = (event as CustomEvent<CopilotPromptEventDetail>).detail;
      const prompt = detail?.prompt?.trim() ?? "";
      if (!prompt) return;
      const context = detail.context === undefined ? activeContext : detail.context;
      openPanel();
      if (detail.autoSend === false || streaming) {
        setInput(prompt);
        setTimeout(() => inputRef.current?.focus(), 30);
        return;
      }
      void sendText(prompt, context ?? null);
    }

    window.addEventListener(COPILOT_PROMPT_EVENT, onPrompt);
    return () => window.removeEventListener(COPILOT_PROMPT_EVENT, onPrompt);
  }, [activeContext, expanded, msgs, streaming]);

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); }
  }

  // ── Collapsed button ────────────────────────────────────────────────────
  if (!expanded) {
    return (
      <button
        className="copilot-toggle-btn"
        style={{ left: pos.x, top: pos.y }}
        onMouseDown={(e) => {
          e.preventDefault();
          dragMoved.current = false;
          dragging.current  = true;
          dragOff.current   = { x: e.clientX - pos.x, y: e.clientY - pos.y };
        }}
        onMouseUp={() => {
          if (!dragMoved.current) toggle();
        }}
        title="Open AI Assistant (drag to move)"
        type="button"
        aria-label="Open AI Assistant"
      >
        <span className="copilot-toggle-label">AI</span>
      </button>
    );
  }

  // ── Expanded panel ───────────────────────────────────────────────────────
  return (
    <div
      className="copilot-panel"
      style={{ left: pos.x, top: pos.y, width: size.w, height: size.h }}
      role="dialog"
      aria-label="AI Assistant"
    >
      {/* Header — drag handle */}
      <div
        className="copilot-header"
        onMouseDown={(e) => {
          if ((e.target as HTMLElement).closest("button")) return;
          e.preventDefault();
          dragMoved.current = false;
          dragging.current  = true;
          dragOff.current   = { x: e.clientX - posSnap.current.x, y: e.clientY - posSnap.current.y };
        }}
      >
        <span className="copilot-title">AI Assistant</span>
        <div className="copilot-header-btns">
          <button type="button" className="copilot-hdr-btn" onClick={() => setMsgs([])} title="New conversation">＋</button>
          {onNavigateSettings && (
            <button type="button" className="copilot-hdr-btn" onClick={onNavigateSettings} title="AI settings">⚙</button>
          )}
          <button type="button" className="copilot-hdr-btn" onClick={toggle} title="Collapse">−</button>
        </div>
      </div>

      {/* Message list */}
      <div className="copilot-body" ref={bodyRef}>
        {msgs.length === 0 ? (
          <div className="copilot-empty">
            Ask anything about your knowledge graph. Active map context is included automatically.
          </div>
        ) : (
          msgs.map((m, i) => (
            <div key={i} className={`copilot-msg copilot-msg-${m.role}`}>
              <div className="copilot-msg-text">
                {m.content}
                {m.role === "assistant" && streaming && i === msgs.length - 1 && (
                  <span className="copilot-cursor-blink" />
                )}
              </div>
              {m.role === "assistant" && m.nodesUsed !== undefined && m.nodesUsed > 0 && (
                <div className="copilot-nodes-chip">{m.nodesUsed} nodes used</div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Input area */}
      <div className="copilot-footer">
        <textarea
          ref={inputRef}
          className="copilot-input"
          placeholder="Ask… (Enter to send, Shift+Enter for newline)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={streaming}
          rows={2}
        />
        <button
          type="button"
          className={`copilot-send-btn${streaming ? " sending" : ""}`}
          onClick={send}
          disabled={streaming || !input.trim()}
          aria-label="Send"
        >
          {streaming ? "…" : "↵"}
        </button>
      </div>

      {/* Resize handle — bottom-right corner */}
      <div
        className="copilot-resize"
        onMouseDown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          resizing.current     = true;
          resizeStart.current  = { x: e.clientX, y: e.clientY, w: sizeSnap.current.w, h: sizeSnap.current.h };
        }}
        title="Drag to resize"
      />
    </div>
  );
}
