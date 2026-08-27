"""
Evaluation script — test permission filtering, search quality, and end-to-end flow.
Run: python scripts/evaluate.py
Exit code 1 if any suite fails.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.auth import get_user_context
from backend.services.retriever import hybrid_search
from backend.services.reranker import rerank
from backend.services.query_router import classify_query


def _search(user_id: str, query: str, top_k: int = 10, department_filter: str | None = None):
    user_ctx = get_user_context(user_id)
    results, _ = hybrid_search(query, user_ctx, top_k=top_k, department_filter=department_filter)
    return results


def _norm_doc_title(title: str) -> str:
    """Match manifest titles with optional (PDF) suffix."""
    return title.replace(" (PDF)", "").strip()


def test_permission_filtering():
    print("=" * 60)
    print("TEST 1: Permission Filtering")
    print("=" * 60)

    test_cases = [
        {
            "user_id": "amrutha",
            "query": "What are the salary bands?",
            "should_see": "Compensation Policy",
            "reason": "HR role can see restricted HR docs",
        },
        {
            "user_id": "harshini",
            "query": "What are the salary bands?",
            "should_not_see": "Compensation Policy",
            "reason": "Engineer cannot see restricted HR docs",
        },
        {
            "user_id": "tanvi",
            "query": "What is the sales commission structure?",
            "should_see": "Quota and Commission Guide",
            "reason": "Sales role can see restricted Sales docs",
        },
        {
            "user_id": "harshini",
            "query": "What is the sales commission structure?",
            "should_not_see": "Quota and Commission Guide",
            "reason": "Engineer cannot see restricted Sales docs",
        },
        {
            "user_id": "bhaskar",
            "query": "What are the salary bands?",
            "should_see": "Compensation Policy",
            "reason": "Admin can see all docs",
        },
        {
            "user_id": "arijith",
            "query": "What are the salary bands?",
            "should_not_see": "Compensation Policy",
            "reason": "Employee-only HR cannot see restricted compensation",
        },
    ]

    passed = 0
    for tc in test_cases:
        results = _search(tc["user_id"], tc["query"], top_k=10)
        doc_titles = [r["doc_title"] for r in results]

        if "should_see" in tc:
            found = tc["should_see"] in doc_titles
            status = "PASS" if found else "FAIL"
            print(f"  {status}: {tc['user_id']} searching '{tc['query']}'")
            print(f"         Expected to see: '{tc['should_see']}' -- {tc['reason']}")
            if found:
                passed += 1
        else:
            blocked = tc["should_not_see"] not in doc_titles
            status = "PASS" if blocked else "FAIL"
            print(f"  {status}: {tc['user_id']} searching '{tc['query']}'")
            print(f"         Expected NOT to see: '{tc['should_not_see']}' -- {tc['reason']}")
            if blocked:
                passed += 1
        print()

    print(f"  Result: {passed}/{len(test_cases)} permission tests passed.\n")
    return passed == len(test_cases)


def test_search_relevance():
    print("=" * 60)
    print("TEST 2: Search Relevance")
    print("=" * 60)

    test_cases = [
        {"query": "What is the PTO policy?", "expected_doc": "Employee Handbook", "user_id": "amrutha"},
        {"query": "What caused incident 5023?", "expected_doc": "Incident Report INC-5023", "user_id": "harshini"},
        {"query": "What are our pricing tiers?", "expected_doc": "Pricing Tiers", "user_id": "tanvi"},
        {"query": "What is the tech stack?", "expected_doc": "Architecture Overview", "user_id": "harshini"},
        {"query": "How do I submit a code review?", "expected_doc": "Coding Standards", "user_id": "harshini"},
        {"query": "What is the remote work policy?", "expected_doc": "Remote Work Policy (Detailed)", "user_id": "amrutha"},
        {"query": "How does incident response work?", "expected_doc": "Incident Response Process", "user_id": "harshini"},
        {"query": "What are the company benefits?", "expected_doc": "Benefits Guide", "user_id": "amrutha"},
        {"query": "Salesforce pipeline stages", "expected_doc": "CRM Workflow", "user_id": "tanvi"},
        {"query": "PostgreSQL backup policy", "expected_doc": "Database Operations Guide", "user_id": "harshini"},
        {"query": "How to handle pricing objections?", "expected_doc": "Objection Handling Guide", "user_id": "tanvi"},
        {"query": "What is our security policy for production?", "expected_doc": "Security Policy", "user_id": "harshini"},
    ]

    passed = 0
    for tc in test_cases:
        results = _search(tc["user_id"], tc["query"], top_k=8)
        ranked = rerank(tc["query"], results, top_n=5)

        top_title = ranked[0]["doc_title"] if ranked else "NONE"
        all_titles = [r["doc_title"] for r in ranked[:5]]

        expected = _norm_doc_title(tc["expected_doc"])
        is_top = _norm_doc_title(top_title) == expected
        is_in_top3 = any(_norm_doc_title(t) == expected for t in all_titles[:3])

        if is_top:
            status = "PASS (top-1)"
        elif is_in_top3:
            status = "PASS (top-3)"
        else:
            status = "FAIL"

        if is_top or is_in_top3:
            passed += 1

        print(f"  {status}: '{tc['query']}'")
        print(f"         Expected: '{tc['expected_doc']}' | Got top-5: {all_titles}")
        print()

    print(f"  Result: {passed}/{len(test_cases)} relevance tests passed.\n")
    return passed == len(test_cases)


def test_query_router():
    print("=" * 60)
    print("TEST 3: Query Router")
    print("=" * 60)

    cases = [
        ("What is the PTO policy?", "conceptual"),
        ("error 5023", "specific"),
        ("What is the tech stack?", "specific"),
        ("INC-5023 billing", "specific"),
    ]
    passed = 0
    for query, expected in cases:
        got = classify_query(query)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: '{query}' -> {got} (expected {expected})")
        if ok:
            passed += 1
    print(f"\n  Result: {passed}/{len(cases)} router tests passed.\n")
    return passed == len(cases)


def test_end_to_end_latency():
    print("=" * 60)
    print("TEST 4: End-to-End Latency (Search + Rerank)")
    print("=" * 60)

    user_ctx = get_user_context("amrutha")
    queries = [
        "What is the remote work policy?",
        "How to request PTO?",
        "What are our company values?",
    ]

    latencies = []
    for q in queries:
        start = time.time()
        results, _ = hybrid_search(q, user_ctx, top_k=20)
        ranked = rerank(q, results, top_n=8)
        elapsed_ms = int((time.time() - start) * 1000)
        latencies.append(elapsed_ms)
        print(f"  '{q}' -> {len(ranked)} results in {elapsed_ms} ms")

    avg = sum(latencies) / len(latencies)
    print(f"\n  Average latency: {int(avg)} ms")
    ok = avg < 5000
    status = "PASS" if ok else "SLOW"
    print(f"  {status}: Target < 5000 ms\n")
    return ok


def main():
    print("\nEKIP PoC Evaluation\n")

    r1 = test_permission_filtering()
    r2 = test_search_relevance()
    r3 = test_query_router()
    r4 = test_end_to_end_latency()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Permission Filtering: {'PASS' if r1 else 'FAIL'}")
    print(f"  Search Relevance:     {'PASS' if r2 else 'FAIL'}")
    print(f"  Query Router:         {'PASS' if r3 else 'FAIL'}")
    print(f"  Latency:              {'PASS' if r4 else 'SLOW'}")

    all_pass = r1 and r2 and r3 and r4
    print(f"\n{'All tests passed!' if all_pass else 'Some tests need attention.'}\n")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
