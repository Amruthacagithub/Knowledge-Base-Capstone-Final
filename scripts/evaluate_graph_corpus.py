"""Evaluate the full corpus-to-authorized-graph path pipeline."""
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "graph-corpus-evaluation-only-32-chars"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.database import Base
from backend.models import Chunk, Document, DocumentVersion, Entity
from backend.services.auth import UserContext
from backend.services.chunk_identity import build_chunk_id
from backend.services.chunker import chunk_document_segments
from backend.services.evidence_store import extract_and_store_version
from backend.services.graph_traversal import rank_evidence_paths, traverse_visible_graph
from backend.services.parser import parse_document


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "graph_corpus_paths_v1.json"
_VERSION_NAMESPACE = uuid.UUID("16743516-20b8-416d-844b-90889a5b2a08")


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    source_errors = _validate_sources(dataset["sources"])
    if source_errors:
        return _failed_source_result(dataset_path, dataset_bytes, dataset, source_errors)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        extraction = _build_graph(db, dataset["sources"])
        case_results = [_evaluate_case(db, case) for case in dataset["cases"]]
    engine.dispose()

    return _aggregate_result(dataset_path, dataset_bytes, extraction, case_results)


def _validate_sources(sources: list[dict]) -> list[dict]:
    errors = []
    for source in sources:
        path = ROOT / source["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual != source["sha256"]:
            errors.append(
                {"path": source["path"], "expected": source["sha256"], "actual": actual}
            )
    return errors


def _build_graph(db, sources: list[dict]) -> dict:
    totals = {"documents": 0, "chunks": 0, "entities": 0, "claims": 0, "relationships": 0}
    for source in sources:
        source_path = ROOT / source["path"]
        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        document_id = str(uuid.uuid5(_VERSION_NAMESPACE, source["path"]))
        version_id = str(uuid.uuid5(_VERSION_NAMESPACE, f"{source['path']}:{source_hash}"))
        document = Document(
            id=document_id,
            title=source_path.stem.replace("_", " ").title(),
            department="Engineering",
            classification="public",
            file_path=source["path"],
            source_kind="manifest",
            is_active=True,
        )
        version = DocumentVersion(
            id=version_id,
            document=document,
            version_number=1,
            content_hash=source_hash,
            storage_uri=source_path.resolve().as_uri(),
            file_type="markdown",
            file_size_bytes=source_path.stat().st_size,
            authority_level=50,
            is_current=True,
        )
        chunks = chunk_document_segments(parse_document(source_path))
        db.add_all([document, version])
        for index, chunk_data in enumerate(chunks):
            text = chunk_data["text"]
            db.add(
                Chunk(
                    id=build_chunk_id(version_id, index),
                    document_version=version,
                    sequence_index=index,
                    text_content=text,
                    content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    page_start=chunk_data["page_start"],
                    page_end=chunk_data["page_end"],
                )
            )
        db.flush()
        extracted = extract_and_store_version(db, version_id)
        totals["documents"] += 1
        totals["chunks"] += len(chunks)
        for name in ("entities", "claims", "relationships"):
            totals[name] += extracted[name]
    db.flush()
    return totals


def _evaluate_case(db, case: dict) -> dict:
    entity_type, canonical_name = case["start"]
    start = (
        db.query(Entity)
        .filter_by(entity_type=entity_type, canonical_name=canonical_name)
        .one_or_none()
    )
    if start is None:
        return _case_result(case, set(), None, {"missing_start": canonical_name})

    user = UserContext(
        user_id=f"corpus-{case['id']}",
        email=f"{case['id']}@example.com",
        department="Engineering",
        roles=case["roles"],
    )
    traversal = traverse_visible_graph(
        db,
        user,
        str(start.id),
        max_depth=case["max_depth"],
        max_paths=case["max_paths"],
    )
    names = {str(entity.id): str(entity.canonical_name) for entity in db.query(Entity).all()}
    predicted_paths = {
        tuple(names[entity_id] for entity_id in path.entity_ids)
        for path in traversal.paths
    }
    ranked = rank_evidence_paths(traversal.paths, case["query"])
    top_path = (
        tuple(names[entity_id] for entity_id in ranked[0].path.entity_ids)
        if ranked
        else None
    )
    return _case_result(case, predicted_paths, top_path, None)


def _case_result(case, predicted_paths, top_path, error):
    expected_paths = {tuple(path) for path in case["expected_paths"]}
    forbidden = set(case["forbidden_entities"])
    leaked = {
        entity_id
        for path in predicted_paths
        for entity_id in path
        if entity_id in forbidden
    }
    expected_top = tuple(case["expected_top_path"]) if case.get("expected_top_path") else None
    return {
        "id": case["id"],
        "predicted_paths": predicted_paths,
        "expected_paths": expected_paths,
        "top_path": top_path,
        "expected_top_path": expected_top,
        "leaked": leaked,
        "error": error,
    }


def _aggregate_result(dataset_path, dataset_bytes, extraction, case_results):
    predicted_total = sum(len(item["predicted_paths"]) for item in case_results)
    expected_total = sum(len(item["expected_paths"]) for item in case_results)
    true_positive = sum(
        len(item["predicted_paths"] & item["expected_paths"])
        for item in case_results
    )
    precision = true_positive / predicted_total if predicted_total else 1.0
    recall = true_positive / expected_total if expected_total else 1.0
    path_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    ranked_cases = [item for item in case_results if item["expected_top_path"] is not None]
    top_accuracy = (
        sum(item["top_path"] == item["expected_top_path"] for item in ranked_cases)
        / len(ranked_cases)
        if ranked_cases
        else 1.0
    )
    exact_cases = sum(
        item["predicted_paths"] == item["expected_paths"]
        and not item["leaked"]
        and item["error"] is None
        for item in case_results
    )
    failures = [
        {
            "id": item["id"],
            "missing_paths": sorted(item["expected_paths"] - item["predicted_paths"]),
            "unexpected_paths": sorted(item["predicted_paths"] - item["expected_paths"]),
            "expected_top_path": item["expected_top_path"],
            "actual_top_path": item["top_path"],
            "leaked_entities": sorted(item["leaked"]),
            "error": item["error"],
        }
        for item in case_results
        if item["predicted_paths"] != item["expected_paths"]
        or item["leaked"]
        or item["error"] is not None
        or (
            item["expected_top_path"] is not None
            and item["top_path"] != item["expected_top_path"]
        )
    ]
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(case_results),
        "source_errors": [],
        "extraction": extraction,
        "exact_case_accuracy": exact_cases / len(case_results),
        "path_precision": precision,
        "path_recall": recall,
        "path_f1": path_f1,
        "top_path_accuracy": top_accuracy,
        "forbidden_entity_leakage": sum(len(item["leaked"]) for item in case_results),
        "failures": failures,
    }


def _failed_source_result(dataset_path, dataset_bytes, dataset, errors):
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(dataset["cases"]),
        "source_errors": errors,
        "failures": [{"id": "source-validation", "errors": errors}],
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2, default=list))
    passed = (
        not result["source_errors"]
        and result["exact_case_accuracy"] >= 0.90
        and result["path_f1"] >= 0.90
        and result["top_path_accuracy"] >= 0.80
        and result["forbidden_entity_leakage"] == 0
    )
    print("PASS: corpus graph path benchmark passed." if passed else "FAIL: corpus graph path benchmark failed.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())