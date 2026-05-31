import { useState } from "react";
import DepartmentFilter from "./DepartmentFilter";
import DocumentLibrary from "./DocumentLibrary";
import DocumentUpload from "./DocumentUpload";

const EXAMPLES = [
  "What is the PTO policy?",
  "What caused incident 5023?",
  "What is the tech stack?",
  "What are our pricing tiers?",
];

export default function Sidebar({
  session,
  token,
  departmentFilter,
  onDepartmentChange,
  onExampleClick,
  onClearConversation,
  onOpenDocument,
  onDocumentUploaded,
  hasConversation,
  isPending,
}) {
  const isAdmin = session.roles?.includes("Admin");
  const [libraryKey, setLibraryKey] = useState(0);

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <span className="mark">T</span>
          <div>
            <span className="brand-title">TechNova</span>
            <span className="brand-sub">Knowledge Base</span>
          </div>
        </div>

        <div className="sidebar-user">
          <div className="sidebar-user-name">{session.user_id}</div>
          <div className="sidebar-user-dept">{session.department}</div>
          <div className="role-tags">
            {session.roles.map((r) => (
              <span key={r} className={`role-tag ${r.toLowerCase()}`}>
                {r}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="sidebar-scroll">
        {isAdmin && (
          <DocumentUpload
            token={token}
            onUploaded={() => {
              setLibraryKey((k) => k + 1);
              onDocumentUploaded?.();
            }}
          />
        )}

        <DocumentLibrary
          key={libraryKey}
          token={token}
          departmentFilter={departmentFilter}
          onOpenDocument={onOpenDocument}
        />

        <DepartmentFilter value={departmentFilter} onChange={onDepartmentChange} />

        {hasConversation && (
          <button
            type="button"
            className="clear-chat-btn"
            onClick={onClearConversation}
            disabled={isPending}
          >
            New conversation
          </button>
        )}

        <div className="sidebar-section">
          <span className="section-label">Try asking</span>
          <div className="example-list">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                className="example-btn sidebar-example"
                onClick={() => onExampleClick(ex)}
                disabled={isPending}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
