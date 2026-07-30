import { useEffect, useState } from "react";
import { fetchDocuments } from "../api";

export default function DocumentLibrary({ token, departmentFilter, onOpenDocument }) {
  const [result, setResult] = useState({ token: null, docs: [], error: null });
  const [expanded, setExpanded] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchDocuments(token)
      .then((data) => {
        if (!cancelled) {
          setResult({ token, docs: data.documents || [], error: null });
        }
      })
      .catch((e) => {
        if (!cancelled) setResult({ token, docs: [], error: e.message });
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const loading = result.token !== token;
  const docs = loading ? [] : result.docs;
  const error = loading ? null : result.error;

  const filtered = docs.filter((d) => {
    if (departmentFilter && d.department !== departmentFilter) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      d.title.toLowerCase().includes(q) ||
      d.department.toLowerCase().includes(q)
    );
  });

  const byDept = filtered.reduce((acc, d) => {
    if (!acc[d.department]) acc[d.department] = [];
    acc[d.department].push(d);
    return acc;
  }, {});

  return (
    <section className="doc-library">
      <button
        type="button"
        className="doc-library-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        <span>
          Your documents
          {!loading && <span className="doc-count"> ({docs.length})</span>}
        </span>
        <span className="chevron-icon">{expanded ? "▾" : "▸"}</span>
      </button>

      {expanded && (
        <div className="doc-library-body">
          <input
            type="search"
            className="doc-library-search"
            placeholder="Filter documents…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {loading && <p className="doc-library-hint">Loading…</p>}
          {error && <p className="doc-library-error">{error}</p>}
          {!loading && !error && filtered.length === 0 && (
            <p className="doc-library-hint">No documents match.</p>
          )}
          {Object.entries(byDept).map(([dept, items]) => (
            <div key={dept} className="doc-dept-group">
              <span className="doc-dept-label">{dept}</span>
              <ul className="doc-list">
                {items.map((d) => (
                  <li key={d.id}>
                    <button
                      type="button"
                      className="doc-list-item"
                      onClick={() => onOpenDocument(d)}
                      title={d.title}
                    >
                      <span className="doc-list-title">{d.title}</span>
                      {d.file_type === "pdf" && (
                        <span className="doc-pdf-badge">PDF</span>
                      )}
                      {d.classification === "restricted" && (
                        <span className="doc-restricted-badge">restricted</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
