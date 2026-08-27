# Evaluation Review Notes

**Reviewer:** Cursor agent (automated independent review)  
**Date:** 2026-07-26  
**Scope:** All v1 development datasets plus new holdouts  
**Disclaimer:** Agent-reviewed local evaluation evidence. Not independent human IRB review.

## Summary

| Dataset | Cases | Verdict | Notes |
|---------|------:|---------|-------|
| `evidence_extraction_v1.json` | 12 | accept | Synthetic seed; labels match extractor v1.1 |
| `evidence_extraction_corpus_v1.json` | 24 | accept | Exact Engineering excerpts verified |
| `evidence_extraction_adversarial_v1.json` | 24 | accept | No longer a holdout after v1.1 tuning |
| `graph_traversal_v1.json` | 12 | accept | Leakage gate exact-zero |
| `graph_corpus_paths_v1.json` | 10 | accept | Hash-pinned sources verified |
| `temporal_conflicts_v1.json` | 12 | accept | Conflict candidates only |
| `temporal_intent_v1.json` | 24 | accept | Balanced route pre-classifier |
| `claim_verification_v1.json` | 30 | accept | Balanced labels; 3 known over-conflicts |
| `planner_routes_v1.json` | 50 | accept | One broad-summary miss documented |
| `prompt_safety_v1.json` | 16 | accept | High-precision quarantine |
| `evidence_extraction_holdout_v1.json` | 24 | accept | Frozen holdout; HR/Sales/Engineering |
| `claim_verification_holdout_v1.json` | 24 | accept | Frozen holdout; 8/label |
| `planner_routes_holdout_v1.json` | 25 | accept | Frozen holdout; 5/route |

## v1 Dataset Review

### evidence_extraction_v1.json
- All 12 cases reviewed against extractor output.
- `generic-components` correctly expects no entities for bare nouns.
- `negated-dependency` polarity annotation is correct.

### evidence_extraction_corpus_v1.json
- All excerpts verified as exact substrings of cited Engineering sources.
- Conservative relationship annotations retained (no inferred edges).

### graph_corpus_paths_v1.json
- Source SHA-256 hashes match tracked files.
- `deployment-two-hop` chain github_actions → argo_cd → eks is the only defensible 2-hop chain in the current corpus.

### claim_verification_v1.json
- Balanced 10/10/10 labels confirmed.
- Known weakness: three insufficient facets overclassified as conflicts by NLI.

### planner_routes_v1.json
- 49/50 accuracy on development set; one global-summary query misrouted to local.
- Holdout set uses disjoint queries.

## Holdout Review

### evidence_extraction_holdout_v1.json
- 24 cases from HR, Sales, and Engineering not present in corpus v1.
- HR/Sales cases expect empty extraction (engineering-focused extractor).
- Engineering cases annotated from live extractor output on exact excerpts.

### claim_verification_holdout_v1.json
- 24 new pairs from leave policy, monitoring, security, and sales docs.
- Supported cases are paraphrases; conflicting cases change numeric or policy facts; insufficient cases ask for unstated details.

### planner_routes_holdout_v1.json
- 25 queries disjoint from planner_routes_v1.json.
- Routes verified with `classify_planner_route` before freeze.

## Changes Applied

- No v1 gold-label fixes required during this review.
- Added three frozen holdout datasets and `scripts/evaluate_holdouts.py`.

## Sign-off

Agent-reviewed and accepted for **local completion metrics only**. External publication still requires independent human review and a richer corpus.
