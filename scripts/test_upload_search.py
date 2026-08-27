#!/usr/bin/env python3
"""Upload a test doc and verify search finds it."""
import json
import os
import sys
import time
import urllib.request

BASE = os.environ.get("SMOKE_API_BASE", "http://localhost:8000").rstrip("/") + "/api"
UNIQUE = "zebra-quantum-20260519"


def login(email: str) -> str:
    req = urllib.request.Request(
        f"{BASE}/auth/login",
        json.dumps({"email": email}).encode(),
        {"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["token"]


def main():
    tok = login("bhaskar@company.com")
    boundary = "----TestBoundary"
    body = b"".join(
        p.encode()
        for p in (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"title\"\r\n\r\nQA Upload Test\r\n",
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"department\"\r\n\r\nEngineering\r\n",
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"classification\"\r\n\r\npublic\r\n",
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                f'filename="qa-test.md"\r\nContent-Type: text/markdown\r\n\r\n'
                f"# QA Test\n\nUnique phrase: {UNIQUE}\n"
            ),
            f"--{boundary}--\r\n",
        )
    )
    req = urllib.request.Request(
        f"{BASE}/documents/upload",
        body,
        {
            "Authorization": f"Bearer {tok}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        print("upload:", resp.status, resp.read().decode()[:120])

    time.sleep(2)
    tok = login("bhaskar@company.com")
    req = urllib.request.Request(
        f"{BASE}/search",
        json.dumps({"query": UNIQUE}).encode(),
        {"Content-Type": "application/json", "Authorization": f"Bearer {tok}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    blob = (data.get("answer") or "") + " ".join(
        c.get("chunk_text", "") for c in data.get("citations", [])
    )
    ok = UNIQUE in blob
    print("search found unique phrase:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
