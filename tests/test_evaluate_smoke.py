import pytest

from backend.services.auth import get_user_context
from backend.services.retriever import hybrid_search


@pytest.mark.integration
def test_permission_smoke_engineer_salary():
    try:
        user = get_user_context("harshini")
        results, _ = hybrid_search("What are the salary bands?", user, top_k=8)
    except Exception as e:
        if "Connection" in str(e) or "refused" in str(e).lower():
            pytest.skip("Qdrant not available")
        raise
    titles = [r["doc_title"] for r in results]
    assert "Compensation Policy" not in titles
