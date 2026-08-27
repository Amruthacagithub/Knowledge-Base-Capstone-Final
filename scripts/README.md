# Scripts

Cross-platform: prefer the `.sh` helpers on macOS/Linux and `.ps1` on Windows. Python scripts work on all OSes via the venv.

| Script | Purpose |
|--------|---------|
| `run_local_trust_stack.sh` / `.ps1` | Docker up → init_db → PDF → ingest → CPU check (`LOCAL_STACK=1`) |
| `run_full_local_verification.sh` / `.ps1` | Full local Trust verification suite |
| `init_db.py` | Create tables and seed 5 demo users |
| `build_pdf_corpus.py` | Generate 10 PDFs and append manifest entries |
| `ingest.py` | Full ingest: parse → chunk → Qdrant + BM25 + PostgreSQL |
| `check_cpu_runtime.py` | Assert enabled local models execute on CPU |
| `smoke_api.py` | Live API smoke (set `SMOKE_API_PASSWORD`) |
| `evaluate.py` | Integration eval: permissions, relevance, router, latency |
| `evaluate_holdouts.py` | Frozen extraction / claim / planner holdouts |
| `evaluate_answer_comparison.py` | Graph vs hybrid retrieval comparison |
| `evaluate_live_verified_generation.py` | Verified-generation faithfulness gate |
| `evaluate_mixed_holdout.py` | 120-question mixed holdout |
| `evaluate_role_comparison.py` | Cross-role document-list leakage check |
| `evaluate_ablations.py` | Component on/off ablations |
| `evaluate_claim_verification.py` | CPU NLI label benchmark |
| `evaluate_verified_generation.py` | Citation faithfulness / unsupported rate |
| `evaluate_query_planner.py` | Five-route planner benchmark |
| `evaluate_prompt_safety.py` | Source instruction-quarantine benchmark |
| `evaluate_evidence_extraction.py` | Entity/relationship/claim F1 |
| `evaluate_graph_traversal.py` / `evaluate_graph_corpus.py` | Graph security + corpus paths |
| `evaluate_temporal_conflicts.py` / `evaluate_temporal_intent.py` | Temporal gates |
| `write_cloudrun_env.py` | Non-secret Cloud Run settings helper |

## Typical order

```bash
python scripts/init_db.py
python scripts/build_pdf_corpus.py
python scripts/ingest.py
python scripts/evaluate.py
```

Or one shot: `./scripts/run_local_trust_stack.sh` / `.\scripts\run_local_trust_stack.ps1`.

## Testing

```bash
python -m pytest tests/ -m "not integration"
python -m pytest tests/ -m integration
```
