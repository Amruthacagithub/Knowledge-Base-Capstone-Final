#!/usr/bin/env python3
"""One-off search smoke: login + POST /search."""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SMOKE_API_BASE", "http://localhost:8000").rstrip("/") + "/api"
QUERY = sys.argv[1] if len(sys.argv) > 1 else "What is the tech stack?"


def req(method, path, body=None, token=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return resp.status, json.loads(resp.read().decode())


def main():
    _, login = req("POST", "/auth/login", {"email": "bhaskar@company.com"})
    token = login["token"]
    code, search = req(
        "POST",
        "/search",
        {"query": QUERY, "department_filter": "Engineering"},
        token=token,
    )
    answer = (search.get("answer") or "")[:500]
    err = search.get("error") or search.get("detail")
    cites = len(search.get("citations") or [])
    llm_err = search.get("llm_error")
    print(f"HTTP {code}")
    print(f"query: {QUERY!r}")
    print(f"citations: {cites} chunks_found: {search.get('chunks_found')}")
    if llm_err:
        print(f"llm_error: {llm_err}")
    if err:
        print(f"error: {err}")
    print(f"answer ({len(search.get('answer') or '')} chars):\n{answer}")
    ok = code == 200 and bool(search.get("answer")) and not llm_err
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as e:
        print(e.read().decode())
        sys.exit(1)
