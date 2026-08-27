# Evaluation and Verification

All commands below run from the project root after dependencies are installed.

## Current verification

The checked-in non-integration backend test suite, frontend lint, frontend unit tests, and production frontend build all pass on the current `trust-rag` worktree.

```powershell
.\venv\Scripts\python.exe -m pytest tests -m "not integration" -q
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
```

For local API/browser smoke checks, start the Docker stack, API, and frontend as described in the root README, then run:

```powershell
$env:SMOKE_API_PASSWORD = "your-bootstrap-password"
$env:SMOKE_TRUST_CHECKS = "true"
.\venv\Scripts\python.exe scripts\smoke_api.py

$env:PLAYWRIGHT_RUN_E2E = "1"
npm --prefix frontend run test:e2e
```

## Reproducible benchmark results

| Dataset / evaluator | Result |
|---|---:|
| Extraction holdout | entity, relationship, and claim F1: 1.000 |
| Claim-verification holdout | accuracy: 0.875; macro F1: 0.878 |
| Query-planner holdout | accuracy and macro F1: 1.000 |
| 120-case mixed holdout | route accuracy: 1.000; document recall: 1.000; forbidden leakage: 0 |
| Answer comparison | document recall: 0.917; graph path gain: 0.0 |
| Role comparison | 8 checks; leakage count: 0 |

Run the checked-in evaluators with:

```powershell
.\venv\Scripts\python.exe scripts\evaluate_holdouts.py
.\venv\Scripts\python.exe scripts\evaluate_answer_comparison.py
.\venv\Scripts\python.exe scripts\evaluate_live_verified_generation.py
.\venv\Scripts\python.exe scripts\evaluate_mixed_holdout.py
.\venv\Scripts\python.exe scripts\evaluate_ablations.py
.\venv\Scripts\python.exe scripts\evaluate_role_comparison.py
```

## Limitations

- Evaluation data and review are agent-authored/reviewed, not an independent external study.
- The CPU NLI verifier has known false-insufficient and false-conflict outcomes; verified mode can abstain on otherwise plausible answers.
- Graph retrieval adds traceability but showed no path-recall gain over hybrid retrieval in the checked-in 12-case comparison.
- The project does not claim production readiness: enterprise OIDC, distributed rate limiting, automated credential rotation, and an external security review are outside scope.
