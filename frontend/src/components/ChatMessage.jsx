import MarkdownContent from "./MarkdownContent";
import TrustDetails from "./TrustDetails";

export default function ChatMessage({
  turn,
  onCitationClick,
  selectedMarker,
}) {
  const isComplete = turn.status === "complete";
  const isPending = turn.status === "pending";
  const isError = turn.status === "error";

  return (
    <article className="chat-turn">
      <div className="q-bubble">{turn.query}</div>

      {isPending && (
        <div className="assistant-pending">
          <div className="typing-indicator" aria-label="Generating answer">
            <span />
            <span />
            <span />
          </div>
          <span className="typing-label">Searching documents and generating answer…</span>
        </div>
      )}

      {isError && (
        <div className="error-msg turn-error">{turn.errorMessage}</div>
      )}

      {isComplete && (
        <div className="a-card">
          <div className="a-label">
            <span className="dot" />
            Answer
            {turn.query_plan?.route && (
              <span className="query-type-badge route" title="Planner route">
                {turn.query_plan.route}
              </span>
            )}
            {turn.query_type && !turn.query_plan?.route && (
              <span className="query-type-badge" title="Search mode">
                {turn.query_type}
              </span>
            )}
          </div>
          <MarkdownContent
            className="a-body markdown-body"
            content={turn.answer}
            citations={turn.citations}
            onCitationClick={onCitationClick}
            selectedMarker={selectedMarker}
          />
          {(turn.claims?.length > 0 || turn.query_plan) && (
            <TrustDetails
              claims={turn.claims}
              queryPlan={turn.query_plan}
              citations={turn.citations}
              onCitationClick={onCitationClick}
              evidenceGraph={turn.evidence_graph}
            />
          )}
          <div className="a-meta">
            <span>{turn.latency_ms} ms</span>
            <span>{turn.chunks_found} chunks</span>
            <span>{turn.citations?.length || 0} sources</span>
            {turn.departments_hit?.length > 0 && (
              <span>{turn.departments_hit.join(", ")}</span>
            )}
          </div>
          {turn.citations?.length > 0 && (
            <div className="citations">
              <div className="c-heading">Sources — click to preview</div>
              <div className="c-list">
                {turn.citations.map((c) => (
                  <button
                    key={c.marker}
                    type="button"
                    className={`c-item c-item-btn ${selectedMarker === c.marker ? "active" : ""}`}
                    onClick={() => onCitationClick(c)}
                  >
                    <span className="c-num">{c.marker}</span>
                    <span className="c-title">{c.doc_title}</span>
                    <span className="c-dept">{c.department}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  );
}
