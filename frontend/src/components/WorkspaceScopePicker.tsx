import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { apiErrorMessage, apiFetch } from "../api/client";
import { useToast } from "./Toast";
import { WorkingStatus } from "./WorkingStatus";

type WorkspaceScopeState = "included" | "excluded" | "partial";

export interface WorkspaceScopeNode {
  name: string;
  path: string;
  relative_path: string;
  kind: "directory" | "file" | "symlink" | "other";
  state: WorkspaceScopeState;
  project_type: string | null;
  is_repo: boolean;
  reasons: string[];
  warnings: string[];
  estimated_file_count: number;
  estimated_included_count: number;
  estimated_excluded_count: number;
  children: WorkspaceScopeNode[];
}

export interface WorkspaceScopeProfile {
  root: string;
  profile_name: string;
  included_paths: string[];
  excluded_paths: string[];
  exclude_patterns: string[];
  signal: {
    hide_low_signal: boolean;
    show_generated: boolean;
    min_visible_signal: string;
  };
}

interface WorkspaceRootSuggestions {
  platform: string;
  initial_root: string;
  roots: string[];
  repo_root: string;
  state_dir: string;
  graph_path: string;
}

interface WorkspaceScopeInspect {
  root: {
    name: string;
    path: string;
    exists: boolean;
    kind: string;
    state: WorkspaceScopeState;
    project_type: string | null;
    estimated_file_count: number;
    estimated_included_count: number;
    estimated_excluded_count: number;
  };
  max_depth: number;
  exclude_patterns: string[];
  tree: WorkspaceScopeNode;
}

interface RebuildStatus {
  status: "idle" | "running" | "complete" | "error";
  last_run: string | null;
  error?: string | null;
  code?: string | null;
  route?: "evaluating" | "local" | "elevated" | null;
  escalation?: {
    route?: "local" | "elevated";
    decision_source?: string;
    reason?: string;
    backend?: string | null;
    model?: string | null;
  } | null;
}

interface WorkspaceScopePickerProps {
  mode?: "settings" | "startup";
  title?: string;
  intro?: string;
  generateLabel?: string;
  autoInspectSavedProfile?: boolean;
  restoreSavedSelection?: boolean;
  initialRoot?: string;
  onGenerated?: () => void;
  onProfileSaved?: (profile: WorkspaceScopeProfile) => void;
}

const EVIDENCE_NODE_LIMIT = 15000;

const pendingScopeInspections = new Map<string, Promise<WorkspaceScopeInspect>>();

function scopePathLabel(node: WorkspaceScopeNode): string {
  return node.relative_path || node.name || node.path;
}

function collectScopePaths(
  node: WorkspaceScopeNode,
  predicate: (node: WorkspaceScopeNode) => boolean,
  includeRoot = false,
): string[] {
  const paths: string[] = [];
  if (includeRoot || node.relative_path) {
    if (predicate(node)) paths.push(node.path);
  }
  for (const child of node.children) {
    paths.push(...collectScopePaths(child, predicate));
  }
  return paths;
}

function isDefaultExcludedNode(node: WorkspaceScopeNode): boolean {
  return node.state === "excluded" || node.reasons.length > 0 || node.kind !== "directory";
}

function defaultExpandedPaths(tree: WorkspaceScopeNode): Set<string> {
  return new Set([tree.path, ...tree.children.slice(0, 12).map((child) => child.path)]);
}

function uniqueOptions(values: Array<string | null | undefined>): string[] {
  return [...new Set(values.map((value) => value?.trim()).filter(Boolean) as string[])];
}

function rebuildStatusText(status: RebuildStatus): string {
  if (status.route === "elevated") {
    const backend = status.escalation?.backend ? ` via ${status.escalation.backend}` : "";
    return `Elevated graph extraction is running${backend}.`;
  }
  if (status.route === "local") return "Local graph generation is running.";
  return "Choosing the graph generation route...";
}

function normalizedPathList(values: Iterable<string> | undefined): string[] {
  return [...new Set(Array.from(values ?? []).map((value) => value.trim()).filter(Boolean))].sort();
}

function samePathList(left: Iterable<string> | undefined, right: Iterable<string> | undefined): boolean {
  const a = normalizedPathList(left);
  const b = normalizedPathList(right);
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

function indexScopeNodes(node: WorkspaceScopeNode, nodes = new Map<string, WorkspaceScopeNode>()): Map<string, WorkspaceScopeNode> {
  nodes.set(node.path, node);
  for (const child of node.children) {
    indexScopeNodes(child, nodes);
  }
  return nodes;
}

function isDescendantPath(path: string, possibleParent: string): boolean {
  const parent = possibleParent.endsWith("/") ? possibleParent : `${possibleParent}/`;
  return path.startsWith(parent);
}

function topLevelSelectedPaths(paths: Iterable<string>): string[] {
  const selected = normalizedPathList(paths).sort((left, right) => left.length - right.length || left.localeCompare(right));
  const topLevel: string[] = [];
  for (const path of selected) {
    if (topLevel.some((parent) => path !== parent && isDescendantPath(path, parent))) continue;
    topLevel.push(path);
  }
  return topLevel;
}

function excludedPathsForSave(excludedPaths: Iterable<string>, includedPaths: Iterable<string>): string[] {
  const included = normalizedPathList(includedPaths);
  return normalizedPathList(excludedPaths).filter(
    (path) => !included.some((includedPath) => includedPath !== path && isDescendantPath(includedPath, path)),
  );
}

function selectedScopeTotals(tree: WorkspaceScopeNode, selectedPaths: Iterable<string>) {
  const nodes = indexScopeNodes(tree);
  return topLevelSelectedPaths(selectedPaths).reduce(
    (totals, path) => {
      const node = nodes.get(path);
      if (!node) {
        totals.missingSelected += 1;
        return totals;
      }
      totals.estimatedFiles += node.estimated_file_count;
      totals.ignoredByDefault += node.estimated_excluded_count;
      return totals;
    },
    { estimatedFiles: 0, ignoredByDefault: 0, missingSelected: 0 },
  );
}

function titleFromPath(path: string): string {
  const segment = path.split("/").filter(Boolean).pop() ?? path;
  const words = segment.replace(/[_-]+/g, " ").trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "Workspace";
  return words.map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

function draftProfileNameForSelection(includedPaths: Iterable<string>): string {
  const paths = normalizedPathList(includedPaths);
  if (paths.length === 1) return `${titleFromPath(paths[0])} Scope`;
  if (paths.length > 1) return `${paths.length.toLocaleString()} Folder Scope`;
  return "Workspace Scope";
}

function requestWorkspaceScopeInspection(root: string, maxDepth: number): Promise<WorkspaceScopeInspect> {
  const key = `${root}::${maxDepth}`;
  const pending = pendingScopeInspections.get(key);
  if (pending) return pending;

  const request = apiFetch(`/workspace-scope/inspect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root, max_depth: maxDepth }),
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(await apiErrorMessage(response));
      return response.json() as Promise<WorkspaceScopeInspect>;
    })
    .finally(() => {
      pendingScopeInspections.delete(key);
    });

  pendingScopeInspections.set(key, request);
  return request;
}

async function requestWorkspaceRootSuggestions(): Promise<WorkspaceRootSuggestions> {
  const response = await apiFetch(`/workspace-scope/suggested-roots`);
  if (!response.ok) throw new Error(await apiErrorMessage(response));
  return response.json() as Promise<WorkspaceRootSuggestions>;
}

export function WorkspaceScopePicker({
  mode = "settings",
  title = "Workspace Scope",
  intro = "Choose a parent folder, inspect the bounded repo tree, select included folders, and generate a scoped map.",
  generateLabel = "Generate Map",
  autoInspectSavedProfile,
  restoreSavedSelection,
  initialRoot,
  onGenerated,
  onProfileSaved,
}: WorkspaceScopePickerProps) {
  const { addToast } = useToast();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inspectRequestRef = useRef(0);
  const [rootInput, setRootInput] = useState("");
  const [selectedRootOption, setSelectedRootOption] = useState("");
  const [profileName, setProfileName] = useState("Workspace Scope");
  const [profileNameTouched, setProfileNameTouched] = useState(false);
  const [scope, setScope] = useState<WorkspaceScopeInspect | null>(null);
  const [profile, setProfile] = useState<WorkspaceScopeProfile | null>(null);
  const [included, setIncluded] = useState<Set<string>>(() => new Set());
  const [excluded, setExcluded] = useState<Set<string>>(() => new Set());
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [inspecting, setInspecting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rootSuggestions, setRootSuggestions] = useState<WorkspaceRootSuggestions | null>(null);
  const suggestedInitialRoot = rootSuggestions?.initial_root || initialRoot || "";

  const rootOptions = useMemo(
    () => uniqueOptions([profile?.root, selectedRootOption, initialRoot, ...(rootSuggestions?.roots ?? [])]),
    [initialRoot, profile?.root, rootSuggestions?.roots, selectedRootOption],
  );

  const includedCount = included.size;
  const excludedCount = excluded.size;
  const selectedTotals = useMemo(
    () => scope ? selectedScopeTotals(scope.tree, included) : { estimatedFiles: 0, ignoredByDefault: 0, missingSelected: 0 },
    [included, scope],
  );
  const selectionEstimateExceedsEvidenceLimit = selectedTotals.estimatedFiles > EVIDENCE_NODE_LIMIT;
  const selectionEstimateApproachesEvidenceLimit = (
    selectedTotals.estimatedFiles > Math.floor(EVIDENCE_NODE_LIMIT * 0.8)
    && !selectionEstimateExceedsEvidenceLimit
  );
  const draftRoot = scope?.root.path ?? rootInput.trim();
  const hasUnsavedScopeChanges = Boolean(
    profile
    && (
      draftRoot !== profile.root
      || !samePathList(included, profile.included_paths)
      || !samePathList(excluded, profile.excluded_paths)
      || profileName.trim() !== profile.profile_name
    ),
  );
  const hasDraftSelection = hasUnsavedScopeChanges || (!profile && includedCount > 0);
  const shouldAutoInspectSavedProfile = autoInspectSavedProfile ?? mode === "settings";
  const shouldRestoreSavedSelection = restoreSavedSelection ?? mode === "settings";
  const generateDisabledReason = !scope
    ? "Inspect a parent folder first."
    : includedCount === 0
    ? "Select at least one non-noisy folder."
    : null;

  const applyInspection = useCallback((data: WorkspaceScopeInspect, nextProfile: WorkspaceScopeProfile | null) => {
    setScope(data);
    setRootInput(data.root.path);
    setSelectedRootOption(data.root.path);
    setExpanded(defaultExpandedPaths(data.tree));
    setExcluded(new Set(collectScopePaths(data.tree, isDefaultExcludedNode)));
    if (nextProfile && nextProfile.root === data.root.path) {
      setIncluded(new Set(nextProfile.included_paths));
      setExcluded(new Set([...nextProfile.excluded_paths, ...collectScopePaths(data.tree, isDefaultExcludedNode)]));
    } else {
      setIncluded(new Set());
    }
  }, []);

  useEffect(() => {
    if (profileNameTouched) return;
    if (
      profile
      && draftRoot === profile.root
      && samePathList(included, profile.included_paths)
      && samePathList(excluded, profile.excluded_paths)
    ) {
      setProfileName(profile.profile_name);
      return;
    }
    setProfileName(draftProfileNameForSelection(included));
  }, [draftRoot, excluded, included, profile, profileNameTouched]);

  const inspectRoot = useCallback(async (root: string, nextProfile: WorkspaceScopeProfile | null = null) => {
    const path = root.trim();
    if (!path) return;
    const requestId = inspectRequestRef.current + 1;
    inspectRequestRef.current = requestId;
    setInspecting(true);
    setError(null);
    setMessage(null);
    try {
      const data = await requestWorkspaceScopeInspection(path, 3);
      if (inspectRequestRef.current !== requestId) return;
      applyInspection(data, nextProfile);
    } catch (err: unknown) {
      if (inspectRequestRef.current !== requestId) return;
      const text = err instanceof Error ? err.message : "Workspace inspection failed";
      setScope(null);
      setIncluded(new Set());
      setError(text);
    } finally {
      if (inspectRequestRef.current === requestId) {
        setInspecting(false);
      }
    }
  }, [applyInspection]);

  const loadSavedProfile = useCallback(() => {
    apiFetch(`/workspace-scope`)
      .then(async (response) => {
        if (!response.ok) throw new Error(await apiErrorMessage(response));
        return response.json() as Promise<{ profile: WorkspaceScopeProfile | null }>;
      })
      .then((data) => {
        setProfile(data.profile);
        if (!data.profile) {
          if (mode === "startup" && suggestedInitialRoot) {
            setRootInput(suggestedInitialRoot);
            setSelectedRootOption(suggestedInitialRoot);
            void inspectRoot(suggestedInitialRoot, null);
          }
          return;
        }
        setRootInput(data.profile.root);
        setSelectedRootOption(data.profile.root);
        setProfileName(data.profile.profile_name);
        setProfileNameTouched(false);
        setIncluded(shouldRestoreSavedSelection ? new Set(data.profile.included_paths) : new Set());
        setExcluded(shouldRestoreSavedSelection ? new Set(data.profile.excluded_paths) : new Set());
        if (shouldAutoInspectSavedProfile) {
          void inspectRoot(data.profile.root, shouldRestoreSavedSelection ? data.profile : null);
        }
      })
      .catch(() => {
        setProfile(null);
        if (mode === "startup" && suggestedInitialRoot) {
          setRootInput(suggestedInitialRoot);
          setSelectedRootOption(suggestedInitialRoot);
          void inspectRoot(suggestedInitialRoot, null);
        }
      });
  }, [inspectRoot, mode, shouldAutoInspectSavedProfile, shouldRestoreSavedSelection, suggestedInitialRoot]);

  useEffect(() => {
    loadSavedProfile();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadSavedProfile]);

  useEffect(() => {
    let alive = true;
    requestWorkspaceRootSuggestions()
      .then((data) => {
        if (!alive) return;
        setRootSuggestions(data);
      })
      .catch(() => {
        if (!alive) return;
        setRootSuggestions(null);
      });
    return () => {
      alive = false;
    };
  }, []);

  function handleRootOption(value: string) {
    setSelectedRootOption(value);
    if (value) setRootInput(value);
  }

  function handleRootShortcut(value: string) {
    setSelectedRootOption(value);
    setRootInput(value);
    setProfileNameTouched(false);
    void inspectRoot(value);
  }

  async function handleInspect(e: FormEvent) {
    e.preventDefault();
    setProfileNameTouched(false);
    await inspectRoot(rootInput);
  }

  function effectiveState(node: WorkspaceScopeNode): WorkspaceScopeState {
    if (excluded.has(node.path)) return "excluded";
    if (included.has(node.path)) return "included";
    return node.state;
  }

  function togglePath(node: WorkspaceScopeNode, include: boolean) {
    if (isDefaultExcludedNode(node)) return;
    setIncluded((prev) => {
      const next = new Set(prev);
      if (include) next.add(node.path);
      else next.delete(node.path);
      return next;
    });
    setExcluded((prev) => {
      const next = new Set(prev);
      if (include) next.delete(node.path);
      else next.add(node.path);
      return next;
    });
  }

  function toggleExpanded(path: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  async function saveProfile(): Promise<WorkspaceScopeProfile | null> {
    const root = scope?.root.path ?? rootInput.trim();
    if (!root || included.size === 0) return null;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const excludedForSave = excludedPathsForSave(excluded, included);
      const response = await apiFetch(`/workspace-scope`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          root,
          profile_name: profileName.trim() || "Workspace Scope",
          included_paths: Array.from(included),
          excluded_paths: excludedForSave,
          exclude_patterns: scope?.exclude_patterns,
          signal: profile?.signal ?? {
            hide_low_signal: true,
            show_generated: false,
            min_visible_signal: "important",
          },
        }),
      });
      if (!response.ok) throw new Error(await apiErrorMessage(response));
      const data = await response.json() as { profile: WorkspaceScopeProfile };
      setProfile(data.profile);
      setProfileName(data.profile.profile_name);
      setProfileNameTouched(false);
      setIncluded(new Set(data.profile.included_paths));
      setExcluded(new Set(data.profile.excluded_paths));
      onProfileSaved?.(data.profile);
      return data.profile;
    } catch (err: unknown) {
      const text = err instanceof Error ? err.message : "Failed to save workspace scope";
      setError(text);
      addToast(text, "error");
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveOnly() {
    const saved = await saveProfile();
    if (!saved) return;
    setMessage("Workspace scope saved.");
    addToast("Workspace scope saved", "success");
  }

  async function handleGenerate() {
    const saved = await saveProfile();
    if (!saved) return;
    setGenerating(true);
    setMessage("Workspace scope saved. Generating map...");
    try {
      const response = await apiFetch(`/graph/rebuild`, { method: "POST" });
      if (!response.ok) throw new Error(await apiErrorMessage(response));
      addToast("Graph generation started", "info");
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const statusResponse = await apiFetch(`/graph/rebuild/status`);
          if (!statusResponse.ok) throw new Error(await apiErrorMessage(statusResponse));
          const status = await statusResponse.json() as RebuildStatus;
          if (status.status === "running") {
            setMessage(rebuildStatusText(status));
          }
          if (status.status === "complete") {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setGenerating(false);
            setMessage("Scoped map generated.");
            addToast("Scoped map generated", "success");
            onGenerated?.();
          } else if (status.status === "error") {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setGenerating(false);
            const text = status.error || "Graph generation failed";
            setError(text);
            addToast(text, "error");
          }
        } catch (err: unknown) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setGenerating(false);
          const text = err instanceof Error ? err.message : "Graph generation failed";
          setError(text);
          addToast(text, "error");
        }
      }, 2000);
    } catch (err: unknown) {
      setGenerating(false);
      const text = err instanceof Error ? err.message : "Graph generation failed";
      setError(text);
      addToast(text, "error");
    }
  }

  function renderNode(node: WorkspaceScopeNode, depth = 0) {
    const state = effectiveState(node);
    const disabled = isDefaultExcludedNode(node);
    const isOpen = expanded.has(node.path);
    const label = scopePathLabel(node);
    const meta = [
      node.project_type,
      `${node.estimated_file_count.toLocaleString()} files`,
      node.estimated_excluded_count > 0 ? `${node.estimated_excluded_count.toLocaleString()} ignored` : null,
    ].filter(Boolean).join(" - ");

    return (
      <div key={node.path} className={`scope-node scope-node-${state}${disabled ? " scope-node-disabled" : ""}`} style={{ "--scope-depth": depth } as CSSProperties}>
        <div className="scope-node-main">
          <button
            type="button"
            className="scope-expand-btn"
            onClick={() => toggleExpanded(node.path)}
            disabled={node.children.length === 0}
            aria-label={isOpen ? "Collapse folder" : "Expand folder"}
          >
            {node.children.length > 0 ? (isOpen ? "v" : ">") : ""}
          </button>
          <label className="scope-node-toggle">
            <input
              type="checkbox"
              checked={included.has(node.path)}
              disabled={disabled}
              onChange={(event) => togglePath(node, event.target.checked)}
            />
            <span className="scope-node-label">{label}</span>
          </label>
          <span className={`scope-state-badge scope-state-${state}`}>{disabled ? "ignored" : state}</span>
        </div>
        <div className="scope-node-meta">
          {meta || node.kind}
          {node.warnings.map((warning) => (
            <span key={warning} className="scope-node-warning">{warning}</span>
          ))}
        </div>
        {node.reasons.length > 0 && (
          <div className="scope-node-reasons">
            {node.reasons.map((reason) => (
              <span key={reason}>{reason}</span>
            ))}
          </div>
        )}
        {node.children.length > 0 && isOpen && (
          <div className="scope-node-children">
            {node.children.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  }

  const treePanel = (
    <div className="scope-tree-panel">
      <div className="scope-tree-panel-head">
        <span>Workspace folders</span>
        <span className="settings-mono">
          {inspecting
            ? "Loading tree..."
            : scope
            ? `${includedCount.toLocaleString()} selected`
            : "No tree loaded"}
        </span>
      </div>
      {scope ? (
        <div className="scope-tree">
          {renderNode(scope.tree)}
        </div>
      ) : (
        <div className="scope-empty-tree">
          {inspecting ? (
            <WorkingStatus label="Inspecting folders" detail={rootInput || suggestedInitialRoot} />
          ) : (
            <div className="scope-empty-row">
              <span className="scope-empty-expander">v</span>
              <input type="checkbox" disabled aria-label="Workspace folders loading" />
              <span className="settings-mono">{rootInput || suggestedInitialRoot || "Choose a local folder"}</span>
              <span className="scope-state-badge scope-state-partial">choose root</span>
            </div>
          )}
        </div>
      )}
    </div>
  );

  return (
    <section className={mode === "startup" ? "scope-picker scope-picker-startup" : "settings-section scope-picker"}>
      <div className="settings-section-title">
        {title}
        {hasDraftSelection ? (
          <span className="scope-draft-pill">Draft</span>
        ) : profile ? (
          <span className="scope-saved-pill">Saved</span>
        ) : null}
      </div>
      <p className="settings-dim" style={{ marginBottom: 10 }}>{intro}</p>

      {mode === "startup" && (
        <div className="scope-root-shortcuts" aria-label="Workspace root shortcuts">
          {rootOptions.map((option) => (
            <button
              key={option}
              type="button"
              className={`scope-root-chip${option === selectedRootOption ? " scope-root-chip-active" : ""}`}
              onClick={() => handleRootShortcut(option)}
              disabled={inspecting && option === selectedRootOption}
            >
              {option}
            </button>
          ))}
        </div>
      )}

      <form className="settings-upload-form scope-root-form" onSubmit={handleInspect}>
        {mode !== "startup" && (
          <select
            className="settings-mono-input scope-root-select"
            value={rootOptions.includes(selectedRootOption) ? selectedRootOption : ""}
            onChange={(event) => handleRootOption(event.target.value)}
            aria-label="Suggested workspace roots"
          >
            <option value="">Suggested roots</option>
            {rootOptions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        )}
        <input
          className="settings-mono-input scope-root-input"
          value={rootInput}
          onChange={(event) => setRootInput(event.target.value)}
          placeholder={suggestedInitialRoot || "Choose a local folder path"}
          type="text"
          aria-label="Exact workspace path"
        />
        <button type="submit" className="settings-upload-btn" disabled={inspecting || !rootInput.trim()}>
          {inspecting ? "Inspecting..." : "Inspect Folder"}
        </button>
      </form>

      {treePanel}

      {(scope || profile) && (
        <div className="scope-summary">
          <span className="settings-mono settings-break">{draftRoot || profile?.root}</span>
          <span>{includedCount.toLocaleString()} selected paths</span>
          <span>{excludedCount.toLocaleString()} ignored paths</span>
          <span>{hasDraftSelection ? "unsaved draft" : "saved profile"}</span>
        </div>
      )}

      <div className="scope-profile-row">
        <label className="settings-label" htmlFor={`workspace-profile-name-${mode}`}>Profile</label>
        <input
          id={`workspace-profile-name-${mode}`}
          className="settings-mono-input"
          value={profileName}
          onChange={(event) => {
            setProfileNameTouched(true);
            setProfileName(event.target.value);
          }}
          placeholder="Workspace Scope"
        />
      </div>

      {scope && (
        <>
          <div className="scope-count-grid">
            <div>
              <span className="scope-count-value">{selectedTotals.estimatedFiles.toLocaleString()}</span>
              <span className="scope-count-label">estimated source files</span>
            </div>
            <div>
              <span className="scope-count-value">{includedCount.toLocaleString()}</span>
              <span className="scope-count-label">selected folders</span>
            </div>
            <div>
              <span className="scope-count-value">{selectedTotals.ignoredByDefault.toLocaleString()}</span>
              <span className="scope-count-label">default-ignored paths</span>
            </div>
          </div>
          {selectedTotals.missingSelected > 0 && (
            <p className="settings-dim scope-count-note">
              {selectedTotals.missingSelected.toLocaleString()} selected path{selectedTotals.missingSelected === 1 ? "" : "s"} are outside the inspected summary depth, so their file estimates are not included here.
            </p>
          )}
          {(selectionEstimateExceedsEvidenceLimit || selectionEstimateApproachesEvidenceLimit) && (
            <p className={`${selectionEstimateExceedsEvidenceLimit ? "settings-err" : "settings-warn-box"} scope-count-note`}>
              This selection has about {selectedTotals.estimatedFiles.toLocaleString()} source files before graph generation. Evidence view is capped at {EVIDENCE_NODE_LIMIT.toLocaleString()} visible nodes; choose fewer folders before generating if you need the full file-level map at once.
            </p>
          )}
          <div className="scope-toolbar">
            <span className="settings-dim">
              Current selection: {includedCount.toLocaleString()} selected, {excludedCount.toLocaleString()} ignored
              {generateDisabledReason ? ` - ${generateDisabledReason}` : ""}
            </span>
            <div className="scope-actions">
              {mode === "settings" && (
                <button
                  type="button"
                  className="settings-upload-btn settings-secondary-btn"
                  onClick={handleSaveOnly}
                  disabled={saving || generating || Boolean(generateDisabledReason)}
                >
                  {saving ? "Saving..." : "Save Scope"}
                </button>
              )}
              <button
                type="button"
                className="settings-upload-btn"
                onClick={handleGenerate}
                disabled={saving || generating || Boolean(generateDisabledReason)}
              >
                {generating ? "Generating..." : generateLabel}
              </button>
            </div>
          </div>
          <div className="scope-patterns">
            <span className="settings-label">Default ignores</span>
            <span>{scope.exclude_patterns.join(", ")}</span>
          </div>
        </>
      )}

      {!scope && (
        <div className="scope-toolbar">
          <span className="settings-dim">{generateDisabledReason}</span>
          <div className="scope-actions">
            <button type="button" className="settings-upload-btn" disabled>
              {generateLabel}
            </button>
          </div>
        </div>
      )}

      {!scope && !error && (
        <p className="settings-dim">No folder inspected yet.</p>
      )}
      {message && <p className="settings-ok">{message}</p>}
      {generating && (
        <WorkingStatus
          label="Generating workspace map"
          detail={message || "Watching the scoped rebuild"}
        />
      )}
      {error && <p className="settings-err">{error}</p>}
    </section>
  );
}
