import { useState } from "react";


function formatDate(value) {
  if (!value) return "Not specified";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

function ClaimChanges({ title, claims, tone }) {
  if (!claims?.length) return null;
  return (
    <section className={`version-change-group ${tone}`}>
      <h4>{title} ({claims.length})</h4>
      <ul>
        {claims.map((claim) => (
          <li key={claim.id}>{claim.text}</li>
        ))}
      </ul>
    </section>
  );
}

function ConflictRow({ conflict, canReview, onReview }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  const review = async (status) => {
    setPending(true);
    setError(null);
    try {
      await onReview(conflict.id, status);
    } catch (reviewError) {
      setError(reviewError.message);
    } finally {
      setPending(false);
    }
  };

  return (
    <li className="version-conflict-row">
      <div>
        <span className={`conflict-status conflict-${conflict.status}`}>
          {conflict.status}
        </span>
        <strong>{conflict.conflict_type.replaceAll("_", " ")}</strong>
        <p>{conflict.rationale}</p>
      </div>
      {canReview && conflict.status === "candidate" && (
        <div className="conflict-actions">
          <button type="button" disabled={pending} onClick={() => review("confirmed")}>
            Confirm
          </button>
          <button type="button" disabled={pending} onClick={() => review("dismissed")}>
            Dismiss
          </button>
        </div>
      )}
      {error && <p className="version-review-error">{error}</p>}
    </li>
  );
}

export default function VersionHistoryPanel({ temporal, canReview, onReviewConflict }) {
  if (!temporal || temporal.available === false) return null;

  return (
    <section className="version-history" aria-labelledby="version-history-title">
      <div className="version-history-heading">
        <div>
          <h3 id="version-history-title">Version history</h3>
          <p>Effective dates and claim-level changes from authorized versions.</p>
        </div>
        {temporal.loading && <span className="version-loading">Loading…</span>}
      </div>

      {temporal.error && <p className="version-review-error">{temporal.error}</p>}
      {temporal.versions?.length > 0 && (
        <ol className="version-timeline">
          {temporal.versions.map((version) => (
            <li key={version.id} className={version.is_current ? "current" : ""}>
              <span className="version-node" aria-hidden="true" />
              <div>
                <strong>Version {version.version_number}</strong>
                {version.is_current && <span className="current-version-badge">Current</span>}
                <span>{formatDate(version.effective_from)}</span>
                <small>Authority {version.authority_level}</small>
              </div>
            </li>
          ))}
        </ol>
      )}

      {temporal.diff && (
        <div className="version-diff">
          <div className="version-diff-heading">
            <h3>Latest change</h3>
            <span>
              v{temporal.versions.at(-2)?.version_number} → v{temporal.versions.at(-1)?.version_number}
            </span>
          </div>
          <div className="version-change-grid">
            <ClaimChanges title="Added" claims={temporal.diff.added} tone="added" />
            <ClaimChanges title="Removed" claims={temporal.diff.removed} tone="removed" />
          </div>
          {temporal.diff.conflicts?.length > 0 && (
            <section className="version-conflicts">
              <h4>Conflict review ({temporal.diff.conflicts.length})</h4>
              <ul>
                {temporal.diff.conflicts.map((conflict) => (
                  <ConflictRow
                    key={conflict.id}
                    conflict={conflict}
                    canReview={canReview}
                    onReview={onReviewConflict}
                  />
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </section>
  );
}