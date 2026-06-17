import { WorkspaceScopePicker } from "../components/WorkspaceScopePicker";

interface WorkspaceScopeProps {
  onGenerated: () => void;
}

export function WorkspaceScope({ onGenerated }: WorkspaceScopeProps) {
  return (
    <div className="workspace-scope-pane">
      <h2 className="settings-heading">Workspace Scope</h2>
      <WorkspaceScopePicker
        mode="startup"
        title="Generate Workspace Map"
        intro="Choose a drive or parent folder, inspect the bounded directory tree, select folders, and generate the map from that scope."
        generateLabel="Generate Map"
        autoInspectSavedProfile
        restoreSavedSelection={false}
        onGenerated={onGenerated}
      />
    </div>
  );
}
