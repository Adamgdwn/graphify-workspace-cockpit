import { useEffect, useRef, useState, type FormEvent } from "react";
import { API } from "../config";

interface AppSettings {
  version: string;
  graph_path: string;
  graph_name: string;
  node_count: number;
  state_dir: string;
  api_key_required: boolean;
}

interface OllamaStatus {
  connected: boolean;
  models: string[];
  url: string;
}

export function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [ollama, setOllama] = useState<OllamaStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function loadAll() {
    fetch(`${API}/settings`)
      .then((r) => r.json())
      .then(setSettings)
      .catch(() => {});
    fetch(`${API}/status/ollama`)
      .then((r) => r.json())
      .then(setOllama)
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
      if (fileRef.current) fileRef.current.value = "";
      loadAll();
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="settings-pane">
      <h2 className="settings-heading">Settings</h2>

      <section className="settings-section">
        <div className="settings-section-title">Active Graph</div>
        {settings ? (
          <div className="settings-grid">
            <div className="settings-row">
              <span className="settings-label">Name</span>
              <span className="settings-value">{settings.graph_name}</span>
            </div>
            <div className="settings-row">
              <span className="settings-label">Nodes</span>
              <span className="settings-value">{settings.node_count}</span>
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
        {uploadError && <p className="settings-err">{uploadError}</p>}
      </section>

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
