#!/usr/bin/env python3
"""RBAC matrix checks against running API (set SMOKE_API_BASE for prod)."""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SMOKE_API_BASE", "http://localhost:8000").rstrip("/") + "/api"


def login(email: str) -> str:
    req = urllib.request.Request(
        f"{BASE}/auth/login",
        json.dumps({"email": email}).encode(),
        {"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["token"]


def search(token: str, query: str) -> dict:
    req = urllib.request.Request(
        f"{BASE}/search",
        json.dumps({"query": query}).encode(),
        {"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def main():
    cases = [
        ("amrutha@company.com", "salary bands", True, "Compensation"),
        ("harshini@company.com", "salary bands", False, "Compensation"),
        ("arijith@company.com", "salary bands", False, "Compensation"),
        ("bhaskar@company.com", "salary bands", True, "Compensation"),
        ("tanvi@company.com", "sales commission structure", True, "Commission"),
        ("harshini@company.com", "sales commission structure", False, "Quota and Commission"),
        ("arijith@company.com", "What is the PTO policy?", True, "Handbook"),
    ]
    failed = 0
    print(f"RBAC matrix @ {BASE}\n")
    for email, query, should_see, needle in cases:
        try:
            tok = login(email)
            data = search(tok, query)
            titles = " ".join(c.get("doc_title", "") for c in data.get("citations", []))
            blob = (titles + " " + (data.get("answer") or "")).lower()
            has = needle.lower() in blob
            ok = has if should_see else not has
            status = "PASS" if ok else "FAIL"
            if not ok:
                failed += 1
            print(f"  [{status}] {email} | {query[:40]} | needle={needle}")
        except Exception as exc:
            failed += 1
            print(f"  [FAIL] {email} | {query[:40]} | error: {exc}")
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
