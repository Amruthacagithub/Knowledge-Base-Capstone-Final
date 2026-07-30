import { useState } from "react";
import { uploadDocument } from "../api";

export default function DocumentUpload({ token, onUploaded }) {
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("HR");
  const [classification, setClassification] = useState("public");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !title.trim()) return;
    setLoading(true);
    setError(null);
    setMessage(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", title.trim());
    fd.append("department", department);
    fd.append("classification", classification);
    try {
      const result = await uploadDocument(token, fd);
      setMessage(`Uploaded "${result.title}" (${result.chunks_indexed} chunks)`);
      setTitle("");
      setFile(null);
      onUploaded?.(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className={`doc-upload ${expanded ? "is-expanded" : ""}`}>
      <button
        type="button"
        className="doc-upload-toggle"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <span>Upload document</span>
        <span className="chevron-icon">{expanded ? "▾" : "▸"}</span>
      </button>

      {expanded && (
        <div className="doc-upload-panel">
          <form className="doc-upload-form" onSubmit={handleSubmit}>
            <label className="doc-upload-field">
              <span>Title</span>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Document title"
                required
              />
            </label>

            <div className="doc-upload-row">
              <label className="doc-upload-field">
                <span>Department</span>
                <select value={department} onChange={(e) => setDepartment(e.target.value)}>
                  <option value="HR">HR</option>
                  <option value="Engineering">Engineering</option>
                  <option value="Sales">Sales</option>
                </select>
              </label>
              <label className="doc-upload-field">
                <span>Access</span>
                <select
                  value={classification}
                  onChange={(e) => setClassification(e.target.value)}
                >
                  <option value="public">Public</option>
                  <option value="restricted">Restricted</option>
                </select>
              </label>
            </div>

            <label className="doc-upload-field doc-upload-file">
              <span>File (.pdf, .md, .txt — max 10 MB)</span>
              <input
                type="file"
                accept=".pdf,.md,.txt"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                required
              />
            </label>

            <button type="submit" className="doc-upload-btn" disabled={loading}>
              {loading ? "Uploading…" : "Upload & index"}
            </button>

            {message && <p className="doc-upload-success">{message}</p>}
            {error && <p className="doc-upload-error">{error}</p>}
          </form>
        </div>
      )}
    </section>
  );
}
