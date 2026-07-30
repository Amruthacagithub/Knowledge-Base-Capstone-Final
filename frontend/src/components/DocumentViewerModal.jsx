import { useEffect, useRef } from "react";
import MarkdownContent from "./MarkdownContent";
import { splitByExcerpts } from "../utils/highlightContent";
import { openDocumentPdf } from "../api";
import VersionHistoryPanel from "./VersionHistoryPanel";

function PageBadge({ page }) {
  if (!page) return null;
  return <span className="page-badge">Page {page}</span>;
}

function keyedSegments(segments, prefix) {
  const occurrences = new Map();
  return segments.map((segment) => {
    let hash = 0;
    for (const character of segment.text) {
      hash = (hash * 31 + character.codePointAt(0)) >>> 0;
    }
    const base = `${segment.type}-${hash.toString(36)}-${segment.text.length}`;
    const occurrence = occurrences.get(base) || 0;
    occurrences.set(base, occurrence + 1);
    return { ...segment, key: `${prefix}-${base}-${occurrence}` };
  });
}

export default function DocumentViewerModal({
  document,
  loading,
  error,
  authToken,
  canReviewConflicts,
  onReviewConflict,
  onClose,
}) {
  const firstHighlightRef = useRef(null);
  const pageHighlightRef = useRef(null);
  const modalRef = useRef(null);
  const closeButtonRef = useRef(null);

  let excerpts = [];
  if (document?.highlight_excerpts?.length > 0) {
    excerpts = document.highlight_excerpts;
  } else if (document?.highlight_excerpt) {
    excerpts = [document.highlight_excerpt];
  }

  const isPdf = document?.file_type === "pdf";
  const targetPage = document?.highlight_page || null;

  useEffect(() => {
    const el = pageHighlightRef.current || firstHighlightRef.current;
    if (document && el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [document]);

  useEffect(() => {
    const previouslyFocused = window.document.activeElement;
    const modal = modalRef.current;
    closeButtonRef.current?.focus();
    window.document.body.classList.add("modal-open");

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !modal) return;
      const focusable = [...modal.querySelectorAll(
        'button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && window.document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && window.document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.document.addEventListener("keydown", handleKeyDown);
    return () => {
      window.document.removeEventListener("keydown", handleKeyDown);
      window.document.body.classList.remove("modal-open");
      previouslyFocused?.focus?.();
    };
  }, [onClose]);

  if (!document && !loading && !error) return null;

  const handleOpenPdf = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (document && authToken) {
      openDocumentPdf(authToken, document.id, targetPage || 1);
    }
  };

  return (
    <div className="doc-modal-overlay">
      <dialog
        open
        ref={modalRef}
        className="doc-modal"
        aria-labelledby="doc-modal-title"
      >
        <header className="doc-modal-header">
          <div className="doc-modal-header-main">
            <h2 id="doc-modal-title">{document?.title || "Document"}</h2>
            {document && (
              <div className="doc-modal-meta">
                <span className={`panel-dept dept-${document.department?.toLowerCase()}`}>
                  {document.department}
                </span>
                <span className="doc-classification">{document.classification}</span>
                {isPdf && <span className="file-type-badge">PDF</span>}
                {targetPage && <PageBadge page={targetPage} />}
                {excerpts.length > 1 && (
                  <span className="doc-highlight-count">
                    {excerpts.length} referenced sections
                  </span>
                )}
              </div>
            )}
            {isPdf && authToken && (
              <button type="button" className="open-pdf-link" onClick={handleOpenPdf}>
                <span>Open PDF</span>
                <span className="view-source-arrow" aria-hidden="true">
                  ↗
                </span>
              </button>
            )}
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="panel-close"
            onClick={onClose}
            aria-label="Close document"
          >
            ×
          </button>
        </header>

        <div className="doc-modal-body">
          {loading && <p className="doc-modal-loading">Loading document…</p>}
          {error && <p className="error-msg">{error}</p>}
          {document && (
            <VersionHistoryPanel
              temporal={document.temporal}
              canReview={canReviewConflicts}
              onReviewConflict={onReviewConflict}
            />
          )}
          {document && isPdf && document.pages?.length > 0 && (
            <article className="doc-modal-content doc-modal-pdf">
              {document.pages.map((pg) => {
                const pageSegments = keyedSegments(
                  splitByExcerpts(pg.text, excerpts),
                  `page-${pg.page}`
                );
                const isTargetPage = targetPage === pg.page;
                return (
                  <section
                    key={pg.page}
                    id={`pdf-page-${pg.page}`}
                    ref={isTargetPage ? pageHighlightRef : undefined}
                    className="pdf-page-section"
                  >
                    <h3 className="pdf-page-heading">Page {pg.page}</h3>
                    {pageSegments.map((seg) => {
                      if (seg.type === "highlight") {
                        return (
                          <div key={seg.key} className="doc-highlight-block">
                            <span className="doc-highlight-label">Referenced section</span>
                            <MarkdownContent
                              content={seg.text}
                              variant="source"
                              className="markdown-body markdown-doc"
                            />
                          </div>
                        );
                      }
                      if (!seg.text?.trim()) return null;
                      return (
                        <MarkdownContent
                          key={seg.key}
                          content={seg.text}
                          variant="source"
                          className="markdown-body markdown-doc"
                        />
                      );
                    })}
                  </section>
                );
              })}
            </article>
          )}
          {document && !isPdf && (
            <article className="doc-modal-content">
              {keyedSegments(
                splitByExcerpts(document.content, excerpts),
                "document"
              ).map((seg, index, segments) => {
                if (seg.type === "highlight") {
                  const isFirst = !segments
                    .slice(0, index)
                    .some((s) => s.type === "highlight");
                  return (
                    <section
                      key={seg.key}
                      ref={isFirst ? firstHighlightRef : undefined}
                      className="doc-highlight-block"
                    >
                      <span className="doc-highlight-label">Referenced section</span>
                      <MarkdownContent
                        content={seg.text}
                        variant="source"
                        className="markdown-body markdown-doc"
                      />
                    </section>
                  );
                }
                if (!seg.text?.trim()) return null;
                return (
                  <MarkdownContent
                    key={seg.key}
                    content={seg.text}
                    variant="source"
                    className="markdown-body markdown-doc"
                  />
                );
              })}
            </article>
          )}
        </div>
      </dialog>
    </div>
  );
}
