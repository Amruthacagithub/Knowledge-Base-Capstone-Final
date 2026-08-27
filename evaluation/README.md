# Trust-RAG Evaluation Assets

`evidence_extraction_v1.json` is a small synthetic seed benchmark authored for this project. It is not copied from an external repository and contains no production or personal data.

`evidence_extraction_corpus_v1.json` contains 24 exact excerpts from tracked Engineering documents. Each excerpt includes its source path and line reference. The evaluator rejects any case whose text is no longer an exact source substring.

`evidence_extraction_adversarial_v1.json` contains 24 machine-authored variants using the project's Engineering vocabulary but sentence structures that are not exact benchmark excerpts. It was frozen before the next extractor changes. It is a development generalization check, not an independently human-reviewed evaluation set.

The benchmark intentionally includes negative and difficult examples. It must be versioned rather than silently edited after failures. New examples go into a new dataset version or receive a documented changelog entry.

Run:

```powershell
.\venv\Scripts\python.exe scripts\evaluate_evidence_extraction.py
.\venv\Scripts\python.exe scripts\evaluate_evidence_extraction.py --dataset evaluation\evidence_extraction_corpus_v1.json --no-threshold
.\venv\Scripts\python.exe scripts\evaluate_evidence_extraction.py --dataset evaluation\evidence_extraction_adversarial_v1.json --no-threshold
```

Metrics are micro precision, recall, and F1 for:

- typed canonical entities;
- directed typed relationships;
- claim predicate and polarity.

This seed benchmark is a development guard, not sufficient final-project evidence. Phase 3C requires a larger independently reviewed set sampled from the Engineering corpus.

The corpus benchmark was conservatively annotated from explicit text only. It is machine cross-reviewed but still requires human reviewer sign-off before it can be described as independently reviewed in the final report.

`graph_traversal_v1.json` is a 12-scenario synthetic security and correctness matrix. It covers role filtering, hidden starts, cycles, stale evidence, and traversal limits. Its leakage gate is exact zero. It validates traversal invariants, not real-world multi-hop answer quality.

```powershell
.\venv\Scripts\python.exe scripts\evaluate_graph_traversal.py
```

`graph_corpus_paths_v1.json` is a source-hashed benchmark over four tracked Engineering documents. Its evaluator rebuilds the graph from the real parser, chunker, extractor, SQL evidence store, authorization filters, traversal, and ranking code. It contains one explicit two-hop deployment chain, grounded one-hop/fan-out paths, depth control, and no-path controls. Duplicate evidence is collapsed to canonical entity paths for path scoring.

```powershell
.\venv\Scripts\python.exe scripts\evaluate_graph_corpus.py
```

This corpus set validates path extraction and ranking. It does not yet evaluate generated answer quality and it does not replace the synthetic restricted-data leakage matrix.

`temporal_conflicts_v1.json` is a 12-case controlled benchmark for current/effective version selection, restricted-document visibility, unchanged claims, value changes, numeric fallback, and polarity changes. Conflict outputs are candidates for review, never automatic truth decisions.

```powershell
.\venv\Scripts\python.exe scripts\evaluate_temporal_conflicts.py
```

`temporal_intent_v1.json` contains 24 labelled current, historical, change, and non-temporal queries for the deterministic planner pre-classifier.

```powershell
.\venv\Scripts\python.exe scripts\evaluate_temporal_intent.py
```

`claim_verification_v1.json` is a balanced 30-pair development benchmark for `supported`, `conflicting`, and `insufficient` NLI decisions. It was machine-authored during development and requires independent human review before external quality claims.

```powershell
.\venv\Scripts\python.exe scripts\evaluate_claim_verification.py
```

The same frozen pairs drive `evaluate_verified_generation.py`, which measures whether only supported claims reach answer prose with exact citations. It also includes malformed JSON and out-of-range marker controls.

```powershell
.\venv\Scripts\python.exe scripts\evaluate_verified_generation.py
```

`planner_routes_v1.json` is a balanced 50-query development set for deterministic `local`, `global`, `multi_hop`, `temporal`, and `comparison` routing.

```powershell
.\venv\Scripts\python.exe scripts\evaluate_query_planner.py
```

`prompt_safety_v1.json` balances direct instruction overrides and credential-exfiltration commands against benign security-policy discussion. Unsafe source chunks are omitted from prompts and cannot support verified claims.

```powershell
.\venv\Scripts\python.exe scripts\evaluate_prompt_safety.py
```