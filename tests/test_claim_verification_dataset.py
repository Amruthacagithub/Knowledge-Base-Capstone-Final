import json
from collections import Counter

from scripts.evaluate_claim_verification import DATASET_PATH, VERIFICATION_LABELS


def test_claim_verification_dataset_is_balanced_and_well_formed():
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases = dataset["cases"]

    assert len(cases) == 30
    assert Counter(case["expected"] for case in cases) == {
        label: 10 for label in VERIFICATION_LABELS
    }
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(case["evidence"].strip() and case["claim"].strip() for case in cases)