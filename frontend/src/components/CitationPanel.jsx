import HighlightedExcerpt from "./HighlightedExcerpt";
import { previewExcerpt } from "../utils/citationExcerpt";

function ViewSourceLink({ onClick, label = "View full document" }) {
  return (
    <button type="button" className="view-source-link" onClick={onClick}>
      {label}
      <span className="view-source-arrow" aria-hidden="true">
        ↗
      </span>
    </button>
  );
}

function PageBadge({ citation }) {
  if (citation?.file_type !== "pdf" || !citation?.page_start) return null;
  return <span className="page-badge">Page {citation.page_start}</span>;
}

function SourcePreview({ citation, className = "", compact = false }) {
  const displayText = compact ? previewExcerpt(citation.chunk_text) : citation.chunk_text;

  return (
    <div className={`panel-chunk cited-excerpt ${className}`.trim()}>
      <span className="cited-excerpt-label">Cited passage</span>
      <HighlightedExcerpt
        content={displayText}
        highlightSource={citation.chunk_text}
      />
    </div>
  );
}

function SourceCard({ citation, highlightsForDoc, onViewFullDocument, onSelect }) {
  return (
    <article className="source-card">
      <div className="source-card-head">
        {onSelect ? (
          <button
            type="button"
            className="source-card-select"
            onClick={() => onSelect(citation)}
          >
            <span className="source-marker">[{citation.marker}]</span>
            <span className="source-card-title">{citation.doc_title}</span>
            <span className="source-preview-label">Preview source</span>
          </button>
        ) : (
          <>
            <span className="source-marker">[{citation.marker}]</span>
            <span className="source-card-title">{citation.doc_title}</span>
          </>
        )}
        <ViewSourceLink
          label="View more"
          onClick={(e) => {
            e.stopPropagation();
            onViewFullDocument({
              doc_id: citation.doc_id,
              doc_title: citation.doc_title,
              highlights: highlightsForDoc,
              page_start: citation.page_start,
            });
          }}
        />
      </div>
      <span className={`panel-dept dept-${(citation.department || "").toLowerCase()}`}>
        {citation.department}
      </span>
      <PageBadge citation={citation} />
      <SourcePreview citation={citation} className="source-card-preview" compact />
    </article>
  );
}

export default function CitationPanel({
  mode,
  citation,
  citations = [],
  onClose,
  onViewFullDocument,
  onSelectCitation,
}) {
  if (mode === "all" && citations.length > 0) {
    const byDoc = citations.reduce((acc, c) => {
      if (!acc[c.doc_id]) acc[c.doc_id] = [];
      acc[c.doc_id].push(c);
      return acc;
    }, {});

    return (
      <aside className="citation-panel citation-panel-all">
        <div className="panel-header">
          <h3>All sources ({citations.length})</h3>
          <button type="button" className="panel-close" onClick={onClose} aria-label="Close panel">
            ×
          </button>
        </div>
        <p className="panel-all-hint">
          Passages cited in the latest answer. Use <strong>View more</strong> to open the full
          document with every referenced section highlighted.
        </p>
        <div className="sources-all-list">
          {citations.map((c) => (
            <SourceCard
              key={c.marker}
              citation={c}
              highlightsForDoc={(byDoc[c.doc_id] || [])
                .map((x) => x.chunk_text)
                .filter(Boolean)}
              onViewFullDocument={onViewFullDocument}
              onSelect={onSelectCitation}
            />
          ))}
        </div>
      </aside>
    );
  }

  if (mode === "single" && citation) {
    return (
      <aside className="citation-panel">
        <div className="panel-header panel-header-with-action">
          <div className="panel-header-left">
            <h3>Source [{citation.marker}]</h3>
            <ViewSourceLink
              onClick={() =>
                onViewFullDocument({
                  doc_id: citation.doc_id,
                  doc_title: citation.doc_title,
                  highlights: [citation.chunk_text],
                  page_start: citation.page_start,
                })
              }
            />
          </div>
          <button type="button" className="panel-close" onClick={onClose} aria-label="Close panel">
            ×
          </button>
        </div>
        <div className="panel-doc-meta">
          <span className="panel-doc-title">{citation.doc_title}</span>
          <PageBadge citation={citation} />
          <span className={`panel-dept dept-${(citation.department || "").toLowerCase()}`}>
            {citation.department}
          </span>
        </div>
        <SourcePreview citation={citation} className="source-panel-preview" />
      </aside>
    );
  }

  return (
    <aside className="citation-panel citation-panel-empty">
      <div className="panel-header">
        <h3>Sources</h3>
        <button type="button" className="panel-close" onClick={onClose} aria-label="Close panel">
          ×
        </button>
      </div>
      <p className="panel-empty-hint">
        Click a citation <span className="cite-pill">[1]</span> in an answer to preview that passage,
        or use <strong>Sources</strong> after an answer to see every reference at once.
      </p>
    </aside>
  );
}
