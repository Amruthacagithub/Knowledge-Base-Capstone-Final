import EvidencePaths from "./EvidencePaths";

const STATUS_LABELS = {
  supported: "Supported",
  conflicting: "Conflicting",
  insufficient: "Insufficient",
};

function matchingCitation(claim, citations) {
  const evidenceIds = new Set(claim.evidence_ids || []);
  return citations.find((citation) => evidenceIds.has(citation.chunk_id));
}

function ClaimRow({ claim, citations, onCitationClick }) {
  const citation = matchingCitation(claim, citations);
  const confidence = Math.round(Math.max(0, Math.min(1, claim.confidence || 0)) * 100);

  return (
    <li className="trust-claim-row">
      <span className={`verification-status status-${claim.status}`}>
        {STATUS_LABELS[claim.status] || claim.status}
      </span>
      <span className="trust-claim-text">{claim.text}</span>
      <span className="trust-confidence">{confidence}%</span>
      {citation && onCitationClick && (
        <button
          type="button"
          className="claim-evidence-btn"
          onClick={() => onCitationClick(citation)}
        >
          Evidence [{citation.marker}]
        </button>
      )}
    </li>
  );
}

function TraceDetails({ queryPlan }) {
  if (!queryPlan) return null;
  const hasCorrection = queryPlan.corrective_retrieval_used;
  const graphTraceCount = queryPlan.trace_ids?.length || 0;

  return (
    <details className="trust-trace">
      <summary>
        <span className="route-badge">{queryPlan.route || "local"}</span>
        <span>Execution trace</span>
        {hasCorrection && <span className="trace-flag">corrected</span>}
      </summary>
      <dl className="trace-grid">
        <div>
          <dt>Route</dt>
          <dd>{queryPlan.route || "local"}</dd>
        </div>
        <div>
          <dt>Subqueries</dt>
          <dd>{queryPlan.subqueries?.length || 0}</dd>
        </div>
        <div>
          <dt>Graph traces</dt>
          <dd>{graphTraceCount}</dd>
        </div>
        <div>
          <dt>Corrective retrieval</dt>
          <dd>{hasCorrection ? "Used" : "Not used"}</dd>
        </div>
      </dl>
      {queryPlan.subqueries?.length > 0 && (
        <ol className="trace-subqueries">
          {queryPlan.subqueries.map((subquery) => (
            <li key={subquery}>{subquery}</li>
          ))}
        </ol>
      )}
      {queryPlan.execution_trace_id && (
        <code className="trace-id">{queryPlan.execution_trace_id}</code>
      )}
    </details>
  );
}

export default function TrustDetails({
  claims = [],
  queryPlan,
  citations = [],
  onCitationClick,
  evidenceGraph,
}) {
  const supported = claims.filter((claim) => claim.status === "supported").length;

  return (
    <section className="trust-details" aria-label="Answer verification">
      {claims.length > 0 && (
        <>
          <div className="trust-heading">
            <h3>Claim verification</h3>
            <span>{supported} of {claims.length} supported</span>
          </div>
          <ul className="trust-claim-list">
            {claims.map((claim) => (
              <ClaimRow
                key={claim.id}
                claim={claim}
                citations={citations}
                onCitationClick={onCitationClick}
              />
            ))}
          </ul>
        </>
      )}
      <EvidencePaths graph={evidenceGraph} />
      <TraceDetails queryPlan={queryPlan} />
    </section>
  );
}