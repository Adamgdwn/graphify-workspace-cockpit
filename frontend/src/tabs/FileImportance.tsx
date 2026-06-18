const IMPORTANCE_ROWS = [
  {
    rank: 1,
    tier: "Anchor",
    defaultMap: "Shown",
    knowledgeLens: "Shown",
    role: "Source-of-truth material for project intent, architecture, governance, operations, and decisions.",
    examples: "README.md, AGENTS.md, START_HERE.md, architecture docs, ADRs, runbooks, policy docs, project-control.yaml",
    reason: "source-of-truth file; governance or architecture document; decision context; configuration boundary",
  },
  {
    rank: 2,
    tier: "Interface",
    defaultMap: "Shown",
    knowledgeLens: "Shown",
    role: "Boundaries other projects or modules depend on, especially contracts, routes, schemas, migrations, auth, storage, and public APIs.",
    examples: "src/routes/users.ts, db/migrations/*.sql, schemas/*.json, contracts/public-api.d.ts, auth/*, storage/*",
    reason: "public API or data boundary; workspace-owned type contract",
  },
  {
    rank: 3,
    tier: "Important",
    defaultMap: "Shown",
    knowledgeLens: "Shown",
    role: "Files that shape runtime behavior or connect enough of the graph to influence build decisions.",
    examples: "main.py, app.py, server.ts, index.tsx, high-signal integration tests, connected implementation nodes",
    reason: "runtime entry point; high-signal test; connected implementation node; high graph degree",
  },
  {
    rank: 4,
    tier: "Evidence",
    defaultMap: "Hidden",
    knowledgeLens: "Held",
    role: "Ordinary implementation or supporting docs that are useful for drilldown, but noisy at broad workspace scale.",
    examples: "leaf components, helpers, local implementation modules, supporting documents outside architecture/governance paths",
    reason: "supporting evidence; supporting document",
  },
  {
    rank: 5,
    tier: "Hidden",
    defaultMap: "Hidden",
    knowledgeLens: "Held",
    role: "Generated, dependency, fixture, ambient, or low-signal files that rarely help cross-project decisions.",
    examples: "node_modules/@types/react/index.d.ts, next-env.d.ts, vite-env.d.ts, global.d.ts, fixtures, mocks, snapshots, lockfiles",
    reason: "dependency type declaration; generated type shim; ambient type declaration; fixture or mock evidence; lockfile",
  },
  {
    rank: 6,
    tier: "Excluded",
    defaultMap: "Excluded",
    knowledgeLens: "Excluded",
    role: "Paths removed before mapping because they are generated, bulky, secret-like, or local state.",
    examples: "node_modules/, .venv/, dist/, build/, .next/, coverage/, graphify-out/, workspace/state/, .env*, *.pem, *.key",
    reason: "default-ignored path; secret-like path; generated output; dependency folder",
  },
];

export function FileImportance() {
  return (
    <div className="importance-pane">
      <div className="importance-header">
        <div>
          <h2 className="settings-heading">Importance Criteria Table</h2>
          <p className="importance-subtitle">Static ranking used by the workspace knowledge lens.</p>
        </div>
        <div className="importance-summary">
          <span>Broad maps: ranks 1-3</span>
          <span>Evidence drilldown: ranks 1-5</span>
        </div>
      </div>

      <div className="importance-table-wrap">
        <table className="importance-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Tier</th>
              <th>Default Map</th>
              <th>Knowledge Lens</th>
              <th>What Counts</th>
              <th>Examples</th>
              <th>Reason Label</th>
            </tr>
          </thead>
          <tbody>
            {IMPORTANCE_ROWS.map((row) => (
              <tr key={row.tier} className={`importance-row importance-row-${row.tier.toLowerCase()}`}>
                <td className="importance-rank">{row.rank}</td>
                <td>
                  <span className={`map-type-badge map-importance-${row.tier.toLowerCase()}`}>
                    {row.tier}
                  </span>
                </td>
                <td>{row.defaultMap}</td>
                <td>{row.knowledgeLens}</td>
                <td>{row.role}</td>
                <td>{row.examples}</td>
                <td>{row.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
