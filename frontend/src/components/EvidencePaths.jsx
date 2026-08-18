function PathFlow({ path }) {
  return (
    <div className="evidence-path-flow" role="list" aria-label="Authorized evidence path">
      {path.entities.map((entity, index) => (
        <div className="evidence-path-step" role="listitem" key={entity.id}>
          {index > 0 && (
            <span className="evidence-path-edge">
              {path.relationships[index - 1]?.type.replaceAll("_", " ")}
            </span>
          )}
          <span className="evidence-path-node">{entity.name}</span>
        </div>
      ))}
      <span className="evidence-path-score">{Math.round(path.score * 100)}%</span>
    </div>
  );
}

export default function EvidencePaths({ graph }) {
  if (!graph?.paths?.length) return null;
  return (
    <section className="evidence-paths" aria-labelledby="evidence-paths-title">
      <div className="evidence-paths-heading">
        <h3 id="evidence-paths-title">Evidence paths</h3>
        <span>{graph.paths.length} authorized</span>
      </div>
      <div className="evidence-path-list">
        {graph.paths.map((path) => (
          <PathFlow key={path.relationship_ids.join(":")} path={path} />
        ))}
      </div>
    </section>
  );
}