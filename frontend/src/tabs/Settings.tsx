import { useEffect, useRef, useState, type FormEvent } from "react";
import { API } from "../config";
import { useToast } from "../components/Toast";

interface AppSettings {
  version: string;
  graph_path: string;
  graph_name: string;
  node_count: number;
  edge_count: number;
  state_dir: string;
  api_key_required: boolean;
}

interface OllamaStatus {
  connected: boolean;
  models: string[];
  url: string;
}

interface GraphEntry {
  name: string;
  path: string;
  active: boolean;
  source: "demo" | "uploaded" | "configured";
  uploaded_at: string | null;
}

interface OrgSettings {
  active_graph: { name: string; path: string };
  ollama_url: string;
  storage_backend: string;
  last_seen_devices: { user: string; last_seen: string }[];
}

export function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [ollama, setOllama] = useState<OllamaStatus | null>(null);
  const [graphs, setGraphs] = useState<GraphEntry[]>([]);
  const [org, setOrg] = useState<OrgSettings | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const { addToast } = useToast();

  function loadAll() {
    fetch(`${API}/settings`)
      .then((r) => r.json())
      .then(setSettings)
      .catch(() => {});
    fetch(`${API}/status/ollama`)
      .then((r) => r.json())
      .then(setOllama)
      .catch(() => {});
    fetch(`${API}/graphs`)
      .then((r) => r.json())
      .then(setGraphs)
      .catch(() => {});
    fetch(`${API}/settings/org`)
      .then((r) => r.json())
      .then(setOrg)
      .catch(() => {});
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg(null);
    setUploadError(null);
    const body = new FormData();
    body.append("file", file);
    try {
      const r = await fetch(`${API}/graph/upload`, { method: "POST", body });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? "Upload failed");
      setUploadMsg(`Activated ${data.filename} (${data.node_count} nodes)`);
      addToast(`Graph activated — ${data.node_count} nodes`, "success");
      if (fileRef.current) fileRef.current.value = "";
      loadAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      setUploadError(msg);
      addToast(msg, "error");
    } finally {
      setUploading(false);
    }
  }

  async function handleActivate(name: string) {
    setActivating(name);
    try {
      const r = await fetch(`${API}/graphs/${encodeURIComponent(name)}`, { method: "POST" });
      if (!r.ok) {
        const data = await r.json().catch(() => ({})) as { detail?: string };
        throw new Error(data.detail ?? `HTTP ${r.status}`);
      }
      addToast(`Graph "${name}" activated`, "success");
      loadAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Activation failed";
      setUploadError(msg);
      addToast(msg, "error");
    } finally {
      setActivating(null);
    }
  }

  function fmtDate(iso: string | null) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-CA", { month: "short", day: "numeric", year: "numeric" });
  }

  function fmtTime(iso: string) {
    return new Date(iso).toLocaleString("en-CA", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  }

  const edgesZero = settings !== null && settings.edge_count === 0;

  return (
    <div className="settings-pane">
      <h2 className="settings-heading">Settings</h2>

      {/* Active Graph */}
      <section className="settings-section">
        <div className="settings-section-title">Active Graph</div>
        {settings ? (
          <div className="settings-grid">
            <div className="settings-row">
              <span className="settings-label">Name</span>
              <span className="settings-value">{settings.graph_name}</span>
            </div>
            <div className="settings-row">
              <span className="settings-label">Nodes / Edges</span>
              <span className={`settings-value${edgesZero ? " settings-warn" : ""}`}>
                {settings.node_count} nodes / {settings.edge_count} edges
                {edgesZero && <span className="settings-warn-tag"> ⚠ no edges — run graphify update to rebuild</span>}
              </span>
            </div>
            <div className="settings-row">
              <span className="settings-label">Path</span>
              <span className="settings-value settings-mono settings-break">
                {settings.graph_path}
              </span>
            </div>
          </div>
        ) : (
          <p className="settings-dim">Loading…</p>
        )}
      </section>

      {/* Available Graphs */}
      <section className="settings-section">
        <div className="settings-section-title">
          Available Graphs
          <button className="settings-refresh-btn" type="button" onClick={loadAll}>
            Refresh
          </button>
        </div>
        {graphs.length === 0 ? (
          <p className="settings-dim">No graphs found.</p>
        ) : (
          <div className="settings-graph-list">
            {graphs.map((g) => (
              <div key={g.path} className={`settings-graph-row${g.active ? " active" : ""}`}>
                <div className="settings-graph-info">
                  <span className="settings-graph-name">{g.name}</span>
                  <span className="settings-graph-meta">
                    {g.source === "demo" ? "demo" : g.source === "configured" ? "configured" : `uploaded ${fmtDate(g.uploaded_at)}`}
                  </span>
                </div>
                {g.active ? (
                  <span className="settings-graph-active-badge">Active</span>
                ) : (
                  <button
                    className="settings-upload-btn"
                    style={{ padding: "4px 12px", fontSize: 12 }}
                    disabled={activating === g.name}
                    onClick={() => handleActivate(g.name)}
                  >
                    {activating === g.name ? "Activating…" : "Activate"}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
        {uploadError && <p className="settings-err">{uploadError}</p>}
      </section>

      {/* Upload Graph */}
      <section className="settings-section">
        <div className="settings-section-title">Upload Graph</div>
        <p className="settings-dim" style={{ marginBottom: 10 }}>
          Upload a Graphify <code>graph.json</code> to activate it without restarting the server.
        </p>
        <form className="settings-upload-form" onSubmit={handleUpload}>
          <input
            ref={fileRef}
            type="file"
            name="graph"
            accept=".json"
            required
            className="settings-file-input"
          />
          <button type="submit" className="settings-upload-btn" disabled={uploading}>
            {uploading ? "Uploading…" : "Activate"}
          </button>
        </form>
        {uploadMsg && <p className="settings-ok">{uploadMsg}</p>}
      </section>

      {/* Ollama */}
      <section className="settings-section">
        <div className="settings-section-title">
          Ollama
          <button className="settings-refresh-btn" type="button" onClick={loadAll}>
            Refresh
          </button>
        </div>
        {ollama ? (
          <div className="settings-grid">
            <div className="settings-row">
              <span className="settings-label">Status</span>
              <span
                className={`settings-value ${ollama.connected ? "settings-connected" : "settings-disconnected"}`}
              >
                {ollama.connected ? "Connected" : "Disconnected"}
              </span>
            </div>
            <div className="settings-row">
              <span className="settings-label">URL</span>
              <span className="settings-value settings-mono">{ollama.url}</span>
            </div>
            {ollama.connected && ollama.models.length > 0 && (
              <div className="settings-row">
                <span className="settings-label">Models</span>
                <span className="settings-value">{ollama.models.join(", ")}</span>
              </div>
            )}
            {ollama.connected && ollama.models.length === 0 && (
              <div className="settings-row">
                <span className="settings-label">Models</span>
                <span className="settings-dim">None pulled yet</span>
              </div>
            )}
          </div>
        ) : (
          <p className="settings-dim">Checking…</p>
        )}
      </section>

      {/* Organisation */}
      {org && (
        <section className="settings-section">
          <div className="settings-section-title">Organisation</div>
          <div className="settings-grid">
            <div className="settings-row">
              <span className="settings-label">Storage</span>
              <span className="settings-value settings-mono">{org.storage_backend}</span>
            </div>
            <div className="settings-row">
              <span className="settings-label">Ollama URL</span>
              <span className="settings-value settings-mono">{org.ollama_url}</span>
            </div>
          </div>
          {org.last_seen_devices.length > 0 && (
            <>
              <div className="settings-label" style={{ padding: "10px 16px 4px", opacity: 0.6, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Last Seen Devices
              </div>
              <div className="settings-grid">
                {org.last_seen_devices.slice(0, 5).map((d) => (
                  <div key={d.user} className="settings-row">
                    <span className="settings-label settings-mono">{d.user}</span>
                    <span className="settings-value settings-dim">{fmtTime(d.last_seen)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {/* API */}
      <section className="settings-section">
        <div className="settings-section-title">API</div>
        {settings ? (
          <div className="settings-grid">
            <div className="settings-row">
              <span className="settings-label">Version</span>
              <span className="settings-value">{settings.version}</span>
            </div>
            <div className="settings-row">
              <span className="settings-label">Auth</span>
              <span className="settings-value">
                {settings.api_key_required ? "API key required" : "No auth (localhost only)"}
              </span>
            </div>
            <div className="settings-row">
              <span className="settings-label">Backend URL</span>
              <span className="settings-value settings-mono">{API}</span>
            </div>
          </div>
        ) : (
          <p className="settings-dim">Loading…</p>
        )}
      </section>
    </div>
  );
}
