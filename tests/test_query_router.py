"""Unit tests for query router."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.query_router import classify_query, alpha_for_query_type


def test_conceptual_query():
    assert classify_query("What is our vacation policy?") == "conceptual"


def test_specific_error_code():
    assert classify_query("What caused error 5023?") == "specific"


def test_specific_incident():
    assert classify_query("INC-5023 root cause") == "specific"


def test_tech_stack_short_query():
    assert classify_query("What is the tech stack?") == "specific"


def test_alpha_weights():
    assert alpha_for_query_type("conceptual") > alpha_for_query_type("specific")


if __name__ == "__main__":
    test_conceptual_query()
    test_specific_error_code()
    test_specific_incident()
    test_tech_stack_short_query()
    test_alpha_weights()
    print("All query_router tests passed.")
