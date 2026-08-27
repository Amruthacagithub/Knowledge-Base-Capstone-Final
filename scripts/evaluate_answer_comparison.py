"""Compare hybrid-only vs hybrid-plus-graph retrieval on frozen cases."""
import hashlib
import json
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "answer-comparison-eval-only-32-chars")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.database import Base
from backend.models import Chunk, Document, DocumentVersion, Entity
from backend.services.auth import UserContext
from backend.services.document_access import user_can_access_document
from backend.services.graph_retrieval import retrieve_graph_candidates
from backend.services.planned_retrieval import merge_authorized_candidates, retrieve_for_plan
from backend.services.query_planner import plan_query
from scripts.evaluate_graph_corpus import _build_graph


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "answer_comparison_v1.json"
_VERSION_NAMESPACE = uuid.UUID("16743516-20b8-416d-844b-90889a5b2a08")


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    sources = [
        {
            "path": source["path"],
            "sha256": hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
        }
        for source in dataset["sources"]
    ]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    case_results = []
    with Session(engine) as db:
        _build_graph(db, sources)
        _normalize_document_metadata(db)
        documents = {doc.file_path: doc for doc in db.query(Document).all()}
        chunks_by_doc = _chunks_by_document(db)
        for case in dataset["cases"]:
            db_entities = {
                str(entity.id): str(entity.canonical_name)
                for entity in db.query(Entity).all()
            }
            case_results.append(
                _evaluate_case(db, case, documents, chunks_by_doc, db_entities)
            )
    engine.dispose()
    return _aggregate(dataset_path, dataset_bytes, case_results)


def _chunks_by_document(db) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for chunk, version, document in (
        db.query(Chunk, DocumentVersion, Document)
        .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .all()
    ):
        grouped.setdefault(document.file_path, []).append(
            {
                "chunk_id": str(chunk.id),
                "doc_id": str(document.id),
                "doc_title": document.title,
                "department": document.department,
                "text": str(chunk.text_content),
                "file_type": "markdown",
                "score": 1.0,
            }
        )
    return grouped


def _evaluate_case(db, case, documents, chunks_by_doc, db_entities):
    user = UserContext(
        user_id=f"compare-{case['id']}",
        email=f"{case['id']}@example.com",
        department=case["department"],
        roles=case["roles"],
    )
    plan = plan_query(case["query"])
    assert plan.route == case["route"], (
        f"{case['id']} route mismatch: {plan.route} != {case['route']}"
    )

    def hybrid_search(**kwargs):
        return _keyword_search(
            kwargs["query"],
            kwargs["user_ctx"],
            documents,
            chunks_by_doc,
            kwargs.get("department_filter"),
        )

    start = time.perf_counter()
    hybrid_candidates, _ = retrieve_for_plan(
        case["query"],
        user,
        _department_filter(case),
        plan,
        search_fn=hybrid_search,
    )
    hybrid_ms = (time.perf_counter() - start) * 1000

    start = time.perf_counter()
    graph_candidates, _ = retrieve_for_plan(
        case["query"],
        user,
        _department_filter(case),
        plan,
        search_fn=hybrid_search,
    )
    if plan.route == "multi_hop":
        graph_candidates = merge_authorized_candidates(
            graph_candidates,
            list(retrieve_graph_candidates(db, user, case["query"]).candidates),
        )
    graph_ms = (time.perf_counter() - start) * 1000

    hybrid_metrics = _score_candidates(hybrid_candidates, case, documents, db_entities)
    graph_metrics = _score_candidates(graph_candidates, case, documents, db_entities)
    return {
        "id": case["id"],
        "route": case["route"],
        "hybrid_only": hybrid_metrics,
        "hybrid_plus_graph": graph_metrics,
        "latency_ms": {"hybrid_only": hybrid_ms, "hybrid_plus_graph": graph_ms},
        "graph_path_gain": graph_metrics["path_recall"] - hybrid_metrics["path_recall"],
    }


def _normalize_document_metadata(db) -> None:
    for document in db.query(Document).all():
        path = document.file_path.replace("\\", "/")
        if "/hr/" in path:
            document.department = "HR"
        elif "/sales/" in path:
            document.department = "Sales"
        else:
            document.department = "Engineering"
        if "internal_api_keys" in path:
            document.classification = "restricted"
    db.flush()


def _department_filter(case: dict) -> str | None:
    if case["route"] in {"comparison", "global", "multi_hop"}:
        return None
    return case.get("department")


def _keyword_search(query, user_ctx, documents, chunks_by_doc, department_filter):
    import re

    tokens = {
        token.casefold()
        for token in re.findall(r"[a-z0-9]+", query.casefold())
        if len(token) > 2
    }
    results = []
    for file_path, doc in documents.items():
        if department_filter and doc.department != department_filter:
            continue
        if not user_can_access_document(doc, user_ctx):
            continue
        for chunk in chunks_by_doc.get(file_path, []):
            text = chunk["text"].casefold()
            overlap = sum(1 for token in tokens if token in text)
            if overlap:
                results.append({**chunk, "score": float(overlap)})
    results.sort(key=lambda item: (-item["score"], item["chunk_id"]))
    return results[:12], "keyword"


def _score_candidates(candidates, case, documents, db_entities=None):
    doc_paths = set()
    entity_ids = set()
    for candidate in candidates:
        doc = documents.get(_doc_path_for_candidate(candidate, documents))
        if doc is not None:
            doc_paths.add(doc.file_path)
        for entity_id in candidate.get("graph_entity_ids", []) or []:
            entity_ids.add(str(entity_id))
        text = candidate.get("text", "").casefold()
        for entity in case.get("forbidden_entities", []):
            if entity.casefold() in text:
                entity_ids.add(entity)

    expected_docs = set(case.get("expected_doc_paths", []))
    forbidden_docs = set(case.get("forbidden_doc_paths", []))
    expected_entities = set(case.get("expected_entities", []))

    entity_names = _entity_names_from_candidates(candidates, expected_entities, db_entities)
    path_hits = sum(1 for entity in expected_entities if entity in entity_names)
    path_recall = path_hits / len(expected_entities) if expected_entities else 1.0
    doc_hit = bool(expected_docs & doc_paths) if expected_docs else not case["must_abstain"]
    if case["must_abstain"]:
        doc_hit = not doc_paths
    leakage_docs = forbidden_docs & doc_paths
    leakage_entities = set(case.get("forbidden_entities", [])) & entity_names
    return {
        "doc_recall": int(doc_hit),
        "path_recall": path_recall,
        "forbidden_doc_leakage": len(leakage_docs),
        "forbidden_entity_leakage": len(leakage_entities),
        "candidate_count": len(candidates),
    }


def _entity_names_from_candidates(candidates, expected_entities, db_entities=None):
    names = set()
    db_entities = db_entities or {}
    for candidate in candidates:
        for entity_id in candidate.get("graph_entity_ids", []) or []:
            canonical = db_entities.get(str(entity_id))
            if canonical:
                names.add(canonical)
        text = candidate.get("text", "").casefold()
        for entity in expected_entities:
            readable = entity.casefold().replace("_", " ")
            if readable in text or entity.casefold() in text:
                names.add(entity)
    return names


def _doc_path_for_candidate(candidate, documents):
    doc_id = candidate.get("doc_id")
    for path, document in documents.items():
        if str(document.id) == str(doc_id):
            return path
    return None


def _aggregate(dataset_path, dataset_bytes, case_results):
    multi_hop = [item for item in case_results if item["route"] == "multi_hop"]
    denied = [
        item
        for item in case_results
        if item["hybrid_only"]["forbidden_doc_leakage"]
        or item["hybrid_plus_graph"]["forbidden_doc_leakage"]
        or item["hybrid_only"]["forbidden_entity_leakage"]
        or item["hybrid_plus_graph"]["forbidden_entity_leakage"]
    ]
    hybrid_latencies = [item["latency_ms"]["hybrid_only"] for item in case_results]
    graph_latencies = [item["latency_ms"]["hybrid_plus_graph"] for item in case_results]
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(case_results),
        "doc_recall": statistics.mean(
            item["hybrid_plus_graph"]["doc_recall"] for item in case_results
        ),
        "forbidden_leakage": len(denied),
        "multi_hop_path_gain": statistics.mean(
            item["graph_path_gain"] for item in multi_hop
        )
        if multi_hop
        else 0.0,
        "latency_ms": {
            "hybrid_p50": statistics.median(hybrid_latencies),
            "hybrid_p95": sorted(hybrid_latencies)[max(0, int(len(hybrid_latencies) * 0.95) - 1)],
            "graph_p50": statistics.median(graph_latencies),
            "graph_p95": sorted(graph_latencies)[max(0, int(len(graph_latencies) * 0.95) - 1)],
        },
        "cases_detail": case_results,
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = result["forbidden_leakage"] == 0 and result["doc_recall"] >= 0.70
    print("PASS: answer comparison benchmark passed." if passed else "FAIL: answer comparison benchmark failed.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
