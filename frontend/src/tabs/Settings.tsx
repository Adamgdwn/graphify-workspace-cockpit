import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import {
  API_AUTH_ERROR_MESSAGE,
  apiErrorMessage,
  apiFetch,
  clearStoredApiKey,
  getStoredApiKey,
  setStoredApiKey,
} from "../api/client";
import { API } from "../config";
import { useToast } from "../components/Toast";
import { WorkingStatus } from "../components/WorkingStatus";

interface SettingsProps {
  onNavigateScope: () => void;
}

interface AppSettings {
  version: string;
  graph_path: string;
  graph_name: string;
  node_count: number;
  edge_count: number;
  state_dir: string;
  api_key_required: boolean;
  graphify: GraphifyStatus;
}

interface GraphifyStatus {
  available: boolean;
  version: string | null;
  code: string | null;
  message: string | null;
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

interface GraphStats {
  raw_node_count: number;
  avg_tokens_per_node: number;
  estimated_tokens_saved_per_query: number;
}

interface OrgSettings {
  active_graph: { name: string; path: string };
  ollama_url: string;
  storage_backend: string;
  last_seen_devices: { user: string; last_seen: string }[];
  graph_stats?: GraphStats;
}

interface RebuildStatus {
  status: "idle" | "running" | "complete" | "error";
  last_run: string | null;
  error?: string | null;
  code?: string | null;
}

interface ConnectorSync {
  status: string;
  started_at?: string;
  finished_at?: string;
  item_count?: number;
  error?: string | null;
}

interface ConnectorInfo {
  id: string;
  display_name: string;
  source: string;
  configured: boolean;
  authenticated: boolean;
  site_urls?: string[];
  sync: ConnectorSync;
}

type AuthFlowState = "idle" | "started" | "polling" | "complete" | "error";

interface DeviceFlow {
  user_code: string;
  verification_uri: string;
  message: string;
}

interface ChatConfig {
  system_prompt: string;
  model: string;
}

interface ClusterSelectionState {
  sources: string[];
  clusters: string[] | null;
}

interface ClusterOption {
  id: string;
  node_count: number;
}

interface ClusterSelectionData {
  selection: ClusterSelectionState;
  available_sources: string[];
  available_clusters: ClusterOption[];
}

export function Settings({ onNavigateScope }: SettingsProps) {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [settingsLoadError, setSettingsLoadError] = useState<string | null>(null);
  const [ollama, setOllama] = useState<OllamaStatus | null>(null);
  const [graphs, setGraphs] = useState<GraphEntry[]>([]);
  const [org, setOrg] = useState<OrgSettings | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const { addToast } = useToast();

  // Cloud connectors
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [authFlow, setAuthFlow] = useState<DeviceFlow | null>(null);
  const [authState, setAuthState] = useState<AuthFlowState>("idle");
  const [syncing, setSyncing] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Rebuild graph
  const [rebuildStatus, setRebuildStatus] = useState<RebuildStatus | null>(null);
  const [rebuilding, setRebuilding] = useState(false);
  const rebuildPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Knowledge source / cluster selection
  const [clusterSel, setClusterSel] = useState<ClusterSelectionData | null>(null);
  const [updatingSel, setUpdatingSel] = useState(false);

  // AI assistant config
  const [chatConfig,  setChatConfig]  = useState<ChatConfig | null>(null);
  const [chatDraft,   setChatDraft]   = useState<ChatConfig | null>(null);
  const [savingChat,  setSavingChat]  = useState(false);

  // Scan directories
  const [scanDirs, setScanDirs] = useState<string[]>([]);
  const [scanDirInput, setScanDirInput] = useState("");
  const [addingDir, setAddingDir] = useState(false);

  // Semantic similarity pass
  const [semanticStatus, setSemanticStatus] = useState<{
    status: string; progress: number; total: number;
    last_run: string | null; error: string | null; edge_count: number; model: string | null;
  } | null>(null);
  const [semanticModel, setSemanticModel] = useState("nomic-embed-text:latest");
  const [runningSemantic, setRunningSemantic] = useState(false);
  const semanticPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // API key
  const [apiKeyInput, setApiKeyInput] = useState(() => getStoredApiKey());
  const [hasStoredApiKey, setHasStoredApiKey] = useState(() => getStoredApiKey().length > 0);
  const [apiKeyStatus, setApiKeyStatus] = useState<string | null>(null);
  const [testingApiKey, setTestingApiKey] = useState(false);

  async function loadJson<T>(path: string): Promise<T> {
    const response = await apiFetch(path);
    if (!response.ok) throw new Error(await apiErrorMessage(response));
    return response.json() as Promise<T>;
  }

  const loadConnectors = useCallback(() => {
    loadJson<ConnectorInfo[]>(`/connectors`)
      .then(setConnectors)
      .catch(() => setConnectors([]));
  }, []);

  function loadAll() {
    loadJson<AppSettings>(`/settings`)
      .then((data) => {
        setSettings(data);
        setSettingsLoadError(null);
      })
      .catch((err: unknown) => {
        setSettings(null);
        setSettingsLoadError(err instanceof Error ? err.message : "Settings unavailable");
      });
    loadJson<OllamaStatus>(`/status/ollama`)
      .then(setOllama)
      .catch(() => setOllama(null));
    loadJson<GraphEntry[]>(`/graphs`)
      .then(setGraphs)
      .catch(() => setGraphs([]));
    loadJson<OrgSettings>(`/settings/org`)
      .then(setOrg)
      .catch(() => setOrg(null));
    loadJson<RebuildStatus>(`/graph/rebuild/status`)
      .then(setRebuildStatus)
      .catch(() => setRebuildStatus(null));
    loadJson<ClusterSelectionData>(`/cluster-selection`)
      .then(setClusterSel)
      .catch(() => setClusterSel(null));
    loadJson<ChatConfig>(`/chat-config`)
      .then((d: ChatConfig) => { setChatConfig(d); setChatDraft(d); })
      .catch(() => { setChatConfig(null); setChatDraft(null); });
    loadJson<{ dirs: string[] }>(`/graph/scan-dirs`)
      .then((d: { dirs: string[] }) => setScanDirs(d.dirs))
      .catch(() => setScanDirs([]));
    loadJson<typeof semanticStatus>(`/graph/semantic-pass/status`)
      .then(setSemanticStatus)
      .catch(() => setSemanticStatus(null));
    loadConnectors();
  }

  async function handleSaveApiKey(e: FormEvent) {
    e.preventDefault();
    const key = apiKeyInput.trim();
    if (!key) {
      clearStoredApiKey();
      setHasStoredApiKey(false);
      setApiKeyStatus("API key cleared.");
      addToast("API key cleared", "info");
      loadAll();
      return;
    }

    setStoredApiKey(key);
    setApiKeyInput(key);
    setHasStoredApiKey(true);
    setApiKeyStatus("API key saved in this browser.");
    addToast("API key saved", "success");
    loadAll();
  }

  async function handleTestApiKey() {
    const key = apiKeyInput.trim();
    if (!key) {
      setApiKeyStatus("Enter an API key to test.");
      return;
    }

    setTestingApiKey(true);
    try {
      const response = await apiFetch(`/settings`, { headers: { "X-API-Key": key } });
      if (!response.ok) throw new Error(await apiErrorMessage(response));
      const data = await response.json() as AppSettings;
      setSettings(data);
      setSettingsLoadError(null);
      setApiKeyStatus("API key accepted.");
      addToast("API key accepted", "success");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : API_AUTH_ERROR_MESSAGE;
      setApiKeyStatus(message);
      addToast(message, "error");
    } finally {
      setTestingApiKey(false);
    }
  }

  function handleClearApiKey() {
    clearStoredApiKey();
    setApiKeyInput("");
    setHasStoredApiKey(false);
    setApiKeyStatus("API key cleared.");
    addToast("API key cleared", "info");
    loadAll();
  }

  async function handleRebuild() {
    setRebuilding(true);
    try {
      const r = await apiFetch(`/graph/rebuild`, { method: "POST" });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
      }
      addToast("Graph rebuild started", "info");
      if (rebuildPollRef.current) clearInterval(rebuildPollRef.current);
      rebuildPollRef.current = setInterval(async () => {
        try {
          const sr = await apiFetch(`/graph/rebuild/status`);
          const sd: RebuildStatus = await sr.json();
          setRebuildStatus(sd);
          if (sd.status === "complete") {
            clearInterval(rebuildPollRef.current!);
            rebuildPollRef.current = null;
            setRebuilding(false);
            addToast("Graph rebuilt successfully", "success");
            loadAll();
          } else if (sd.status === "error") {
            clearInterval(rebuildPollRef.current!);
            rebuildPollRef.current = null;
            setRebuilding(false);
            addToast(`Rebuild error: ${sd.error ?? "unknown"}`, "error");
          }
        } catch {
          clearInterval(rebuildPollRef.current!);
          rebuildPollRef.current = null;
          setRebuilding(false);
        }
      }, 2000);
    } catch (err: unknown) {
      setRebuilding(false);
      addToast(err instanceof Error ? err.message : "Rebuild failed", "error");
    }
  }

  async function applyClusterSel(sel: { sources: string[]; clusters: string[] | null }) {
    setUpdatingSel(true);
    try {
      const r = await apiFetch(`/cluster-selection`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(sel),
      });
      if (!r.ok) throw new Error(await apiErrorMessage(r));
      const data = await r.json() as ClusterSelectionState;
      setClusterSel((prev) => prev ? { ...prev, selection: data } : null);
      addToast("Knowledge sources updated", "info");
    } catch {
      addToast("Failed to update selection", "error");
    } finally {
      setUpdatingSel(false);
    }
  }

  async function toggleSource(source: string) {
    if (!clusterSel) return;
    const current = clusterSel.selection.sources;
    const next = current.includes(source)
      ? current.filter((s) => s !== source)
      : [...current, source];
    await applyClusterSel({ sources: next, clusters: clusterSel.selection.clusters });
  }

  async function toggleCluster(clusterId: string) {
    if (!clusterSel) return;
    const allIds = clusterSel.available_clusters.map((c) => c.id);
    const current = clusterSel.selection.clusters ?? allIds;
    const next = current.includes(clusterId)
      ? current.filter((c) => c !== clusterId)
      : [...current, clusterId];
    const isAll = next.length === allIds.length && allIds.every((id) => next.includes(id));
    await applyClusterSel({ sources: clusterSel.selection.sources, clusters: isAll ? null : next });
  }

  async function handleSelectAll() {
    if (!clusterSel) return;
    await applyClusterSel({ sources: clusterSel.available_sources, clusters: null });
  }

  async function handleDeselectAll() {
    if (!clusterSel) return;
    await applyClusterSel({ sources: clusterSel.available_sources, clusters: [] });
  }

  async function handleAddScanDir(e: FormEvent) {
    e.preventDefault();
    const path = scanDirInput.trim();
    if (!path) return;
    setAddingDir(true);
    try {
      const r = await apiFetch(`/graph/scan-dirs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      if (!r.ok) {
        addToast(await apiErrorMessage(r), "error");
      } else {
        const d = await r.json() as { dirs: string[] };
        setScanDirs(d.dirs);
        setScanDirInput("");
        addToast("Directory added", "success");
      }
    } catch {
      addToast("Failed to add directory", "error");
    } finally {
      setAddingDir(false);
    }
  }

  async function handleRemoveScanDir(path: string) {
    try {
      const r = await apiFetch(`/graph/scan-dirs`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      if (r.ok) {
        const d = await r.json() as { dirs: string[] };
        setScanDirs(d.dirs);
        addToast("Directory removed", "info");
      }
    } catch {
      addToast("Failed to remove directory", "error");
    }
  }

  async function handleRunSemanticPass() {
    setRunningSemantic(true);
    try {
      const r = await apiFetch(`/graph/semantic-pass`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: semanticModel, threshold: 0.78 }),
      });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
      }
      addToast("Semantic analysis started", "info");
      if (semanticPollRef.current) clearInterval(semanticPollRef.current);
      semanticPollRef.current = setInterval(async () => {
        try {
          const sr = await apiFetch(`/graph/semantic-pass/status`);
          const sd = await sr.json();
          setSemanticStatus(sd);
          if (sd.status === "complete") {
            clearInterval(semanticPollRef.current!);
            semanticPollRef.current = null;
            setRunningSemantic(false);
            addToast(`Semantic analysis complete — ${sd.edge_count} similarity edges found`, "success");
          } else if (sd.status === "error") {
            clearInterval(semanticPollRef.current!);
            semanticPollRef.current = null;
            setRunningSemantic(false);
            addToast(`Semantic analysis failed: ${sd.error}`, "error");
          }
        } catch { /* ignore poll errors */ }
      }, 3000);
    } catch (err) {
      addToast(`Failed to start semantic analysis: ${(err as Error).message}`, "error");
      setRunningSemantic(false);
    }
  }

  async function handleSaveChatConfig() {
    if (!chatDraft) return;
    setSavingChat(true);
    try {
      const r = await apiFetch(`/chat-config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(chatDraft),
      });
      if (!r.ok) throw new Error(await apiErrorMessage(r));
      const saved = await r.json() as ChatConfig;
      setChatConfig(saved);
      setChatDraft(saved);
      addToast("AI Assistant config saved", "success");
    } catch {
      addToast("Failed to save AI config", "error");
    } finally {
      setSavingChat(false);
    }
  }

  useEffect(() => {
    loadAll();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleMicrosoftAuth() {
    setAuthState("started");
    setAuthFlow(null);
    try {
      const r = await apiFetch(`/connectors/microsoft/auth`, { method: "POST" });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
      }
      const flow: DeviceFlow = await r.json();
      setAuthFlow(flow);
      setAuthState("polling");
      // Start polling
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const pr = await apiFetch(`/connectors/microsoft/auth/poll`, { method: "POST" });
          const pd = await pr.json() as { status: string; detail?: string };
          if (pd.status === "complete") {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setAuthState("complete");
            setAuthFlow(null);
            addToast("Microsoft account connected", "success");
            loadConnectors();
          } else if (pd.status === "error") {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setAuthState("error");
            addToast(pd.detail ?? "Auth error", "error");
          }
        } catch {
          // keep polling
        }
      }, 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Auth failed";
      setAuthState("error");
      addToast(msg, "error");
    }
  }

  async function handleRevoke() {
    try {
      const r = await apiFetch(`/connectors/microsoft/auth`, { method: "DELETE" });
      if (!r.ok) throw new Error(await apiErrorMessage(r));
      setAuthState("idle");
      addToast("Microsoft account disconnected", "info");
      loadConnectors();
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : "Revoke failed", "error");
    }
  }

  async function handleSync(connectorId: string) {
    setSyncing(connectorId);
    try {
      const r = await apiFetch(`/connectors/${connectorId}/sync`, { method: "POST" });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
      }
      addToast(`${connectorId} sync started`, "info");
      // Poll for completion
      const poll = setInterval(async () => {
        try {
          const sr = await apiFetch(`/connectors/${connectorId}/status`);
          const sd = await sr.json() as ConnectorSync;
          if (sd.status !== "syncing") {
            clearInterval(poll);
            setSyncing(null);
            if (sd.status === "complete") {
              addToast(`${connectorId} sync complete — ${sd.item_count ?? 0} items ingested`, "success");
              loadAll();
            } else if (sd.status === "error") {
              addToast(`${connectorId} sync error: ${sd.error ?? "unknown"}`, "error");
            }
            loadConnectors();
          }
        } catch {
          clearInterval(poll);
          setSyncing(null);
        }
      }, 3000);
    } catch (err: unknown) {
      setSyncing(null);
      addToast(err instanceof Error ? err.message : "Sync failed", "error");
    }
  }

  // Cleanup polls on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (rebuildPollRef.current) clearInterval(rebuildPollRef.current);
    };
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
      const r = await apiFetch(`/graph/upload`, { method: "POST", body });
      if (!r.ok) throw new Error(await apiErrorMessage(r, "Upload failed"));
      const data = await r.json();
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
    setUploadError(null);
    try {
      const r = await apiFetch(`/graphs/${encodeURIComponent(name)}/activate`, { method: "POST" });
      if (!r.ok) {
        throw new Error(await apiErrorMessage(r));
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
  const graphifyMissing = settings?.graphify.available === false;

  return (
    <div className="settings-pane">
      <h2 className="settings-heading">Settings</h2>

      <section className="settings-section">
        <div className="settings-section-title">Workspace Scope</div>
        <p className="settings-dim">
          Drive, folder, and workspace selection now lives in its own tab. Generate a scoped map there, then review it on Map.
        </p>
        <div className="scope-actions">
          <button type="button" className="settings-upload-btn" onClick={onNavigateScope}>
            Open Workspace Scope
          </button>
        </div>
      </section>

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
            <div className="settings-row">
              <span className="settings-label">Graphify</span>
              <span
                className={`settings-value ${settings.graphify.available ? "settings-connected" : "settings-disconnected"}`}
              >
                {settings.graphify.available
                  ? settings.graphify.version ?? "Available"
                  : "Missing"}
                {!settings.graphify.available && (
                  <span className="settings-warn-tag">
                    Install graphifyy to enable Ask and graph rebuild.
                  </span>
                )}
              </span>
            </div>
          </div>
        ) : (
          <WorkingStatus label="Loading settings" />
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

      {/* Rebuild Graph */}
      <section className="settings-section">
        <div className="settings-section-title">Rebuild Graph</div>
        <p className="settings-dim" style={{ marginBottom: 10 }}>
          Rebuild from the saved workspace scope above when one exists; otherwise it falls back to the local repo scan.
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            type="button"
            className="settings-upload-btn"
            onClick={handleRebuild}
            disabled={rebuilding || graphifyMissing}
          >
            {rebuilding ? "Rebuilding…" : "Rebuild Graph"}
          </button>
          {graphifyMissing && (
            <span className="settings-dim settings-warn" style={{ fontSize: 12 }}>
              Graphify CLI missing
            </span>
          )}
          {rebuilding && <span className="settings-dim" style={{ fontSize: 12 }}>Running graphify update…</span>}
          {rebuildStatus && !rebuilding && rebuildStatus.status !== "idle" && (
            <span className={`settings-dim${rebuildStatus.status === "error" ? " settings-warn" : ""}`} style={{ fontSize: 12 }}>
              {rebuildStatus.status === "complete"
                ? `Last rebuild: ${rebuildStatus.last_run ? fmtTime(rebuildStatus.last_run) : "—"}`
                : rebuildStatus.status === "error"
                ? `Error: ${rebuildStatus.error ?? "unknown"}`
                : ""}
            </span>
          )}
        </div>
      </section>

      {/* Local Repositories */}
      <section className="settings-section">
        <div className="settings-section-title">Local Repositories</div>
        <p className="settings-dim" style={{ marginBottom: 10 }}>
          Directories scanned by graphify when you rebuild the graph.
          Add any local repo or folder — each is scanned and merged into one graph.
          Then click <strong>Rebuild Graph</strong> above to apply.
        </p>
        {scanDirs.length === 0 ? (
          <p className="settings-dim" style={{ marginBottom: 8 }}>
            No directories configured — rebuild uses this repo only.
          </p>
        ) : (
          <div className="connector-list" style={{ marginBottom: 8 }}>
            {scanDirs.map((d) => (
              <div key={d} className="connector-row">
                <span className="settings-value settings-mono settings-break" style={{ flex: 1, fontSize: 12 }}>{d}</span>
                <button
                  className="settings-refresh-btn"
                  type="button"
                  onClick={() => handleRemoveScanDir(d)}
                  style={{ color: "#f97316" }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
        <form className="settings-upload-form" onSubmit={handleAddScanDir} style={{ gap: 8 }}>
          <input
            className="settings-mono-input"
            style={{ flex: 1 }}
            value={scanDirInput}
            onChange={(e) => setScanDirInput(e.target.value)}
            placeholder="/home/user/code/my-repo"
            type="text"
          />
          <button type="submit" className="settings-upload-btn" disabled={addingDir || !scanDirInput.trim()}>
            {addingDir ? "Adding…" : "Add Directory"}
          </button>
        </form>
      </section>

      {/* Semantic Analysis */}
      <section className="settings-section">
        <div className="settings-section-title">Semantic Analysis</div>
        <p className="settings-dim" style={{ marginBottom: 10 }}>
          Runs an overnight embedding pass on every node using your local LLM, then draws purple dashed edges
          between nodes with similar meaning — across files and across repos. Reveals overlaps (same
          capability built twice) and gaps. Results appear in the Map via the <strong>Semantic</strong> toggle.
        </p>

        {!ollama?.connected && (
          <p className="settings-dim" style={{ color: "#f97316", marginBottom: 10 }}>
            Ollama not connected — make sure it is running before starting the analysis.
          </p>
        )}

        {ollama?.connected && !ollama.models.some((m) => m.startsWith("nomic-embed-text")) && (
          <div className="settings-row" style={{ marginBottom: 10, padding: "8px 10px", background: "#1a1c2a", borderRadius: 6, border: "1px solid #2a3050" }}>
            <span className="settings-dim" style={{ fontSize: 12 }}>
              Recommended: <code>nomic-embed-text</code> (137 MB, purpose-built for semantic similarity).
              Run <code>ollama pull nomic-embed-text</code> in a terminal then reload this page, or pick an existing model below.
            </span>
          </div>
        )}

        <div className="settings-row" style={{ marginBottom: 10 }}>
          <span className="settings-label">Embedding model</span>
          <select
            className="settings-mono-input"
            style={{ flex: 1, maxWidth: 260 }}
            value={semanticModel}
            onChange={(e) => setSemanticModel(e.target.value)}
          >
            {ollama?.models.filter((m) => m.startsWith("nomic-embed-text")).map((m) => (
              <option key={m} value={m}>{m} (recommended)</option>
            ))}
            {ollama?.models.filter((m) => !m.startsWith("nomic-embed-text")).map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        {semanticStatus && semanticStatus.status !== "idle" && (
          <div style={{ marginBottom: 10 }}>
            {semanticStatus.status === "running" && (
              <>
                <WorkingStatus
                  label={`Embedding nodes ${semanticStatus.progress} / ${semanticStatus.total}`}
                />
                <div style={{ background: "#1a1c2a", borderRadius: 4, height: 6, overflow: "hidden" }}>
                  <div style={{
                    background: "#a855f7",
                    height: "100%",
                    width: semanticStatus.total > 0
                      ? `${Math.round((semanticStatus.progress / semanticStatus.total) * 100)}%`
                      : "0%",
                    transition: "width 1s linear",
                  }} />
                </div>
              </>
            )}
            {semanticStatus.status === "complete" && (
              <p className="settings-dim" style={{ color: "#4ade80" }}>
                Complete — {semanticStatus.edge_count} semantic edges found
                {semanticStatus.last_run ? ` (${new Date(semanticStatus.last_run).toLocaleString()})` : ""}.
                Toggle <strong>Semantic</strong> on the Map to view them.
              </p>
            )}
            {semanticStatus.status === "error" && (
              <p className="settings-dim" style={{ color: "#f97316" }}>
                Error: {semanticStatus.error}
              </p>
            )}
          </div>
        )}

        <button
          className="settings-upload-btn"
          onClick={handleRunSemanticPass}
          disabled={runningSemantic || !ollama?.connected || semanticStatus?.status === "running"}
        >
          {runningSemantic || semanticStatus?.status === "running"
            ? `Analysing… ${semanticStatus?.progress ?? 0}/${semanticStatus?.total ?? 0}`
            : semanticStatus?.status === "complete"
            ? "Re-run Semantic Analysis"
            : "Run Semantic Analysis"}
        </button>
      </section>

      {/* Knowledge Sources */}
      {clusterSel && (
        <section className="settings-section" id="knowledge-sources">
          <div className="settings-section-title">
            Knowledge Sources
            <div style={{ display: "flex", gap: 6 }}>
              <button className="settings-refresh-btn" type="button" onClick={handleSelectAll} disabled={updatingSel}>
                Select all
              </button>
              <button className="settings-refresh-btn" type="button" onClick={handleDeselectAll} disabled={updatingSel}>
                Deselect all
              </button>
            </div>
          </div>
          <p className="settings-dim" style={{ marginBottom: 10 }}>
            Toggle which sources and clusters feed the map, queries, and recommendations.
          </p>

          {/* Source toggles — only show if cloud sources are available */}
          {clusterSel.available_sources.length > 1 && (
            <>
              <div className="ks-group-label">Sources</div>
              <div className="ks-toggle-list">
                {clusterSel.available_sources.map((src) => {
                  const active = clusterSel.selection.sources.includes(src);
                  const label = src === "local"
                    ? "Local workspace"
                    : src.charAt(0).toUpperCase() + src.slice(1);
                  return (
                    <label key={src} className="ks-toggle-row">
                      <input
                        type="checkbox"
                        className="ks-toggle-check"
                        checked={active}
                        disabled={updatingSel}
                        onChange={() => toggleSource(src)}
                      />
                      <span className="ks-toggle-label">{label}</span>
                    </label>
                  );
                })}
              </div>
            </>
          )}

          {/* Cluster toggles */}
          {clusterSel.available_clusters.length > 0 && (
            <>
              <div className="ks-group-label" style={{ marginTop: 14 }}>Clusters</div>
              <div className="ks-cluster-grid">
                {clusterSel.available_clusters.map((c) => {
                  const allIds = clusterSel.available_clusters.map((x) => x.id);
                  const activeClusters = clusterSel.selection.clusters ?? allIds;
                  const active = activeClusters.includes(c.id);
                  return (
                    <label key={c.id} className="ks-toggle-row">
                      <input
                        type="checkbox"
                        className="ks-toggle-check"
                        checked={active}
                        disabled={updatingSel}
                        onChange={() => toggleCluster(c.id)}
                      />
                      <span className="ks-toggle-label">{c.id}</span>
                      <span className="ks-node-count">{c.node_count.toLocaleString()}</span>
                    </label>
                  );
                })}
              </div>
            </>
          )}

          {clusterSel.available_clusters.length === 0 && clusterSel.available_sources.length <= 1 && (
            <p className="settings-dim">No clusters found in the active graph.</p>
          )}
        </section>
      )}

      {/* AI Assistant */}
      {chatDraft && (
        <section className="settings-section" id="ai-assistant">
          <div className="settings-section-title">AI Assistant</div>
          <p className="settings-dim" style={{ marginBottom: 10 }}>
            System prompt and model for the floating AI panel. Changes take effect on the next message.
          </p>
          <div className="settings-grid">
            <div className="settings-row" style={{ alignItems: "flex-start" }}>
              <span className="settings-label" style={{ paddingTop: 6 }}>System prompt</span>
              <textarea
                className="settings-prompt-textarea"
                value={chatDraft.system_prompt}
                onChange={(e) => setChatDraft({ ...chatDraft, system_prompt: e.target.value })}
                rows={4}
              />
            </div>
            <div className="settings-row">
              <span className="settings-label">Model</span>
              <input
                className="settings-mono-input"
                value={chatDraft.model}
                onChange={(e) => setChatDraft({ ...chatDraft, model: e.target.value })}
                placeholder="phi4:latest"
              />
            </div>
          </div>
          <div style={{ padding: "8px 16px 4px" }}>
            <button
              className="settings-upload-btn"
              type="button"
              onClick={handleSaveChatConfig}
              disabled={
                savingChat ||
                (chatDraft.system_prompt === chatConfig?.system_prompt &&
                  chatDraft.model === chatConfig?.model)
              }
            >
              {savingChat ? "Saving…" : "Save"}
            </button>
          </div>
        </section>
      )}

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
            <div className="settings-row">
              <span className="settings-label">Est. tokens saved/query</span>
              <span className="settings-value">
                {org.graph_stats && org.graph_stats.estimated_tokens_saved_per_query > 0
                  ? `~${org.graph_stats.estimated_tokens_saved_per_query.toLocaleString()}`
                  : "—"}
              </span>
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
        <div className="settings-grid">
          {settings && (
            <div className="settings-row">
              <span className="settings-label">Version</span>
              <span className="settings-value">{settings.version}</span>
            </div>
          )}
          <div className="settings-row">
            <span className="settings-label">Auth</span>
            <span className="settings-value">
              {settings
                ? settings.api_key_required
                  ? "API key required"
                  : "No auth (localhost only)"
                : settingsLoadError === API_AUTH_ERROR_MESSAGE
                ? API_AUTH_ERROR_MESSAGE
                : "Unknown"}
            </span>
          </div>
          <div className="settings-row">
            <span className="settings-label">Backend URL</span>
            <span className="settings-value settings-mono">{API}</span>
          </div>
          <div className="settings-row">
            <span className="settings-label">Stored key</span>
            <span className="settings-value">
              {hasStoredApiKey ? "Saved locally" : "Not saved"}
            </span>
          </div>
          <div className="settings-row" style={{ alignItems: "flex-start" }}>
            <span className="settings-label" style={{ paddingTop: 7 }}>API key</span>
            <form className="settings-upload-form" onSubmit={handleSaveApiKey} style={{ flex: 1, gap: 8 }}>
              <input
                className="settings-mono-input"
                style={{ flex: 1, minWidth: 180 }}
                type="password"
                value={apiKeyInput}
                onChange={(event) => setApiKeyInput(event.target.value)}
                placeholder={hasStoredApiKey ? "Saved API key" : "Paste API key"}
                autoComplete="off"
                aria-label="Backend API key"
              />
              <button type="submit" className="settings-upload-btn">
                Save
              </button>
              <button
                type="button"
                className="settings-upload-btn"
                onClick={handleTestApiKey}
                disabled={testingApiKey || !apiKeyInput.trim()}
              >
                {testingApiKey ? "Testing…" : "Test"}
              </button>
              <button
                type="button"
                className="settings-refresh-btn"
                onClick={handleClearApiKey}
                disabled={!hasStoredApiKey && !apiKeyInput}
              >
                Clear
              </button>
            </form>
          </div>
        </div>
        {settingsLoadError && !settings && (
          <p className="settings-err">{settingsLoadError}</p>
        )}
        {apiKeyStatus && (
          <p className={apiKeyStatus === API_AUTH_ERROR_MESSAGE || apiKeyStatus.startsWith("Enter") ? "settings-err" : "settings-ok"}>
            {apiKeyStatus}
          </p>
        )}
        <p className="settings-dim" style={{ marginTop: 8 }}>
          Stored in this browser and sent as <code>X-API-Key</code>.
        </p>
      </section>

      {/* Connected Sources */}
      <section className="settings-section">
        <div className="settings-section-title">
          Connected Sources
          <button className="settings-refresh-btn" type="button" onClick={loadConnectors}>
            Refresh
          </button>
        </div>
        <p className="settings-dim" style={{ marginBottom: 12 }}>
          Cloud knowledge sources ingested into the active graph.
          Requires <code>MICROSOFT_CLIENT_ID</code> and <code>MICROSOFT_TENANT_ID</code> env vars.
        </p>

        {connectors.length === 0 ? (
          <p className="settings-dim">No connectors available — set MICROSOFT_CLIENT_ID to enable.</p>
        ) : (
          <div className="connector-list">
            {connectors.map((c) => {
              const syncStatus = c.sync?.status;
              const lastSync = c.sync?.finished_at
                ? fmtTime(c.sync.finished_at)
                : null;
              const isThisSyncing = syncing === c.id;
              return (
                <div key={c.id} className="connector-row">
                  <div className="connector-info">
                    <span className="connector-name">{c.display_name}</span>
                    <span className={`connector-status ${c.authenticated ? "conn-ok-text" : "conn-off-text"}`}>
                      {c.authenticated ? "Connected" : "Not connected"}
                    </span>
                    {syncStatus && syncStatus !== "never_synced" && (
                      <span className="connector-meta">
                        {syncStatus === "syncing" ? "Syncing…" : (
                          <>
                            {lastSync && `Last sync: ${lastSync}`}
                            {c.sync?.item_count != null && ` · ${c.sync.item_count} items`}
                            {c.sync?.error && (
                              <span className="settings-warn"> · {c.sync.error}</span>
                            )}
                          </>
                        )}
                      </span>
                    )}
                  </div>
                  <div className="connector-actions">
                    {c.authenticated && (
                      <button
                        className="settings-upload-btn"
                        style={{ padding: "4px 12px", fontSize: 12 }}
                        disabled={isThisSyncing || syncStatus === "syncing"}
                        onClick={() => handleSync(c.id)}
                      >
                        {isThisSyncing ? "Syncing…" : "Sync Now"}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Microsoft auth flow */}
        {connectors.some((c) => c.source === "microsoft") && (
          <div className="connector-auth-panel">
            {authState === "idle" || authState === "error" ? (
              connectors.find((c) => c.source === "microsoft")?.authenticated ? (
                <button
                  className="settings-upload-btn connector-disconnect-btn"
                  onClick={handleRevoke}
                >
                  Disconnect Microsoft Account
                </button>
              ) : (
                <button
                  className="settings-upload-btn"
                  onClick={handleMicrosoftAuth}
                  disabled={!connectors.find((c) => c.source === "microsoft")?.configured}
                >
                  Connect Microsoft Account
                </button>
              )
            ) : authState === "started" ? (
              <p className="settings-dim">Starting device flow…</p>
            ) : authState === "polling" && authFlow ? (
              <div className="connector-device-flow">
                <p className="connector-device-instruction">
                  Go to <strong>{authFlow.verification_uri}</strong> and enter code:
                </p>
                <div className="connector-device-code">{authFlow.user_code}</div>
                <p className="settings-dim connector-device-hint">
                  Waiting for sign-in…
                </p>
              </div>
            ) : authState === "complete" ? (
              <p className="settings-ok">Microsoft account connected.</p>
            ) : null}
            {!connectors.find((c) => c.source === "microsoft")?.configured && (
              <p className="settings-dim" style={{ marginTop: 8, fontSize: 12 }}>
                Set <code>MICROSOFT_CLIENT_ID</code> in backend env to enable.
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
