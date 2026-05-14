/**
 * API client for Knowledge Base backend.
 * Local: omit VITE_API_URL (defaults to http://localhost:8000).
 * Production (Vercel): set VITE_API_URL to your Cloud Run URL (no trailing slash).
 */
const API_ROOT = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const BASE = `${API_ROOT}/api`;

function authHeaders(token) {
    return {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
    };
}

export async function login(email, password = "") {
    const res = await fetch(`${BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = err.detail;
        let message = "Login failed";
        if (typeof detail === "string") {
            message = detail;
        } else if (Array.isArray(detail)) {
            message = detail.map((item) => item.msg || item).join("; ");
        }
        throw new Error(message || "Login failed");
    }
    return res.json();
}

export async function logout(token) {
    const res = await fetch(`${BASE}/auth/logout`, {
        method: "POST",
        headers: authHeaders(token),
    });
    if (!res.ok && res.status !== 401) {
        throw new Error("Sign out failed");
    }
}

export async function search(token, query, departmentFilter = null) {
    const body = { query };
    if (departmentFilter) body.department_filter = departmentFilter;

    const res = await fetch(`${BASE}/search`, {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Search failed");
    }
    return res.json();
}

export async function fetchDocuments(token) {
    const res = await fetch(`${BASE}/documents`, {
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to load documents");
    }
    return res.json();
}

export async function fetchDocument(token, docId, highlights = null, page = null) {
    const params = new URLSearchParams();
    let list = [];
    if (Array.isArray(highlights)) {
        list = highlights;
    } else if (highlights != null) {
        list = [highlights];
    }
    for (const h of list) {
        const excerpt = String(h).trim().slice(0, 1500);
        if (excerpt) params.append("highlight", excerpt);
    }
    if (page != null) params.set("page", String(page));
    const qs = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(`${BASE}/documents/${encodeURIComponent(docId)}${qs}`, {
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to load document");
    }
    return res.json();
}

export async function fetchDocumentVersions(token, docId) {
    const res = await fetch(`${BASE}/documents/${encodeURIComponent(docId)}/versions`, {
        headers: authHeaders(token),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const error = new Error(err.detail || "Failed to load version history");
        error.status = res.status;
        throw error;
    }
    return res.json();
}

export async function fetchDocumentDiff(token, docId, fromVersionId, toVersionId) {
    const params = new URLSearchParams({
        from_version_id: fromVersionId,
        to_version_id: toVersionId,
    });
    const res = await fetch(
        `${BASE}/documents/${encodeURIComponent(docId)}/diff?${params.toString()}`,
        { headers: authHeaders(token) }
    );
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to compare document versions");
    }
    return res.json();
}

export async function reviewDocumentConflict(token, docId, conflictId, status) {
    const res = await fetch(
        `${BASE}/documents/${encodeURIComponent(docId)}/conflicts/${encodeURIComponent(conflictId)}`,
        {
            method: "PATCH",
            headers: authHeaders(token),
            body: JSON.stringify({ status }),
        }
    );
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to review conflict");
    }
    return res.json();
}

export function documentFileUrl(docId) {
    return `${BASE}/documents/${encodeURIComponent(docId)}/file`;
}

export async function openDocumentPdf(token, docId, page = 1) {
    const res = await fetch(documentFileUrl(docId), {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Failed to open PDF");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    window.open(`${url}#page=${page}`, "_blank", "noopener,noreferrer");
}

export async function uploadDocument(token, formData) {
    const res = await fetch(`${BASE}/documents/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Upload failed");
    }
    return res.json();
}
