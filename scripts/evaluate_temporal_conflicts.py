"""Evaluate temporal selection, conflict candidates, and authorization."""
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "temporal-evaluation-only-32-characters"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.database import Base
from backend.models import (
    Chunk,
    Document,
    DocumentVersion,
    Entity,
    EvidenceClaim,
    ExtractionRun,
)
from backend.services.auth import UserContext
from backend.services.conflict_detection import detect_version_conflicts
from backend.services.temporal_retrieval import (
    current_visible_version,
    visible_version_effective_at,
    visible_version_history,
)


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "temporal_conflicts_v1.json"
_ID_NAMESPACE = uuid.UUID("cf224a8f-d01f-4258-9278-db0fa2814bcc")


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    dataset = json.loads(dataset_bytes.decode("utf-8"))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    results = []
    with Session(engine) as db:
        for case in dataset["cases"]:
            results.append(_evaluate_case(db, case))
    engine.dispose()
    return _aggregate(dataset_path, dataset_bytes, results)


def _evaluate_case(db, case):
    document, first, second = _seed_case(db, case)
    user = UserContext(
        user_id=f"temporal-{case['id']}",
        email=f"{case['id']}@example.com",
        department="Engineering",
        roles=case["roles"],
    )
    visible = bool(visible_version_history(db, user, document.id))
    current_number = (
        current_visible_version(db, user, document.id).version_number if visible else None
    )
    effective_number = None
    if visible and case.get("effective_at"):
        effective_number = visible_version_effective_at(
            db,
            user,
            document.id,
            datetime.fromisoformat(case["effective_at"]),
        ).version_number
    conflicts = detect_version_conflicts(db, document.id, first.id, second.id)
    predicted_conflicts = {conflict.conflict_type for conflict in conflicts}
    expected_conflicts = (
        {case["expected_conflict"]} if case["expected_conflict"] else set()
    )
    expected_visible = case.get("expected_visible", True)
    return {
        "id": case["id"],
        "predicted_conflicts": predicted_conflicts,
        "expected_conflicts": expected_conflicts,
        "visible": visible,
        "expected_visible": expected_visible,
        "current_number": current_number,
        "expected_current_number": 2 if expected_visible else None,
        "effective_number": effective_number,
        "expected_effective_number": case.get("expected_effective_version"),
    }


def _seed_case(db, case):
    prefix = case["id"]
    document = Document(
        id=f"{prefix}-document",
        title=prefix,
        department=case["department"],
        classification=case["classification"],
        file_path=f"evaluation/{prefix}.md",
        source_kind="manifest",
        is_active=True,
    )
    first = _version(document, prefix, 1, "a", False)
    second = _version(document, prefix, 2, "b", True)
    db.add_all([document, first, second])
    db.flush()
    subjects = case["subject"] if isinstance(case["subject"], list) else [case["subject"]] * 2
    _claim(db, prefix, first, "from", subjects[0], case["from"])
    _claim(db, prefix, second, "to", subjects[1], case["to"])
    return document, first, second


def _version(document, prefix, number, hash_character, current):
    boundary = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return DocumentVersion(
        id=f"{prefix}-v{number}",
        document=document,
        version_number=number,
        content_hash=hash_character * 64,
        storage_uri=f"file:///tmp/{prefix}-v{number}.md",
        file_type="markdown",
        file_size_bytes=10,
        effective_from=(
            datetime(2025, 1, 1, tzinfo=timezone.utc) if number == 1 else boundary
        ),
        effective_to=boundary if number == 1 else None,
        is_current=current,
    )


def _claim(db, prefix, version, side, subject_name, claim_data):
    entity_id = str(uuid.uuid5(_ID_NAMESPACE, f"entity:{subject_name}"))
    entity = db.get(Entity, entity_id)
    if entity is None:
        entity = Entity(
            id=entity_id,
            entity_type="policy",
            canonical_name=subject_name,
            display_name=subject_name.replace("_", " ").title(),
        )
        db.add(entity)
    chunk_id = f"{prefix}-{side}-chunk"
    chunk = Chunk(
        id=chunk_id,
        document_version=version,
        sequence_index=0,
        text_content=claim_data["text"],
        content_hash=hashlib.sha256(chunk_id.encode()).hexdigest(),
        page_start=1,
        page_end=1,
    )
    run = ExtractionRun(
        id=f"{prefix}-{side}-run",
        document_version_id=version.id,
        extractor_name=f"temporal-{side}",
        extractor_version="1",
        schema_version="1",
        status="succeeded",
    )
    db.add_all([chunk, run])
    db.flush()
    claim_id = f"{prefix}-{side}-claim"
    db.add(
        EvidenceClaim(
            id=claim_id,
            chunk_id=chunk.id,
            extraction_run_id=run.id,
            subject_entity_id=entity.id,
            claim_hash=hashlib.sha256(claim_id.encode()).hexdigest(),
            claim_text=claim_data["text"],
            predicate=claim_data["predicate"],
            object_text=claim_data["object"],
            polarity=claim_data["polarity"],
            confidence=0.9,
        )
    )
    db.flush()


def _aggregate(dataset_path, dataset_bytes, results):
    predicted_total = sum(len(item["predicted_conflicts"]) for item in results)
    expected_total = sum(len(item["expected_conflicts"]) for item in results)
    true_positive = sum(
        len(item["predicted_conflicts"] & item["expected_conflicts"])
        for item in results
    )
    precision = true_positive / predicted_total if predicted_total else 1.0
    recall = true_positive / expected_total if expected_total else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    exact = sum(
        item["predicted_conflicts"] == item["expected_conflicts"]
        and item["visible"] == item["expected_visible"]
        and item["current_number"] == item["expected_current_number"]
        and item["effective_number"] == item["expected_effective_number"]
        for item in results
    )
    failures = [
        {
            "id": item["id"],
            "predicted_conflicts": sorted(item["predicted_conflicts"]),
            "expected_conflicts": sorted(item["expected_conflicts"]),
            "visible": item["visible"],
            "expected_visible": item["expected_visible"],
            "current_number": item["current_number"],
            "expected_current_number": item["expected_current_number"],
            "effective_number": item["effective_number"],
            "expected_effective_number": item["expected_effective_number"],
        }
        for item in results
        if item["predicted_conflicts"] != item["expected_conflicts"]
        or item["visible"] != item["expected_visible"]
        or item["current_number"] != item["expected_current_number"]
        or item["effective_number"] != item["expected_effective_number"]
    ]
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(results),
        "exact_case_accuracy": exact / len(results),
        "conflict_precision": precision,
        "conflict_recall": recall,
        "conflict_f1": f1,
        "failures": failures,
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2, default=list))
    passed = (
        result["exact_case_accuracy"] >= 0.90
        and result["conflict_precision"] >= 0.90
        and result["conflict_recall"] >= 0.90
    )
    print("PASS: temporal conflict benchmark passed." if passed else "FAIL: temporal conflict benchmark failed.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())