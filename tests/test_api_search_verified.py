from backend.routers import search_router


def _candidate(chunk_id="chunk-1"):
    return {
        "chunk_id": chunk_id,
        "doc_id": "doc-1",
        "doc_title": "Leave Policy",
        "department": "HR",
        "text": "Employees receive 20 PTO days.",
        "file_type": "markdown",
        "score": 1.0,
    }


def test_search_response_exposes_additive_verified_claim_metadata(
    client,
    admin_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        search_router,
        "hybrid_search",
        lambda **kwargs: ([_candidate()], "conceptual"),
    )
    monkeypatch.setattr(search_router, "rerank", lambda **kwargs: kwargs["candidates"])
    monkeypatch.setattr(
        search_router,
        "generate_answer",
        lambda **kwargs: {
            "answer": "- Employees receive 20 PTO days. [1]",
            "citations": [
                {
                    "marker": 1,
                    "doc_title": "Leave Policy",
                    "doc_id": "doc-1",
                    "department": "HR",
                    "chunk_text": "Employees receive 20 PTO days.",
                    "file_type": "markdown",
                }
            ],
            "claims": [
                {
                    "id": "claim-1",
                    "text": "Employees receive 20 PTO days.",
                    "status": "supported",
                    "confidence": 0.98,
                    "evidence_ids": ["chunk-1"],
                }
            ],
            "query_plan": {
                "route": "local",
                "subqueries": [],
                "corrective_retrieval_used": False,
            },
        },
    )

    response = client.post(
        "/api/search",
        headers=admin_headers,
        json={"query": "How much PTO is available?"},
    )

    assert response.status_code == 200
    assert response.json()["claims"][0]["status"] == "supported"
    assert response.json()["query_plan"]["route"] == "local"


def test_corrective_retriever_reuses_user_and_department_filter(
    client,
    engineer_headers,
    monkeypatch,
):
    calls = []

    def fake_hybrid_search(**kwargs):
        calls.append(kwargs)
        return ([_candidate(f"chunk-{len(calls)}")], "conceptual")

    def fake_generate_answer(**kwargs):
        corrective = kwargs["corrective_retriever"]("PTO is 20 days")
        assert corrective[0]["chunk_id"] == "chunk-2"
        return {"answer": "Answer [1]", "citations": []}

    monkeypatch.setattr(search_router, "hybrid_search", fake_hybrid_search)
    monkeypatch.setattr(search_router, "rerank", lambda **kwargs: kwargs["candidates"])
    monkeypatch.setattr(search_router, "generate_answer", fake_generate_answer)

    response = client.post(
        "/api/search",
        headers=engineer_headers,
        json={"query": "PTO", "department_filter": "HR"},
    )

    assert response.status_code == 200
    assert len(calls) == 2
    assert calls[0]["user_ctx"].user_id == calls[1]["user_ctx"].user_id
    assert calls[1]["department_filter"] == "HR"


def test_zero_result_search_still_exposes_planned_route(
    client,
    admin_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        search_router,
        "hybrid_search",
        lambda **kwargs: ([], "conceptual"),
    )

    response = client.post(
        "/api/search",
        headers=admin_headers,
        json={"query": "Compare PTO and parental leave policies"},
    )

    assert response.status_code == 200
    plan = response.json()["query_plan"]
    assert plan["route"] == "comparison"
    assert plan["subqueries"] == ["PTO", "parental leave policies"]
    assert plan["corrective_retrieval_used"] is False
    assert plan["trace_ids"] == []
    assert plan["execution_trace_id"]


def test_search_rejects_oversized_query_before_retrieval(
    client,
    admin_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        search_router,
        "hybrid_search",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("retrieval called")),
    )

    response = client.post(
        "/api/search",
        headers=admin_headers,
        json={"query": "x" * 1001},
    )

    assert response.status_code == 422