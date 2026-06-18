#!/usr/bin/env python3
"""List Gemini models for your API keys and test generateContent on each."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai

from backend.config import get_gemini_api_keys

# Gemini 3 family (Google AI Studio / API — verify against live list)
CANDIDATE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
]

TEST_PROMPT = "Reply with exactly: OK"


def list_models_for_key(api_key: str, key_label: str) -> list[str]:
    client = genai.Client(api_key=api_key)
    names = []
    print(f"\n--- Models from API (key {key_label}) with generateContent ---")
    try:
        for m in client.models.list():
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" in actions:
                name = m.name.replace("models/", "")
                names.append(name)
                print(f"  {name}")
    except Exception as e:
        print(f"  list failed: {e}")
    return names


def test_generate(client: genai.Client, model: str) -> tuple[str, str]:
    try:
        t0 = time.time()
        r = client.models.generate_content(model=model, contents=TEST_PROMPT)
        ms = int((time.time() - t0) * 1000)
        text = (r.text or "").strip()[:80]
        return "OK", f"{ms}ms {text!r}"
    except Exception as e:
        return "FAIL", str(e)[:120]


def main():
    keys = get_gemini_api_keys()
    if not keys:
        print("No GEMINI_API_KEY in .env")
        return 1

    all_listed: set[str] = set()
    for i, key in enumerate(keys, start=1):
        listed = list_models_for_key(key, str(i))
        all_listed.update(listed)

    # Prefer gemini-3* from list, then candidates, then anything listed
    to_test = []
    for pattern in ("gemini-3", "gemini-2.5", "gemini-2.0"):
        for name in sorted(all_listed):
            if pattern in name and name not in to_test:
                to_test.append(name)
    for c in CANDIDATE_MODELS:
        if c not in to_test:
            to_test.append(c)

    print("\n--- generateContent probe (key #1) ---")
    client = genai.Client(api_key=keys[0])
    results = []
    for model in to_test:
        status, detail = test_generate(client, model)
        results.append((model, status, detail))
        mark = "PASS" if status == "OK" else "FAIL"
        print(f"  [{mark}] {model}: {detail}")
        time.sleep(0.5)

    passed = [m for m, s, _ in results if s == "OK"]
    gemini3 = [m for m in passed if "gemini-3" in m or "gemini-3" in m]
    print("\n=== Summary ===")
    print(f"Keys configured: {len(keys)}")
    print(f"Listed with generateContent: {len(all_listed)}")
    print(f"Probe passed: {len(passed)}")
    if passed:
        print("Working models:", ", ".join(passed))
    if gemini3:
        print("Gemini 3 family working:", ", ".join(gemini3))
    else:
        print("No gemini-3* model passed probe (may not be on AI Studio free tier yet).")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
