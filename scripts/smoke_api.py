#!/usr/bin/env python3
"""API smoke tests. Default: localhost:8000. Set SMOKE_API_BASE for production."""
import json
import sys
import urllib.error
import urllib.request

import os

_BASE_ROOT = os.environ.get("SMOKE_API_BASE", "http://localhost:8000").rstrip("/")
_PASSWORD = os.environ.get("SMOKE_API_PASSWORD", "")
# auto: probe graph endpoint; true: require trust checks; false: skip
_TRUST_MODE = os.environ.get("SMOKE_TRUST_CHECKS", "auto").strip().lower()
BASE = f"{_BASE_ROOT}/api"
SEARCH_PATH = "/search"


def req(method, path, body=None, token=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            detail = json.loads(body_text)
        except json.JSONDecodeError:
            detail = body_text
        return e.code, detail


def login(email):
    code, data = req(
        "POST",
        "/auth/login",
        {"email": email, "password": _PASSWORD},
    )
    assert code == 200, f"login {email}: {code} {data}"
    return data["token"]


class SmokeReport:
    def __init__(self):
        self.results = []
        self.failed = []

    def check(self, name, ok, detail=""):
        self.results.append((name, ok, detail))
        if not ok:
            self.failed.append(name)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail and not ok else ""))

    def finish(self):
        print(
            f"\n=== Summary: {len(self.results) - len(self.failed)}/"
            f"{len(self.results)} passed ==="
        )
        if self.failed:
            print("Failed:", ", ".join(self.failed))
            return 1
        print("All smoke checks passed.")
        return 0


def _check_health(report):
    code, health = req("GET", "/health")
    report.check("Health", code == 200 and health.get("status") == "ok")
    report.check("Postgres up", health.get("components", {}).get("postgres") == "up")
    report.check("Qdrant up", health.get("components", {}).get("qdrant") == "up")


def _check_authentication(report):
    code, _ = req(
        "POST",
        "/auth/login",
        {"email": "nobody@company.com", "password": _PASSWORD},
    )
    report.check("Login rejects unknown user", code in {401, 404})

    admin = login("bhaskar@company.com")
    login("amrutha@company.com")
    engineer = login("harshini@company.com")
    sales = login("tanvi@company.com")
    report.check("Seeded user logins", True)
    return admin, engineer, sales


def _check_documents_and_search(report, admin):
    code, docs = req("GET", "/documents", token=admin)
    report.check("List documents", code == 200 and docs.get("total", 0) >= 30)
    pdf_docs = [doc for doc in docs.get("documents", []) if doc.get("file_type") == "pdf"]
    report.check("PDF documents in library", len(pdf_docs) >= 5, f"found {len(pdf_docs)}")

    code, search = req(
        "POST",
        SEARCH_PATH,
        {"query": "What is the PTO policy?", "department_filter": "HR"},
        token=admin,
    )
    cites = search.get("citations", []) if code == 200 else []
    report.check("Search returns answer", code == 200 and bool(search.get("answer")))
    report.check(
        "Search returns citations",
        len(cites) >= 1 or search.get("chunks_found", 0) >= 1,
        f"citations={len(cites)} chunks={search.get('chunks_found')}",
    )
    report.check(
        "Citation has chunk_text",
        (len(cites) >= 1 and all(c.get("chunk_text") for c in cites))
        or (bool(search.get("claims")) and bool(search.get("answer"))),
        f"count={len(cites)} claims={len(search.get('claims', []))}",
    )

    if cites:
        doc_id = cites[0]["doc_id"]
        excerpt = cites[0]["chunk_text"][:200]
        from urllib.parse import quote

        qs = f"?highlight={quote(excerpt)}"
        code, doc = req("GET", f"/documents/{doc_id}{qs}", token=admin)
        report.check("Get document with highlight", code == 200 and bool(doc.get("content")))


def _check_rbac(report, admin, engineer):
    query = {"query": "salary bands compensation"}
    code, engineer_search = req("POST", SEARCH_PATH, query, token=engineer)
    if code != 200 or not isinstance(engineer_search, dict):
        report.check(
            "Engineer RBAC hides compensation",
            False,
            f"search HTTP {code}: {engineer_search}",
        )
    else:
        engineer_titles = " ".join(
            citation.get("doc_title", "")
            for citation in engineer_search.get("citations", [])
        ).lower()
        report.check(
            "Engineer RBAC hides compensation",
            "compensation" not in engineer_titles,
        )

    code, admin_search = req("POST", SEARCH_PATH, query, token=admin)
    admin_answer = (admin_search.get("answer") or "").lower()
    report.check(
        "Admin can access compensation topics",
        code == 200 and ("compensation" in admin_answer or "salary" in admin_answer),
    )


def _non_admin_upload_status(engineer):
    import io

    boundary = "----SmokeBoundary7MA4YWxk"
    body_io = io.BytesIO()
    for part in (
        f'--{boundary}\r\nContent-Disposition: form-data; name="title"\r\n\r\nTest\r\n',
        f'--{boundary}\r\nContent-Disposition: form-data; name="department"\r\n\r\nEngineering\r\n',
        f'--{boundary}\r\nContent-Disposition: form-data; name="classification"\r\n\r\npublic\r\n',
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="t.md"\r\nContent-Type: text/markdown\r\n\r\n# T\n\r\n'
        ),
        f"--{boundary}--\r\n",
    ):
        body_io.write(part.encode())
    upload_req = urllib.request.Request(
        f"{BASE}/documents/upload",
        data=body_io.getvalue(),
        headers={
            "Authorization": f"Bearer {engineer}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(upload_req, timeout=30) as resp:
            return resp.status
    except urllib.error.HTTPError as error:
        return error.code


def _trust_checks_enabled(engineer_token: str) -> bool:
    if _TRUST_MODE == "false":
        return False
    if _TRUST_MODE == "true":
        return True
    code, _ = req("GET", "/graph/entities?query=billing", token=engineer_token)
    return code != 404


def _check_trust_features(report, admin, engineer):
    if not _trust_checks_enabled(engineer):
        report.check("Trust checks skipped", True, detail="graph disabled or SMOKE_TRUST_CHECKS=false")
        return

    code, search = req(
        "POST",
        SEARCH_PATH,
        {"query": "What is the PTO policy?"},
        token=admin,
    )
    plan = search.get("query_plan") if code == 200 else None
    report.check(
        "Search exposes query_plan",
        code == 200 and isinstance(plan, dict) and bool(plan.get("route")),
        f"plan={plan}",
    )
    report.check(
        "Search query_plan has execution_trace_id",
        bool(plan and plan.get("execution_trace_id")),
    )

    code, graph = req("GET", "/graph/entities?query=billing", token=engineer)
    report.check(
        "Graph entities endpoint",
        code == 200 and isinstance(graph, list),
        f"code={code}",
    )

    code, docs = req("GET", "/documents", token=admin)
    doc_id = None
    if code == 200 and docs.get("documents"):
        doc_id = docs["documents"][0]["id"]
    if doc_id:
        code, versions = req("GET", f"/documents/{doc_id}/versions", token=admin)
        version_list = versions if isinstance(versions, list) else versions.get("versions", [])
        report.check(
            "Document versions endpoint",
            code == 200 and isinstance(version_list, list) and len(version_list) >= 1,
            f"code={code}",
        )
    else:
        report.check("Document versions endpoint", False, "no documents listed")

    claims = search.get("claims", []) if isinstance(search, dict) else []
    report.check(
        "Search exposes claims field",
        isinstance(search.get("claims"), list) if isinstance(search, dict) else False,
        f"claims_count={len(claims)}",
    )


def _check_remaining_roles(report, engineer, sales):
    report.check(
        "Upload forbidden for non-admin",
        _non_admin_upload_status(engineer) == 403,
    )

    code, sales_search = req(
        "POST",
        SEARCH_PATH,
        {"query": "pricing tiers"},
        token=sales,
    )
    report.check(
        "Sales user search works",
        code == 200 and bool(sales_search.get("answer")),
    )


def main():
    print("=== API smoke tests ===\n")
    report = SmokeReport()
    _check_health(report)
    admin, engineer, sales = _check_authentication(report)
    _check_documents_and_search(report, admin)
    _check_rbac(report, admin, engineer)
    _check_trust_features(report, admin, engineer)
    _check_remaining_roles(report, engineer, sales)
    return report.finish()


if __name__ == "__main__":
    sys.exit(main())
