import { useState, useRef, useEffect, useCallback } from "react";
import {
  search,
  fetchDocument,
  fetchDocumentDiff,
  fetchDocumentVersions,
  reviewDocumentConflict,
} from "../api";
import AppShell from "./AppShell";
import Sidebar from "./Sidebar";
import CitationPanel from "./CitationPanel";
import ChatMessage from "./ChatMessage";
import DocumentViewerModal from "./DocumentViewerModal";
import ThemeToggle from "./ThemeToggle";

export default function SearchPage({ session, onLogout, theme, onThemeChange }) {
  const [query, setQuery] = useState("");
  const [turns, setTurns] = useState([]);
  const [isPending, setIsPending] = useState(false);
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [selectedMarker, setSelectedMarker] = useState(null);
  const [sourcesPanelOpen, setSourcesPanelOpen] = useState(false);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [panelMode, setPanelMode] = useState("empty"); // empty | single | all
  const [viewerState, setViewerState] = useState({
    open: false,
    loading: false,
    error: null,
    document: null,
  });
  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const scrollToBottom = () => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 80);
  };

  const normalizeHighlights = (highlights) => {
    if (highlights == null) return null;
    const list = Array.isArray(highlights) ? highlights : [highlights];
    return list.map((h) => (typeof h === "string" ? h.trim() : "")).filter(Boolean);
  };

  const openFullDocument = useCallback(
    async ({ doc_id, highlights = null, page_start = null }) => {
      setViewerState({ open: true, loading: true, error: null, document: null });
      try {
        const doc = await fetchDocument(
          session.token,
          doc_id,
          normalizeHighlights(highlights),
          page_start
        );
        setViewerState({
          open: true,
          loading: false,
          error: null,
          document: {
            ...doc,
            temporal: { available: true, loading: true, versions: [], diff: null },
          },
        });
        try {
          const versions = await fetchDocumentVersions(session.token, doc_id);
          let diff = null;
          if (versions.length >= 2) {
            diff = await fetchDocumentDiff(
              session.token,
              doc_id,
              versions.at(-2).id,
              versions.at(-1).id
            );
          }
          setViewerState((current) =>
            current.document?.id === doc_id
              ? {
                  ...current,
                  document: {
                    ...current.document,
                    temporal: { available: true, loading: false, versions, diff },
                  },
                }
              : current
          );
        } catch (temporalError) {
          setViewerState((current) =>
            current.document?.id === doc_id
              ? {
                  ...current,
                  document: {
                    ...current.document,
                    temporal: {
                      available: temporalError.status !== 404,
                      loading: false,
                      versions: [],
                      diff: null,
                      error: temporalError.status === 404 ? null : temporalError.message,
                    },
                  },
                }
              : current
          );
        }
      } catch (e) {
        setViewerState({
          open: true,
          loading: false,
          error: e.message,
          document: null,
        });
      }
    },
    [session.token]
  );

  const closeFullDocument = () => {
    setViewerState({ open: false, loading: false, error: null, document: null });
  };

  const reviewConflict = async (conflictId, status) => {
    const documentId = viewerState.document?.id;
    if (!documentId) return;
    const reviewed = await reviewDocumentConflict(
      session.token,
      documentId,
      conflictId,
      status
    );
    setViewerState((current) => ({
      ...current,
      document: {
        ...current.document,
        temporal: {
          ...current.document.temporal,
          diff: {
            ...current.document.temporal.diff,
            conflicts: current.document.temporal.diff.conflicts.map((conflict) =>
              conflict.id === reviewed.id ? reviewed : conflict
            ),
          },
        },
      },
    }));
  };

  const handleCitationClick = (citation) => {
    setSelectedCitation(citation);
    setSelectedMarker(citation.marker);
    setPanelMode("single");
    setSourcesPanelOpen(true);
  };

  const openAllSources = () => {
    const last = [...turns].reverse().find((t) => t.status === "complete" && t.citations?.length);
    if (!last?.citations?.length) {
      setPanelMode("empty");
      setSelectedCitation(null);
      setSelectedMarker(null);
      setSourcesPanelOpen(true);
      return;
    }
    setPanelMode("all");
    setSelectedCitation(null);
    setSelectedMarker(null);
    setSourcesPanelOpen(true);
  };

  const closeSourcesPanel = () => {
    setSourcesPanelOpen(false);
    setSelectedCitation(null);
    setSelectedMarker(null);
    setPanelMode("empty");
  };

  const handleCitationFromMarkdown = (citationOrMarker) => {
    if (typeof citationOrMarker === "object") {
      handleCitationClick(citationOrMarker);
      return;
    }
    const lastTurn = turns.at(-1);
    const c = lastTurn?.citations?.find((x) => x.marker === citationOrMarker);
    if (c) handleCitationClick(c);
  };

  const doSearch = async (q) => {
    const text = (q || query).trim();
    if (!text || isPending) return;

    const turnId = crypto.randomUUID();
    setQuery("");
    setIsPending(true);
    setSelectedCitation(null);
    setSelectedMarker(null);
    setPanelMode("empty");
    setSourcesPanelOpen(false);

    setTurns((prev) => [...prev, { id: turnId, query: text, status: "pending" }]);
    scrollToBottom();

    try {
      const data = await search(session.token, text, departmentFilter || null);
      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId ? { id: turnId, query: text, status: "complete", ...data } : t
        )
      );
    } catch (err) {
      const msg = err.message || "Search failed";
      let errorMessage = msg;
      if (msg.includes("401") || msg.toLowerCase().includes("token")) {
        errorMessage = "Session expired. Please sign out and log in again.";
      } else if (
        msg.toLowerCase().includes("failed to fetch") ||
        msg.toLowerCase().includes("network")
      ) {
        errorMessage =
          "Cannot reach the API. Check your connection, or try again in a moment.";
      }
      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId ? { id: turnId, query: text, status: "error", errorMessage } : t
        )
      );
    } finally {
      setIsPending(false);
      scrollToBottom();
    }
  };

  const clearConversation = () => {
    setTurns([]);
    closeSourcesPanel();
    setQuery("");
  };

  const showWelcome = turns.length === 0;

  const lastAnswerCitations =
    [...turns].reverse().find((t) => t.status === "complete" && t.citations?.length)?.citations ||
    [];
  const lastTurnId = turns.at(-1)?.id;
  let sourcesTitle = "Show sources panel";
  if (sourcesPanelOpen) {
    sourcesTitle = "Hide sources";
  } else if (lastAnswerCitations.length) {
    sourcesTitle = `Show all ${lastAnswerCitations.length} sources`;
  }

  const header = (
    <header className="topbar shell-header">
      <div className="brand">
        <span className="mark">T</span>
        <span className="brand-product">TechNova</span>
        <span className="brand-context">Knowledge Base</span>
      </div>
      <div className="topbar-right">
        <button
          type="button"
          className="header-btn mobile-nav-toggle"
          aria-expanded={navigationOpen}
          aria-controls="workspace-navigation"
          onClick={() => setNavigationOpen((open) => !open)}
        >
          Menu
        </button>
        <button
          type="button"
          className={`header-btn sources-toggle ${sourcesPanelOpen ? "active" : ""}`}
          onClick={() => {
            if (sourcesPanelOpen && panelMode === "all") closeSourcesPanel();
            else openAllSources();
          }}
          title={sourcesTitle}
        >
          Sources
        </button>
        <ThemeToggle theme={theme} onThemeChange={onThemeChange} />
        <button type="button" className="logout-btn" onClick={onLogout}>
          Sign out
        </button>
      </div>
    </header>
  );

  const main = (
    <>
      <div className="main-content shell-chat">
        {showWelcome ? (
          <div className="welcome">
            <h2>What do you want to know?</h2>
            <p>
              Ask about HR policies, engineering runbooks, or sales materials.
              Your access: <strong>{session.roles.join(", ")}</strong>
            </p>
            {departmentFilter && (
              <p className="filter-hint">
                Filtering to: <strong>{departmentFilter}</strong> only
              </p>
            )}
            <div className="welcome-examples">
              {[
                "What is the PTO policy?",
                "What is the tech stack?",
                "What are our pricing tiers?",
              ].map((ex) => (
                <button
                  key={ex}
                  type="button"
                  className="example-btn"
                  onClick={() => doSearch(ex)}
                  disabled={isPending}
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="results-area">
            {turns.map((turn) => (
              <ChatMessage
                key={turn.id}
                turn={turn}
                onCitationClick={handleCitationFromMarkdown}
                selectedMarker={
                  turn.id === lastTurnId ? selectedMarker : null
                }
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="search-bar-wrap shell-search">
        <form className="search-bar" onSubmit={(e) => { e.preventDefault(); doSearch(); }}>
          <input
            ref={inputRef}
            type="text"
            placeholder="Ask a question…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isPending}
          />
          <button type="submit" className="send-btn" disabled={isPending || !query.trim()}>
            ↑
          </button>
        </form>
      </div>

      {viewerState.open && (
        <DocumentViewerModal
          document={viewerState.document}
          loading={viewerState.loading}
          error={viewerState.error}
          authToken={session.token}
          canReviewConflicts={session.roles.includes("Admin")}
          onReviewConflict={reviewConflict}
          onClose={closeFullDocument}
        />
      )}
    </>
  );

  return (
    <AppShell
      header={header}
      sidebar={
        <div id="workspace-navigation" className="navigation-drawer">
          <Sidebar
            session={session}
            token={session.token}
            departmentFilter={departmentFilter}
            onDepartmentChange={(department) => {
              setDepartmentFilter(department);
              setNavigationOpen(false);
            }}
            onExampleClick={(example) => {
              setNavigationOpen(false);
              doSearch(example);
            }}
            onClearConversation={() => {
              clearConversation();
              setNavigationOpen(false);
            }}
            onOpenDocument={(doc) => {
              setNavigationOpen(false);
              openFullDocument({ doc_id: doc.id });
            }}
            onDocumentUploaded={() => {}}
            hasConversation={turns.length > 0}
            isPending={isPending}
          />
        </div>
      }
      main={main}
      panelOpen={sourcesPanelOpen}
      navigationOpen={navigationOpen}
      onCloseNavigation={() => setNavigationOpen(false)}
      panel={
        <CitationPanel
          mode={panelMode}
          citation={selectedCitation}
          citations={lastAnswerCitations}
          onClose={closeSourcesPanel}
          onViewFullDocument={openFullDocument}
          onSelectCitation={handleCitationClick}
          authToken={session.token}
        />
      }
    />
  );
}
