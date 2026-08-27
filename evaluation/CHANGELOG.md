# Evaluation Dataset Changelog

## 2026-07-26 (local completion)

- Added agent-reviewed holdouts: `evidence_extraction_holdout_v1.json`, `claim_verification_holdout_v1.json`, `planner_routes_holdout_v1.json`.
- Added `evaluation/REVIEW_NOTES.md` and `scripts/evaluate_holdouts.py`.
- Holdouts are frozen before local completion metric claims.

## 2026-07-26

- Added `evidence_extraction_adversarial_v1.json` before extractor v1.1 changes.
- Corrected seed case `generic-components`: bare generic nouns `Cluster` and `API` are not stable named graph entities and now expect no extraction.
- Corpus dataset annotations were independently machine-reviewed. Suggested changes that required context outside the exact excerpt or collapsed legitimately different predicates were rejected. Human reviewer sign-off remains required.
- Extractor v1.1 was tuned against `evidence_extraction_adversarial_v1.json`; its resulting 1.0 score is a development regression result, not held-out evidence.
- Added `graph_traversal_v1.json` with exact-zero leakage and bounded traversal scenarios.
- Added `graph_corpus_paths_v1.json`, hash-pinned to four tracked Engineering sources, for end-to-end corpus path and ranking evaluation.
- Changed chunking to preserve Markdown paragraph/line boundaries after the corpus graph audit exposed fabricated cross-row edges in flattened dependency maps.
- Added `temporal_conflicts_v1.json` before polarity-conflict detector changes, covering selection, RBAC, value changes, and no-conflict controls.
- Added `temporal_intent_v1.json` with balanced current, historical, change, and non-temporal query classes.
- Added `claim_verification_v1.json` before NLI verifier implementation; this is a balanced development set, not an independent holdout.
- Reused the frozen claim pairs for the end-to-end verified-generation gate; labels were not changed after observing model output.
- Added `planner_routes_v1.json` before five-route planner implementation; it is a balanced development set, not an independent holdout.
- Added `prompt_safety_v1.json` before source-quarantine implementation, balancing direct instruction attacks with benign security discussion.