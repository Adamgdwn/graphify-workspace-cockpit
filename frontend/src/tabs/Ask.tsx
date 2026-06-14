import { useState } from "react";

type Mode = "query" | "path" | "explain";

interface EvidenceNode {
  label: string;
  src?: string;
  loc?: string;
  community?: string;
  relation?: string;
  direction?: string;
}

interface AskResponse {
  session_id: string;
  question: string;
  mode_used: Mode;
  answer: string;
  evidence: EvidenceNode[];
  suggestions: string[];
}

const MODE_LABELS: Record<Mode, string> = {
  query: "Query",
  path: "Path",
  explain: "Explain",
};

const MODE_HINTS: Record<Mode, string> = {
  query: "Broad question — returns matching nodes from the graph",
  path: "Relationship — shortest path between two named nodes",
  explain: "Node detail — connections and metadata for a named node",
};

export function Ask() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<Mode>("query");
  const [nodeA, setNodeA] = useState("");
  const [nodeB, setNodeB] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<AskResponse | null>(null);

  async function submit(q: string, m: Mode, a?: string, b?: string) {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const body: Record<string, string> = { question: q, mode: m };
      if (m === "path") {
        body.node_a = a ?? "";
        body.node_b = b ?? "";
      } else if (m === "explain") {
        body.node_a = a || q;
      }
      const res = await fetch("http://localhost:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(detail.detail ?? res.statusText);
      }
      setResponse(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    submit(question, mode, nodeA, nodeB);
  }

  function handleSuggestion(s: string) {
    setQuestion(s);
    submit(s, "query");
  }

  return (
    <div className="ask-pane">
      <h2 className="ask-heading">Ask</h2>
      <p className="ask-subheading">Query the workspace graph.</p>

      <form className="ask-form" onSubmit={handleSubmit}>
        <div className="ask-mode-row">
          {(["query", "path", "explain"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              className={`mode-btn${mode === m ? " active" : ""}`}
              onClick={() => setMode(m)}
            >
              {MODE_LABELS[m]}
            </button>
          ))}
        </div>
        <p className="ask-mode-hint">{MODE_HINTS[mode]}</p>

        {mode === "path" ? (
          <div className="ask-path-row">
            <input
              className="ask-node-input"
              placeholder="From node (e.g. FastAPI)"
              value={nodeA}
              onChange={(e) => setNodeA(e.target.value)}
              required
            />
            <span className="ask-path-arrow">→</span>
            <input
              className="ask-node-input"
              placeholder="To node (e.g. health)"
              value={nodeB}
              onChange={(e) => setNodeB(e.target.value)}
              required
            />
          </div>
        ) : mode === "explain" ? (
          <input
            className="ask-single-input"
            placeholder="Node name (e.g. FastAPI)"
            value={nodeA}
            onChange={(e) => setNodeA(e.target.value)}
            required
          />
        ) : (
          <textarea
            className="ask-textarea"
            rows={3}
            placeholder="What projects are in this workspace?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
          />
        )}

        <button className="ask-submit" type="submit" disabled={loading}>
          {loading ? "Running…" : "Ask"}
        </button>
      </form>

      {error && <div className="ask-error">{error}</div>}

      {response && (
        <div className="ask-result">
          <div className="ask-answer">
            <pre className="ask-answer-text">{response.answer}</pre>
          </div>

          {response.evidence.length > 0 && (
            <details className="ask-evidence" open>
              <summary className="ask-evidence-summary">
                Evidence nodes ({response.evidence.length})
              </summary>
              <ul className="ask-evidence-list">
                {response.evidence.map((e, i) => (
                  <li key={i} className="ask-evidence-item">
                    <span className="evidence-label">{e.label}</span>
                    {e.src && (
                      <span className="evidence-src">
                        {e.src}
                        {e.loc ? ` ${e.loc}` : ""}
                      </span>
                    )}
                    {e.relation && (
                      <span className="evidence-relation">
                        {e.direction} {e.relation}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          )}

          {response.suggestions.length > 0 && (
            <div className="ask-suggestions">
              <span className="ask-suggestions-label">Follow-up:</span>
              <div className="ask-suggestions-row">
                {response.suggestions.map((s, i) => (
                  <button
                    key={i}
                    type="button"
                    className="suggestion-btn"
                    onClick={() => handleSuggestion(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <p className="ask-session-id">Session {response.session_id}</p>
        </div>
      )}
    </div>
  );
}
